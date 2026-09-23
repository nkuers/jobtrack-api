from typing import Annotated

from fastapi import APIRouter, Depends, Query, Response, status
from sqlalchemy.orm import Session

from app.auth.current_user import get_current_user
from app.db.dependency import get_db
from app.dependencies.business_rate_limit import enforce_business_write_rate_limit
from app.models.user import User
from app.schemas.interview import (
    AwareDatetime,
    InterviewCreate,
    InterviewListResponse,
    InterviewResponse,
    InterviewStatus,
    InterviewUpdate,
)
from app.services.interview_service import InterviewService

router = APIRouter(prefix="/api/v1/interviews", tags=["Interviews"])


@router.post(
    "",
    response_model=InterviewResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(enforce_business_write_rate_limit)],
)
def create_interview(
    data: InterviewCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return InterviewService(db).create(current_user.id, data)


@router.get("", response_model=InterviewListResponse)
def list_interviews(
    application_id: Annotated[int | None, Query(gt=0)] = None,
    interview_status: Annotated[InterviewStatus | None, Query(alias="status")] = None,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return InterviewService(db).list(
        current_user.id,
        application_id=application_id,
        status=interview_status,
        page=page,
        page_size=page_size,
    )


@router.get("/upcoming", response_model=list[InterviewResponse])
def list_upcoming_interviews(
    until: AwareDatetime | None = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return InterviewService(db).upcoming(current_user.id, until=until, limit=limit)


@router.get("/{interview_id}", response_model=InterviewResponse)
def get_interview(
    interview_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return InterviewService(db).get(current_user.id, interview_id)


@router.patch(
    "/{interview_id}",
    response_model=InterviewResponse,
    dependencies=[Depends(enforce_business_write_rate_limit)],
)
def update_interview(
    interview_id: int,
    data: InterviewUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return InterviewService(db).update(current_user.id, interview_id, data)


@router.delete(
    "/{interview_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(enforce_business_write_rate_limit)],
)
def delete_interview(
    interview_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Response:
    InterviewService(db).delete(current_user.id, interview_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
