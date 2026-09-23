"""prevent concurrent interview overlaps

Revision ID: d7b9f6a2c410
Revises: c6a8e4f5b321
Create Date: 2026-09-23
"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

revision: str = "d7b9f6a2c410"
down_revision: Union[str, Sequence[str], None] = "c6a8e4f5b321"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS btree_gist")
    op.add_column(
        "interviews",
        sa.Column("scheduled_end_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.execute(
        "UPDATE interviews "
        "SET scheduled_end_at = "
        "scheduled_at + duration_minutes * INTERVAL '1 minute'"
    )
    op.alter_column("interviews", "scheduled_end_at", nullable=False)
    op.create_check_constraint(
        "ck_interviews_scheduled_window",
        "interviews",
        "scheduled_end_at = scheduled_at + duration_minutes * INTERVAL '1 minute'",
    )
    op.execute(
        "ALTER TABLE interviews "
        "ADD CONSTRAINT ex_interviews_owner_scheduled_window "
        "EXCLUDE USING gist ("
        "owner_id WITH =, "
        "tstzrange(scheduled_at, scheduled_end_at, '[)') WITH &&"
        ") WHERE (status = 'scheduled')"
    )


def downgrade() -> None:
    op.execute(
        "ALTER TABLE interviews DROP CONSTRAINT ex_interviews_owner_scheduled_window"
    )
    op.drop_constraint(
        "ck_interviews_scheduled_window",
        "interviews",
        type_="check",
    )
    op.drop_column("interviews", "scheduled_end_at")
