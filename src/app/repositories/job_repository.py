from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.models.application import Application
from app.models.job import Job
from app.schemas.job import JobSortField, SortOrder


class JobRepository:
    SORT_COLUMNS = {
        JobSortField.CREATED_AT: Job.created_at,
        JobSortField.UPDATED_AT: Job.updated_at,
        JobSortField.TITLE: Job.title,
        JobSortField.SALARY_MIN: Job.salary_min,
        JobSortField.SALARY_MAX: Job.salary_max,
    }

    def __init__(self, db: Session):
        self.db = db

    def create(self, job: Job) -> Job:
        self.db.add(job)
        self.db.flush()
        return job

    def get_owned(self, job_id: int, owner_id: int) -> Job | None:
        return self.db.scalar(
            select(Job).where(Job.id == job_id, Job.owner_id == owner_id)
        )

    def list_owned(
        self,
        owner_id: int,
        *,
        company_id: int | None,
        status: str | None,
        work_mode: str | None,
        keyword: str | None,
        sort_by: JobSortField,
        sort_order: SortOrder,
        page: int,
        page_size: int,
    ) -> tuple[list[Job], int]:
        filters = [Job.owner_id == owner_id]
        if company_id is not None:
            filters.append(Job.company_id == company_id)
        if status is not None:
            filters.append(Job.status == status)
        if work_mode is not None:
            filters.append(Job.work_mode == work_mode)
        if keyword:
            pattern = f"%{keyword}%"
            filters.append(
                or_(
                    Job.title.ilike(pattern),
                    Job.location.ilike(pattern),
                    Job.source.ilike(pattern),
                )
            )

        total = self.db.scalar(select(func.count()).select_from(Job).where(*filters))
        sort_column = self.SORT_COLUMNS[sort_by]
        order_expression = (
            sort_column.asc() if sort_order == SortOrder.ASC else sort_column.desc()
        )
        statement = (
            select(Job)
            .where(*filters)
            .order_by(order_expression, Job.id.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        return list(self.db.scalars(statement).all()), int(total or 0)

    def update(self, job: Job, values: dict[str, object]) -> Job:
        for field, value in values.items():
            setattr(job, field, value)
        self.db.flush()
        return job

    def delete(self, job: Job) -> None:
        self.db.delete(job)
        self.db.flush()

    def has_applications(self, job_id: int, owner_id: int) -> bool:
        statement = select(Application.id).where(
            Application.job_id == job_id,
            Application.owner_id == owner_id,
        )
        return self.db.scalar(statement.limit(1)) is not None
