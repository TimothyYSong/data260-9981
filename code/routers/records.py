from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session as DatabaseSession
from sqlalchemy.orm import joinedload

from database import get_db
from models import InspectionNote, Restaurant, RestaurantInspection, User
from routers.auth import get_current_user
from schemas import (
    RestaurantInspectionCreate,
    RestaurantInspectionResponse,
    RestaurantInspectionUpdate,
    RestaurantInspectionWithNotesResponse,
)


router = APIRouter(prefix="/records", tags=["records"])


@router.post(
    "",
    response_model=RestaurantInspectionResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_record(
    record: RestaurantInspectionCreate,
    db: DatabaseSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    restaurant = (
        db.query(Restaurant)
        .filter(Restaurant.id == record.restaurant_id)
        .first()
    )

    if restaurant is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Restaurant not found.",
        )

    new_record = RestaurantInspection(
        restaurant_name=record.restaurant_name,
        restaurant_address=record.restaurant_address,
        inspection_code=record.inspection_code,
        violation_count=record.violation_count,
        restaurant_id=record.restaurant_id,
    )

    db.add(new_record)

    try:
        db.commit()
        db.refresh(new_record)
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An inspection with this inspection code already exists.",
        )

    return new_record


@router.get(
    "",
    response_model=list[RestaurantInspectionResponse],
)
def get_records(
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=10, ge=1, le=100),
    db: DatabaseSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    return (
        db.query(RestaurantInspection)
        .offset(skip)
        .limit(limit)
        .all()
    )


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
                "inspection_code": record.inspection_code,
                "violation_count": record.violation_count,
                "restaurant_id": record.restaurant_id,
                "created_at": record.created_at,
                "updated_at": record.updated_at,
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
                "inspection_code": record.inspection_code,
                "violation_count": record.violation_count,
                "restaurant_id": record.restaurant_id,
                "created_at": record.created_at,
                "updated_at": record.updated_at,
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
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Record not found.",
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
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Record not found.",
        )

    restaurant = (
        db.query(Restaurant)
        .filter(Restaurant.id == updated_record.restaurant_id)
        .first()
    )

    if restaurant is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Restaurant not found.",
        )

    record.restaurant_name = updated_record.restaurant_name
    record.restaurant_address = updated_record.restaurant_address
    record.inspection_code = updated_record.inspection_code
    record.violation_count = updated_record.violation_count
    record.restaurant_id = updated_record.restaurant_id

    try:
        db.commit()
        db.refresh(record)
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An inspection with this inspection code already exists.",
        )

    return record


@router.delete(
    "/{record_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
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
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Record not found.",
        )

    db.query(InspectionNote).filter(
        InspectionNote.restaurant_inspection_id == record_id
    ).delete()

    db.delete(record)
    db.commit()

    