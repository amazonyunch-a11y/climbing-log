from sqlalchemy import Column, DateTime, ForeignKey, Integer
from sqlalchemy.orm import relationship

from app.db.base_class import Base


class UserProfile(Base):
    __tablename__ = "userProfile"

    id = Column(Integer, primary_key=True)
    userId = Column(Integer, ForeignKey("user.id"))
    birthDate = Column(DateTime)
    heightCm = Column(Integer)
    weightKg = Column(Integer)
    armLengthCm = Column(Integer)
    createdAt = Column(DateTime)
    updatedAt = Column(DateTime)

    user = relationship("User", back_populates="profiles")
