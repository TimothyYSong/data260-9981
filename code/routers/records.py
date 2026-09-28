from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session as DatabaseSession
from sqlalchemy.orm import joinedload

from database import get_db
from models import InspectionNote, RestaurantInspection, User
from routers.auth import get_current_user
from schemas import (
    RestaurantInspectionCreate,
    RestaurantInspectionResponse,
    RestaurantInspectionUpdate,
    RestaurantInspectionWithNotesResponse,
)


router = APIRouter(prefix="/records", tags=["records"])


@router.post("", response_model=RestaurantInspectionResponse)
def create_record(
    record: RestaurantInspectionCreate,
    db: DatabaseSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    new_record = RestaurantInspection(
        restaurant_name=record.restaurant_name,
        restaurant_address=record.restaurant_address,
    )

    db.add(new_record)
    db.commit()
    db.refresh(new_record)

    return new_record


@router.get("", response_model=list[RestaurantInspectionResponse])
def get_records(
    db: DatabaseSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    return db.query(RestaurantInspection).all()


@router.get(
    "/part3/nplus1",
    response_model=list[RestaurantInspectionWithNotesResponse],
)
def get_records_with_notes_nplus1(
    page_size: int = 10,
    db: DatabaseSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    records = (
        db.query(RestaurantInspection)
        .order_by(RestaurantInspection.id)
        .limit(page_size)
        .all()
    )

    result = []

    for record in records:
        notes = (
            db.query(InspectionNote)
            .filter(
                InspectionNote.restaurant_inspection_id == record.id
            )
            .all()
        )

        result.append(
            {
                "id": record.id,
                "restaurant_name": record.restaurant_name,
                "restaurant_address": record.restaurant_address,
                "notes": notes,
            }
        )

    return result


@router.get(
    "/part3/fixed",
    response_model=list[RestaurantInspectionWithNotesResponse],
)
def get_records_with_notes_fixed(
    page_size: int = 10,
    db: DatabaseSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    records = (
        db.query(RestaurantInspection)
        .options(joinedload(RestaurantInspection.notes))
        .order_by(RestaurantInspection.id)
        .limit(page_size)
        .all()
    )

    result = []

    for record in records:
        result.append(
            {
                "id": record.id,
                "restaurant_name": record.restaurant_name,
                "restaurant_address": record.restaurant_address,
                "notes": record.notes,
            }
        )

    return result


@router.get(
    "/{record_id}",
    response_model=RestaurantInspectionResponse,
)
def get_record(
    record_id: int,
    db: DatabaseSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    record = (
        db.query(RestaurantInspection)
        .filter(RestaurantInspection.id == record_id)
        .first()
    )

    if record is None:
        raise HTTPException(
            status_code=404,
            detail="Record not found",
        )

    return record


@router.put(
    "/{record_id}",
    response_model=RestaurantInspectionResponse,
)
def update_record(
    record_id: int,
    updated_record: RestaurantInspectionUpdate,
    db: DatabaseSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    record = (
        db.query(RestaurantInspection)
        .filter(RestaurantInspection.id == record_id)
        .first()
    )

    if record is None:
        raise HTTPException(
            status_code=404,
            detail="Record not found",
        )

    record.restaurant_name = updated_record.restaurant_name
    record.restaurant_address = updated_record.restaurant_address

    db.commit()
    db.refresh(record)

    return record


@router.delete("/{record_id}")
def delete_record(
    record_id: int,
    db: DatabaseSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    record = (
        db.query(RestaurantInspection)
        .filter(RestaurantInspection.id == record_id)
        .first()
    )

    if record is None:
        raise HTTPException(
            status_code=404,
            detail="Record not found",
        )

    db.delete(record)
    db.commit()

    return {"message": "Record deleted"}