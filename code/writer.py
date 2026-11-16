import json
import logging
import os
import time

from kafka import KafkaConsumer, KafkaProducer
from hw10_tracing import trace_stage, record_kafka_queue_wait
import re
from tool_executor import execute_tool

PREFIX = "s9981"
INPUT_TOPIC = f"{PREFIX}_tasks"
OUTPUT_TOPIC = f"{PREFIX}_drafts"
DEAD_LETTER_TOPIC = f"{PREFIX}_dead_letter"

BOOTSTRAP_SERVERS = os.getenv(
    "KAFKA_BOOTSTRAP_SERVERS", "localhost:9092"
)

MAX_ATTEMPTS = 3

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
)
logging.getLogger("kafka").setLevel(logging.WARNING)
logger = logging.getLogger(__name__)

# Part 3.I: In-memory duplicate detection.
processed_ids = set()



def create_draft(task):
    correlation_id = task["correlation_id"]
    question = task["question"]
    steps = task["steps"]

    if not isinstance(question, str) or not question.strip():
        raise ValueError("Invalid question")

    if not isinstance(steps, list) or not steps:
        raise ValueError("Invalid steps")

    if not all(
        isinstance(step, str) and step.strip()
        for step in steps
    ):
        raise ValueError("Invalid plan step")

    # Preserve HW8's optional processing delay.
    delay = float(os.getenv("WRITER_PROCESSING_DELAY", "0"))

    if delay > 0:
        time.sleep(delay)

    question_lower = question.lower()

    # Retrieve inspection records by numeric ID.
    match = re.search(
        r"\binspection\s*(?:id\s*)?#?\s*(\d+)\b",
        question_lower,
    )

    if match and any(
        word in question_lower
        for word in ("retrieve", "detail", "show", "get")
    ):
        inspection_id = int(match.group(1))

        tool_result = json.loads(
            execute_tool(
                "inspection_detail",
                {"inspection_id": inspection_id},
            )
        )

        if tool_result.get("ok"):
            data = tool_result["data"]

            answer = (
                f"Inspection details for ID {inspection_id}:\n"
                f"- Inspection Code: {data.get('inspection_code')}\n"
                f"- Restaurant: {data.get('restaurant_name')}\n"
                f"- Address: {data.get('restaurant_address')}\n"
                f"- Violation Count: {data.get('violation_count')}\n"
                f"- Restaurant ID: {data.get('restaurant_id')}\n"
                f"- Created At: {data.get('created_at')}\n"
                f"- Updated At: {data.get('updated_at')}"
            )
        else:
            error = tool_result.get("error", "Unknown error")

            if "not found" in error.lower():
                answer = (
                    f"Inspection {inspection_id} was not found "
                    "in the available records."
                )
            else:
                # Preserve retry/dead-letter behavior for
                # actual inspection retrieval failures.
                raise ValueError(
                    f"Inspection retrieval failed: {error}"
                )

    elif "checklist" in question_lower:
        answer = (
            "A restaurant inspection checklist should cover "
            "food storage temperatures, employee hygiene, "
            "sanitation, cross-contamination prevention, "
            "pest control, and equipment cleanliness."
        )

    else:
        answer = (
            "The requested task is not yet supported by "
            "the Kafka Writer's available retrieval logic."
        )

    return {
        "correlation_id": correlation_id,
        "question": question,
        "plan": steps,
        "draft": answer,
    }



def main():
    producer = KafkaProducer(
        bootstrap_servers=BOOTSTRAP_SERVERS,
        value_serializer=lambda value: json.dumps(value).encode("utf-8"),
    )

    consumer = KafkaConsumer(
        INPUT_TOPIC,
        bootstrap_servers=BOOTSTRAP_SERVERS,
        group_id=f"{PREFIX}_writers",
        auto_offset_reset="earliest",
        enable_auto_commit=False,
        value_deserializer=lambda value: json.loads(
            value.decode("utf-8")
        ),
    )

    logger.info(
        "WRITER READY: %s -> %s",
        INPUT_TOPIC,
        OUTPUT_TOPIC,
    )

    for message in consumer:
        task = message.value

        logger.info(
            "WRITER RECEIVED: %s",
            json.dumps(task),
        )

        # Part 3.IV: Record partition and processing order.
        if isinstance(task, dict) and "sequence" in task:
            logger.info(
                "WRITER ORDER: sequence=%s, partition=%s, "
                "offset=%s, entity_id=%s, pid=%s",
                task["sequence"],
                message.partition,
                message.offset,
                task.get("entity_id"),
                os.getpid(),
            )

        correlation_id = (
            task.get("correlation_id", "missing")
            if isinstance(task, dict)
            else "missing"
        )

        record_kafka_queue_wait(
            message, correlation_id, 'writer'
        )

        # Part 3.I: Skip previously processed tasks.
        if correlation_id in processed_ids:
            logger.info(
                "WRITER DUPLICATE SKIPPED: correlation_id=%s",
                correlation_id,
            )
            consumer.commit()
            continue

        # Part 3.III: Retry failed processing up to three times.
        for attempt in range(1, MAX_ATTEMPTS + 1):
            try:
                with trace_stage(
                    correlation_id, 'writer',
                    attempt=attempt,
                    input_topic=INPUT_TOPIC,
                    output_topic=OUTPUT_TOPIC,
                ):
                    draft = create_draft(task)

                    producer.send(
                        OUTPUT_TOPIC,
                        value=draft,
                    ).get(timeout=15)

                    logger.info(
                        "WRITER SENT: %s",
                        json.dumps(draft),
                    )

                    processed_ids.add(correlation_id)
                    break

            except (KeyError, TypeError, ValueError) as error:
                logger.warning(
                    "WRITER RETRY: correlation_id=%s, "
                    "attempt=%s/%s, error=%s",
                    correlation_id,
                    attempt,
                    MAX_ATTEMPTS,
                    error,
                )

                if attempt == MAX_ATTEMPTS:
                    dead_letter = {
                        "correlation_id": correlation_id,
                        "original_message": task,
                        "error": str(error),
                        "attempts": MAX_ATTEMPTS,
                        "source_topic": INPUT_TOPIC,
                    }

                    with trace_stage(
                        correlation_id, 'dead_letter_publish',
                        output_topic=DEAD_LETTER_TOPIC,
                    ):
                        producer.send(
                            DEAD_LETTER_TOPIC,
                            value=dead_letter,
                        ).get(timeout=15)

                    logger.error(
                        "WRITER DEAD LETTER SENT: %s",
                        json.dumps(dead_letter),
                    )

        # Commit only after successful output or dead-letter delivery.
        consumer.commit()

        logger.info(
            "WRITER OFFSET COMMITTED: "
            "correlation_id=%s, offset=%s",
            correlation_id,
            message.offset,
        )


if __name__ == "__main__":
    main()