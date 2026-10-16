from typing import Literal

from pydantic import BaseModel


class StatisticsSummaryResponse(BaseModel):
    period: Literal["weekly", "monthly"]
    session_count: int
    total_duration_minutes: int
    total_attempts: int
    total_sends: int
    send_rate: float


class GradeStatisticsResponse(BaseModel):
    grade_label: str | None
    attempts: int
    sends: int
    send_rate: float


class GymStatisticsResponse(BaseModel):
    gym_id: int
    gym_name: str | None
    visit_count: int
