"""create applications and status history

Revision ID: b5f7d3e4a210
Revises: a4e8c1d2f390
Create Date: 2026-09-22
"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

revision: str = "b5f7d3e4a210"
down_revision: Union[str, Sequence[str], None] = "a4e8c1d2f390"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

STATUS_SQL = (
    "'saved', 'applied', 'screening', 'interview', "
    "'offer', 'rejected', 'withdrawn', 'archived'"
)


def upgrade() -> None:
    op.create_table(
        "applications",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("owner_id", sa.Integer(), nullable=False),
        sa.Column("job_id", sa.Integer(), nullable=False),
        sa.Column(
            "status",
            sa.String(length=20),
            server_default="saved",
            nullable=False,
        ),
        sa.Column(
            "priority",
            sa.Integer(),
            server_default="3",
            nullable=False,
        ),
        sa.Column("applied_at", sa.Date(), nullable=True),
        sa.Column("deadline", sa.Date(), nullable=True),
        sa.Column("next_action_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
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
            f"status IN ({STATUS_SQL})",
            name="ck_applications_status",
        ),
        sa.CheckConstraint(
            "priority BETWEEN 1 AND 5",
            name="ck_applications_priority",
        ),
        sa.ForeignKeyConstraint(["job_id"], ["jobs.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["owner_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "owner_id",
            "job_id",
            name="uq_applications_owner_job",
        ),
    )
    op.create_index(
        "ix_applications_owner_created_at",
        "applications",
        ["owner_id", "created_at"],
        unique=False,
    )
    op.create_index(
        "ix_applications_owner_next_action_at",
        "applications",
        ["owner_id", "next_action_at"],
        unique=False,
    )
    op.create_index(
        "ix_applications_owner_status_updated_at",
        "applications",
        ["owner_id", "status", "updated_at"],
        unique=False,
    )

    op.create_table(
        "application_status_history",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("application_id", sa.Integer(), nullable=False),
        sa.Column("from_status", sa.String(length=20), nullable=False),
        sa.Column("to_status", sa.String(length=20), nullable=False),
        sa.Column(
            "changed_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.CheckConstraint(
            f"from_status IN ({STATUS_SQL})",
            name="ck_application_status_history_from_status",
        ),
        sa.CheckConstraint(
            f"to_status IN ({STATUS_SQL})",
            name="ck_application_status_history_to_status",
        ),
        sa.CheckConstraint(
            "from_status <> to_status",
            name="ck_application_status_history_changed",
        ),
        sa.ForeignKeyConstraint(
            ["application_id"],
            ["applications.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_application_status_history_application_changed_at",
        "application_status_history",
        ["application_id", "changed_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_application_status_history_application_changed_at",
        table_name="application_status_history",
    )
    op.drop_table("application_status_history")
    op.drop_index(
        "ix_applications_owner_status_updated_at",
        table_name="applications",
    )
    op.drop_index(
        "ix_applications_owner_next_action_at",
        table_name="applications",
    )
    op.drop_index(
        "ix_applications_owner_created_at",
        table_name="applications",
    )
    op.drop_table("applications")
