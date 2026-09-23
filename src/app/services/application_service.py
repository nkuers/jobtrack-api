from __future__ import annotations

from datetime import UTC, date, datetime

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.business_observability import observe_business_write
from app.exceptions.domain import ResourceConflictError, ResourceNotFoundError
from app.models.application import Application
from app.models.application_status_history import ApplicationStatusHistory
from app.repositories.application_repository import ApplicationRepository
from app.repositories.job_repository import JobRepository
from app.schemas.application import (
    ApplicationCreate,
    ApplicationListResponse,
    ApplicationSortField,
    ApplicationStatus,
    ApplicationUpdate,
    SortOrder,
)
from app.services.dashboard_cache import invalidate_dashboard_cache

APPLICATION_NOT_FOUND = "Application not found"
APPLICATION_CONFLICT = "An application for this job already exists"
INVALID_STATUS_TRANSITION = "Invalid application status transition"
INVALID_APPLICATION_DATES = "deadline cannot be before applied_at"
APPLICATION_HAS_INTERVIEWS = "Application cannot be deleted while it has interviews"
JOB_NOT_FOUND = "Job not found"

ALLOWED_STATUS_TRANSITIONS: dict[ApplicationStatus, frozenset[ApplicationStatus]] = {
    ApplicationStatus.SAVED: frozenset(
        {ApplicationStatus.APPLIED, ApplicationStatus.WITHDRAWN}
    ),
    ApplicationStatus.APPLIED: frozenset(
        {
            ApplicationStatus.SCREENING,
            ApplicationStatus.REJECTED,
            ApplicationStatus.WITHDRAWN,
        }
    ),
    ApplicationStatus.SCREENING: frozenset(
        {
            ApplicationStatus.INTERVIEW,
            ApplicationStatus.REJECTED,
            ApplicationStatus.WITHDRAWN,
        }
    ),
    ApplicationStatus.INTERVIEW: frozenset(
        {
            ApplicationStatus.OFFER,
            ApplicationStatus.REJECTED,
            ApplicationStatus.WITHDRAWN,
        }
    ),
    ApplicationStatus.OFFER: frozenset({ApplicationStatus.ARCHIVED}),
    ApplicationStatus.REJECTED: frozenset({ApplicationStatus.ARCHIVED}),
    ApplicationStatus.WITHDRAWN: frozenset({ApplicationStatus.ARCHIVED}),
    ApplicationStatus.ARCHIVED: frozenset(),
}


