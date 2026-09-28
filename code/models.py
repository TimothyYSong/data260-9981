from datetime import datetime

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import relationship

from database import Base


class RestaurantInspection(Base):
    __tablename__ = "restaurant_inspections"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    restaurant_name = Column(String(255), nullable=False)
    restaurant_address = Column(String(255), nullable=False)
    notes = relationship(
        "InspectionNote",
        back_populates="restaurant_inspection",
    )


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    name = Column(String(255), nullable=False)
    email = Column(String(255), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)

    sessions = relationship("Session", back_populates="user")


class Session(Base):
    __tablename__ = "sessions"

    id = Column(String(255), primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    expires_at = Column(DateTime, nullable=False)

    user = relationship("User", back_populates="sessions")


class InspectionNote(Base):
    __tablename__ = "inspection_notes"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    restaurant_inspection_id = Column(
        Integer,
        ForeignKey("restaurant_inspections.id"),
        nullable=False,
    )
    note = Column(String(255), nullable=False)
    restaurant_inspection = relationship(
        "RestaurantInspection",
        back_populates="notes",
    )