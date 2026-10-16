from datetime import datetime, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.security import create_access_token, hash_password, verify_password
from app.db.session import get_db
from app.models.user import User
from app.models.user_profile import UserProfile
from app.schemas.auth import (
    CurrentUserResponse,
    LoginRequest,
    SignupRequest,
    SignupResponse,
    TokenResponse,
)


router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/signup", response_model=SignupResponse, status_code=status.HTTP_201_CREATED)
def signup(payload: SignupRequest, db: Annotated[Session, Depends(get_db)]) -> SignupResponse:
    existing_user = db.scalar(select(User).where(User.email == payload.email))
    if existing_user is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email is already registered",
        )

    now = datetime.now(timezone.utc)
    user = User(
        email=payload.email,
        passwordHash=hash_password(payload.password),
        nickname=payload.nickname,
        createdAt=now.isoformat().replace("+00:00", "Z"),
        updatedAt=now.replace(tzinfo=None),
    )
    db.add(user)

    try:
        db.flush()
        profile_now = now.replace(tzinfo=None)
        db.add(
            UserProfile(
                userId=user.id,
                createdAt=profile_now,
                updatedAt=profile_now,
            )
        )
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email is already registered",
        ) from None

    db.refresh(user)
    return SignupResponse(
        id=user.id,
        email=user.email,
        nickname=user.nickname,
        created_at=user.createdAt,
    )


@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest, db: Annotated[Session, Depends(get_db)]) -> TokenResponse:
    user = db.scalar(select(User).where(User.email == payload.email))
    if user is None or not verify_password(payload.password, user.passwordHash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return TokenResponse(access_token=create_access_token(user.id), token_type="bearer")


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(_: Annotated[User, Depends(get_current_user)]) -> Response:
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/me", response_model=CurrentUserResponse)
def get_me(
    current_user: Annotated[User, Depends(get_current_user)],
) -> CurrentUserResponse:
    return CurrentUserResponse(
        id=current_user.id,
        email=current_user.email,
        nickname=current_user.nickname,
    )
