from datetime import datetime, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.gyms import Gyms
from app.models.user import User
from app.schemas.gym import (
    GymCreateRequest,
    GymCreateResponse,
    GymResponse,
    GymUpdateRequest,
)


router = APIRouter(prefix="/api/gyms", tags=["gyms"])


def _now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _to_response(gym: Gyms) -> GymResponse:
    return GymResponse(id=gym.id, name=gym.name, location=gym.lacation)


def _to_created_response(gym: Gyms) -> GymCreateResponse:
    created_at = gym.createAt.replace(tzinfo=timezone.utc).isoformat().replace("+00:00", "Z")
    return GymCreateResponse(
        id=gym.id,
        name=gym.name,
        location=gym.lacation,
        created_at=created_at,
    )


def _get_owned_gym(db: Session, gym_id: int, current_user: User) -> Gyms:
    gym = db.scalar(
        select(Gyms).where(Gyms.id == gym_id, Gyms.userId == current_user.id)
    )
    if gym is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Gym not found")
    return gym


@router.get("", response_model=list[GymResponse])
def list_gyms(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> list[GymResponse]:
    gyms = db.scalars(
        select(Gyms).where(Gyms.userId == current_user.id).order_by(Gyms.id)
    ).all()
    return [_to_response(gym) for gym in gyms]


@router.post("", response_model=GymCreateResponse, status_code=status.HTTP_201_CREATED)
def create_gym(
    payload: GymCreateRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> GymCreateResponse:
    now = _now()
    gym = Gyms(
        userId=current_user.id,
        name=payload.name,
        lacation=payload.location,
        createAt=now,
        updateAt=now,
    )
    db.add(gym)
    db.commit()
    db.refresh(gym)
    return _to_created_response(gym)


@router.get("/{gymId}", response_model=GymResponse)
def get_gym(
    gymId: int,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> GymResponse:
    return _to_response(_get_owned_gym(db, gymId, current_user))


@router.patch("/{gymId}", response_model=GymResponse)
def update_gym(
    gymId: int,
    payload: GymUpdateRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> GymResponse:
    gym = _get_owned_gym(db, gymId, current_user)
    changes = payload.model_dump(exclude_unset=True)
    if "name" in changes:
        gym.name = changes["name"]
    if "location" in changes:
        gym.lacation = changes["location"]
    if changes:
        gym.updateAt = _now()
        db.commit()
        db.refresh(gym)
    return _to_response(gym)


@router.delete("/{gymId}", status_code=status.HTTP_204_NO_CONTENT)
def delete_gym(
    gymId: int,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> Response:
    gym = _get_owned_gym(db, gymId, current_user)
    db.delete(gym)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
