from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.business_observability import observe_business_write
from app.exceptions.domain import ResourceConflictError, ResourceNotFoundError
from app.models.company import Company
from app.repositories.company_repository import CompanyRepository
from app.schemas.company import CompanyCreate, CompanyListResponse, CompanyUpdate
from app.services.dashboard_cache import invalidate_dashboard_cache

COMPANY_NOT_FOUND = "Company not found"
COMPANY_NAME_CONFLICT = "A company with this name already exists"
COMPANY_HAS_JOBS = "Company cannot be deleted while it has jobs"


class CompanyService:
    def __init__(self, db: Session):
        self.db = db
        self.repository = CompanyRepository(db)

    @observe_business_write("company", "create")
    def create(self, owner_id: int, data: CompanyCreate) -> Company:
        if self.repository.get_by_normalized_name(owner_id, data.name):
            raise ResourceConflictError(COMPANY_NAME_CONFLICT)

        company = Company(
            owner_id=owner_id,
            **self._database_values(data.model_dump()),
        )
        try:
            self.repository.create(company)
            self.db.commit()
            self.db.refresh(company)
            invalidate_dashboard_cache(owner_id)
            return company
        except IntegrityError as exc:
            self.db.rollback()
            raise ResourceConflictError(COMPANY_NAME_CONFLICT) from exc
        except Exception:
            self.db.rollback()
            raise

    def get(self, owner_id: int, company_id: int) -> Company:
        company = self.repository.get_owned(company_id, owner_id)
        if company is None:
            raise ResourceNotFoundError(COMPANY_NOT_FOUND)
        return company

    def list(
        self,
        owner_id: int,
        *,
        keyword: str | None,
        industry: str | None,
        location: str | None,
        page: int,
        page_size: int,
    ) -> CompanyListResponse:
        companies, total = self.repository.list_owned(
            owner_id,
            keyword=keyword,
            industry=industry,
            location=location,
            page=page,
            page_size=page_size,
        )
        return CompanyListResponse(
            items=companies,
            total=total,
            page=page,
            page_size=page_size,
        )

    @observe_business_write("company", "update")
    def update(
        self,
        owner_id: int,
        company_id: int,
        data: CompanyUpdate,
    ) -> Company:
        company = self.get(owner_id, company_id)
        values = self._database_values(data.model_dump(exclude_unset=True))
        new_name = values.get("name")
        if isinstance(new_name, str) and self.repository.get_by_normalized_name(
            owner_id,
            new_name,
            exclude_id=company.id,
        ):
            raise ResourceConflictError(COMPANY_NAME_CONFLICT)

        try:
            self.repository.update(company, values)
            self.db.commit()
            self.db.refresh(company)
            invalidate_dashboard_cache(owner_id)
            return company
        except IntegrityError as exc:
            self.db.rollback()
            raise ResourceConflictError(COMPANY_NAME_CONFLICT) from exc
        except Exception:
            self.db.rollback()
            raise

    @observe_business_write("company", "delete")
    def delete(self, owner_id: int, company_id: int) -> None:
        company = self.get(owner_id, company_id)
        if self.repository.has_jobs(company.id, owner_id):
            raise ResourceConflictError(COMPANY_HAS_JOBS)
        try:
            self.repository.delete(company)
            self.db.commit()
            invalidate_dashboard_cache(owner_id)
        except IntegrityError as exc:
            self.db.rollback()
            raise ResourceConflictError(COMPANY_HAS_JOBS) from exc
        except Exception:
            self.db.rollback()
            raise

    @staticmethod
    def _database_values(values: dict[str, object]) -> dict[str, object]:
        website = values.get("website")
        if website is not None:
            values["website"] = str(website)
        return values
