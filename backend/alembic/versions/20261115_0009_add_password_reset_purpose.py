"""Add purpose to password reset codes.

Revision ID: 20261115_0009
Revises: 20261112_0008
Create Date: 2026-11-15
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "20261115_0009"
down_revision: Union[str, Sequence[str], None] = "20261112_0008"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


purpose_enum = postgresql.ENUM(
    "password_reset",
    "email_verification",
    name="password_reset_purpose",
    create_type=False,
)


def upgrade() -> None:
    purpose_enum.create(op.get_bind(), checkfirst=False)
    op.add_column(
        "passwordResetCodes",
        sa.Column("purpose", purpose_enum, nullable=True),
    )
    op.execute(
        'UPDATE "passwordResetCodes" '
        "SET purpose = 'password_reset'::password_reset_purpose "
        "WHERE purpose IS NULL"
    )
    op.alter_column(
        "passwordResetCodes",
        "purpose",
        existing_type=purpose_enum,
        nullable=False,
        server_default=sa.text("'password_reset'::password_reset_purpose"),
    )


def downgrade() -> None:
    op.drop_column("passwordResetCodes", "purpose")
    purpose_enum.drop(op.get_bind(), checkfirst=False)
