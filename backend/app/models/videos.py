from sqlalchemy import Column, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import relationship

from app.db.base_class import Base


class Videos(Base):
    __tablename__ = "videos"

    id = Column(Integer, primary_key=True)
    userId = Column(Integer, ForeignKey("user.id"))
    sessionId = Column(Integer, ForeignKey("climbingSession.id"))
    storagePath = Column(String)
    thumbnailPath = Column(String)
    title = Column(String)
    gradLabel = Column(Integer)
    notes = Column(String)
    orginaFilename = Column(String)
    fileSize = Column(String)
    durationSeconds = Column(String)
    mimeTpe = Column(String)
    recordedAt = Column(DateTime)
    createdAt = Column(DateTime)
    updateAt = Column(DateTime)

    user = relationship("User", back_populates="videos")
    session = relationship("ClimbingSession", back_populates="videos")
