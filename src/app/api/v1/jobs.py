from typing import Annotated

from fastapi import APIRouter, Depends, Query, Response, status
from sqlalchemy.orm import Session

from app.auth.current_user import get_current_user
from app.db.dependency import get_db
from app.dependencies.business_rate_limit import enforce_business_write_rate_limit
from app.models.user import User
from app.schemas.job import (
    JobCreate,
    JobListResponse,
    JobResponse,
    JobSortField,
    JobStatus,
    JobUpdate,
    SortOrder,
    WorkMode,
)
from app.services.job_service import JobService

router = APIRouter(prefix="/api/v1/jobs", tags=["Jobs"])


@router.post(
    "",
    response_model=JobResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(enforce_business_write_rate_limit)],
)
def create_job(
    data: JobCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return JobService(db).create(current_user.id, data)


@router.get("", response_model=JobListResponse)
def list_jobs(
    company_id: Annotated[int | None, Query(gt=0)] = None,
    job_status: Annotated[JobStatus | None, Query(alias="status")] = None,
    work_mode: WorkMode | None = None,
    keyword: Annotated[str | None, Query(max_length=200)] = None,
    sort_by: JobSortField = JobSortField.CREATED_AT,
    sort_order: SortOrder = SortOrder.DESC,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return JobService(db).list(
        current_user.id,
        company_id=company_id,
        status=job_status,
        work_mode=work_mode,
        keyword=keyword,
        sort_by=sort_by,
        sort_order=sort_order,
        page=page,
        page_size=page_size,
    )


@router.get("/{job_id}", response_model=JobResponse)
def get_job(
    job_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return JobService(db).get(current_user.id, job_id)


@router.patch(
    "/{job_id}",
    response_model=JobResponse,
    dependencies=[Depends(enforce_business_write_rate_limit)],
)
def update_job(
    job_id: int,
    data: JobUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return JobService(db).update(current_user.id, job_id, data)


@router.delete(
    "/{job_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(enforce_business_write_rate_limit)],
)
def delete_job(
    job_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Response:
    JobService(db).delete(current_user.id, job_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
