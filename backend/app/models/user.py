from sqlalchemy import Column, DateTime, Integer, String
from sqlalchemy.orm import relationship

from app.db.base_class import Base


class User(Base):
    __tablename__ = "user"

    id = Column(Integer, primary_key=True)
    email = Column(String, unique=True)
    passwordHash = Column(String)
    nickname = Column(String)
    createdAt = Column(String, unique=True)
    updatedAt = Column(DateTime)

    profiles = relationship("UserProfile", back_populates="user")
    gyms = relationship("Gyms", back_populates="user")
    sessions = relationship("ClimbingSession", back_populates="user")
    videos = relationship("Videos", back_populates="user")
    stopwatch_sessions = relationship("StopwatchSession", back_populates="user")
