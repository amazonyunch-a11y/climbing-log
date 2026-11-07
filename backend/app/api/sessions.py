from datetime import date, datetime, time
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.datetime_utils import (
    kst_input_to_utc,
    utc_now,
    utc_to_iso_z,
    utc_to_kst_date,
)
from app.db.session import get_db
from app.models.climbing_session import ClimbingSession
from app.models.grade_logs import GradeLogs
from app.models.gyms import Gyms
from app.models.stopwatch_session import StopwatchSession
from app.models.user import User
from app.schemas.session import (
    SessionCreateRequest,
    SessionCreateResponse,
    SessionDetailResponse,
    SessionUpdateRequest,
)
from app.services.stopwatch_linking import (
    link_stopwatch_to_session,
    pending_stopwatches_for_date,
)


router = APIRouter(prefix="/api/sessions", tags=["sessions"])


def _as_session_date(value: date) -> datetime:
    return datetime.combine(value, time.min)


def _duration_minutes(started_at: datetime, ended_at: datetime | None) -> int | None:
    if ended_at is None:
        return None
    if ended_at <= started_at:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="ended_at must be after started_at",
        )
    return int((ended_at - started_at).total_seconds() // 60)


def _validate_kst_session_dates(
    session_date: date,
    started_at: datetime,
    ended_at: datetime | None,
) -> None:
    if utc_to_kst_date(started_at) != session_date:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="started_at must be on session_date in Asia/Seoul",
        )
    if ended_at is not None and utc_to_kst_date(ended_at) != session_date:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="ended_at must be on session_date in Asia/Seoul",
        )


def _get_owned_gym(db: Session, gym_id: int, current_user: User) -> Gyms:
    gym = db.scalar(
        select(Gyms).where(Gyms.id == gym_id, Gyms.userId == current_user.id)
    )
    if gym is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Gym not found")
    return gym


def _get_owned_session(
    db: Session, session_id: int, current_user: User
) -> ClimbingSession:
    climbing_session = db.scalar(
        select(ClimbingSession).where(
            ClimbingSession.id == session_id,
            ClimbingSession.userId == current_user.id,
        )
    )
    if climbing_session is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found",
        )
    return climbing_session


def _get_linkable_stopwatch(
    db: Session,
    stopwatch_id: int,
    session_date: date,
    current_user: User,
) -> StopwatchSession:
    stopwatch = db.scalar(
        select(StopwatchSession)
        .where(
            StopwatchSession.id == stopwatch_id,
            StopwatchSession.userId == current_user.id,
        )
        .with_for_update()
    )
    if stopwatch is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Stopwatch not found",
        )
    if stopwatch.status != "completed":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Stopwatch is not completed",
        )
    if stopwatch.climbingSessionId is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Stopwatch is already linked",
        )
    if utc_to_kst_date(stopwatch.createdAt) != session_date:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Stopwatch must be on session_date in Asia/Seoul",
        )
    return stopwatch


def _grade_totals_by_session_id(
    db: Session, session_ids: list[int]
) -> dict[int, tuple[int, int]]:
    if not session_ids:
        return {}

    rows = db.execute(
        select(
            GradeLogs.sessionId,
            func.coalesce(func.sum(GradeLogs.attempts), 0).label("total_attempts"),
            func.coalesce(func.sum(GradeLogs.sends), 0).label("total_sends"),
        )
        .where(GradeLogs.sessionId.in_(session_ids))
        .group_by(GradeLogs.sessionId)
    ).all()
    return {
        row.sessionId: (int(row.total_attempts), int(row.total_sends))
        for row in rows
    }


def _to_create_response(
    climbing_session: ClimbingSession,
    totals: tuple[int, int],
) -> SessionCreateResponse:
    total_attempts, total_sends = totals
    return SessionCreateResponse(
        id=climbing_session.id,
        gym_id=climbing_session.gymId,
        session_date=climbing_session.sessionDate.date(),
        started_at=utc_to_iso_z(climbing_session.startedAt),
        ended_at=utc_to_iso_z(climbing_session.endedAt),
        duration_minutes=climbing_session.durationMintes,
        total_attempts=total_attempts,
        total_sends=total_sends,
        notes=climbing_session.notes,
        duration_source=climbing_session.durationSource,
        stopwatch_id=(
            climbing_session.stopwatch_session.id
            if climbing_session.stopwatch_session is not None
            else None
        ),
    )


def _to_detail_response(
    climbing_session: ClimbingSession,
    gym: Gyms,
    totals: tuple[int, int],
) -> SessionDetailResponse:
    return SessionDetailResponse(
        **_to_create_response(climbing_session, totals).model_dump(),
        gym_name=gym.name,
    )


