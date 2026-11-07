from sqlalchemy import CheckConstraint, Column, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import relationship

from app.db.base_class import Base


class ClimbingSession(Base):
    __tablename__ = "climbingSession"
    __table_args__ = (
        CheckConstraint(
            "\"durationSource\" IN ('manual', 'stopwatch')",
            name="ck_climbingSession_durationSource",
        ),
    )

    id = Column(Integer, primary_key=True)
    userId = Column(Integer, ForeignKey("user.id"))
    gymId = Column(Integer, ForeignKey("gyms.id"))
    sessionDate = Column(DateTime)
    startedAt = Column(DateTime)
    endedAt = Column(DateTime)
    durationMintes = Column(Integer)
    durationSource = Column(
        String,
        nullable=False,
        default="manual",
        server_default="manual",
    )
    totalAteempts = Column(Integer)
    totalSends = Column(Integer)
    notes = Column(String)
    createdAt = Column(DateTime)

    user = relationship("User", back_populates="sessions")
    gym = relationship("Gyms", back_populates="sessions")
    grade_logs = relationship("GradeLogs", back_populates="session")
    videos = relationship("Videos", back_populates="session")
    stopwatch_session = relationship(
        "StopwatchSession", back_populates="climbing_session", uselist=False
    )
