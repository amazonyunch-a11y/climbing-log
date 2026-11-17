from sqlalchemy import Column, DateTime, Integer, String, UniqueConstraint
from sqlalchemy.orm import relationship

from app.db.base_class import Base


class User(Base):
    __tablename__ = "user"
    __table_args__ = (UniqueConstraint("nickname", name="uq_user_nickname"),)

    id = Column(Integer, primary_key=True)
    email = Column(String, unique=True)
    passwordHash = Column(String)
    nickname = Column(String)
    createdAt = Column(String, unique=True)
    updatedAt = Column(DateTime)
    authVersion = Column(Integer, nullable=False, default=1, server_default="1")
    emailVerifiedAt = Column(DateTime, nullable=True)

    profiles = relationship("UserProfile", back_populates="user")
    gyms = relationship("Gyms", back_populates="user")
    sessions = relationship("ClimbingSession", back_populates="user")
    videos = relationship("Videos", back_populates="user")
    stopwatch_sessions = relationship("StopwatchSession", back_populates="user")
    password_reset_codes = relationship(
        "PasswordResetCode", back_populates="user", passive_deletes=True
    )
