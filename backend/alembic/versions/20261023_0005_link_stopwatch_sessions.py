"""Link stopwatch sessions to climbing sessions.

Revision ID: 20261023_0005
Revises: 20261014_0004
Create Date: 2026-10-23
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20261023_0005"
down_revision: Union[str, Sequence[str], None] = "20261014_0004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "stopwatchSessions",
        sa.Column("climbingSessionId", sa.Integer(), nullable=True),
    )
    op.create_foreign_key(
        "fk_stopwatchSessions_climbingSessionId_climbingSession",
        "stopwatchSessions",
        "climbingSession",
        ["climbingSessionId"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_unique_constraint(
        "uq_stopwatchSessions_climbingSessionId",
        "stopwatchSessions",
        ["climbingSessionId"],
    )
    op.create_index("ix_stopwatchSessions_userId", "stopwatchSessions", ["userId"])

    op.add_column(
        "climbingSession",
        sa.Column(
            "durationSource",
            sa.String(),
            nullable=True,
            server_default="manual",
        ),
    )
    op.execute(
        "UPDATE \"climbingSession\" "
        "SET \"durationSource\" = 'manual' "
        "WHERE \"durationSource\" IS NULL"
    )
    op.alter_column(
        "climbingSession",
        "durationSource",
        existing_type=sa.String(),
        nullable=False,
        server_default="manual",
    )
    op.create_check_constraint(
        "ck_climbingSession_durationSource",
        "climbingSession",
        "\"durationSource\" IN ('manual', 'stopwatch')",
    )


def downgrade() -> None:
    op.drop_constraint(
        "ck_climbingSession_durationSource", "climbingSession", type_="check"
    )
    op.drop_column("climbingSession", "durationSource")

    op.drop_index("ix_stopwatchSessions_userId", table_name="stopwatchSessions")
    op.drop_constraint(
        "uq_stopwatchSessions_climbingSessionId",
        "stopwatchSessions",
        type_="unique",
    )
    op.drop_constraint(
        "fk_stopwatchSessions_climbingSessionId_climbingSession",
        "stopwatchSessions",
        type_="foreignkey",
    )
    op.drop_column("stopwatchSessions", "climbingSessionId")
