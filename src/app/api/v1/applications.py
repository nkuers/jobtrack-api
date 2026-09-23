from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, Query, Response, status
from sqlalchemy.orm import Session

from app.auth.current_user import get_current_user
from app.db.dependency import get_db
from app.dependencies.business_rate_limit import enforce_business_write_rate_limit
from app.models.user import User
from app.schemas.application import (
    ApplicationCreate,
    ApplicationListResponse,
    ApplicationResponse,
    ApplicationSortField,
    ApplicationStatus,
    ApplicationStatusHistoryResponse,
    ApplicationStatusUpdate,
    ApplicationUpdate,
    AwareDatetime,
    SortOrder,
)
from app.services.application_service import ApplicationService

router = APIRouter(prefix="/api/v1/applications", tags=["Applications"])


@router.post(
    "",
    response_model=ApplicationResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(enforce_business_write_rate_limit)],
)
def create_application(
    data: ApplicationCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return ApplicationService(db).create(current_user.id, data)


@router.get("", response_model=ApplicationListResponse)
def list_applications(
    application_status: Annotated[
        ApplicationStatus | None,
        Query(alias="status"),
    ] = None,
    company_id: Annotated[int | None, Query(gt=0)] = None,
    applied_from: date | None = None,
    applied_to: date | None = None,
    priority: Annotated[int | None, Query(ge=1, le=5)] = None,
    next_action_before: AwareDatetime | None = None,
    sort_by: ApplicationSortField = ApplicationSortField.CREATED_AT,
    sort_order: SortOrder = SortOrder.DESC,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return ApplicationService(db).list(
        current_user.id,
        status=application_status,
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


@router.get("/{application_id}", response_model=ApplicationResponse)
def get_application(
    application_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return ApplicationService(db).get(current_user.id, application_id)


@router.patch(
    "/{application_id}",
    response_model=ApplicationResponse,
    dependencies=[Depends(enforce_business_write_rate_limit)],
)
def update_application(
    application_id: int,
    data: ApplicationUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return ApplicationService(db).update(current_user.id, application_id, data)


@router.patch(
    "/{application_id}/status",
    response_model=ApplicationResponse,
    dependencies=[Depends(enforce_business_write_rate_limit)],
)
def change_application_status(
    application_id: int,
    data: ApplicationStatusUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return ApplicationService(db).change_status(
        current_user.id,
        application_id,
        data.status,
    )


@router.get(
    "/{application_id}/history",
    response_model=list[ApplicationStatusHistoryResponse],
)
def list_application_history(
    application_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return ApplicationService(db).history(current_user.id, application_id)


@router.delete(
    "/{application_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(enforce_business_write_rate_limit)],
)
def delete_application(
    application_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Response:
    ApplicationService(db).delete(current_user.id, application_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
