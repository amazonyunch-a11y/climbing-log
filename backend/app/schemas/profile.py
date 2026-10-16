from datetime import date

from pydantic import BaseModel


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
