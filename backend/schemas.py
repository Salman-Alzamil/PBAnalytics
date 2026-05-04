from pydantic import BaseModel, EmailStr, field_validator
import re 
from datetime import date, time

class ContactCreate(BaseModel):
    first_name: str
    last_name: str
    phone: str
    email: EmailStr
    city: str | None = None
    notes: str | None = None
    profile_picture_id: int | None = None

    @field_validator("phone")
    @classmethod
    def validate_phone(cls, v): # Ensures phone is in Saudi format: +966 followed by exactly 9 digits
        if not re.match(r'^\+966[0-9]{9}$', v):
            raise ValueError("Phone number must be in the format +966XXXXXXXXX")
        return v
    
    @field_validator("first_name", "last_name")
    @classmethod
    def validate_name(cls, v): # Strips whitespace and title-cases the name, rejects empty strings
        if not v.strip():
            raise ValueError("Name cannot be empty")
        return v.strip().title()
    
class ContactResponse(ContactCreate):
    id: int
    possible_duplicates: bool
    profile_picture_id: int | None = None

    model_config = {"from_attributes": True}


class CallHistoryResponse(BaseModel):
    id: int
    call_id: str
    phone_number: str
    contact_name: str | None
    date: date
    time: time
    duration_seconds: int
    call_type: str
    status: str

    model_config = {"from_attributes": True}