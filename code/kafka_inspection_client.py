import json
import logging
import os
import time
from uuid import uuid4

from kafka import KafkaConsumer, KafkaProducer

PREFIX = "s9981"
REQUEST_TOPIC = f"{PREFIX}_entity_requests"
RESPONSE_TOPIC = f"{PREFIX}_entity_responses"
BOOTSTRAP_SERVERS = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")

logger = logging.getLogger(__name__)


class InspectionKafkaClient:
    def __init__(self):
        self.producer = KafkaProducer(
            bootstrap_servers=BOOTSTRAP_SERVERS,
            value_serializer=lambda value: json.dumps(value).encode("utf-8"),
        )

        self.consumer = KafkaConsumer(
            RESPONSE_TOPIC,
            bootstrap_servers=BOOTSTRAP_SERVERS,
            group_id=None,
            auto_offset_reset="latest",
            enable_auto_commit=False,
            value_deserializer=lambda value: json.loads(value.decode("utf-8")),
        )

        self.consumer.poll(timeout_ms=1000)

    def request(self, operation, data, correlation_id=None, timeout=20):
        if correlation_id is None:
            correlation_id = str(uuid4())

        request = {
            "correlation_id": correlation_id,
            "reply_to": RESPONSE_TOPIC,
            "operation": operation,
            "data": data,
        }

        logger.info("CLIENT SENT REQUEST: %s", json.dumps(request))
        self.producer.send(REQUEST_TOPIC, value=request).get(timeout=10)

        deadline = time.monotonic() + timeout

        while time.monotonic() < deadline:
            records = self.consumer.poll(timeout_ms=500)

            for messages in records.values():
                for message in messages:
                    response = message.value

                    if response.get("correlation_id") == correlation_id:
                        logger.info(
                            "CLIENT RECEIVED RESPONSE: %s",
                            json.dumps(response),
                        )
                        return response

        raise TimeoutError(
            f"No matching Kafka response for correlation_id={correlation_id}"
        )

    def close(self):
        self.consumer.close()
        self.producer.close()
