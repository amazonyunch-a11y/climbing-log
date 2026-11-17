from datetime import date, datetime, time, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.nickname import user_unique_conflict
from app.db.session import get_db
from app.models.user import User
from app.models.user_profile import UserProfile
from app.schemas.profile import ProfileResponse, ProfileUpdateRequest


router = APIRouter(prefix="/api/profile", tags=["profile"])


def _now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _get_or_create_profile(db: Session, user: User) -> tuple[UserProfile, bool]:
    profile = db.scalar(
        select(UserProfile)
        .where(UserProfile.userId == user.id)
        .order_by(UserProfile.id)
    )
    if profile is not None:
        return profile, False

    now = _now()
    profile = UserProfile(userId=user.id, createdAt=now, updatedAt=now)
    db.add(profile)
    db.flush()
    return profile, True


def _to_response(user: User, profile: UserProfile) -> ProfileResponse:
    birth_date = profile.birthDate
    if isinstance(birth_date, datetime):
        birth_date = birth_date.date()

    return ProfileResponse(
        user_id=user.id,
        nickname=user.nickname,
        birth_date=birth_date,
        height_cm=profile.heightCm,
        weight_kg=profile.weightKg,
        arm_length_cm=profile.armLengthCm,
    )


@router.get("", response_model=ProfileResponse)
def get_profile(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> ProfileResponse:
    profile, was_created = _get_or_create_profile(db, current_user)
    if was_created:
        db.commit()
        db.refresh(profile)

    return _to_response(current_user, profile)


@router.patch("", response_model=ProfileResponse)
def update_profile(
    payload: ProfileUpdateRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> ProfileResponse:
    profile, was_created = _get_or_create_profile(db, current_user)
    changes = payload.model_dump(exclude_unset=True)

    if "nickname" in changes:
        nickname = changes["nickname"]
        if nickname != current_user.nickname:
            taken = db.scalar(
                select(User.id).where(User.nickname == nickname, User.id != current_user.id)
            )
            if taken is not None:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="Nickname is already taken",
                )
            current_user.nickname = nickname

    profile_fields = {
        "height_cm": "heightCm",
        "weight_kg": "weightKg",
        "arm_length_cm": "armLengthCm",
    }
    for request_name, model_name in profile_fields.items():
        if request_name in changes:
            setattr(profile, model_name, changes[request_name])

    if "birth_date" in changes:
        value = changes["birth_date"]
        profile.birthDate = (
            datetime.combine(value, time.min) if isinstance(value, date) else None
        )

    if was_created or changes:
        profile.updatedAt = _now()
        try:
            db.commit()
        except IntegrityError as error:
            db.rollback()
            if user_unique_conflict(error) == "nickname":
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="Nickname is already taken",
                ) from None
            raise
        db.refresh(profile)

    return _to_response(current_user, profile)
