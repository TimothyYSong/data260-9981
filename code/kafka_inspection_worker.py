import json
import logging
import os
from uuid import uuid4

from kafka import KafkaConsumer, KafkaProducer
from pydantic import ValidationError

from inspection_schemas import InspectionCreate

PREFIX = "s9981"
REQUEST_TOPIC = f"{PREFIX}_entity_requests"
RESPONSE_TOPIC = f"{PREFIX}_entity_responses"
BOOTSTRAP_SERVERS = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
)
logger = logging.getLogger(__name__)

inspections = {}


def process_request(request):
    operation = request.get("operation")
    data = request.get("data")

    if operation not in ("CREATE_INSPECTION", "GET_INSPECTION"):
        return {"success": False, "error": "Unknown operation"}

    if not isinstance(data, dict):
        return {"success": False, "error": "Invalid data object"}

    if operation == "CREATE_INSPECTION":
        try:
            inspection = InspectionCreate.model_validate(data)

            if not inspection.restaurant_name.strip():
                return {
                    "success": False,
                    "error": "restaurant_name cannot be empty",
                }

            inspection_id = str(uuid4())
            inspections[inspection_id] = {
                "inspection_id": inspection_id,
                **inspection.model_dump(mode="json"),
            }

            return {
                "success": True,
                "inspection_id": inspection_id,
                "message": "Entity created",
            }

        except ValidationError as exc:
            return {
                "success": False,
                "error": f"Invalid inspection data: {exc.error_count()} validation error(s)",
            }

    if operation == "GET_INSPECTION":
        inspection_id = data.get("inspection_id")

        if not isinstance(inspection_id, str) or not inspection_id.strip():
            return {"success": False, "error": "Invalid inspection_id"}

        entity = inspections.get(inspection_id)

        if entity is None:
            return {"success": False, "error": "Entity not found"}

        return {"success": True, "entity": entity}

    return {"success": False, "error": "Unknown operation"}


def main():
    producer = KafkaProducer(
        bootstrap_servers=BOOTSTRAP_SERVERS,
        value_serializer=lambda value: json.dumps(value).encode("utf-8"),
    )

    consumer = KafkaConsumer(
        REQUEST_TOPIC,
        bootstrap_servers=BOOTSTRAP_SERVERS,
        group_id=f"{PREFIX}_inspection_workers",
        auto_offset_reset="earliest",
        enable_auto_commit=False,
        value_deserializer=lambda value: json.loads(value.decode("utf-8")),
    )

    logger.info("Consumer is ready and listening...")

    for message in consumer:
        request = message.value
        logger.info("WORKER RECEIVED: %s", json.dumps(request))

        correlation_id = request.get("correlation_id")
        reply_to = request.get("reply_to")

        if not isinstance(reply_to, str) or reply_to != RESPONSE_TOPIC:
            logger.error("Invalid reply_to; request skipped")
            consumer.commit()
            continue

        try:
            response = process_request(request)
            response["correlation_id"] = correlation_id

            logger.info("WORKER PROCESSED: %s", request.get("operation"))

            producer.send(reply_to, value=response).get(timeout=15)
            logger.info("WORKER SENT RESPONSE: %s", json.dumps(response))

            consumer.commit()

        except Exception:
            logger.exception("Worker processing failed; offset not committed")
            raise


if __name__ == "__main__":
    main()
