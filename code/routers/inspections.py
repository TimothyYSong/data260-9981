from fastapi import APIRouter, HTTPException, status
from fastapi.encoders import jsonable_encoder
from pymongo.errors import PyMongoError

from inspection_schemas import (
    InspectionCreate,
    InspectionDocument,
    utc_now,
)
from mongo_database import inspections_collection
from bson import ObjectId


router = APIRouter(prefix="/api/inspections", tags=["Inspections"])


@router.post("", status_code=status.HTTP_201_CREATED)
def create_inspection(inspection: InspectionCreate):
    document = InspectionDocument(
        **inspection.model_dump(exclude_none=True)
    )

    record = document.model_dump(exclude_none=True)
    record["status"] = document.status.value
    record["inspection_type"] = document.inspection_type.value

    try:
        result = inspections_collection.insert_one(record.copy())
    except PyMongoError as exc:
        raise HTTPException(
            status_code=500,
            detail="Failed to create inspection"
        ) from exc

    return jsonable_encoder({
        "id": str(result.inserted_id),
        **record
    })


@router.get("")
def get_all_inspections():
    try:
        documents = list(inspections_collection.find({}))
    except PyMongoError as exc:
        raise HTTPException(
            status_code=500,
            detail="Failed to retrieve inspections"
        ) from exc

    for document in documents:
        document["id"] = str(document.pop("_id"))

    return jsonable_encoder(documents)


@router.get("/{inspection_id}")
def get_inspection_by_id(inspection_id: str):
    if not ObjectId.is_valid(inspection_id):
        raise HTTPException(
            status_code=400,
            detail="Invalid inspection ID"
        )

    try:
        document = inspections_collection.find_one(
            {"_id": ObjectId(inspection_id)}
        )
    except PyMongoError as exc:
        raise HTTPException(
            status_code=500,
            detail="Failed to retrieve inspection"
        ) from exc

    if document is None:
        raise HTTPException(
            status_code=404,
            detail="Inspection not found"
        )

    document["id"] = str(document.pop("_id"))

    return jsonable_encoder(document)


@router.put("/{inspection_id}")
def update_inspection(
    inspection_id: str,
    inspection: InspectionCreate
):
    if not ObjectId.is_valid(inspection_id):
        raise HTTPException(
            status_code=400,
            detail="Invalid inspection ID"
        )

    object_id = ObjectId(inspection_id)

    try:
        existing = inspections_collection.find_one(
            {"_id": object_id}
        )

        if existing is None:
            raise HTTPException(
                status_code=404,
                detail="Inspection not found"
            )

        document = InspectionDocument(
            **inspection.model_dump(exclude_none=True)
        )

        record = document.model_dump(exclude_none=True)
        record["status"] = document.status.value
        record["inspection_type"] = document.inspection_type.value

        record["created_at"] = existing["created_at"]
        record["updated_at"] = utc_now()

        result = inspections_collection.replace_one(
            {"_id": object_id},
            record
        )

    except PyMongoError as exc:
        raise HTTPException(
            status_code=500,
            detail="Failed to update inspection"
        ) from exc

    if result.matched_count == 0:
        raise HTTPException(
            status_code=404,
            detail="Inspection not found"
        )

    return jsonable_encoder({
        "id": str(object_id),
        **record
    })


@router.delete("/{inspection_id}")
def delete_inspection(inspection_id: str):
    if not ObjectId.is_valid(inspection_id):
        raise HTTPException(
            status_code=400,
            detail="Invalid inspection ID"
        )

    try:
        result = inspections_collection.delete_one(
            {"_id": ObjectId(inspection_id)}
        )
    except PyMongoError as exc:
        raise HTTPException(
            status_code=500,
            detail="Failed to delete inspection"
        ) from exc

    if result.deleted_count == 0:
        raise HTTPException(
            status_code=404,
            detail="Inspection not found"
        )

    return {
        "message": "Inspection deleted",
        "id": inspection_id
    }
