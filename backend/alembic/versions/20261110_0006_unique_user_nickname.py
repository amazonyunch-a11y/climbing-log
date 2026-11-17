"""Require unique user nicknames without rewriting existing values.

Revision ID: 20261110_0006
Revises: 20261023_0005
Create Date: 2026-11-10
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20261110_0006"
down_revision: Union[str, Sequence[str], None] = "20261023_0005"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    duplicates = op.get_bind().execute(
        sa.text(
            'SELECT "nickname", COUNT(*) FROM "user" '
            'WHERE "nickname" IS NOT NULL '
            'GROUP BY "nickname" HAVING COUNT(*) > 1'
        )
    ).all()
    if duplicates:
        names = ", ".join(repr(name) for name, _ in duplicates)
        raise RuntimeError(
            f"Duplicate user.nickname values must be resolved before migration: {names}"
        )

    with op.batch_alter_table("user") as batch_op:
        batch_op.create_unique_constraint("uq_user_nickname", ["nickname"])


def downgrade() -> None:
    with op.batch_alter_table("user") as batch_op:
        batch_op.drop_constraint("uq_user_nickname", type_="unique")
