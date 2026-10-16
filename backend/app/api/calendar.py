from datetime import date, datetime, time, timedelta
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.climbing_session import ClimbingSession
from app.models.grade_logs import GradeLogs
from app.models.gyms import Gyms
from app.models.user import User
from app.schemas.calendar import (
    CalendarDateResponse,
    CalendarMonthlyItemResponse,
    CalendarSessionResponse,
)


router = APIRouter(prefix="/api/calendar", tags=["calendar"])


def _day_range(value: date) -> tuple[datetime, datetime]:
    start = datetime.combine(value, time.min)
    end = datetime.combine(value + timedelta(days=1), time.min)
    return start, end


def _month_range(year: int, month: int) -> tuple[datetime, datetime]:
    start = datetime(year, month, 1)
    end = datetime(year + 1, 1, 1) if month == 12 else datetime(year, month + 1, 1)
    return start, end


@router.get("", response_model=list[CalendarMonthlyItemResponse])
def get_monthly_calendar(
    year: Annotated[int, Query()],
    month: Annotated[int, Query(ge=1, le=12)],
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> list[CalendarMonthlyItemResponse]:
    start, end = _month_range(year, month)
    session_day = func.date(ClimbingSession.sessionDate).label("session_day")
    rows = db.execute(
        select(session_day, func.count(ClimbingSession.id).label("session_count"))
        .where(
            ClimbingSession.userId == current_user.id,
            ClimbingSession.sessionDate >= start,
            ClimbingSession.sessionDate < end,
        )
        .group_by(session_day)
        .order_by(session_day)
    ).all()
    return [
        CalendarMonthlyItemResponse(
            date=row.session_day,
            session_count=row.session_count,
        )
        for row in rows
    ]


@router.get("/{date}", response_model=CalendarDateResponse)
def get_daily_calendar(
    date: date,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> CalendarDateResponse:
    start, end = _day_range(date)
    rows = db.execute(
        select(
            ClimbingSession.id,
            Gyms.name.label("gym_name"),
            ClimbingSession.durationMintes.label("duration_minutes"),
            func.coalesce(func.sum(GradeLogs.attempts), 0).label("total_attempts"),
            func.coalesce(func.sum(GradeLogs.sends), 0).label("total_sends"),
        )
        .join(Gyms, ClimbingSession.gymId == Gyms.id)
        .outerjoin(GradeLogs, GradeLogs.sessionId == ClimbingSession.id)
        .where(
            ClimbingSession.userId == current_user.id,
            Gyms.userId == current_user.id,
            ClimbingSession.sessionDate >= start,
            ClimbingSession.sessionDate < end,
        )
        .group_by(
            ClimbingSession.id,
            Gyms.name,
            ClimbingSession.durationMintes,
            ClimbingSession.startedAt,
        )
        .order_by(ClimbingSession.startedAt, ClimbingSession.id)
    ).all()

    return CalendarDateResponse(
        date=date,
        sessions=[
            CalendarSessionResponse(
                id=row.id,
                gym_name=row.gym_name,
                duration_minutes=row.duration_minutes,
                total_attempts=row.total_attempts,
                total_sends=row.total_sends,
            )
            for row in rows
        ],
    )
