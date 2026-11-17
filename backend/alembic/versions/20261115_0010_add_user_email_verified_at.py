"""Add email verification timestamp to users.

Revision ID: 20261115_0010
Revises: 20261115_0009
Create Date: 2026-11-15
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20261115_0010"
down_revision: Union[str, Sequence[str], None] = "20261115_0009"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "user",
        sa.Column("emailVerifiedAt", sa.DateTime(), nullable=True),
    )
    op.execute(
        'UPDATE "user" '
        'SET "emailVerifiedAt" = CURRENT_TIMESTAMP AT TIME ZONE \'UTC\' '
        'WHERE "emailVerifiedAt" IS NULL'
    )


def downgrade() -> None:
    op.drop_column("user", "emailVerifiedAt")
