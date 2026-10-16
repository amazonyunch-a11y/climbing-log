from pydantic import BaseModel, Field, model_validator


class GradeLogCreateRequest(BaseModel):
    grade_label: str
    attempts: int = Field(ge=0)
    sends: int = Field(ge=0)

    @model_validator(mode="after")
    def validate_sends(self) -> "GradeLogCreateRequest":
        if self.sends > self.attempts:
            raise ValueError("sends must not exceed attempts")
        return self


class GradeLogUpdateRequest(BaseModel):
    grade_label: str | None = None
    attempts: int | None = Field(default=None, ge=0)
    sends: int | None = Field(default=None, ge=0)


class GradeLogResponse(BaseModel):
    id: int
    session_id: int
    grade_label: str | None
    attempts: int | None
    sends: int | None
