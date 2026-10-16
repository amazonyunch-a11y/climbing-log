"""Create the initial Climbing Log schema.

Revision ID: 20260915_0001
Revises:
Create Date: 2026-09-15
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20260915_0001"
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "user",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("email", sa.String(), unique=True),
        sa.Column("passwordHash", sa.String()),
        sa.Column("nickname", sa.String()),
        sa.Column("createdAt", sa.String(), unique=True),
        sa.Column("updatedAt", sa.DateTime()),
    )
    op.create_table(
        "userProfile",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("userId", sa.Integer(), sa.ForeignKey("user.id")),
        sa.Column("birthDate", sa.DateTime()),
        sa.Column("heithtCm", sa.Integer()),
        sa.Column("weighKg", sa.Integer()),
        sa.Column("armLengthCm", sa.Integer()),
        sa.Column("createdAt", sa.DateTime()),
        sa.Column("updateAt", sa.DateTime()),
    )
    op.create_table(
        "gyms",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("userId", sa.Integer(), sa.ForeignKey("user.id")),
        sa.Column("name", sa.String()),
        sa.Column("lacation", sa.String()),
        sa.Column("createAt", sa.DateTime()),
        sa.Column("updateAt", sa.DateTime()),
    )
    op.create_table(
        "climbinSeesion",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("userId", sa.Integer(), sa.ForeignKey("user.id")),
        sa.Column("gymId", sa.Integer(), sa.ForeignKey("gyms.id")),
        sa.Column("sessionDate", sa.DateTime()),
        sa.Column("startedAt", sa.DateTime()),
        sa.Column("endedAt", sa.DateTime()),
        sa.Column("durationMintes", sa.Integer()),
        sa.Column("totalAteempts", sa.Integer()),
        sa.Column("totalSends", sa.Integer()),
        sa.Column("notes", sa.String()),
        sa.Column("createdAt", sa.DateTime()),
    )
    op.create_table(
        "gradeLogs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("sessionId", sa.Integer(), sa.ForeignKey("climbinSeesion.id")),
        sa.Column("gradeLabel", sa.String()),
        sa.Column("attempts", sa.Integer()),
        sa.Column("sends", sa.Integer()),
        sa.Column("createdAt", sa.DateTime()),
        sa.Column("endedAt", sa.DateTime()),
    )
    op.create_table(
        "videos",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("userId", sa.Integer(), sa.ForeignKey("user.id")),
        sa.Column("sessionId", sa.Integer(), sa.ForeignKey("climbinSeesion.id")),
        sa.Column("storagePath", sa.String()),
        sa.Column("thumbnailPath", sa.String()),
        sa.Column("title", sa.String()),
        sa.Column("gradLabel", sa.Integer()),
        sa.Column("notes", sa.String()),
        sa.Column("orginaFilename", sa.String()),
        sa.Column("fileSize", sa.String()),
        sa.Column("durationSeconds", sa.String()),
        sa.Column("mimeTpe", sa.String()),
        sa.Column("recordedAt", sa.DateTime()),
        sa.Column("createdAt", sa.DateTime()),
        sa.Column("updateAt", sa.DateTime()),
    )


def downgrade() -> None:
    op.drop_table("videos")
    op.drop_table("gradeLogs")
    op.drop_table("climbinSeesion")
    op.drop_table("gyms")
    op.drop_table("userProfile")
    op.drop_table("user")
