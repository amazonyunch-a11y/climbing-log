import hashlib
import hmac
import secrets
import threading
import time
from collections import defaultdict, deque

from app.core.config import get_settings


class PasswordResetConfigurationError(RuntimeError):
    pass


class SlidingWindowRateLimiter:
    def __init__(self) -> None:
        self._attempts: dict[tuple[str, str], deque[float]] = defaultdict(deque)
        self._lock = threading.Lock()

    def allow(self, scope: str, key: str, *, limit: int, window_seconds: int) -> bool:
        now = time.monotonic()
        cutoff = now - window_seconds
        bucket_key = (scope, key)
        with self._lock:
            attempts = self._attempts[bucket_key]
            while attempts and attempts[0] <= cutoff:
                attempts.popleft()
            if len(attempts) >= limit:
                return False
            attempts.append(now)
            return True

    def clear(self) -> None:
        with self._lock:
            self._attempts.clear()


password_reset_rate_limiter = SlidingWindowRateLimiter()


def generate_password_reset_code() -> str:
    return f"{secrets.randbelow(1_000_000):06d}"


def hash_password_reset_code(*, user_id: int, code: str) -> str:
    secret = get_settings().password_reset_code_secret
    if not secret:
        raise PasswordResetConfigurationError(
            "PASSWORD_RESET_CODE_SECRET is not configured"
        )
    message = f"{user_id}:{code}".encode("utf-8")
    return hmac.new(secret.encode("utf-8"), message, hashlib.sha256).hexdigest()


def verify_password_reset_code(*, user_id: int, code: str, code_hash: str) -> bool:
    candidate = hash_password_reset_code(user_id=user_id, code=code)
    return hmac.compare_digest(candidate, code_hash)
