from typing import Literal

from pydantic import BaseModel


class StopwatchResponse(BaseModel):
    id: int
    status: Literal["in_progress", "paused", "canceled"]
    startedAt: str
    endedAt: str | None
    elapsedSeconds: int
