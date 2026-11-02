import logging
from uuid import uuid4

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from kafka_inspection_client import InspectionKafkaClient
from inspection_schemas import InspectionCreate

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
)

logger = logging.getLogger(__name__)

app = FastAPI(title="HW8 Local Restaurant Inspections Kafka API")


class InspectionGetRequest(BaseModel):
    inspection_id: str


def kafka_request(operation, data):
    correlation_id = str(uuid4())
    logger.info(
        "API REQUEST: operation=%s correlation_id=%s",
        operation,
        correlation_id,
    )

    client = InspectionKafkaClient()

    try:
        response = client.request(
            operation=operation,
            data=data,
            correlation_id=correlation_id,
        )

        logger.info("API RESPONSE: %s", response)
        return response

    except TimeoutError:
        raise HTTPException(
            status_code=504,
            detail="Kafka worker response timed out",
        )

    finally:
        client.close()


@app.get("/health")
def health():
    return {"status": "ok", "service": "hw08-kafka-api"}


@app.post("/api/hw08/inspections")
def create_inspection(inspection: InspectionCreate):
    return kafka_request(
        "CREATE_INSPECTION",
        inspection.model_dump(mode="json"),
    )


@app.post("/api/hw08/inspections/get")
def get_inspection(request: InspectionGetRequest):
    return kafka_request(
        "GET_INSPECTION",
        {"inspection_id": request.inspection_id},
    )
