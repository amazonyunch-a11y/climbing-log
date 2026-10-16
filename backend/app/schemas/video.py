from pydantic import BaseModel, field_validator


class VideoCreateRequest(BaseModel):
    storage_path: str

    @field_validator("storage_path")
    @classmethod
    def validate_storage_path(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("storage_path must not be empty")
        if not value.startswith("videos/"):
            raise ValueError("storage_path must start with videos/")
        if ".." in value or "\\" in value:
            raise ValueError("storage_path contains an invalid path segment")
        if not value.lower().endswith((".mp4", ".mov", ".m4v")):
            raise ValueError("storage_path has an unsupported video extension")
        return value


class VideoResponse(BaseModel):
    id: int
    session_id: int
    storage_path: str
    file_url: str
    uploaded_at: str
