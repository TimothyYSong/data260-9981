from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from database import get_db
from models import Restaurant, RestaurantInspection
from schemas import (
    RestaurantCreate,
    RestaurantInspectionResponse,
    RestaurantResponse,
    RestaurantUpdate,
)


router = APIRouter(
    prefix="/restaurants",
    tags=["restaurants"],
)


@router.post(
    "",
    response_model=RestaurantResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_restaurant(
    payload: RestaurantCreate,
    db: Session = Depends(get_db),
):
    restaurant = Restaurant(
        name=payload.name,
        address=payload.address,
        permit_code=payload.permit_code,
    )

    db.add(restaurant)

    try:
        db.commit()
        db.refresh(restaurant)
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A restaurant with this permit code already exists.",
        )

    return restaurant


@router.get(
    "",
    response_model=list[RestaurantResponse],
)
def list_restaurants(
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=10, ge=1, le=100),
    db: Session = Depends(get_db),
):
    restaurants = (
        db.query(Restaurant)
        .offset(skip)
        .limit(limit)
        .all()
    )

    return restaurants


@router.get(
    "/{restaurant_id}",
    response_model=RestaurantResponse,
)
def get_restaurant(
    restaurant_id: int,
    db: Session = Depends(get_db),
):
    restaurant = (
        db.query(Restaurant)
        .filter(Restaurant.id == restaurant_id)
        .first()
    )

    if restaurant is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Restaurant not found.",
        )

    return restaurant


@router.get(
    "/{restaurant_id}/inspections",
    response_model=list[RestaurantInspectionResponse],
)
def get_restaurant_inspections(
    restaurant_id: int,
    db: Session = Depends(get_db),
):
    restaurant = (
        db.query(Restaurant)
        .filter(Restaurant.id == restaurant_id)
        .first()
    )

    if restaurant is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Restaurant not found.",
        )

    inspections = (
        db.query(RestaurantInspection)
        .filter(RestaurantInspection.restaurant_id == restaurant_id)
        .all()
    )

    return inspections


@router.put(
    "/{restaurant_id}",
    response_model=RestaurantResponse,
)
def update_restaurant(
    restaurant_id: int,
    payload: RestaurantUpdate,
    db: Session = Depends(get_db),
):
    restaurant = (
        db.query(Restaurant)
        .filter(Restaurant.id == restaurant_id)
        .first()
    )

    if restaurant is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Restaurant not found.",
        )

    restaurant.name = payload.name
    restaurant.address = payload.address
    restaurant.permit_code = payload.permit_code

    try:
        db.commit()
        db.refresh(restaurant)
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A restaurant with this permit code already exists.",
        )

    return restaurant


@router.delete(
    "/{restaurant_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_restaurant(
    restaurant_id: int,
    db: Session = Depends(get_db),
):
    restaurant = (
        db.query(Restaurant)
        .filter(Restaurant.id == restaurant_id)
        .first()
    )

    if restaurant is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Restaurant not found.",
        )

    associated_inspection = (
        db.query(RestaurantInspection)
        .filter(RestaurantInspection.restaurant_id == restaurant_id)
        .first()
    )

    if associated_inspection is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Cannot delete restaurant with existing inspections.",
        )

    db.delete(restaurant)
    db.commit()