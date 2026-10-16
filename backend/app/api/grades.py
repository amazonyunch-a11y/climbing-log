from datetime import datetime, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.climbing_session import ClimbingSession
from app.models.grade_logs import GradeLogs
from app.models.user import User
from app.schemas.grade_log import (
    GradeLogCreateRequest,
    GradeLogResponse,
    GradeLogUpdateRequest,
)


router = APIRouter(tags=["grades"])


def _now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


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


def _get_owned_grade_log(
    db: Session, grade_id: int, current_user: User
) -> GradeLogs:
    grade_log = db.scalar(
        select(GradeLogs)
        .join(ClimbingSession, GradeLogs.sessionId == ClimbingSession.id)
        .where(
            GradeLogs.id == grade_id,
            ClimbingSession.userId == current_user.id,
        )
    )
    if grade_log is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Grade log not found",
        )
    return grade_log


def _validate_counts(attempts: int, sends: int) -> None:
    if sends > attempts:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="sends must not exceed attempts",
        )


def _to_response(grade_log: GradeLogs) -> GradeLogResponse:
    return GradeLogResponse(
        id=grade_log.id,
        session_id=grade_log.sessionId,
        grade_label=grade_log.gradeLabel,
        attempts=grade_log.attempts,
        sends=grade_log.sends,
    )


@router.get(
    "/api/sessions/{sessionId}/grades",
    response_model=list[GradeLogResponse],
)
def list_grade_logs(
    sessionId: int,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> list[GradeLogResponse]:
    _get_owned_session(db, sessionId, current_user)
    grade_logs = db.scalars(
        select(GradeLogs)
        .where(GradeLogs.sessionId == sessionId)
        .order_by(GradeLogs.id)
    ).all()
    return [_to_response(grade_log) for grade_log in grade_logs]


@router.post(
    "/api/sessions/{sessionId}/grades",
    response_model=GradeLogResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_grade_log(
    sessionId: int,
    payload: GradeLogCreateRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> GradeLogResponse:
    _get_owned_session(db, sessionId, current_user)
    grade_log = GradeLogs(
        sessionId=sessionId,
        gradeLabel=payload.grade_label,
        attempts=payload.attempts,
        sends=payload.sends,
        createdAt=_now(),
    )
    db.add(grade_log)
    db.commit()
    db.refresh(grade_log)
    return _to_response(grade_log)


@router.patch("/api/grades/{gradeId}", response_model=GradeLogResponse)
def update_grade_log(
    gradeId: int,
    payload: GradeLogUpdateRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> GradeLogResponse:
    grade_log = _get_owned_grade_log(db, gradeId, current_user)
    changes = payload.model_dump(exclude_unset=True)
    attempts = changes.get("attempts", grade_log.attempts)
    sends = changes.get("sends", grade_log.sends)
    _validate_counts(attempts, sends)

    if "grade_label" in changes:
        grade_log.gradeLabel = changes["grade_label"]
    if "attempts" in changes:
        grade_log.attempts = attempts
    if "sends" in changes:
        grade_log.sends = sends
    if changes:
        db.commit()
        db.refresh(grade_log)
    return _to_response(grade_log)


@router.delete("/api/grades/{gradeId}", status_code=status.HTTP_204_NO_CONTENT)
def delete_grade_log(
    gradeId: int,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> Response:
    grade_log = _get_owned_grade_log(db, gradeId, current_user)
    db.delete(grade_log)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
