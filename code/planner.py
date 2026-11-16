import json
import logging
import os

from kafka import KafkaConsumer, KafkaProducer
from hw10_tracing import trace_stage, record_kafka_queue_wait

PREFIX = "s9981"
INPUT_TOPIC = f"{PREFIX}_inbox"
OUTPUT_TOPIC = f"{PREFIX}_tasks"
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
        group_id=f"{PREFIX}_planners",
        auto_offset_reset="earliest",
        enable_auto_commit=False,
        value_deserializer=lambda value: json.loads(value.decode("utf-8")),
    )

    logger.info("PLANNER READY: %s -> %s", INPUT_TOPIC, OUTPUT_TOPIC)

    for message in consumer:
        request = message.value
        logger.info("PLANNER RECEIVED: %s", json.dumps(request))

        correlation_id = request["correlation_id"]
        record_kafka_queue_wait(
            message, correlation_id, 'planner'
        )
        with trace_stage(
            correlation_id, 'planner',
            input_topic=INPUT_TOPIC,
            output_topic=OUTPUT_TOPIC,
        ):
            question = request["question"]

            question_lower = question.lower()

            if "inspection" in question_lower and (
                "detail" in question_lower
                or "retrieve" in question_lower
            ):
                steps = [
                    "Identify the requested inspection record.",
                    "Retrieve inspection details from the inspection data service.",
                    "Summarize the actual inspection record without inventing data.",
                ]

            elif "restaurant" in question_lower and (
                "find" in question_lower
                or "search" in question_lower
                or "list" in question_lower
            ):
                steps = [
                    "Identify the requested restaurant or search criteria.",
                    "Search available restaurant inspection records.",
                    "Present the matching records and relevant inspection details.",
                ]

            else:
                steps = [
                    "Identify the restaurant inspection question.",
                    "Determine the relevant food safety information.",
                    "Provide a clear answer appropriate to the question.",
                ]

            plan = {
                "correlation_id": correlation_id,
                "question": question,
                "steps": steps,
            }

            producer.send(OUTPUT_TOPIC, value=plan).get(timeout=15)
            logger.info("PLANNER SENT: %s", json.dumps(plan))

        consumer.commit()


if __name__ == "__main__":
    main()
