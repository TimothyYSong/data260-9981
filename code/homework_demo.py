import json
import logging
from uuid import uuid4

from kafka_inspection_client import InspectionKafkaClient

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
)

logging.getLogger("kafka").setLevel(logging.WARNING)

logger = logging.getLogger(__name__)


def main():
    client = InspectionKafkaClient()

    try:
        create_id = str(uuid4())

        logger.info("=== CREATE_INSPECTION ===")
        logger.info("CREATE correlation_id: %s", create_id)

        create_response = client.request(
            operation="CREATE_INSPECTION",
            data={
                "restaurant_name": "O2 Valley",
                "inspection_type": "routine",
                "inspection_date": "2026-11-01T12:00:00",
                "description": "HW8 complete Kafka demonstration",
            },
            correlation_id=create_id,
        )

        logger.info(
            "CREATE RESPONSE: %s",
            json.dumps(create_response),
        )

        assert create_response["success"] is True
        assert create_response["correlation_id"] == create_id

        inspection_id = create_response["inspection_id"]

        logger.info("Generated inspection_id: %s", inspection_id)
        logger.info("CREATE correlation_id preserved: PASS")

        get_id = str(uuid4())

        logger.info("=== GET_INSPECTION ===")
        logger.info("GET correlation_id: %s", get_id)

        get_response = client.request(
            operation="GET_INSPECTION",
            data={"inspection_id": inspection_id},
            correlation_id=get_id,
        )

        logger.info(
            "GET RESPONSE: %s",
            json.dumps(get_response),
        )

        assert get_response["success"] is True
        assert get_response["correlation_id"] == get_id
        assert get_response["entity"]["inspection_id"] == inspection_id

        logger.info(
            "RETRIEVED ENTITY: %s",
            json.dumps(get_response["entity"]),
        )

        logger.info("GET correlation_id preserved: PASS")
        logger.info("CREATE -> GET round trip: PASS")

    finally:
        client.close()


if __name__ == "__main__":
    main()
