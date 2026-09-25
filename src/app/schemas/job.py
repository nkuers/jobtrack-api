from datetime import datetime
from enum import StrEnum
from typing import Annotated, Self

from pydantic import (
    AnyHttpUrl,
    BaseModel,
    ConfigDict,
    Field,
    field_validator,
    model_validator,
)

from app.schemas.company import CompanySummary

JobTitle = Annotated[str, Field(min_length=1, max_length=200)]
Location = Annotated[str, Field(min_length=1, max_length=255)]
Source = Annotated[str, Field(min_length=1, max_length=100)]
JobUrl = Annotated[AnyHttpUrl, Field(max_length=2048)]
Description = Annotated[str, Field(max_length=20000)]
Salary = Annotated[int, Field(ge=0, le=9_223_372_036_854_775_807)]
Currency = Annotated[str, Field(pattern=r"^[A-Za-z]{3}$")]


class EmploymentType(StrEnum):
    FULL_TIME = "full_time"
    PART_TIME = "part_time"
    CONTRACT = "contract"
    INTERNSHIP = "internship"
    TEMPORARY = "temporary"


class WorkMode(StrEnum):
    ONSITE = "onsite"
    HYBRID = "hybrid"
    REMOTE = "remote"


class JobStatus(StrEnum):
    OPEN = "open"
    PAUSED = "paused"
    CLOSED = "closed"


class JobSortField(StrEnum):
    CREATED_AT = "created_at"
    UPDATED_AT = "updated_at"
    TITLE = "title"
    SALARY_MIN = "salary_min"
    SALARY_MAX = "salary_max"


class SortOrder(StrEnum):
    ASC = "asc"
    DESC = "desc"


def _strip_required(value: str) -> str:
    normalized = value.strip()
    if not normalized:
        raise ValueError("Value cannot be blank")
    return normalized


def _strip_optional(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = value.strip()
    return normalized or None


class SalaryRangeMixin(BaseModel):
    salary_min: Salary | None = None
    salary_max: Salary | None = None
    salary_currency: Currency = "CNY"

    @field_validator("salary_currency")
    @classmethod
    def normalize_currency(cls, value: str) -> str:
        return value.upper()

    @model_validator(mode="after")
    def validate_salary_range(self) -> Self:
        if (
            self.salary_min is not None
            and self.salary_max is not None
            and self.salary_min > self.salary_max
        ):
            raise ValueError("salary_min cannot exceed salary_max")
        return self


class JobCreate(SalaryRangeMixin):
    company_id: Annotated[int, Field(gt=0)]
    title: JobTitle
    employment_type: EmploymentType = EmploymentType.FULL_TIME
    work_mode: WorkMode = WorkMode.ONSITE
    location: Location | None = None
    source: Source | None = None
    url: JobUrl | None = None
    description: Description | None = None
    status: JobStatus = JobStatus.OPEN

    model_config = ConfigDict(extra="forbid")

    _normalize_title = field_validator("title")(_strip_required)
    _normalize_optional_text = field_validator(
        "location",
        "source",
        "description",
    )(_strip_optional)


class JobUpdate(BaseModel):
    company_id: Annotated[int, Field(gt=0)] | None = None
    title: JobTitle | None = None
    employment_type: EmploymentType | None = None
    work_mode: WorkMode | None = None
    location: Location | None = None
    source: Source | None = None
    url: JobUrl | None = None
    salary_min: Salary | None = None
    salary_max: Salary | None = None
    salary_currency: Currency | None = None
    description: Description | None = None
    status: JobStatus | None = None

    model_config = ConfigDict(extra="forbid")

    @field_validator("company_id", "title", "employment_type", "work_mode", "status")
    @classmethod
    def reject_null_required_fields(cls, value):
        if value is None:
            raise ValueError("Field cannot be null")
        return value

    @field_validator("title")
    @classmethod
    def normalize_optional_title(cls, value: str | None) -> str | None:
        return _strip_required(value) if value is not None else value

    @field_validator("salary_currency")
    @classmethod
    def normalize_optional_currency(cls, value: str | None) -> str | None:
        if value is None:
            raise ValueError("salary_currency cannot be null")
        return value.upper()

    _normalize_optional_text = field_validator(
        "location",
        "source",
        "description",
    )(_strip_optional)

    @model_validator(mode="after")
    def validate_supplied_salary_range(self) -> Self:
        if (
            self.salary_min is not None
            and self.salary_max is not None
            and self.salary_min > self.salary_max
        ):
            raise ValueError("salary_min cannot exceed salary_max")
        return self


class JobResponse(BaseModel):
    id: int
    company_id: int
    title: str
    employment_type: EmploymentType
    work_mode: WorkMode
    location: str | None = None
    source: str | None = None
    url: AnyHttpUrl | None = None
    salary_min: int | None = None
    salary_max: int | None = None
    salary_currency: str
    description: str | None = None
    status: JobStatus
    company_summary: CompanySummary = Field(validation_alias="company")
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class JobSummary(BaseModel):
    id: int
    company_id: int
    title: str
    status: JobStatus
    company_summary: CompanySummary = Field(validation_alias="company")

    model_config = ConfigDict(from_attributes=True)


class JobListResponse(BaseModel):
    items: list[JobResponse]
    total: int
    page: int
    page_size: int
