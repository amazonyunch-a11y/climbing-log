from datetime import date

from pydantic import BaseModel, field_validator

from app.core.nickname import validate_nickname


class ProfileResponse(BaseModel):
    user_id: int
    nickname: str | None
    birth_date: date | None
    height_cm: int | None
    weight_kg: int | None
    arm_length_cm: int | None


class ProfileUpdateRequest(BaseModel):
    nickname: str | None = None
    birth_date: date | None = None
    height_cm: int | None = None
    weight_kg: int | None = None
    arm_length_cm: int | None = None

    @field_validator("nickname")
    @classmethod
    def check_nickname(cls, value: str | None) -> str:
        if value is None:
            raise ValueError("Nickname cannot be null")
        return validate_nickname(value)
