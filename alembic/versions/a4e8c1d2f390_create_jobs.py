"""create jobs

Revision ID: a4e8c1d2f390
Revises: 7d9e2a4b1c30
Create Date: 2026-09-22
"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

revision: str = "a4e8c1d2f390"
down_revision: Union[str, Sequence[str], None] = "7d9e2a4b1c30"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "jobs",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("owner_id", sa.Integer(), nullable=False),
        sa.Column("company_id", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column(
            "employment_type",
            sa.String(length=20),
            server_default="full_time",
            nullable=False,
        ),
        sa.Column(
            "work_mode",
            sa.String(length=20),
            server_default="onsite",
            nullable=False,
        ),
        sa.Column("location", sa.String(length=255), nullable=True),
        sa.Column("source", sa.String(length=100), nullable=True),
        sa.Column("url", sa.String(length=2048), nullable=True),
        sa.Column("salary_min", sa.BigInteger(), nullable=True),
        sa.Column("salary_max", sa.BigInteger(), nullable=True),
        sa.Column(
            "salary_currency",
            sa.String(length=3),
            server_default="CNY",
            nullable=False,
        ),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column(
            "status",
            sa.String(length=20),
            server_default="open",
            nullable=False,
        ),
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
            "employment_type IN "
            "('full_time', 'part_time', 'contract', 'internship', 'temporary')",
            name="ck_jobs_employment_type",
        ),
        sa.CheckConstraint(
            "work_mode IN ('onsite', 'hybrid', 'remote')",
            name="ck_jobs_work_mode",
        ),
        sa.CheckConstraint(
            "status IN ('open', 'paused', 'closed')",
            name="ck_jobs_status",
        ),
        sa.CheckConstraint(
            "salary_min IS NULL OR salary_min >= 0",
            name="ck_jobs_salary_min_nonnegative",
        ),
        sa.CheckConstraint(
            "salary_max IS NULL OR salary_max >= 0",
            name="ck_jobs_salary_max_nonnegative",
        ),
        sa.CheckConstraint(
            "salary_min IS NULL OR salary_max IS NULL OR salary_min <= salary_max",
            name="ck_jobs_salary_range",
        ),
        sa.CheckConstraint(
            "salary_currency ~ '^[A-Z]{3}$'",
            name="ck_jobs_salary_currency",
        ),
        sa.ForeignKeyConstraint(["company_id"], ["companies.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["owner_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_jobs_owner_company",
        "jobs",
        ["owner_id", "company_id"],
        unique=False,
    )
    op.create_index(
        "ix_jobs_owner_created_at",
        "jobs",
        ["owner_id", "created_at"],
        unique=False,
    )
    op.create_index(
        "ix_jobs_owner_status_updated_at",
        "jobs",
        ["owner_id", "status", "updated_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_jobs_owner_status_updated_at", table_name="jobs")
    op.drop_index("ix_jobs_owner_created_at", table_name="jobs")
    op.drop_index("ix_jobs_owner_company", table_name="jobs")
    op.drop_table("jobs")
