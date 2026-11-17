import re

from sqlalchemy.exc import IntegrityError


NICKNAME_PATTERN = re.compile(r"(?=.*[A-Z])(?=.*[a-z])[A-Za-z0-9]{5,15}")
NICKNAME_ERROR = (
    "Nickname must be 5-15 ASCII letters or digits and include "
    "at least one uppercase and one lowercase letter"
)


def validate_nickname(value: str) -> str:
    # Trim surrounding spaces only; tabs and newlines remain invalid.
    nickname = value.strip(" ")
    if NICKNAME_PATTERN.fullmatch(nickname) is None:
        raise ValueError(NICKNAME_ERROR)
    return nickname


def user_unique_conflict(error: IntegrityError) -> str | None:
    """Identify the violated user constraint without guessing from a failed transaction."""
    constraint = getattr(getattr(error.orig, "diag", None), "constraint_name", None)
    if constraint == "uq_user_nickname":
        return "nickname"
    if constraint == "user_email_key":
        return "email"

    # SQLite's test database reports the column instead of a constraint name.
    message = str(error.orig)
    if "UNIQUE constraint failed: user.nickname" in message:
        return "nickname"
    if "UNIQUE constraint failed: user.email" in message:
        return "email"
    return None
