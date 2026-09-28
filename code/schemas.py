from pydantic import BaseModel, EmailStr


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class RestaurantInspectionCreate(BaseModel):
    restaurant_name: str
    restaurant_address: str


class RestaurantInspectionUpdate(BaseModel):
    restaurant_name: str
    restaurant_address: str


class RestaurantInspectionResponse(BaseModel):
    id: int
    restaurant_name: str
    restaurant_address: str

    model_config = {
        "from_attributes": True
    }

class InspectionNoteResponse(BaseModel):
    id: int
    restaurant_inspection_id: int
    note: str

    model_config = {"from_attributes": True}


class RestaurantInspectionWithNotesResponse(BaseModel):
    id: int
    restaurant_name: str
    restaurant_address: str
    notes: list[InspectionNoteResponse]