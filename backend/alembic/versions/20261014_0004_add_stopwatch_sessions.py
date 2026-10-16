"""Add standalone stopwatch sessions.

Revision ID: 20261014_0004
Revises: 20260923_0003
Create Date: 2026-10-14
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20261014_0004"
down_revision: Union[str, Sequence[str], None] = "20260923_0003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "stopwatchSessions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("userId", sa.Integer(), sa.ForeignKey("user.id"), nullable=False),
        sa.Column("startedAt", sa.DateTime(), nullable=False),
        sa.Column("endedAt", sa.DateTime()),
        sa.Column("elapsedSeconds", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("createdAt", sa.DateTime(), nullable=False),
        sa.Column("updatedAt", sa.DateTime(), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("stopwatchSessions")
