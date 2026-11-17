from datetime import datetime, timedelta, timezone
import logging
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from fastapi.responses import JSONResponse
from sqlalchemy import func, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.nickname import user_unique_conflict
from app.core.password_reset import (
    generate_password_reset_code,
    hash_password_reset_code,
    password_reset_rate_limiter,
    verify_password_reset_code,
)
from app.core.security import create_access_token, hash_password, verify_password
from app.db.session import get_db
from app.models.password_reset_code import PasswordResetCode, PasswordResetPurpose
from app.models.user import User
from app.models.user_profile import UserProfile
from app.schemas.auth import (
    AuthMessageResponse,
    CurrentUserResponse,
    EmailVerificationConfirmRequest,
    EmailVerificationConfirmResponse,
    EmailVerificationRequest,
    LoginRequest,
    PasswordResetConfirmRequest,
    PasswordResetRequest,
    SignupRequest,
    SignupResponse,
    TokenResponse,
)
from app.services.resend import (
    ResendDeliveryError,
    send_email_verification_code_email,
    send_password_reset_code_email,
)


router = APIRouter(prefix="/api/auth", tags=["auth"])
logger = logging.getLogger(__name__)

PASSWORD_RESET_REQUEST_MESSAGE = (
    "회원가입시 입력하신 이메일을 확인해 주세요. "
    "해당 메일주소로 인증 코드를 발송했습니다."
)
PASSWORD_RESET_CONFIRM_MESSAGE = (
    "비밀번호가 변경되었습니다. 새 비밀번호로 로그인해 주세요."
)
PASSWORD_RESET_INVALID_MESSAGE = "인증번호가 올바르지 않거나 만료되었습니다."
PASSWORD_RESET_RATE_LIMIT_MESSAGE = (
    "요청이 너무 많습니다. 잠시 후 다시 시도해 주세요."
)
PASSWORD_POLICY_MESSAGE = "비밀번호는 8자 이상이어야 합니다."
EMAIL_VERIFICATION_REQUEST_MESSAGE = "입력한 이메일 주소로 인증번호를 발송했습니다."
EMAIL_VERIFICATION_CONFIRM_MESSAGE = "이메일 인증이 완료되었습니다."
UNVERIFIED_LOGIN_MESSAGE = "이메일 인증을 완료한 후 로그인해 주세요."


def _utc_now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _normalize_email(email: str) -> str:
    return email.strip().lower()


def _client_ip(request: Request) -> str:
    return request.client.host if request.client is not None else "unknown"


def _message_error(message: str, status_code: int) -> JSONResponse:
    return JSONResponse(status_code=status_code, content={"message": message})


def _request_success() -> AuthMessageResponse:
    return AuthMessageResponse(message=PASSWORD_RESET_REQUEST_MESSAGE)


def _invalid_code_response() -> JSONResponse:
    return _message_error(PASSWORD_RESET_INVALID_MESSAGE, status.HTTP_400_BAD_REQUEST)


def _latest_active_code_statement(
    user_id: int,
    purpose: PasswordResetPurpose,
):
    return (
        select(PasswordResetCode)
        .where(
            PasswordResetCode.userId == user_id,
            PasswordResetCode.purpose == purpose,
            PasswordResetCode.usedAt.is_(None),
            PasswordResetCode.invalidatedAt.is_(None),
        )
        .order_by(PasswordResetCode.createdAt.desc(), PasswordResetCode.id.desc())
        .with_for_update()
    )


def _latest_active_reset_code_statement(user_id: int):
    return _latest_active_code_statement(
        user_id,
        PasswordResetPurpose.PASSWORD_RESET,
    )


