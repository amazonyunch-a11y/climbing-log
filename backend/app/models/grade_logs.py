from sqlalchemy import Column, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import relationship

from app.db.base_class import Base


class GradeLogs(Base):
    __tablename__ = "gradeLogs"

    id = Column(Integer, primary_key=True)
    sessionId = Column(Integer, ForeignKey("climbingSession.id"))
    gradeLabel = Column(String)
    attempts = Column(Integer)
    sends = Column(Integer)
    createdAt = Column(DateTime)
    endedAt = Column(DateTime)

    session = relationship("ClimbingSession", back_populates="grade_logs")
