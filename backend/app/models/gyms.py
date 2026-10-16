from sqlalchemy import Column, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import relationship

from app.db.base_class import Base


class Gyms(Base):
    __tablename__ = "gyms"

    id = Column(Integer, primary_key=True)
    userId = Column(Integer, ForeignKey("user.id"))
    name = Column(String)
    lacation = Column(String)
    createAt = Column(DateTime)
    updateAt = Column(DateTime)

    user = relationship("User", back_populates="gyms")
    sessions = relationship("ClimbingSession", back_populates="gym")
