from datetime import datetime, timedelta, timezone
from dataclasses import dataclass

import jwt
from jwt.exceptions import InvalidTokenError
from pwdlib import PasswordHash

from app.core.config import get_settings


password_hash = PasswordHash.recommended()


def hash_password(password: str) -> str:
    return password_hash.hash(password)


def verify_password(password: str, hashed_password: str) -> bool:
    return password_hash.verify(password, hashed_password)


@dataclass(frozen=True)
class AccessTokenClaims:
    user_id: int
    auth_version: int


def create_access_token(user_id: int, auth_version: int = 1) -> str:
    settings = get_settings()
    expires_at = datetime.now(timezone.utc) + timedelta(
        minutes=settings.access_token_expire_minutes
    )
    return jwt.encode(
        {"sub": str(user_id), "auth_version": auth_version, "exp": expires_at},
        settings.jwt_secret_key,
        algorithm=settings.jwt_algorithm,
    )


def decode_access_token(token: str) -> AccessTokenClaims | None:
    settings = get_settings()
    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret_key,
            algorithms=[settings.jwt_algorithm],
        )
        subject = payload.get("sub")
        if subject is None:
            return None
        auth_version = payload.get("auth_version", 1)
        return AccessTokenClaims(
            user_id=int(subject),
            auth_version=int(auth_version),
        )
    except (InvalidTokenError, TypeError, ValueError):
        return None
