from typing import Literal

from pydantic import BaseModel


class StopwatchResponse(BaseModel):
    id: int
    status: Literal["in_progress", "paused", "completed", "canceled"]
    startedAt: str
    endedAt: str | None
    elapsedSeconds: int
    linkedSessionId: int | None
    sessionLinkStatus: Literal["unlinked", "linked", "pending", "ambiguous"]
