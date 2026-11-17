"""Add password reset code storage and user auth version.

Revision ID: 20261112_0007
Revises: 20261110_0006
Create Date: 2026-11-12
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20261112_0007"
down_revision: Union[str, Sequence[str], None] = "20261110_0006"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "user",
        sa.Column("authVersion", sa.Integer(), nullable=True, server_default="1"),
    )
    op.execute('UPDATE "user" SET "authVersion" = 1 WHERE "authVersion" IS NULL')
    op.alter_column(
        "user",
        "authVersion",
        existing_type=sa.Integer(),
        nullable=False,
        server_default="1",
    )

    op.create_table(
        "passwordResetCodes",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("userId", sa.Integer(), nullable=False),
        sa.Column("codeHash", sa.String(), nullable=False),
        sa.Column("expiresAt", sa.DateTime(), nullable=False),
        sa.Column("usedAt", sa.DateTime(), nullable=True),
        sa.Column("failedAttempts", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("requestedIp", sa.String(), nullable=False),
        sa.Column("createdAt", sa.DateTime(), nullable=False),
        sa.Column("updatedAt", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(
            ["userId"],
            ["user.id"],
            name="fk_passwordResetCodes_userId_user",
            ondelete="CASCADE",
        ),
    )
    op.create_index(
        "ix_passwordResetCodes_userId_createdAt",
        "passwordResetCodes",
        ["userId", "createdAt"],
    )
    op.create_index(
        "ix_passwordResetCodes_requestedIp_createdAt",
        "passwordResetCodes",
        ["requestedIp", "createdAt"],
    )
    op.create_index("ix_passwordResetCodes_expiresAt", "passwordResetCodes", ["expiresAt"])
    op.create_index("ix_passwordResetCodes_usedAt", "passwordResetCodes", ["usedAt"])
    op.create_index("ix_passwordResetCodes_codeHash", "passwordResetCodes", ["codeHash"])


def downgrade() -> None:
    op.drop_index("ix_passwordResetCodes_codeHash", table_name="passwordResetCodes")
    op.drop_index("ix_passwordResetCodes_usedAt", table_name="passwordResetCodes")
    op.drop_index("ix_passwordResetCodes_expiresAt", table_name="passwordResetCodes")
    op.drop_index(
        "ix_passwordResetCodes_requestedIp_createdAt", table_name="passwordResetCodes"
    )
    op.drop_index(
        "ix_passwordResetCodes_userId_createdAt", table_name="passwordResetCodes"
    )
    op.drop_table("passwordResetCodes")
    op.drop_column("user", "authVersion")
