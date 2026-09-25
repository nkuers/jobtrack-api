from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.application import ApplicationStatus, ApplicationSummary
from app.schemas.interview import InterviewType
from app.schemas.job import JobSummary


class DashboardInterview(BaseModel):
    id: int
    application_id: int
    interview_type: InterviewType
    scheduled_at: datetime
    duration_minutes: int
    application_summary: ApplicationSummary = Field(validation_alias="application")

    model_config = ConfigDict(from_attributes=True)


class DashboardAction(BaseModel):
    application_id: int
    job_id: int
    status: ApplicationStatus
    next_action_at: datetime
    job_summary: JobSummary

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
