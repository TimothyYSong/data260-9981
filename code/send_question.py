import json
import logging
import os
from uuid import uuid4

from kafka import KafkaProducer

PREFIX = "s9981"
OUTPUT_TOPIC = f"{PREFIX}_inbox"
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

    message = {
        "correlation_id": str(uuid4()),
        "question": "What should a restaurant inspection checklist include?",
    }

    producer.send(OUTPUT_TOPIC, value=message).get(timeout=15)
    logger.info("QUESTION SENT to %s: %s", OUTPUT_TOPIC, json.dumps(message))

    producer.close()


if __name__ == "__main__":
    main()
