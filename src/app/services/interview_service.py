from __future__ import annotations

from datetime import UTC, datetime, timedelta

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.business_observability import observe_business_write
from app.exceptions.domain import ResourceConflictError, ResourceNotFoundError
from app.models.interview import Interview
from app.repositories.application_repository import ApplicationRepository
from app.repositories.interview_repository import InterviewRepository
from app.schemas.interview import (
    InterviewCreate,
    InterviewListResponse,
    InterviewStatus,
    InterviewUpdate,
)
from app.services.dashboard_cache import invalidate_dashboard_cache

INTERVIEW_NOT_FOUND = "Interview not found"
APPLICATION_NOT_FOUND = "Application not found"
INTERVIEW_CONFLICT = "Interview overlaps another scheduled interview"
INVALID_INTERVIEW_STATUS = "Invalid interview status transition"
FEEDBACK_REQUIRES_COMPLETED = "Feedback is only allowed for completed interviews"

ALLOWED_STATUS_TRANSITIONS = {
    InterviewStatus.SCHEDULED: frozenset(
        {InterviewStatus.COMPLETED, InterviewStatus.CANCELLED}
    ),
    InterviewStatus.COMPLETED: frozenset(),
    InterviewStatus.CANCELLED: frozenset(),
}


class InterviewService:
    def __init__(self, db: Session):
        self.db = db
        self.repository = InterviewRepository(db)
        self.application_repository = ApplicationRepository(db)

    @observe_business_write("interview", "create")
    def create(self, owner_id: int, data: InterviewCreate) -> Interview:
        if self.application_repository.get_owned(data.application_id, owner_id) is None:
            raise ResourceNotFoundError(APPLICATION_NOT_FOUND)
        if self.repository.has_overlap(
            owner_id,
            scheduled_at=data.scheduled_at,
            duration_minutes=data.duration_minutes,
        ):
            raise ResourceConflictError(INTERVIEW_CONFLICT)

        interview = Interview(
            owner_id=owner_id,
            scheduled_end_at=self._scheduled_end(
                data.scheduled_at,
                data.duration_minutes,
            ),
            **self._database_values(data.model_dump()),
        )
        try:
            self.repository.create(interview)
            self.db.commit()
            self.db.refresh(interview)
            invalidate_dashboard_cache(owner_id)
            return interview
        except IntegrityError as exc:
            self.db.rollback()
            raise ResourceConflictError(
                "Interview conflicts with an existing resource"
            ) from exc
        except Exception:
            self.db.rollback()
            raise

    def get(self, owner_id: int, interview_id: int) -> Interview:
        interview = self.repository.get_owned(interview_id, owner_id)
        if interview is None:
            raise ResourceNotFoundError(INTERVIEW_NOT_FOUND)
        return interview

    def list(
        self,
        owner_id: int,
        *,
        application_id: int | None,
        status: str | None,
        page: int,
        page_size: int,
    ) -> InterviewListResponse:
        interviews, total = self.repository.list_owned(
            owner_id,
            application_id=application_id,
            status=status,
            page=page,
            page_size=page_size,
        )
        return InterviewListResponse(
            items=interviews,
            total=total,
            page=page,
            page_size=page_size,
        )

    def upcoming(
        self,
        owner_id: int,
        *,
        until: datetime | None,
        limit: int,
    ) -> list[Interview]:
        now = datetime.now(UTC)
        if until is not None and until < now:
            raise ResourceConflictError("until cannot be in the past")
        return self.repository.list_upcoming(
            owner_id,
            now=now,
            until=until,
            limit=limit,
        )

    @observe_business_write("interview", "update")
    def update(
        self,
        owner_id: int,
        interview_id: int,
        data: InterviewUpdate,
    ) -> Interview:
        interview = self.get(owner_id, interview_id)
        values = self._database_values(data.model_dump(exclude_unset=True))
        target_status = InterviewStatus(values.get("status", interview.status))
        current_status = InterviewStatus(interview.status)
        if (
            target_status != current_status
            and target_status not in ALLOWED_STATUS_TRANSITIONS[current_status]
        ):
            raise ResourceConflictError(INVALID_INTERVIEW_STATUS)

        feedback = values.get("feedback", interview.feedback)
        if feedback is not None and target_status != InterviewStatus.COMPLETED:
            raise ResourceConflictError(FEEDBACK_REQUIRES_COMPLETED)

        scheduled_at = values.get("scheduled_at", interview.scheduled_at)
        duration_minutes = values.get("duration_minutes", interview.duration_minutes)
        values["scheduled_end_at"] = self._scheduled_end(
            scheduled_at,
            duration_minutes,
        )
        if target_status == InterviewStatus.SCHEDULED and self.repository.has_overlap(
            owner_id,
            scheduled_at=scheduled_at,
            duration_minutes=duration_minutes,
            exclude_id=interview.id,
        ):
            raise ResourceConflictError(INTERVIEW_CONFLICT)

        try:
            self.repository.update(interview, values)
            self.db.commit()
            self.db.refresh(interview)
            invalidate_dashboard_cache(owner_id)
            return interview
        except IntegrityError as exc:
            self.db.rollback()
            raise ResourceConflictError(INTERVIEW_CONFLICT) from exc
        except Exception:
            self.db.rollback()
            raise

    @observe_business_write("interview", "delete")
    def delete(self, owner_id: int, interview_id: int) -> None:
        interview = self.get(owner_id, interview_id)
        try:
            self.repository.delete(interview)
            self.db.commit()
            invalidate_dashboard_cache(owner_id)
        except Exception:
            self.db.rollback()
            raise

    @staticmethod
    def _database_values(values: dict[str, object]) -> dict[str, object]:
        for field in ("interview_type", "status"):
            value = values.get(field)
            if value is not None:
                values[field] = str(value)
        meeting_url = values.get("meeting_url")
        if meeting_url is not None:
            values["meeting_url"] = str(meeting_url)
        return values

    @staticmethod
    def _scheduled_end(
        scheduled_at: datetime,
        duration_minutes: int,
    ) -> datetime:
        return scheduled_at + timedelta(minutes=duration_minutes)
