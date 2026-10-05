from datetime import datetime

from pydantic import BaseModel, EmailStr, Field


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class RestaurantCreate(BaseModel):
    name: str
    address: str
    permit_code: str = Field(pattern=r"^REST-\d+$")


class RestaurantUpdate(BaseModel):
    name: str
    address: str
    permit_code: str = Field(pattern=r"^REST-\d+$")


class RestaurantResponse(BaseModel):
    id: int
    name: str
    address: str
    permit_code: str
    created_at: datetime
    updated_at: datetime

    model_config = {
        "from_attributes": True
    }


class RestaurantInspectionCreate(BaseModel):
    restaurant_name: str
    restaurant_address: str
    inspection_code: str = Field(pattern=r"^INSP-\d+$")
    violation_count: int = Field(default=0, ge=0)
    restaurant_id: int


class RestaurantInspectionUpdate(BaseModel):
    restaurant_name: str
    restaurant_address: str
    inspection_code: str = Field(pattern=r"^INSP-\d+$")
    violation_count: int = Field(ge=0)
    restaurant_id: int


class RestaurantInspectionResponse(BaseModel):
    id: int
    restaurant_name: str
    restaurant_address: str
    inspection_code: str
    violation_count: int
    restaurant_id: int
    created_at: datetime
    updated_at: datetime

    model_config = {
        "from_attributes": True
    }


class InspectionNoteResponse(BaseModel):
    id: int
    restaurant_inspection_id: int
    note: str

    model_config = {
        "from_attributes": True
    }


class RestaurantInspectionWithNotesResponse(BaseModel):
    id: int
    restaurant_name: str
    restaurant_address: str
    inspection_code: str
    violation_count: int
    restaurant_id: int
    created_at: datetime
    updated_at: datetime
    notes: list[InspectionNoteResponse]

    model_config = {
        "from_attributes": True
    }