import re

from pydantic import BaseModel, field_validator

from app.core.nickname import validate_nickname


EMAIL_PATTERN = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def normalize_and_validate_email(value: str) -> str:
    normalized = value.strip().lower()
    if not EMAIL_PATTERN.fullmatch(normalized):
        raise ValueError("Invalid email address")
    return normalized


class SignupRequest(BaseModel):
    email: str
    password: str
    nickname: str

    @field_validator("nickname")
    @classmethod
    def check_nickname(cls, value: str) -> str:
        return validate_nickname(value)

    @field_validator("email")
    @classmethod
    def check_email(cls, value: str) -> str:
        return normalize_and_validate_email(value)


class SignupResponse(BaseModel):
    id: int
    email: str
    nickname: str
    created_at: str


class LoginRequest(BaseModel):
    email: str
    password: str

    @field_validator("email")
    @classmethod
    def check_email(cls, value: str) -> str:
        return normalize_and_validate_email(value)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str


class CurrentUserResponse(BaseModel):
    id: int
    email: str
    nickname: str


class PasswordResetRequest(BaseModel):
    email: str


class PasswordResetConfirmRequest(BaseModel):
    email: str
    code: str
    new_password: str
    new_password_confirm: str


class AuthMessageResponse(BaseModel):
    message: str


class EmailVerificationRequest(BaseModel):
    email: str

    @field_validator("email")
    @classmethod
    def check_email(cls, value: str) -> str:
        return normalize_and_validate_email(value)


class EmailVerificationConfirmRequest(BaseModel):
    email: str
    code: str

    @field_validator("email")
    @classmethod
    def check_email(cls, value: str) -> str:
        return normalize_and_validate_email(value)


class EmailVerificationConfirmResponse(BaseModel):
    message: str
    verified: bool
