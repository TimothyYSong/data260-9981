import json
import logging
import os

from kafka import KafkaConsumer, KafkaProducer
from hw10_tracing import trace_stage, record_kafka_queue_wait

PREFIX = "s9981"
INPUT_TOPIC = f"{PREFIX}_drafts"
OUTPUT_TOPIC = f"{PREFIX}_final"
BOOTSTRAP_SERVERS = os.getenv(
    "KAFKA_BOOTSTRAP_SERVERS", "localhost:9092"
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
)
logging.getLogger("kafka").setLevel(logging.WARNING)
logger = logging.getLogger(__name__)


def main():
    producer = KafkaProducer(
        bootstrap_servers=BOOTSTRAP_SERVERS,
        value_serializer=lambda value: json.dumps(value).encode("utf-8"),
    )

    consumer = KafkaConsumer(
        INPUT_TOPIC,
        bootstrap_servers=BOOTSTRAP_SERVERS,
        group_id=f"{PREFIX}_reviewers",
        auto_offset_reset="earliest",
        enable_auto_commit=False,
        value_deserializer=lambda value: json.loads(value.decode("utf-8")),
    )

    logger.info("REVIEWER READY: %s -> %s", INPUT_TOPIC, OUTPUT_TOPIC)

    for message in consumer:
        draft_message = message.value
        logger.info("REVIEWER RECEIVED: %s", json.dumps(draft_message))

        correlation_id = draft_message["correlation_id"]
        record_kafka_queue_wait(
            message, correlation_id, 'reviewer'
        )
        with trace_stage(
            correlation_id, 'reviewer',
            input_topic=INPUT_TOPIC,
            output_topic=OUTPUT_TOPIC,
        ):
            draft = draft_message["draft"]


            question = draft_message.get("question", "")
            plan = draft_message.get("plan", [])

            if not isinstance(draft, str) or not draft.strip():
                status = "rejected"
                answer = "The draft was empty or invalid."
                review_reason = "Empty or invalid Writer draft."

            elif (
                "inspection" in question.lower()
                and any(
                    word in question.lower()
                    for word in ("retrieve", "detail", "show", "get")
                )
            ):
                if (
                    "inspection details for id" in draft.lower()
                    or "was not found" in draft.lower()
                ):
                    status = "approved"
                    answer = draft
                    review_reason = (
                        "Draft addresses the requested inspection record."
                    )
                else:
                    status = "rejected"
                    answer = draft
                    review_reason = (
                        "Draft does not provide requested inspection details."
                    )

            else:
                status = "approved"
                answer = draft
                review_reason = (
                    "Draft is nonempty and passes basic relevance checks."
                )

            final_message = {
                "correlation_id": correlation_id,
                "question": question,
                "plan": plan,
                "draft": draft,
                "status": status,
                "answer": answer,
                "review_reason": review_reason,
            }


            producer.send(OUTPUT_TOPIC, value=final_message).get(timeout=15)
            logger.info("REVIEWER SENT: %s", json.dumps(final_message))

        consumer.commit()


if __name__ == "__main__":
    main()
