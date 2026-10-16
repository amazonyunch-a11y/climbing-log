from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.climbing_session import ClimbingSession
from app.models.grade_logs import GradeLogs
from app.models.gyms import Gyms
from app.models.user import User
from app.schemas.statistics import (
    GradeStatisticsResponse,
    GymStatisticsResponse,
    StatisticsSummaryResponse,
)


router = APIRouter(prefix="/api/statistics", tags=["statistics"])


@dataclass(frozen=True)
class StatisticsPeriod:
    period: Literal["weekly", "monthly"]
    start: datetime
    end: datetime


def _get_statistics_period(
    period: Annotated[Literal["weekly", "monthly"], Query()],
    year: Annotated[int | None, Query(ge=1, le=9999)] = None,
    month: Annotated[int | None, Query(ge=1, le=12)] = None,
    start_date: Annotated[date | None, Query()] = None,
) -> StatisticsPeriod:
    if period == "monthly":
        if year is None or month is None:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail="year and month are required for monthly statistics",
            )
        start = datetime(year, month, 1)
        end = datetime(year + 1, 1, 1) if month == 12 else datetime(
            year, month + 1, 1
        )
        return StatisticsPeriod(period=period, start=start, end=end)

    if start_date is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="start_date is required for weekly statistics",
        )
    start = datetime.combine(start_date, time.min)
    return StatisticsPeriod(period=period, start=start, end=start + timedelta(days=7))


def _session_filters(
    current_user: User, statistics_period: StatisticsPeriod
) -> tuple:
    return (
        ClimbingSession.userId == current_user.id,
        ClimbingSession.sessionDate >= statistics_period.start,
        ClimbingSession.sessionDate < statistics_period.end,
    )


def _send_rate(attempts: int, sends: int) -> float:
    return 0.0 if attempts == 0 else sends / attempts * 100


@router.get("/summary", response_model=StatisticsSummaryResponse)
def get_statistics_summary(
    statistics_period: Annotated[StatisticsPeriod, Depends(_get_statistics_period)],
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> StatisticsSummaryResponse:
    filters = _session_filters(current_user, statistics_period)
    session_count, total_duration_minutes = db.execute(
        select(
            func.count(ClimbingSession.id),
            func.coalesce(func.sum(ClimbingSession.durationMintes), 0),
        ).where(*filters)
    ).one()
    total_attempts, total_sends = db.execute(
        select(
            func.coalesce(func.sum(GradeLogs.attempts), 0),
            func.coalesce(func.sum(GradeLogs.sends), 0),
        )
        .join(ClimbingSession, GradeLogs.sessionId == ClimbingSession.id)
        .where(*filters)
    ).one()

    attempts = int(total_attempts)
    sends = int(total_sends)
    return StatisticsSummaryResponse(
        period=statistics_period.period,
        session_count=int(session_count),
        total_duration_minutes=int(total_duration_minutes),
        total_attempts=attempts,
        total_sends=sends,
        send_rate=_send_rate(attempts, sends),
    )


@router.get("/grades", response_model=list[GradeStatisticsResponse])
def get_grade_statistics(
    statistics_period: Annotated[StatisticsPeriod, Depends(_get_statistics_period)],
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> list[GradeStatisticsResponse]:
    rows = db.execute(
        select(
            GradeLogs.gradeLabel,
            func.coalesce(func.sum(GradeLogs.attempts), 0).label("attempts"),
            func.coalesce(func.sum(GradeLogs.sends), 0).label("sends"),
        )
        .join(ClimbingSession, GradeLogs.sessionId == ClimbingSession.id)
        .where(*_session_filters(current_user, statistics_period))
        .group_by(GradeLogs.gradeLabel)
        .order_by(GradeLogs.gradeLabel)
    ).all()
    return [
        GradeStatisticsResponse(
            grade_label=row.gradeLabel,
            attempts=int(row.attempts),
            sends=int(row.sends),
            send_rate=_send_rate(int(row.attempts), int(row.sends)),
        )
        for row in rows
    ]


@router.get("/gyms", response_model=list[GymStatisticsResponse])
def get_gym_statistics(
    statistics_period: Annotated[StatisticsPeriod, Depends(_get_statistics_period)],
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> list[GymStatisticsResponse]:
    rows = db.execute(
        select(
            Gyms.id.label("gym_id"),
            Gyms.name.label("gym_name"),
            func.count(ClimbingSession.id).label("visit_count"),
        )
        .join(Gyms, ClimbingSession.gymId == Gyms.id)
        .where(
            *_session_filters(current_user, statistics_period),
            Gyms.userId == current_user.id,
        )
        .group_by(Gyms.id, Gyms.name)
        .order_by(func.count(ClimbingSession.id).desc(), Gyms.id)
    ).all()
    return [
        GymStatisticsResponse(
            gym_id=row.gym_id,
            gym_name=row.gym_name,
            visit_count=int(row.visit_count),
        )
        for row in rows
    ]
