"""Rename climbinSeesion to climbingSession.

Revision ID: 20260915_0002
Revises: 20260915_0001
Create Date: 2026-09-15
"""

from typing import Sequence, Union

from alembic import op


revision: str = "20260915_0002"
down_revision: Union[str, Sequence[str], None] = "20260915_0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.rename_table("climbinSeesion", "climbingSession")


def downgrade() -> None:
    op.rename_table("climbingSession", "climbinSeesion")