class ApplicationService:
    def __init__(self, db: Session):
        self.db = db
        self.repository = ApplicationRepository(db)
        self.job_repository = JobRepository(db)

    @observe_business_write("application", "create")
    def create(self, owner_id: int, data: ApplicationCreate) -> Application:
        if self.job_repository.get_owned(data.job_id, owner_id) is None:
            raise ResourceNotFoundError(JOB_NOT_FOUND)
        if self.repository.get_by_job(data.job_id, owner_id) is not None:
            raise ResourceConflictError(APPLICATION_CONFLICT)

        values = self._database_values(data.model_dump())
        if data.status == ApplicationStatus.APPLIED and data.applied_at is None:
            values["applied_at"] = datetime.now(UTC).date()
        if (
            values["applied_at"] is not None
            and values["deadline"] is not None
            and values["deadline"] < values["applied_at"]
        ):
            raise ResourceConflictError(INVALID_APPLICATION_DATES)
        application = Application(owner_id=owner_id, **values)
        try:
            self.repository.create(application)
            self.db.commit()
            self.db.refresh(application)
            invalidate_dashboard_cache(owner_id)
            return application
        except IntegrityError as exc:
            self.db.rollback()
            raise ResourceConflictError(APPLICATION_CONFLICT) from exc
        except Exception:
            self.db.rollback()
            raise

    def get(self, owner_id: int, application_id: int) -> Application:
        application = self.repository.get_owned(application_id, owner_id)
        if application is None:
            raise ResourceNotFoundError(APPLICATION_NOT_FOUND)
        return application

    def list(
        self,
        owner_id: int,
        *,
        status: str | None,
        company_id: int | None,
        applied_from: date | None,
        applied_to: date | None,
        priority: int | None,
        next_action_before: datetime | None,
        sort_by: ApplicationSortField,
        sort_order: SortOrder,
        page: int,
        page_size: int,
    ) -> ApplicationListResponse:
        applications, total = self.repository.list_owned(
            owner_id,
            status=status,
            company_id=company_id,
            applied_from=applied_from,
            applied_to=applied_to,
            priority=priority,
            next_action_before=next_action_before,
            sort_by=sort_by,
            sort_order=sort_order,
            page=page,
            page_size=page_size,
        )
        return ApplicationListResponse(
            items=applications,
            total=total,
            page=page,
            page_size=page_size,
        )

    @observe_business_write("application", "update")
    def update(
        self,
        owner_id: int,
        application_id: int,
        data: ApplicationUpdate,
    ) -> Application:
        application = self.get(owner_id, application_id)
        values = data.model_dump(exclude_unset=True)
        applied_at = values.get("applied_at", application.applied_at)
        deadline = values.get("deadline", application.deadline)
        if applied_at is not None and deadline is not None and deadline < applied_at:
            raise ResourceConflictError(INVALID_APPLICATION_DATES)
        if application.status == ApplicationStatus.SAVED and applied_at is not None:
            raise ResourceConflictError("A saved application cannot have applied_at")
        if application.status != ApplicationStatus.SAVED and applied_at is None:
            raise ResourceConflictError("An active application must have applied_at")

        try:
            self.repository.update(application, values)
            self.db.commit()
            self.db.refresh(application)
            invalidate_dashboard_cache(owner_id)
            return application
        except Exception:
            self.db.rollback()
            raise

    @observe_business_write("application", "status_change")
    def change_status(
        self,
        owner_id: int,
        application_id: int,
        target_status: ApplicationStatus,
    ) -> Application:
        try:
            application = self.repository.get_owned_for_update(
                application_id,
                owner_id,
            )
            if application is None:
                raise ResourceNotFoundError(APPLICATION_NOT_FOUND)

            current_status = ApplicationStatus(application.status)
            if target_status not in ALLOWED_STATUS_TRANSITIONS[current_status]:
                raise ResourceConflictError(INVALID_STATUS_TRANSITION)

            history = ApplicationStatusHistory(
                application_id=application.id,
                from_status=current_status.value,
                to_status=target_status.value,
            )
            application.status = target_status.value
            if (
                target_status == ApplicationStatus.APPLIED
                and application.applied_at is None
            ):
                application.applied_at = datetime.now(UTC).date()
                if (
                    application.deadline is not None
                    and application.deadline < application.applied_at
                ):
                    raise ResourceConflictError(INVALID_APPLICATION_DATES)
            self.repository.add_history(history)
            self.db.flush()
            self.db.commit()
            self.db.refresh(application)
            invalidate_dashboard_cache(owner_id)
            return application
        except (ResourceNotFoundError, ResourceConflictError):
            self.db.rollback()
            raise
        except Exception:
            self.db.rollback()
            raise

    def history(
        self,
        owner_id: int,
        application_id: int,
    ) -> list[ApplicationStatusHistory]:
        application = self.get(owner_id, application_id)
        return self.repository.list_history(application.id)

    @observe_business_write("application", "delete")
    def delete(self, owner_id: int, application_id: int) -> None:
        application = self.get(owner_id, application_id)
        if self.repository.has_interviews(application.id, owner_id):
            raise ResourceConflictError(APPLICATION_HAS_INTERVIEWS)
        try:
            self.repository.delete(application)
            self.db.commit()
            invalidate_dashboard_cache(owner_id)
        except IntegrityError as exc:
            self.db.rollback()
            raise ResourceConflictError(APPLICATION_HAS_INTERVIEWS) from exc
        except Exception:
            self.db.rollback()
            raise

    @staticmethod
    def _database_values(values: dict[str, object]) -> dict[str, object]:
        status = values.get("status")
        if status is not None:
            values["status"] = str(status)
        return values
