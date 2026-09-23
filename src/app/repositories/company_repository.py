from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.models.company import Company
from app.models.job import Job


class CompanyRepository:
    def __init__(self, db: Session):
        self.db = db

    def create(self, company: Company) -> Company:
        self.db.add(company)
        self.db.flush()
        return company

    def get_owned(self, company_id: int, owner_id: int) -> Company | None:
        statement = select(Company).where(
            Company.id == company_id,
            Company.owner_id == owner_id,
        )
        return self.db.scalar(statement)

    def get_by_normalized_name(
        self,
        owner_id: int,
        name: str,
        *,
        exclude_id: int | None = None,
    ) -> Company | None:
        statement = select(Company).where(
            Company.owner_id == owner_id,
            func.lower(func.trim(Company.name)) == name.strip().casefold(),
        )
        if exclude_id is not None:
            statement = statement.where(Company.id != exclude_id)
        return self.db.scalar(statement)

    def list_owned(
        self,
        owner_id: int,
        *,
        keyword: str | None,
        industry: str | None,
        location: str | None,
        page: int,
        page_size: int,
    ) -> tuple[list[Company], int]:
        filters = [Company.owner_id == owner_id]
        if keyword:
            pattern = f"%{keyword}%"
            filters.append(
                or_(
                    Company.name.ilike(pattern),
                    Company.industry.ilike(pattern),
                    Company.location.ilike(pattern),
                )
            )
        if industry:
            filters.append(Company.industry.ilike(industry))
        if location:
            filters.append(Company.location.ilike(f"%{location}%"))

        total = self.db.scalar(
            select(func.count()).select_from(Company).where(*filters)
        )
        statement = (
            select(Company)
            .where(*filters)
            .order_by(Company.created_at.desc(), Company.id.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        return list(self.db.scalars(statement).all()), int(total or 0)

    def update(self, company: Company, values: dict[str, object]) -> Company:
        for field, value in values.items():
            setattr(company, field, value)
        self.db.flush()
        return company

    def delete(self, company: Company) -> None:
        self.db.delete(company)
        self.db.flush()

    def has_jobs(self, company_id: int, owner_id: int) -> bool:
        statement = select(Job.id).where(
            Job.company_id == company_id,
            Job.owner_id == owner_id,
        )
        return self.db.scalar(statement.limit(1)) is not None
