import json
import logging
import os

from kafka import KafkaConsumer, KafkaProducer

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
        draft = draft_message["draft"]

        if isinstance(draft, str) and draft.strip():
            status = "approved"
            answer = draft
        else:
            status = "rejected"
            answer = "The draft was empty or invalid."

        final_message = {
            "correlation_id": correlation_id,
            "status": status,
            "answer": answer,
        }

        producer.send(OUTPUT_TOPIC, value=final_message).get(timeout=15)
        logger.info("REVIEWER SENT: %s", json.dumps(final_message))

        consumer.commit()


if __name__ == "__main__":
    main()
