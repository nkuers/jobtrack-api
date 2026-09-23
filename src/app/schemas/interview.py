from datetime import UTC, datetime
from enum import StrEnum
from typing import Annotated

from pydantic import (
    AfterValidator,
    AnyHttpUrl,
    BaseModel,
    ConfigDict,
    Field,
    field_validator,
)


class InterviewType(StrEnum):
    PHONE_SCREEN = "phone_screen"
    TECHNICAL = "technical"
    BEHAVIORAL = "behavioral"
    SYSTEM_DESIGN = "system_design"
    HIRING_MANAGER = "hiring_manager"
    ONSITE = "onsite"
    OTHER = "other"


class InterviewStatus(StrEnum):
    SCHEDULED = "scheduled"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


def _require_timezone(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("Datetime must include a timezone")
    return value.astimezone(UTC)


def _strip_optional(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = value.strip()
    return normalized or None


AwareDatetime = Annotated[datetime, AfterValidator(_require_timezone)]
DurationMinutes = Annotated[int, Field(ge=15, le=480)]
Location = Annotated[str, Field(max_length=255)]
LongText = Annotated[str, Field(max_length=10000)]
MeetingUrl = Annotated[AnyHttpUrl, Field(max_length=2048)]


class InterviewCreate(BaseModel):
    application_id: Annotated[int, Field(gt=0)]
    interview_type: InterviewType
    scheduled_at: AwareDatetime
    duration_minutes: DurationMinutes = 60
    location: Location | None = None
    meeting_url: MeetingUrl | None = None
    notes: LongText | None = None

    model_config = ConfigDict(extra="forbid")

    _normalize_text = field_validator("location", "notes")(_strip_optional)


class InterviewUpdate(BaseModel):
    interview_type: InterviewType | None = None
    status: InterviewStatus | None = None
    scheduled_at: AwareDatetime | None = None
    duration_minutes: DurationMinutes | None = None
    location: Location | None = None
    meeting_url: MeetingUrl | None = None
    notes: LongText | None = None
    feedback: LongText | None = None

    model_config = ConfigDict(extra="forbid")

    @field_validator(
        "interview_type",
        "status",
        "scheduled_at",
        "duration_minutes",
    )
    @classmethod
    def reject_null_required_fields(cls, value):
        if value is None:
            raise ValueError("Field cannot be null")
        return value

    _normalize_text = field_validator("location", "notes", "feedback")(_strip_optional)


class InterviewResponse(BaseModel):
    id: int
    application_id: int
    interview_type: InterviewType
    status: InterviewStatus
    scheduled_at: datetime
    duration_minutes: int
    location: str | None = None
    meeting_url: AnyHttpUrl | None = None
    notes: str | None = None
    feedback: str | None = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class InterviewListResponse(BaseModel):
    items: list[InterviewResponse]
    total: int
    page: int
    page_size: int
