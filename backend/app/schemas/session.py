from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel


class SessionCreateRequest(BaseModel):
    gym_id: int
    session_date: date
    started_at: datetime
    ended_at: datetime | None = None
    total_attempts: int = 0
    total_sends: int = 0
    notes: str | None = None
    stopwatch_id: int | None = None


class SessionUpdateRequest(BaseModel):
    gym_id: int | None = None
    session_date: date | None = None
    started_at: datetime | None = None
    ended_at: datetime | None = None
    total_attempts: int | None = None
    total_sends: int | None = None
    notes: str | None = None


class SessionCreateResponse(BaseModel):
    id: int
    gym_id: int
    session_date: date
    started_at: str
    ended_at: str | None
    duration_minutes: int | None
    total_attempts: int
    total_sends: int
    notes: str | None
    duration_source: Literal["manual", "stopwatch"]
    stopwatch_id: int | None


class SessionDetailResponse(SessionCreateResponse):
    gym_name: str | None
