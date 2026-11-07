from datetime import date, datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.datetime_utils import utc_now, utc_to_iso_z
from app.db.session import get_db
from app.models.stopwatch_session import StopwatchSession
from app.models.user import User
from app.schemas.stopwatch import StopwatchResponse
from app.services.stopwatch_linking import (
    auto_link_stopwatch_to_session,
    pending_stopwatches_for_date,
)


router = APIRouter(prefix="/api/stopwatch", tags=["stopwatch"])
IN_PROGRESS = "in_progress"
PAUSED = "paused"
CANCELED = "canceled"
COMPLETED = "completed"


def _get_owned_stopwatch(
    db: Session, stopwatch_id: int, current_user: User
) -> StopwatchSession:
    stopwatch = db.scalar(
        select(StopwatchSession).where(
            StopwatchSession.id == stopwatch_id,
            StopwatchSession.userId == current_user.id,
        )
    )
    if stopwatch is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Stopwatch not found")
    return stopwatch


def _elapsed_seconds(started_at: datetime, ended_at: datetime) -> int:
    return max(0, int((ended_at - started_at).total_seconds()))


def _active_stopwatch(db: Session, current_user: User) -> StopwatchSession | None:
    return db.scalar(
        select(StopwatchSession)
        .where(
            StopwatchSession.userId == current_user.id,
            StopwatchSession.status.in_((IN_PROGRESS, PAUSED)),
        )
        .order_by(desc(StopwatchSession.id))
    )


def _response_elapsed_seconds(stopwatch: StopwatchSession, now: datetime) -> int:
    if stopwatch.status != IN_PROGRESS:
        return stopwatch.elapsedSeconds
    return stopwatch.elapsedSeconds + _elapsed_seconds(stopwatch.startedAt, now)


def _to_response(
    stopwatch: StopwatchSession, session_link_status: str | None = None
) -> StopwatchResponse:
    now = utc_now()
    return StopwatchResponse(
        id=stopwatch.id,
        status=stopwatch.status,
        # startedAt in the API is the whole workout's first start. The model's
        # startedAt is intentionally reused as the current segment start on resume.
        startedAt=utc_to_iso_z(stopwatch.createdAt),
        endedAt=utc_to_iso_z(stopwatch.endedAt),
        elapsedSeconds=_response_elapsed_seconds(stopwatch, now),
        linkedSessionId=stopwatch.climbingSessionId,
        sessionLinkStatus=session_link_status or (
            "linked"
            if stopwatch.climbingSessionId is not None
            else "pending"
            if stopwatch.status == COMPLETED
            else "unlinked"
        ),
    )


@router.post("", response_model=StopwatchResponse, status_code=status.HTTP_201_CREATED)
def start_stopwatch(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> StopwatchResponse:
    active = _active_stopwatch(db, current_user)
    if active is not None and active.status == IN_PROGRESS:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An active stopwatch already exists",
        )

    now = utc_now()
    if active is not None:
        active.startedAt = now
        active.endedAt = None
        active.status = IN_PROGRESS
        active.updatedAt = now
        db.commit()
        db.refresh(active)
        return _to_response(active)

    stopwatch = StopwatchSession(
        userId=current_user.id,
        startedAt=now,
        elapsedSeconds=0,
        status=IN_PROGRESS,
        createdAt=now,
        updatedAt=now,
    )
    db.add(stopwatch)
    db.commit()
    db.refresh(stopwatch)
    return _to_response(stopwatch)


@router.get("/active", response_model=StopwatchResponse)
def get_active_stopwatch(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> StopwatchResponse:
    stopwatch = _active_stopwatch(db, current_user)
    if stopwatch is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No active stopwatch")
    return _to_response(stopwatch)


def _pause_stopwatch(
    stopwatch_id: int,
    current_user: User,
    db: Session,
) -> StopwatchResponse:
    stopwatch = _get_owned_stopwatch(db, stopwatch_id, current_user)
    if stopwatch.status != IN_PROGRESS:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Stopwatch is no longer in progress",
        )

    now = utc_now()
    stopwatch.endedAt = now
    stopwatch.elapsedSeconds = _response_elapsed_seconds(stopwatch, now)
    stopwatch.status = PAUSED
    stopwatch.updatedAt = now
    db.commit()
    db.refresh(stopwatch)
    return _to_response(stopwatch)


@router.patch("/{stopwatchId}/stop", response_model=StopwatchResponse)
def stop_stopwatch(
    stopwatchId: int,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> StopwatchResponse:
    return _pause_stopwatch(stopwatchId, current_user, db)


@router.patch("/{stopwatchId}/finish", response_model=StopwatchResponse)
def finish_stopwatch(
    stopwatchId: int,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> StopwatchResponse:
    stopwatch = _get_owned_stopwatch(db, stopwatchId, current_user)
    if stopwatch.status not in (IN_PROGRESS, PAUSED):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Stopwatch is not active")

    now = utc_now()
    if stopwatch.status == IN_PROGRESS:
        stopwatch.elapsedSeconds = _response_elapsed_seconds(stopwatch, now)
    stopwatch.endedAt = now
    stopwatch.status = COMPLETED
    stopwatch.updatedAt = now
    try:
        session_link_status = auto_link_stopwatch_to_session(db, stopwatch)
        db.commit()
    except Exception:
        db.rollback()
        raise
    db.refresh(stopwatch)
    return _to_response(stopwatch, session_link_status)


@router.patch("/{stopwatchId}/reset", response_model=StopwatchResponse)
def reset_stopwatch(
    stopwatchId: int,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> StopwatchResponse:
    stopwatch = _get_owned_stopwatch(db, stopwatchId, current_user)
    if stopwatch.status not in (IN_PROGRESS, PAUSED):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Stopwatch is no longer active",
        )
    if stopwatch.climbingSessionId is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Stopwatch is linked")

    now = utc_now()
    stopwatch.elapsedSeconds = _response_elapsed_seconds(stopwatch, now)
    stopwatch.endedAt = now
    stopwatch.status = CANCELED
    stopwatch.updatedAt = now
    db.commit()
    db.refresh(stopwatch)
    return _to_response(stopwatch)


@router.get("/pending", response_model=list[StopwatchResponse])
def get_pending_stopwatches(
    session_date: Annotated[date, Query()],
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> list[StopwatchResponse]:
    return [
        _to_response(stopwatch)
        for stopwatch in pending_stopwatches_for_date(db, current_user.id, session_date)
    ]
