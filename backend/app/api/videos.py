from datetime import datetime, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.climbing_session import ClimbingSession
from app.models.user import User
from app.models.videos import Videos
from app.schemas.video import VideoCreateRequest, VideoResponse
from app.services.storage import (
    StorageConfigurationError,
    StorageDeletionError,
    build_public_file_url,
    delete_storage_object,
)


router = APIRouter(tags=["videos"])
MAX_VIDEOS_PER_SESSION = 5


def _now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _as_iso_utc(value: datetime) -> str:
    return value.replace(tzinfo=timezone.utc).isoformat().replace("+00:00", "Z")


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
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")
    return climbing_session


def _get_owned_video(db: Session, video_id: int, current_user: User) -> Videos:
    video = db.scalar(
        select(Videos)
        .join(ClimbingSession, Videos.sessionId == ClimbingSession.id)
        .where(Videos.id == video_id, ClimbingSession.userId == current_user.id)
    )
    if video is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Video not found")
    return video


def _to_response(video: Videos) -> VideoResponse:
    if video.storagePath is None or video.createdAt is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Video metadata is incomplete",
        )
    try:
        file_url = build_public_file_url(video.storagePath)
    except RuntimeError as error:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Supabase Storage public URL configuration is required",
        ) from error

    return VideoResponse(
        id=video.id,
        session_id=video.sessionId,
        storage_path=video.storagePath,
        file_url=file_url,
        uploaded_at=_as_iso_utc(video.createdAt),
    )


@router.post(
    "/api/sessions/{sessionId}/videos",
    response_model=VideoResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_video(
    sessionId: int,
    payload: VideoCreateRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> VideoResponse:
    _get_owned_session(db, sessionId, current_user)
    video_count = db.scalar(
        select(func.count()).select_from(Videos).where(Videos.sessionId == sessionId)
    )
    if (video_count or 0) >= MAX_VIDEOS_PER_SESSION:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"A session can have at most {MAX_VIDEOS_PER_SESSION} videos",
        )
    now = _now()
    video = Videos(
        userId=current_user.id,
        sessionId=sessionId,
        storagePath=payload.storage_path,
        createdAt=now,
        updateAt=now,
    )
    db.add(video)
    db.commit()
    db.refresh(video)
    return _to_response(video)


@router.get(
    "/api/sessions/{sessionId}/videos",
    response_model=list[VideoResponse],
)
def list_videos(
    sessionId: int,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> list[VideoResponse]:
    _get_owned_session(db, sessionId, current_user)
    videos = db.scalars(
        select(Videos).where(Videos.sessionId == sessionId).order_by(Videos.id)
    ).all()
    return [_to_response(video) for video in videos]


@router.delete("/api/videos/{videoId}", status_code=status.HTTP_204_NO_CONTENT)
def delete_video(
    videoId: int,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> Response:
    video = _get_owned_video(db, videoId, current_user)
    if not video.storagePath:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Video metadata is incomplete",
        )
    try:
        delete_storage_object(video.storagePath)
    except StorageConfigurationError as error:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Video storage delete is not configured. Please contact support.",
        ) from error
    except StorageDeletionError as error:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Video file could not be deleted from storage. Please retry.",
        ) from error
    except Exception as error:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Video file could not be deleted from storage. Please retry.",
        ) from error
    db.delete(video)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
