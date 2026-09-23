from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.application import ApplicationStatus
from app.schemas.interview import InterviewType


class DashboardInterview(BaseModel):
    id: int
    application_id: int
    interview_type: InterviewType
    scheduled_at: datetime
    duration_minutes: int

    model_config = ConfigDict(from_attributes=True)


class DashboardAction(BaseModel):
    application_id: int
    job_id: int
    status: ApplicationStatus
    next_action_at: datetime

    model_config = ConfigDict(from_attributes=True)


class DashboardResponse(BaseModel):
    company_count: int = Field(ge=0)
    job_count: int = Field(ge=0)
    application_status_counts: dict[ApplicationStatus, int]
    applications_last_7_days: int = Field(ge=0)
    offer_conversion_rate: float = Field(ge=0, le=1)
    upcoming_interviews: list[DashboardInterview]
    overdue_actions: list[DashboardAction]
    upcoming_actions: list[DashboardAction]
    generated_at: datetime
