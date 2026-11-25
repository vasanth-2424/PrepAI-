from datetime import datetime

from pydantic import BaseModel, Field, field_validator


class UserResponse(BaseModel):
    id: int
    name: str
    email: str
    created_at: datetime

    model_config = {"from_attributes": True}


class UserUpdateRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)

    @field_validator("name")
    @classmethod
    def strip_name(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("Name cannot be empty")
        return cleaned
