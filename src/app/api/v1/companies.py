from typing import Annotated

from fastapi import APIRouter, Depends, Query, Response, status
from sqlalchemy.orm import Session

from app.auth.current_user import get_current_user
from app.db.dependency import get_db
from app.dependencies.business_rate_limit import enforce_business_write_rate_limit
from app.models.user import User
from app.schemas.company import (
    CompanyCreate,
    CompanyListResponse,
    CompanyResponse,
    CompanyUpdate,
)
from app.services.company_service import CompanyService

router = APIRouter(
    prefix="/api/v1/companies",
    tags=["Companies"],
)


@router.post(
    "",
    response_model=CompanyResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(enforce_business_write_rate_limit)],
)
def create_company(
    data: CompanyCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return CompanyService(db).create(current_user.id, data)


@router.get("", response_model=CompanyListResponse)
def list_companies(
    keyword: Annotated[str | None, Query(max_length=120)] = None,
    industry: Annotated[str | None, Query(max_length=100)] = None,
    location: Annotated[str | None, Query(max_length=255)] = None,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return CompanyService(db).list(
        current_user.id,
        keyword=keyword,
        industry=industry,
        location=location,
        page=page,
        page_size=page_size,
    )


@router.get("/{company_id}", response_model=CompanyResponse)
def get_company(
    company_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return CompanyService(db).get(current_user.id, company_id)


@router.patch(
    "/{company_id}",
    response_model=CompanyResponse,
    dependencies=[Depends(enforce_business_write_rate_limit)],
)
def update_company(
    company_id: int,
    data: CompanyUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return CompanyService(db).update(current_user.id, company_id, data)


@router.delete(
    "/{company_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(enforce_business_write_rate_limit)],
)
def delete_company(
    company_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Response:
    CompanyService(db).delete(current_user.id, company_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
