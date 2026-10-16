"""Rename UserProfile typo columns.

Revision ID: 20260923_0003
Revises: 20260915_0002
Create Date: 2026-09-23
"""

from typing import Sequence, Union

from alembic import op


revision: str = "20260923_0003"
down_revision: Union[str, Sequence[str], None] = "20260915_0002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.alter_column("userProfile", "heithtCm", new_column_name="heightCm")
    op.alter_column("userProfile", "weighKg", new_column_name="weightKg")
    op.alter_column("userProfile", "updateAt", new_column_name="updatedAt")


def downgrade() -> None:
    op.alter_column("userProfile", "heightCm", new_column_name="heithtCm")
    op.alter_column("userProfile", "weightKg", new_column_name="weighKg")
    op.alter_column("userProfile", "updatedAt", new_column_name="updateAt")