@router.get("", response_model=list[SessionDetailResponse])
def list_sessions(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> list[SessionDetailResponse]:
    rows = db.execute(
        select(ClimbingSession, Gyms)
        .join(Gyms, ClimbingSession.gymId == Gyms.id)
        .where(
            ClimbingSession.userId == current_user.id,
            Gyms.userId == current_user.id,
        )
        .order_by(ClimbingSession.id)
    ).all()
    totals_by_session_id = _grade_totals_by_session_id(
        db, [climbing_session.id for climbing_session, _ in rows]
    )
    return [
        _to_detail_response(
            climbing_session,
            gym,
            totals_by_session_id.get(climbing_session.id, (0, 0)),
        )
        for climbing_session, gym in rows
    ]


@router.post("", response_model=SessionCreateResponse, status_code=status.HTTP_201_CREATED)
def create_session(
    payload: SessionCreateRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> SessionCreateResponse:
    _get_owned_gym(db, payload.gym_id, current_user)
    started_at = kst_input_to_utc(payload.started_at)
    ended_at = (
        kst_input_to_utc(payload.ended_at) if payload.ended_at is not None else None
    )
    _validate_kst_session_dates(payload.session_date, started_at, ended_at)

    selected_stopwatch: StopwatchSession | None = None
    selected_automatically = False
    if "stopwatch_id" in payload.model_fields_set:
        if payload.stopwatch_id is not None:
            selected_stopwatch = _get_linkable_stopwatch(
                db,
                payload.stopwatch_id,
                payload.session_date,
                current_user,
            )
    else:
        pending_stopwatches = pending_stopwatches_for_date(
            db, current_user.id, payload.session_date
        )
        if len(pending_stopwatches) == 1:
            selected_stopwatch = _get_linkable_stopwatch(
                db,
                pending_stopwatches[0].id,
                payload.session_date,
                current_user,
            )
            selected_automatically = True

    climbing_session = ClimbingSession(
        userId=current_user.id,
        gymId=payload.gym_id,
        sessionDate=_as_session_date(payload.session_date),
        startedAt=started_at,
        endedAt=ended_at,
        durationMintes=_duration_minutes(started_at, ended_at),
        durationSource="manual",
        notes=payload.notes,
        createdAt=utc_now(),
    )
    db.add(climbing_session)
    try:
        db.flush()
        if selected_stopwatch is not None:
            uses_stopwatch_times = (
                selected_automatically
                or (
                    started_at == selected_stopwatch.createdAt
                    and ended_at == selected_stopwatch.endedAt
                )
            )
            if uses_stopwatch_times:
                _validate_kst_session_dates(
                    payload.session_date,
                    selected_stopwatch.createdAt,
                    selected_stopwatch.endedAt,
                )
            link_stopwatch_to_session(
                selected_stopwatch,
                climbing_session,
                use_stopwatch_times=uses_stopwatch_times,
            )
        db.commit()
    except Exception:
        db.rollback()
        raise
    db.refresh(climbing_session)
    totals = _grade_totals_by_session_id(db, [climbing_session.id]).get(
        climbing_session.id, (0, 0)
    )
    return _to_create_response(climbing_session, totals)


@router.get("/{sessionId}", response_model=SessionDetailResponse)
def get_session(
    sessionId: int,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> SessionDetailResponse:
    climbing_session = _get_owned_session(db, sessionId, current_user)
    gym = _get_owned_gym(db, climbing_session.gymId, current_user)
    totals = _grade_totals_by_session_id(db, [climbing_session.id]).get(
        climbing_session.id, (0, 0)
    )
    return _to_detail_response(climbing_session, gym, totals)


@router.patch("/{sessionId}", response_model=SessionDetailResponse)
def update_session(
    sessionId: int,
    payload: SessionUpdateRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> SessionDetailResponse:
    climbing_session = _get_owned_session(db, sessionId, current_user)
    changes = payload.model_dump(exclude_unset=True)

    gym_id = changes.get("gym_id", climbing_session.gymId)
    gym = _get_owned_gym(db, gym_id, current_user)

    session_date = changes.get("session_date", climbing_session.sessionDate.date())
    started_at = (
        kst_input_to_utc(changes["started_at"])
        if "started_at" in changes
        else climbing_session.startedAt
    )
    if "ended_at" in changes:
        ended_at = (
            kst_input_to_utc(changes["ended_at"])
            if changes["ended_at"] is not None
            else None
        )
    else:
        ended_at = climbing_session.endedAt
    if {"session_date", "started_at", "ended_at"}.intersection(changes):
        _validate_kst_session_dates(session_date, started_at, ended_at)

    if "gym_id" in changes:
        climbing_session.gymId = gym_id
    if "session_date" in changes:
        climbing_session.sessionDate = _as_session_date(changes["session_date"])
    if "started_at" in changes:
        climbing_session.startedAt = started_at
    if "ended_at" in changes:
        climbing_session.endedAt = ended_at
    if "notes" in changes:
        climbing_session.notes = changes["notes"]

    if changes:
        climbing_session.durationMintes = _duration_minutes(
            climbing_session.startedAt, climbing_session.endedAt
        )
        if {"session_date", "started_at", "ended_at"}.intersection(changes):
            climbing_session.durationSource = "manual"
        db.commit()
        db.refresh(climbing_session)

    totals = _grade_totals_by_session_id(db, [climbing_session.id]).get(
        climbing_session.id, (0, 0)
    )
    return _to_detail_response(climbing_session, gym, totals)


@router.delete("/{sessionId}", status_code=status.HTTP_204_NO_CONTENT)
def delete_session(
    sessionId: int,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> Response:
    climbing_session = _get_owned_session(db, sessionId, current_user)
    if climbing_session.stopwatch_session is not None:
        climbing_session.stopwatch_session.climbingSessionId = None
    db.delete(climbing_session)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
