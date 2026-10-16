from pydantic import BaseModel


class SignupRequest(BaseModel):
    email: str
    password: str
    nickname: str


class SignupResponse(BaseModel):
    id: int
    email: str
    nickname: str
    created_at: str


class LoginRequest(BaseModel):
    email: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str


class CurrentUserResponse(BaseModel):
    id: int
    email: str
    nickname: str
