from datetime import datetime, timezone
from enum import Enum

from pydantic import BaseModel, Field


class InspectionStatus(str, Enum):
    pending = "pending"
    passed = "passed"
    failed = "failed"


class InspectionType(str, Enum):
    routine = "routine"
    follow_up = "follow_up"
    complaint = "complaint"


def utc_now():
    return datetime.now(timezone.utc)


class InspectionDocument(BaseModel):
    restaurant_name: str = Field(
        ..., min_length=1, max_length=100
    )
    description: str | None = None
    status: InspectionStatus = InspectionStatus.pending
    inspection_type: InspectionType
    inspection_date: datetime
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)



class InspectionCreate(BaseModel):
    restaurant_name: str = Field(
        ..., min_length=1, max_length=100
    )
    description: str | None = None
    status: InspectionStatus = InspectionStatus.pending
    inspection_type: InspectionType
    inspection_date: datetime
