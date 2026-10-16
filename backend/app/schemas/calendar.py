from datetime import date

from pydantic import BaseModel


class CalendarMonthlyItemResponse(BaseModel):
    date: date
    session_count: int


class CalendarSessionResponse(BaseModel):
    id: int
    gym_name: str | None
    duration_minutes: int | None
    total_attempts: int
    total_sends: int


class CalendarDateResponse(BaseModel):
    date: date
    sessions: list[CalendarSessionResponse]
