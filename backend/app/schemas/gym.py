from pydantic import BaseModel


class GymCreateRequest(BaseModel):
    name: str
    location: str


class GymUpdateRequest(BaseModel):
    name: str | None = None
    location: str | None = None


class GymResponse(BaseModel):
    id: int
    name: str | None
    location: str | None


class GymCreateResponse(GymResponse):
    created_at: str
