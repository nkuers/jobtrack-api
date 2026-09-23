from datetime import UTC, datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.application import APPLICATION_STATUS_SQL


class ApplicationStatusHistory(Base):
    __tablename__ = "application_status_history"
    __table_args__ = (
        CheckConstraint(
            f"from_status IN ({APPLICATION_STATUS_SQL})",
            name="ck_application_status_history_from_status",
        ),
        CheckConstraint(
            f"to_status IN ({APPLICATION_STATUS_SQL})",
            name="ck_application_status_history_to_status",
        ),
        CheckConstraint(
            "from_status <> to_status",
            name="ck_application_status_history_changed",
        ),
        Index(
            "ix_application_status_history_application_changed_at",
            "application_id",
            "changed_at",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    application_id: Mapped[int] = mapped_column(
        ForeignKey("applications.id", ondelete="CASCADE"),
        nullable=False,
    )
    from_status: Mapped[str] = mapped_column(String(20), nullable=False)
    to_status: Mapped[str] = mapped_column(String(20), nullable=False)
    changed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False,
    )
