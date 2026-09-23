"""create companies

Revision ID: 7d9e2a4b1c30
Revises: 65bcb8a12535
Create Date: 2026-09-22
"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

revision: str = "7d9e2a4b1c30"
down_revision: Union[str, Sequence[str], None] = "65bcb8a12535"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "companies",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("owner_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("website", sa.String(length=2048), nullable=True),
        sa.Column("industry", sa.String(length=100), nullable=True),
        sa.Column("location", sa.String(length=255), nullable=True),
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
        sa.ForeignKeyConstraint(["owner_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_companies_owner_created_at",
        "companies",
        ["owner_id", "created_at"],
        unique=False,
    )
    op.create_index(
        "uq_companies_owner_name_normalized",
        "companies",
        ["owner_id", sa.text("lower(trim(name))")],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index(
        "uq_companies_owner_name_normalized",
        table_name="companies",
    )
    op.drop_index("ix_companies_owner_created_at", table_name="companies")
    op.drop_table("companies")
