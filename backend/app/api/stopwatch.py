from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.datetime_utils import utc_now, utc_to_iso_z
from app.db.session import get_db
from app.models.stopwatch_session import StopwatchSession
from app.models.user import User
from app.schemas.stopwatch import StopwatchResponse


router = APIRouter(prefix="/api/stopwatch", tags=["stopwatch"])
IN_PROGRESS = "in_progress"
PAUSED = "paused"
CANCELED = "canceled"


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


def _to_response(stopwatch: StopwatchSession) -> StopwatchResponse:
    now = utc_now()
    return StopwatchResponse(
        id=stopwatch.id,
        status=stopwatch.status,
        startedAt=utc_to_iso_z(stopwatch.startedAt),
        endedAt=utc_to_iso_z(stopwatch.endedAt),
        elapsedSeconds=_response_elapsed_seconds(stopwatch, now),
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

    now = utc_now()
    stopwatch.elapsedSeconds = _response_elapsed_seconds(stopwatch, now)
    stopwatch.endedAt = now
    stopwatch.status = CANCELED
    stopwatch.updatedAt = now
    db.commit()
    db.refresh(stopwatch)
    return _to_response(stopwatch)
