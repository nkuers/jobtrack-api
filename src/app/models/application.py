from datetime import UTC, date, datetime

from sqlalchemy import (
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    ForeignKeyConstraint,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base

APPLICATION_STATUSES = (
    "saved",
    "applied",
    "screening",
    "interview",
    "offer",
    "rejected",
    "withdrawn",
    "archived",
)
APPLICATION_STATUS_SQL = ", ".join(f"'{value}'" for value in APPLICATION_STATUSES)


class Application(Base):
    __tablename__ = "applications"
    __table_args__ = (
        UniqueConstraint(
            "owner_id",
            "id",
            name="uq_applications_owner_id",
        ),
        ForeignKeyConstraint(
            ["owner_id", "job_id"],
            ["jobs.owner_id", "jobs.id"],
            name="fk_applications_owner_job",
            ondelete="RESTRICT",
        ),
        UniqueConstraint(
            "owner_id",
            "job_id",
            name="uq_applications_owner_job",
        ),
        CheckConstraint(
            f"status IN ({APPLICATION_STATUS_SQL})",
            name="ck_applications_status",
        ),
        CheckConstraint(
            "priority BETWEEN 1 AND 5",
            name="ck_applications_priority",
        ),
        Index("ix_applications_owner_created_at", "owner_id", "created_at"),
        Index(
            "ix_applications_owner_status_updated_at",
            "owner_id",
            "status",
            "updated_at",
        ),
        Index(
            "ix_applications_owner_next_action_at",
            "owner_id",
            "next_action_at",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    owner_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    job_id: Mapped[int] = mapped_column(
        nullable=False,
    )
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="saved")
    priority: Mapped[int] = mapped_column(Integer, nullable=False, default=3)
    applied_at: Mapped[date | None] = mapped_column(Date, nullable=True)
    deadline: Mapped[date | None] = mapped_column(Date, nullable=True)
    next_action_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
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
