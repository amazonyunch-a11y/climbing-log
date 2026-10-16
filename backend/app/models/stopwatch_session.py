from sqlalchemy import Column, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import relationship

from app.db.base_class import Base


class StopwatchSession(Base):
    __tablename__ = "stopwatchSessions"

    id = Column(Integer, primary_key=True)
    userId = Column(Integer, ForeignKey("user.id"), nullable=False)
    startedAt = Column(DateTime, nullable=False)
    endedAt = Column(DateTime)
    elapsedSeconds = Column(Integer, nullable=False, default=0)
    status = Column(String, nullable=False)
    createdAt = Column(DateTime, nullable=False)
    updatedAt = Column(DateTime, nullable=False)

    user = relationship("User", back_populates="stopwatch_sessions")
