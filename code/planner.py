import json
import logging
import os

from kafka import KafkaConsumer, KafkaProducer

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
        question = request["question"]

        plan = {
            "correlation_id": correlation_id,
            "question": question,
            "steps": [
                "Identify the restaurant inspection objective.",
                "List relevant food safety inspection checks.",
                "Organize the checks into a clear answer.",
            ],
        }

        producer.send(OUTPUT_TOPIC, value=plan).get(timeout=15)
        logger.info("PLANNER SENT: %s", json.dumps(plan))

        consumer.commit()


if __name__ == "__main__":
    main()
