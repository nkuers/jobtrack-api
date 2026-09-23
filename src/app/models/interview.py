from datetime import UTC, datetime

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base

INTERVIEW_TYPES = (
    "phone_screen",
    "technical",
    "behavioral",
    "system_design",
    "hiring_manager",
    "onsite",
    "other",
)
INTERVIEW_STATUSES = ("scheduled", "completed", "cancelled")
INTERVIEW_TYPE_SQL = ", ".join(f"'{value}'" for value in INTERVIEW_TYPES)
INTERVIEW_STATUS_SQL = ", ".join(f"'{value}'" for value in INTERVIEW_STATUSES)


class Interview(Base):
    __tablename__ = "interviews"
    __table_args__ = (
        CheckConstraint(
            f"interview_type IN ({INTERVIEW_TYPE_SQL})",
            name="ck_interviews_type",
        ),
        CheckConstraint(
            f"status IN ({INTERVIEW_STATUS_SQL})",
            name="ck_interviews_status",
        ),
        CheckConstraint(
            "duration_minutes BETWEEN 15 AND 480",
            name="ck_interviews_duration",
        ),
        Index("ix_interviews_owner_scheduled_at", "owner_id", "scheduled_at"),
        Index("ix_interviews_owner_application", "owner_id", "application_id"),
        Index(
            "ix_interviews_owner_status_scheduled", "owner_id", "status", "scheduled_at"
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    owner_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    application_id: Mapped[int] = mapped_column(
        ForeignKey("applications.id", ondelete="RESTRICT"),
        nullable=False,
    )
    interview_type: Mapped[str] = mapped_column(String(30), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="scheduled")
    scheduled_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    duration_minutes: Mapped[int] = mapped_column(Integer, nullable=False, default=60)
    location: Mapped[str | None] = mapped_column(String(255), nullable=True)
    meeting_url: Mapped[str | None] = mapped_column(String(2048), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    feedback: Mapped[str | None] = mapped_column(Text, nullable=True)
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
