from datetime import UTC, datetime

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Job(Base):
    __tablename__ = "jobs"
    __table_args__ = (
        CheckConstraint(
            "employment_type IN "
            "('full_time', 'part_time', 'contract', 'internship', 'temporary')",
            name="ck_jobs_employment_type",
        ),
        CheckConstraint(
            "work_mode IN ('onsite', 'hybrid', 'remote')",
            name="ck_jobs_work_mode",
        ),
        CheckConstraint(
            "status IN ('open', 'paused', 'closed')",
            name="ck_jobs_status",
        ),
        CheckConstraint(
            "salary_min IS NULL OR salary_min >= 0",
            name="ck_jobs_salary_min_nonnegative",
        ),
        CheckConstraint(
            "salary_max IS NULL OR salary_max >= 0",
            name="ck_jobs_salary_max_nonnegative",
        ),
        CheckConstraint(
            "salary_min IS NULL OR salary_max IS NULL OR salary_min <= salary_max",
            name="ck_jobs_salary_range",
        ),
        CheckConstraint(
            "salary_currency ~ '^[A-Z]{3}$'",
            name="ck_jobs_salary_currency",
        ),
        Index("ix_jobs_owner_created_at", "owner_id", "created_at"),
        Index("ix_jobs_owner_status_updated_at", "owner_id", "status", "updated_at"),
        Index("ix_jobs_owner_company", "owner_id", "company_id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    owner_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    company_id: Mapped[int] = mapped_column(
        ForeignKey("companies.id", ondelete="RESTRICT"),
        nullable=False,
    )
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    employment_type: Mapped[str] = mapped_column(
        String(20), nullable=False, default="full_time"
    )
    work_mode: Mapped[str] = mapped_column(String(20), nullable=False, default="onsite")
    location: Mapped[str | None] = mapped_column(String(255), nullable=True)
    source: Mapped[str | None] = mapped_column(String(100), nullable=True)
    url: Mapped[str | None] = mapped_column(String(2048), nullable=True)
    salary_min: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    salary_max: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    salary_currency: Mapped[str] = mapped_column(
        String(3), nullable=False, default="CNY"
    )
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="open")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
        nullable=False,
    )
