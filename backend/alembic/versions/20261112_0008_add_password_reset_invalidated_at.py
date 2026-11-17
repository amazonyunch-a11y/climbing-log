"""Add password reset code invalidation timestamp.

Revision ID: 20261112_0008
Revises: 20261112_0007
Create Date: 2026-11-12
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20261112_0008"
down_revision: Union[str, Sequence[str], None] = "20261112_0007"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "passwordResetCodes",
        sa.Column("invalidatedAt", sa.DateTime(), nullable=True),
    )
    op.create_index(
        "ix_passwordResetCodes_userId_invalidatedAt",
        "passwordResetCodes",
        ["userId", "invalidatedAt"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_passwordResetCodes_userId_invalidatedAt",
        table_name="passwordResetCodes",
    )
    op.drop_column("passwordResetCodes", "invalidatedAt")
