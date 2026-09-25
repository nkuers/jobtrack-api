from datetime import UTC, date, datetime
from enum import StrEnum
from typing import Annotated, Self

from pydantic import (
    AfterValidator,
    BaseModel,
    ConfigDict,
    Field,
    field_validator,
    model_validator,
)

from app.schemas.job import JobSummary

Priority = Annotated[int, Field(ge=1, le=5)]
Notes = Annotated[str, Field(max_length=10000)]


class ApplicationStatus(StrEnum):
    SAVED = "saved"
    APPLIED = "applied"
    SCREENING = "screening"
    INTERVIEW = "interview"
    OFFER = "offer"
    REJECTED = "rejected"
    WITHDRAWN = "withdrawn"
    ARCHIVED = "archived"


class ApplicationSortField(StrEnum):
    CREATED_AT = "created_at"
    UPDATED_AT = "updated_at"
    APPLIED_AT = "applied_at"
    DEADLINE = "deadline"
    NEXT_ACTION_AT = "next_action_at"
    PRIORITY = "priority"


class SortOrder(StrEnum):
    ASC = "asc"
    DESC = "desc"


def _normalize_notes(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = value.strip()
    return normalized or None


def _require_timezone(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("Datetime must include a timezone")
    return value.astimezone(UTC)


AwareDatetime = Annotated[datetime, AfterValidator(_require_timezone)]


class ApplicationCreate(BaseModel):
    job_id: Annotated[int, Field(gt=0)]
    status: ApplicationStatus = ApplicationStatus.SAVED
    priority: Priority = 3
    applied_at: date | None = None
    deadline: date | None = None
    next_action_at: AwareDatetime | None = None
    notes: Notes | None = None

    model_config = ConfigDict(extra="forbid")

    _normalize_notes = field_validator("notes")(_normalize_notes)

    @model_validator(mode="after")
    def validate_initial_state(self) -> Self:
        if self.status not in {ApplicationStatus.SAVED, ApplicationStatus.APPLIED}:
            raise ValueError("Initial status must be saved or applied")
        if self.status == ApplicationStatus.SAVED and self.applied_at is not None:
            raise ValueError("A saved application cannot have applied_at")
        if (
            self.applied_at is not None
            and self.deadline is not None
            and self.deadline < self.applied_at
        ):
            raise ValueError("deadline cannot be before applied_at")
        return self


class ApplicationUpdate(BaseModel):
    priority: Priority | None = None
    applied_at: date | None = None
    deadline: date | None = None
    next_action_at: AwareDatetime | None = None
    notes: Notes | None = None

    model_config = ConfigDict(extra="forbid")

    @field_validator("priority")
    @classmethod
    def reject_null_priority(cls, value: int | None) -> int:
        if value is None:
            raise ValueError("priority cannot be null")
        return value

    _normalize_notes = field_validator("notes")(_normalize_notes)

    @model_validator(mode="after")
    def validate_supplied_dates(self) -> Self:
        if (
            self.applied_at is not None
            and self.deadline is not None
            and self.deadline < self.applied_at
        ):
            raise ValueError("deadline cannot be before applied_at")
        return self


class ApplicationStatusUpdate(BaseModel):
    status: ApplicationStatus

    model_config = ConfigDict(extra="forbid")


class ApplicationResponse(BaseModel):
    id: int
    job_id: int
    status: ApplicationStatus
    priority: int
    applied_at: date | None = None
    deadline: date | None = None
    next_action_at: datetime | None = None
    notes: str | None = None
    created_at: datetime
    updated_at: datetime
    job_summary: JobSummary = Field(validation_alias="job")

    model_config = ConfigDict(from_attributes=True)


class ApplicationSummary(BaseModel):
    id: int
    job_id: int
    status: ApplicationStatus
    priority: int
    job_summary: JobSummary = Field(validation_alias="job")

    model_config = ConfigDict(from_attributes=True)


class ApplicationListResponse(BaseModel):
    items: list[ApplicationResponse]
    total: int
    page: int
    page_size: int


class ApplicationStatusHistoryResponse(BaseModel):
    id: int
    application_id: int
    from_status: ApplicationStatus
    to_status: ApplicationStatus
    changed_at: datetime

    model_config = ConfigDict(from_attributes=True)
