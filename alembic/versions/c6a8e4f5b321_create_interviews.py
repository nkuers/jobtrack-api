"""create interviews

Revision ID: c6a8e4f5b321
Revises: b5f7d3e4a210
Create Date: 2026-09-22
"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

revision: str = "c6a8e4f5b321"
down_revision: Union[str, Sequence[str], None] = "b5f7d3e4a210"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

TYPE_SQL = (
    "'phone_screen', 'technical', 'behavioral', 'system_design', "
    "'hiring_manager', 'onsite', 'other'"
)
STATUS_SQL = "'scheduled', 'completed', 'cancelled'"


def upgrade() -> None:
    op.create_table(
        "interviews",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("owner_id", sa.Integer(), nullable=False),
        sa.Column("application_id", sa.Integer(), nullable=False),
        sa.Column("interview_type", sa.String(length=30), nullable=False),
        sa.Column(
            "status",
            sa.String(length=20),
            server_default="scheduled",
            nullable=False,
        ),
        sa.Column("scheduled_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "duration_minutes",
            sa.Integer(),
            server_default="60",
            nullable=False,
        ),
        sa.Column("location", sa.String(length=255), nullable=True),
        sa.Column("meeting_url", sa.String(length=2048), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("feedback", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.CheckConstraint(
            f"interview_type IN ({TYPE_SQL})",
            name="ck_interviews_type",
        ),
        sa.CheckConstraint(
            f"status IN ({STATUS_SQL})",
            name="ck_interviews_status",
        ),
        sa.CheckConstraint(
            "duration_minutes BETWEEN 15 AND 480",
            name="ck_interviews_duration",
        ),
        sa.ForeignKeyConstraint(
            ["application_id"],
            ["applications.id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(["owner_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_interviews_owner_application",
        "interviews",
        ["owner_id", "application_id"],
        unique=False,
    )
    op.create_index(
        "ix_interviews_owner_scheduled_at",
        "interviews",
        ["owner_id", "scheduled_at"],
        unique=False,
    )
    op.create_index(
        "ix_interviews_owner_status_scheduled",
        "interviews",
        ["owner_id", "status", "scheduled_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_interviews_owner_status_scheduled", table_name="interviews")
    op.drop_index("ix_interviews_owner_scheduled_at", table_name="interviews")
    op.drop_index("ix_interviews_owner_application", table_name="interviews")
    op.drop_table("interviews")
