"""enforce parent ownership

Revision ID: f8c1d4e7a920
Revises: d7b9f6a2c410
Create Date: 2026-09-23
"""

from typing import Sequence, Union

from alembic import op

revision: str = "f8c1d4e7a920"
down_revision: Union[str, Sequence[str], None] = "d7b9f6a2c410"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_unique_constraint(
        "uq_companies_owner_id",
        "companies",
        ["owner_id", "id"],
    )
    op.create_unique_constraint(
        "uq_jobs_owner_id",
        "jobs",
        ["owner_id", "id"],
    )
    op.create_unique_constraint(
        "uq_applications_owner_id",
        "applications",
        ["owner_id", "id"],
    )

    op.create_foreign_key(
        "fk_jobs_owner_company",
        "jobs",
        "companies",
        ["owner_id", "company_id"],
        ["owner_id", "id"],
        ondelete="RESTRICT",
    )
    op.create_foreign_key(
        "fk_applications_owner_job",
        "applications",
        "jobs",
        ["owner_id", "job_id"],
        ["owner_id", "id"],
        ondelete="RESTRICT",
    )
    op.create_foreign_key(
        "fk_interviews_owner_application",
        "interviews",
        "applications",
        ["owner_id", "application_id"],
        ["owner_id", "id"],
        ondelete="RESTRICT",
    )

    op.drop_constraint("jobs_company_id_fkey", "jobs", type_="foreignkey")
    op.drop_constraint(
        "applications_job_id_fkey",
        "applications",
        type_="foreignkey",
    )
    op.drop_constraint(
        "interviews_application_id_fkey",
        "interviews",
        type_="foreignkey",
    )


def downgrade() -> None:
    op.create_foreign_key(
        "jobs_company_id_fkey",
        "jobs",
        "companies",
        ["company_id"],
        ["id"],
        ondelete="RESTRICT",
    )
    op.create_foreign_key(
        "applications_job_id_fkey",
        "applications",
        "jobs",
        ["job_id"],
        ["id"],
        ondelete="RESTRICT",
    )
    op.create_foreign_key(
        "interviews_application_id_fkey",
        "interviews",
        "applications",
        ["application_id"],
        ["id"],
        ondelete="RESTRICT",
    )

    op.drop_constraint(
        "fk_interviews_owner_application",
        "interviews",
        type_="foreignkey",
    )
    op.drop_constraint(
        "fk_applications_owner_job",
        "applications",
        type_="foreignkey",
    )
    op.drop_constraint("fk_jobs_owner_company", "jobs", type_="foreignkey")

    op.drop_constraint(
        "uq_applications_owner_id",
        "applications",
        type_="unique",
    )
    op.drop_constraint("uq_jobs_owner_id", "jobs", type_="unique")
    op.drop_constraint("uq_companies_owner_id", "companies", type_="unique")
