from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.business_observability import observe_business_write
from app.exceptions.domain import ResourceConflictError, ResourceNotFoundError
from app.models.job import Job
from app.repositories.company_repository import CompanyRepository
from app.repositories.job_repository import JobRepository
from app.schemas.job import (
    JobCreate,
    JobListResponse,
    JobSortField,
    JobUpdate,
    SortOrder,
)
from app.services.dashboard_cache import invalidate_dashboard_cache

JOB_NOT_FOUND = "Job not found"
JOB_CONFLICT = "Job conflicts with an existing resource"
JOB_HAS_APPLICATIONS = "Job cannot be deleted while it has applications"
COMPANY_NOT_FOUND = "Company not found"


class JobService:
    def __init__(self, db: Session):
        self.db = db
        self.repository = JobRepository(db)
        self.company_repository = CompanyRepository(db)

    @observe_business_write("job", "create")
    def create(self, owner_id: int, data: JobCreate) -> Job:
        self._require_owned_company(data.company_id, owner_id)
        job = Job(owner_id=owner_id, **self._database_values(data.model_dump()))
        try:
            self.repository.create(job)
            self.db.commit()
            self.db.refresh(job)
            invalidate_dashboard_cache(owner_id)
            return job
        except IntegrityError as exc:
            self.db.rollback()
            raise ResourceConflictError(JOB_CONFLICT) from exc
        except Exception:
            self.db.rollback()
            raise

    def get(self, owner_id: int, job_id: int) -> Job:
        job = self.repository.get_owned(job_id, owner_id)
        if job is None:
            raise ResourceNotFoundError(JOB_NOT_FOUND)
        return job

    def list(
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
    ) -> JobListResponse:
        jobs, total = self.repository.list_owned(
            owner_id,
            company_id=company_id,
            status=status,
            work_mode=work_mode,
            keyword=keyword,
            sort_by=sort_by,
            sort_order=sort_order,
            page=page,
            page_size=page_size,
        )
        return JobListResponse(
            items=jobs,
            total=total,
            page=page,
            page_size=page_size,
        )

    @observe_business_write("job", "update")
    def update(self, owner_id: int, job_id: int, data: JobUpdate) -> Job:
        job = self.get(owner_id, job_id)
        values = self._database_values(data.model_dump(exclude_unset=True))
        company_id = values.get("company_id")
        if isinstance(company_id, int):
            self._require_owned_company(company_id, owner_id)

        salary_min = values.get("salary_min", job.salary_min)
        salary_max = values.get("salary_max", job.salary_max)
        if (
            isinstance(salary_min, int)
            and isinstance(salary_max, int)
            and salary_min > salary_max
        ):
            raise ResourceConflictError("salary_min cannot exceed salary_max")

        try:
            self.repository.update(job, values)
            self.db.commit()
            self.db.refresh(job)
            invalidate_dashboard_cache(owner_id)
            return job
        except IntegrityError as exc:
            self.db.rollback()
            raise ResourceConflictError(JOB_CONFLICT) from exc
        except Exception:
            self.db.rollback()
            raise

    @observe_business_write("job", "delete")
    def delete(self, owner_id: int, job_id: int) -> None:
        job = self.get(owner_id, job_id)
        if self.repository.has_applications(job.id, owner_id):
            raise ResourceConflictError(JOB_HAS_APPLICATIONS)
        try:
            self.repository.delete(job)
            self.db.commit()
            invalidate_dashboard_cache(owner_id)
        except IntegrityError as exc:
            self.db.rollback()
            raise ResourceConflictError(JOB_HAS_APPLICATIONS) from exc
        except Exception:
            self.db.rollback()
            raise

    def _require_owned_company(self, company_id: int, owner_id: int) -> None:
        if self.company_repository.get_owned(company_id, owner_id) is None:
            raise ResourceNotFoundError(COMPANY_NOT_FOUND)

    @staticmethod
    def _database_values(values: dict[str, object]) -> dict[str, object]:
        url = values.get("url")
        if url is not None:
            values["url"] = str(url)
        for field in ("employment_type", "work_mode", "status"):
            value = values.get(field)
            if value is not None:
                values[field] = str(value)
        return values