@router.post("/signup", response_model=SignupResponse, status_code=status.HTTP_201_CREATED)
def signup(payload: SignupRequest, db: Annotated[Session, Depends(get_db)]) -> SignupResponse:
    existing_user = db.scalar(select(User).where(User.email == payload.email))
    if existing_user is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email is already registered",
        )

    existing_nickname = db.scalar(select(User.id).where(User.nickname == payload.nickname))
    if existing_nickname is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Nickname is already taken",
        )

    now = datetime.now(timezone.utc)
    user = User(
        email=payload.email,
        passwordHash=hash_password(payload.password),
        nickname=payload.nickname,
        createdAt=now.isoformat().replace("+00:00", "Z"),
        updatedAt=now.replace(tzinfo=None),
        emailVerifiedAt=None,
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
    except IntegrityError as error:
        db.rollback()
        conflict = user_unique_conflict(error)
        if conflict is None:
            raise
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "Nickname is already taken"
                if conflict == "nickname"
                else "Email is already registered"
            ),
        ) from None

    db.refresh(user)
    return SignupResponse(
        id=user.id,
        email=user.email,
        nickname=user.nickname,
        created_at=user.createdAt,
    )


@router.post(
    "/login",
    response_model=TokenResponse,
    responses={status.HTTP_403_FORBIDDEN: {"model": AuthMessageResponse}},
)
def login(
    payload: LoginRequest,
    db: Annotated[Session, Depends(get_db)],
) -> TokenResponse | JSONResponse:
    user = db.scalar(select(User).where(User.email == payload.email))
    if user is None or not verify_password(payload.password, user.passwordHash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if user.emailVerifiedAt is None:
        return _message_error(UNVERIFIED_LOGIN_MESSAGE, status.HTTP_403_FORBIDDEN)

    return TokenResponse(
        access_token=create_access_token(user.id, user.authVersion),
        token_type="bearer",
    )


@router.post(
    "/password-reset/request",
    response_model=AuthMessageResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
def request_password_reset(
    payload: PasswordResetRequest,
    request: Request,
    db: Annotated[Session, Depends(get_db)],
) -> AuthMessageResponse:
    email = _normalize_email(payload.email)
    now = _utc_now()
    request_ip = _client_ip(request)

    dummy_code = generate_password_reset_code()
    hash_password_reset_code(user_id=0, code=dummy_code)

    if not password_reset_rate_limiter.allow(
        "password-reset-request-ip",
        request_ip,
        limit=10,
        window_seconds=15 * 60,
    ):
        return _request_success()

    recent_ip_count = db.scalar(
        select(func.count(PasswordResetCode.id)).where(
            PasswordResetCode.requestedIp == request_ip,
            PasswordResetCode.purpose == PasswordResetPurpose.PASSWORD_RESET,
            PasswordResetCode.createdAt >= now - timedelta(minutes=15),
        )
    )
    if (recent_ip_count or 0) >= 10:
        return _request_success()

    user = db.scalar(select(User).where(func.lower(User.email) == email))
    if user is None:
        return _request_success()

    last_minute_count = db.scalar(
        select(func.count(PasswordResetCode.id)).where(
            PasswordResetCode.userId == user.id,
            PasswordResetCode.purpose == PasswordResetPurpose.PASSWORD_RESET,
            PasswordResetCode.createdAt >= now - timedelta(seconds=60),
        )
    )
    recent_count = db.scalar(
        select(func.count(PasswordResetCode.id)).where(
            PasswordResetCode.userId == user.id,
            PasswordResetCode.purpose == PasswordResetPurpose.PASSWORD_RESET,
            PasswordResetCode.createdAt >= now - timedelta(minutes=15),
        )
    )
    if (last_minute_count or 0) >= 1 or (recent_count or 0) >= 3:
        return _request_success()

    code = generate_password_reset_code()
    code_hash = hash_password_reset_code(user_id=user.id, code=code)
    try:
        db.execute(
            update(PasswordResetCode)
            .where(
                PasswordResetCode.userId == user.id,
                PasswordResetCode.purpose == PasswordResetPurpose.PASSWORD_RESET,
                PasswordResetCode.usedAt.is_(None),
                PasswordResetCode.invalidatedAt.is_(None),
            )
            .values(invalidatedAt=now, updatedAt=now)
        )
        db.add(
            PasswordResetCode(
                userId=user.id,
                codeHash=code_hash,
                expiresAt=now + timedelta(minutes=5),
                failedAttempts=0,
                requestedIp=request_ip,
                createdAt=now,
                updatedAt=now,
                purpose=PasswordResetPurpose.PASSWORD_RESET,
            )
        )
        db.flush()
        send_password_reset_code_email(recipient=user.email, code=code)
        db.commit()
    except ResendDeliveryError as error:
        db.rollback()
        logger.warning(
            "Password reset email was not sent (%s)",
            type(error).__name__,
        )
    except Exception:
        db.rollback()
        raise

    return _request_success()


@router.post(
    "/password-reset/confirm",
    response_model=AuthMessageResponse,
    status_code=status.HTTP_202_ACCEPTED,
    responses={
        status.HTTP_400_BAD_REQUEST: {"model": AuthMessageResponse},
        422: {"model": AuthMessageResponse},
        status.HTTP_429_TOO_MANY_REQUESTS: {"model": AuthMessageResponse},
    },
)
def confirm_password_reset(
    payload: PasswordResetConfirmRequest,
    request: Request,
    db: Annotated[Session, Depends(get_db)],
) -> AuthMessageResponse | JSONResponse:
    request_ip = _client_ip(request)
    if not password_reset_rate_limiter.allow(
        "password-reset-confirm-ip",
        request_ip,
        limit=10,
        window_seconds=15 * 60,
    ):
        return _message_error(
            PASSWORD_RESET_RATE_LIMIT_MESSAGE,
            status.HTTP_429_TOO_MANY_REQUESTS,
        )

    if (
        len(payload.new_password) < 8
        or payload.new_password != payload.new_password_confirm
    ):
        return _message_error(PASSWORD_POLICY_MESSAGE, 422)

    email = _normalize_email(payload.email)
    now = _utc_now()
    user = db.scalar(select(User).where(func.lower(User.email) == email))
    if user is None:
        hash_password_reset_code(user_id=0, code=payload.code)
        return _invalid_code_response()

    reset_code = db.scalar(_latest_active_reset_code_statement(user.id))
    if reset_code is None:
        hash_password_reset_code(user_id=user.id, code=payload.code)
        return _invalid_code_response()

    if reset_code.expiresAt <= now or reset_code.failedAttempts >= 5:
        reset_code.invalidatedAt = reset_code.invalidatedAt or now
        reset_code.updatedAt = now
        db.commit()
        return _invalid_code_response()

    if not verify_password_reset_code(
        user_id=user.id,
        code=payload.code,
        code_hash=reset_code.codeHash,
    ):
        reset_code.failedAttempts += 1
        reset_code.updatedAt = now
        if reset_code.failedAttempts >= 5:
            reset_code.invalidatedAt = now
        db.commit()
        return _invalid_code_response()

    try:
        user.passwordHash = hash_password(payload.new_password)
        user.authVersion = (user.authVersion or 1) + 1
        user.updatedAt = now
        reset_code.usedAt = now
        reset_code.updatedAt = now
        db.commit()
    except Exception:
        db.rollback()
        raise

    return AuthMessageResponse(message=PASSWORD_RESET_CONFIRM_MESSAGE)


@router.post(
    "/email-verification/request",
    response_model=AuthMessageResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
def request_email_verification(
    payload: EmailVerificationRequest,
    request: Request,
    db: Annotated[Session, Depends(get_db)],
) -> AuthMessageResponse:
    email = payload.email
    now = _utc_now()
    request_ip = _client_ip(request)
    success = AuthMessageResponse(message=EMAIL_VERIFICATION_REQUEST_MESSAGE)

    dummy_code = generate_password_reset_code()
    hash_password_reset_code(user_id=0, code=dummy_code)

    if not password_reset_rate_limiter.allow(
        "email-verification-request-ip",
        request_ip,
        limit=10,
        window_seconds=15 * 60,
    ):
        return success

    recent_ip_count = db.scalar(
        select(func.count(PasswordResetCode.id)).where(
            PasswordResetCode.requestedIp == request_ip,
            PasswordResetCode.purpose == PasswordResetPurpose.EMAIL_VERIFICATION,
            PasswordResetCode.createdAt >= now - timedelta(minutes=15),
        )
    )
    if (recent_ip_count or 0) >= 10:
        return success

    user = db.scalar(select(User).where(func.lower(User.email) == email))
    if user is None or user.emailVerifiedAt is not None:
        return success

    last_minute_count = db.scalar(
        select(func.count(PasswordResetCode.id)).where(
            PasswordResetCode.userId == user.id,
            PasswordResetCode.purpose == PasswordResetPurpose.EMAIL_VERIFICATION,
            PasswordResetCode.createdAt >= now - timedelta(seconds=60),
        )
    )
    recent_count = db.scalar(
        select(func.count(PasswordResetCode.id)).where(
            PasswordResetCode.userId == user.id,
            PasswordResetCode.purpose == PasswordResetPurpose.EMAIL_VERIFICATION,
            PasswordResetCode.createdAt >= now - timedelta(minutes=15),
        )
    )
    if (last_minute_count or 0) >= 1 or (recent_count or 0) >= 3:
        return success

    code = generate_password_reset_code()
    code_hash = hash_password_reset_code(user_id=user.id, code=code)
    try:
        db.execute(
            update(PasswordResetCode)
            .where(
                PasswordResetCode.userId == user.id,
                PasswordResetCode.purpose
                == PasswordResetPurpose.EMAIL_VERIFICATION,
                PasswordResetCode.usedAt.is_(None),
                PasswordResetCode.invalidatedAt.is_(None),
            )
            .values(invalidatedAt=now, updatedAt=now)
        )
        db.add(
            PasswordResetCode(
                userId=user.id,
                codeHash=code_hash,
                expiresAt=now + timedelta(minutes=10),
                failedAttempts=0,
                requestedIp=request_ip,
                createdAt=now,
                updatedAt=now,
                purpose=PasswordResetPurpose.EMAIL_VERIFICATION,
            )
        )
        db.flush()
        send_email_verification_code_email(recipient=user.email, code=code)
        db.commit()
    except ResendDeliveryError as error:
        db.rollback()
        logger.warning(
            "Email verification message was not sent (%s)",
            type(error).__name__,
        )
    except Exception:
        db.rollback()
        raise

    return success


@router.post(
    "/email-verification/confirm",
    response_model=EmailVerificationConfirmResponse,
    responses={
        status.HTTP_400_BAD_REQUEST: {"model": AuthMessageResponse},
        status.HTTP_429_TOO_MANY_REQUESTS: {"model": AuthMessageResponse},
    },
)
def confirm_email_verification(
    payload: EmailVerificationConfirmRequest,
    request: Request,
    db: Annotated[Session, Depends(get_db)],
) -> EmailVerificationConfirmResponse | JSONResponse:
    request_ip = _client_ip(request)
    if not password_reset_rate_limiter.allow(
        "email-verification-confirm-ip",
        request_ip,
        limit=10,
        window_seconds=15 * 60,
    ):
        return _message_error(
            PASSWORD_RESET_RATE_LIMIT_MESSAGE,
            status.HTTP_429_TOO_MANY_REQUESTS,
        )

    now = _utc_now()
    user = db.scalar(select(User).where(func.lower(User.email) == payload.email))
    if user is None:
        hash_password_reset_code(user_id=0, code=payload.code)
        return _invalid_code_response()

    verification_code = db.scalar(
        _latest_active_code_statement(
            user.id,
            PasswordResetPurpose.EMAIL_VERIFICATION,
        )
    )
    if verification_code is None:
        hash_password_reset_code(user_id=user.id, code=payload.code)
        return _invalid_code_response()

    if (
        verification_code.expiresAt <= now
        or verification_code.failedAttempts >= 5
    ):
        verification_code.invalidatedAt = verification_code.invalidatedAt or now
        verification_code.updatedAt = now
        db.commit()
        return _invalid_code_response()

    if not verify_password_reset_code(
        user_id=user.id,
        code=payload.code,
        code_hash=verification_code.codeHash,
    ):
        verification_code.failedAttempts += 1
        verification_code.updatedAt = now
        if verification_code.failedAttempts >= 5:
            verification_code.invalidatedAt = now
        db.commit()
        return _invalid_code_response()

    try:
        user.emailVerifiedAt = now
        verification_code.usedAt = now
        verification_code.updatedAt = now
        db.commit()
    except Exception:
        db.rollback()
        raise

    return EmailVerificationConfirmResponse(
        message=EMAIL_VERIFICATION_CONFIRM_MESSAGE,
        verified=True,
    )


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
