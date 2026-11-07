from datetime import date, datetime, time

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.datetime_utils import kst_date_to_utc_range, utc_to_kst_date
from app.models.climbing_session import ClimbingSession
from app.models.stopwatch_session import StopwatchSession


COMPLETED = "completed"


def pending_stopwatches_for_date(
    db: Session, user_id: int, session_date: date
) -> list[StopwatchSession]:
    start, end = kst_date_to_utc_range(session_date)
    return db.scalars(
        select(StopwatchSession)
        .where(
            StopwatchSession.userId == user_id,
            StopwatchSession.status == COMPLETED,
            StopwatchSession.climbingSessionId.is_(None),
            StopwatchSession.createdAt >= start,
            StopwatchSession.createdAt < end,
        )
        .order_by(StopwatchSession.id)
    ).all()


def link_stopwatch_to_session(
    stopwatch: StopwatchSession,
    climbing_session: ClimbingSession,
    *,
    use_stopwatch_times: bool = True,
) -> None:
    stopwatch.climbingSessionId = climbing_session.id
    if use_stopwatch_times:
        climbing_session.durationSource = "stopwatch"
        climbing_session.startedAt = stopwatch.createdAt
        climbing_session.endedAt = stopwatch.endedAt
        climbing_session.durationMintes = stopwatch.elapsedSeconds // 60
    else:
        climbing_session.durationSource = "manual"


def auto_link_stopwatch_to_session(
    db: Session, stopwatch: StopwatchSession
) -> str:
    if stopwatch.climbingSessionId is not None:
        return "linked"

    session_date = datetime.combine(utc_to_kst_date(stopwatch.createdAt), time.min)
    candidates = db.scalars(
        select(ClimbingSession)
        .where(
            ClimbingSession.userId == stopwatch.userId,
            func.date(ClimbingSession.sessionDate) == session_date.date(),
        )
        .outerjoin(StopwatchSession, StopwatchSession.climbingSessionId == ClimbingSession.id)
        .where(StopwatchSession.id.is_(None))
    ).all()
    if len(candidates) == 1:
        link_stopwatch_to_session(stopwatch, candidates[0])
        return "linked"
    return "pending" if not candidates else "ambiguous"
