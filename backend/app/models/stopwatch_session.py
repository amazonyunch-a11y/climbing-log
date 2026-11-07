from sqlalchemy import Column, DateTime, ForeignKey, Index, Integer, String, UniqueConstraint
from sqlalchemy.orm import relationship

from app.db.base_class import Base


class StopwatchSession(Base):
    __tablename__ = "stopwatchSessions"
    __table_args__ = (
        UniqueConstraint(
            "climbingSessionId", name="uq_stopwatchSessions_climbingSessionId"
        ),
        Index("ix_stopwatchSessions_userId", "userId"),
    )

    id = Column(Integer, primary_key=True)
    userId = Column(Integer, ForeignKey("user.id"), nullable=False)
    climbingSessionId = Column(
        Integer,
        ForeignKey(
            "climbingSession.id",
            name="fk_stopwatchSessions_climbingSessionId_climbingSession",
            ondelete="SET NULL",
        ),
        nullable=True,
    )
    startedAt = Column(DateTime, nullable=False)
    endedAt = Column(DateTime)
    elapsedSeconds = Column(Integer, nullable=False, default=0)
    status = Column(String, nullable=False)
    createdAt = Column(DateTime, nullable=False)
    updatedAt = Column(DateTime, nullable=False)

    user = relationship("User", back_populates="stopwatch_sessions")
    climbing_session = relationship(
        "ClimbingSession", back_populates="stopwatch_session"
    )
