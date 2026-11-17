from enum import Enum as PyEnum

from sqlalchemy import Column, DateTime, Enum, ForeignKey, Index, Integer, String
from sqlalchemy.orm import relationship

from app.db.base_class import Base


class PasswordResetPurpose(str, PyEnum):
    PASSWORD_RESET = "password_reset"
    EMAIL_VERIFICATION = "email_verification"


class PasswordResetCode(Base):
    __tablename__ = "passwordResetCodes"
    __table_args__ = (
        Index("ix_passwordResetCodes_userId_createdAt", "userId", "createdAt"),
        Index("ix_passwordResetCodes_requestedIp_createdAt", "requestedIp", "createdAt"),
        Index("ix_passwordResetCodes_expiresAt", "expiresAt"),
        Index("ix_passwordResetCodes_usedAt", "usedAt"),
        Index(
            "ix_passwordResetCodes_userId_invalidatedAt",
            "userId",
            "invalidatedAt",
        ),
        Index("ix_passwordResetCodes_codeHash", "codeHash"),
    )

    id = Column(Integer, primary_key=True)
    userId = Column(
        Integer,
        ForeignKey(
            "user.id",
            name="fk_passwordResetCodes_userId_user",
            ondelete="CASCADE",
        ),
        nullable=False,
    )
    codeHash = Column(String, nullable=False)
    expiresAt = Column(DateTime, nullable=False)
    usedAt = Column(DateTime, nullable=True)
    invalidatedAt = Column(DateTime, nullable=True)
    failedAttempts = Column(Integer, nullable=False, default=0, server_default="0")
    requestedIp = Column(String, nullable=False)
    createdAt = Column(DateTime, nullable=False)
    updatedAt = Column(DateTime, nullable=False)
    purpose = Column(
        Enum(
            PasswordResetPurpose,
            name="password_reset_purpose",
            values_callable=lambda enum_class: [member.value for member in enum_class],
            validate_strings=True,
            create_constraint=True,
        ),
        nullable=False,
        default=PasswordResetPurpose.PASSWORD_RESET,
        server_default=PasswordResetPurpose.PASSWORD_RESET.value,
    )

    user = relationship("User", back_populates="password_reset_codes")
