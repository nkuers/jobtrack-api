from datetime import date, datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session, joinedload

from app.models.application import Application
from app.models.application_status_history import ApplicationStatusHistory
from app.models.interview import Interview
from app.models.job import Job
from app.schemas.application import ApplicationSortField, SortOrder


class ApplicationRepository:
    SORT_COLUMNS = {
        ApplicationSortField.CREATED_AT: Application.created_at,
        ApplicationSortField.UPDATED_AT: Application.updated_at,
        ApplicationSortField.APPLIED_AT: Application.applied_at,
        ApplicationSortField.DEADLINE: Application.deadline,
        ApplicationSortField.NEXT_ACTION_AT: Application.next_action_at,
        ApplicationSortField.PRIORITY: Application.priority,
    }

    def __init__(self, db: Session):
        self.db = db

    def create(self, application: Application) -> Application:
        self.db.add(application)
        self.db.flush()
        return application

    def get_owned(self, application_id: int, owner_id: int) -> Application | None:
        return self.db.scalar(
            select(Application)
            .options(
                joinedload(Application.job, innerjoin=True).joinedload(
                    Job.company,
                    innerjoin=True,
                )
            )
            .where(
                Application.id == application_id,
                Application.owner_id == owner_id,
            )
        )

    def get_owned_for_update(
        self,
        application_id: int,
        owner_id: int,
    ) -> Application | None:
        statement = (
            select(Application)
            .where(
                Application.id == application_id,
                Application.owner_id == owner_id,
            )
            .with_for_update()
        )
        return self.db.scalar(statement)

    def get_by_job(self, job_id: int, owner_id: int) -> Application | None:
        return self.db.scalar(
            select(Application).where(
                Application.job_id == job_id,
                Application.owner_id == owner_id,
            )
        )

    def list_owned(
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
    ) -> tuple[list[Application], int]:
        filters = [Application.owner_id == owner_id]
        if status is not None:
            filters.append(Application.status == status)
        if company_id is not None:
            filters.append(Job.company_id == company_id)
        if applied_from is not None:
            filters.append(Application.applied_at >= applied_from)
        if applied_to is not None:
            filters.append(Application.applied_at <= applied_to)
        if priority is not None:
            filters.append(Application.priority == priority)
        if next_action_before is not None:
            filters.append(Application.next_action_at <= next_action_before)

        count_statement = (
            select(func.count())
            .select_from(Application)
            .join(Job, Job.id == Application.job_id)
            .where(*filters)
        )
        total = self.db.scalar(count_statement)
        sort_column = self.SORT_COLUMNS[sort_by]
        order_expression = (
            sort_column.asc() if sort_order == SortOrder.ASC else sort_column.desc()
        )
        statement = (
            select(Application)
            .options(
                joinedload(Application.job, innerjoin=True).joinedload(
                    Job.company,
                    innerjoin=True,
                )
            )
            .join(Job, Job.id == Application.job_id)
            .where(*filters)
            .order_by(order_expression, Application.id.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        return list(self.db.scalars(statement).all()), int(total or 0)

    def update(
        self,
        application: Application,
        values: dict[str, object],
    ) -> Application:
        for field, value in values.items():
            setattr(application, field, value)
        self.db.flush()
        return application

    def add_history(self, history: ApplicationStatusHistory) -> None:
        self.db.add(history)
        self.db.flush()

    def list_history(
        self,
        application_id: int,
    ) -> list[ApplicationStatusHistory]:
        statement = (
            select(ApplicationStatusHistory)
            .where(ApplicationStatusHistory.application_id == application_id)
            .order_by(
                ApplicationStatusHistory.changed_at.asc(),
                ApplicationStatusHistory.id.asc(),
            )
        )
        return list(self.db.scalars(statement).all())

    def has_interviews(self, application_id: int, owner_id: int) -> bool:
        return (
            self.db.scalar(
                select(Interview.id)
                .where(
                    Interview.application_id == application_id,
                    Interview.owner_id == owner_id,
                )
                .limit(1)
            )
            is not None
        )

    def delete(self, application: Application) -> None:
        self.db.delete(application)
        self.db.flush()
