from datetime import datetime, timedelta

from sqlalchemy import distinct, func, or_, select
from sqlalchemy.orm import Session

from app.models.application import Application
from app.models.application_status_history import ApplicationStatusHistory
from app.models.company import Company
from app.models.interview import Interview
from app.models.job import Job
from app.schemas.application import ApplicationStatus
from app.schemas.dashboard import (
    DashboardAction,
    DashboardInterview,
    DashboardResponse,
)

ACTIONABLE_STATUSES = (
    ApplicationStatus.SAVED.value,
    ApplicationStatus.APPLIED.value,
    ApplicationStatus.SCREENING.value,
    ApplicationStatus.INTERVIEW.value,
    ApplicationStatus.OFFER.value,
)
LIST_LIMIT = 20


class DashboardRepository:
    def __init__(self, db: Session):
        self.db = db

    def aggregate(self, owner_id: int, *, now: datetime) -> DashboardResponse:
        company_count, job_count = self.db.execute(
            select(
                select(func.count(Company.id))
                .where(Company.owner_id == owner_id)
                .scalar_subquery(),
                select(func.count(Job.id))
                .where(Job.owner_id == owner_id)
                .scalar_subquery(),
            )
        ).one()

        status_rows = self.db.execute(
            select(Application.status, func.count(Application.id))
            .where(Application.owner_id == owner_id)
            .group_by(Application.status)
        ).all()
        status_counts = {status: 0 for status in ApplicationStatus}
        status_counts.update(
            {ApplicationStatus(status): int(count) for status, count in status_rows}
        )

        recent_count = self.db.scalar(
            select(func.count(Application.id)).where(
                Application.owner_id == owner_id,
                Application.created_at >= now - timedelta(days=7),
            )
        )
        applied_count = self.db.scalar(
            select(func.count(Application.id)).where(
                Application.owner_id == owner_id,
                Application.applied_at.is_not(None),
            )
        )
        offer_count = self.db.scalar(
            select(func.count(distinct(Application.id)))
            .select_from(Application)
            .outerjoin(
                ApplicationStatusHistory,
                ApplicationStatusHistory.application_id == Application.id,
            )
            .where(
                Application.owner_id == owner_id,
                Application.applied_at.is_not(None),
                or_(
                    Application.status == ApplicationStatus.OFFER.value,
                    ApplicationStatusHistory.to_status == ApplicationStatus.OFFER.value,
                ),
            )
        )
        applied_total = int(applied_count or 0)
        conversion_rate = (
            round(int(offer_count or 0) / applied_total, 4) if applied_total else 0.0
        )

        horizon = now + timedelta(days=7)
        interview_rows = self.db.scalars(
            select(Interview)
            .where(
                Interview.owner_id == owner_id,
                Interview.status == "scheduled",
                Interview.scheduled_at >= now,
                Interview.scheduled_at <= horizon,
            )
            .order_by(Interview.scheduled_at.asc(), Interview.id.asc())
            .limit(LIST_LIMIT)
        ).all()

        overdue_rows = self.db.scalars(
            self._action_query(owner_id)
            .where(Application.next_action_at < now)
            .order_by(Application.next_action_at.asc(), Application.id.asc())
            .limit(LIST_LIMIT)
        ).all()
        upcoming_rows = self.db.scalars(
            self._action_query(owner_id)
            .where(
                Application.next_action_at >= now,
                Application.next_action_at <= horizon,
            )
            .order_by(Application.next_action_at.asc(), Application.id.asc())
            .limit(LIST_LIMIT)
        ).all()

        return DashboardResponse(
            company_count=int(company_count or 0),
            job_count=int(job_count or 0),
            application_status_counts=status_counts,
            applications_last_7_days=int(recent_count or 0),
            offer_conversion_rate=conversion_rate,
            upcoming_interviews=[
                DashboardInterview.model_validate(interview)
                for interview in interview_rows
            ],
            overdue_actions=[self._action(item) for item in overdue_rows],
            upcoming_actions=[self._action(item) for item in upcoming_rows],
            generated_at=now,
        )

    @staticmethod
    def _action_query(owner_id: int):
        return select(Application).where(
            Application.owner_id == owner_id,
            Application.status.in_(ACTIONABLE_STATUSES),
            Application.next_action_at.is_not(None),
        )

    @staticmethod
    def _action(application: Application) -> DashboardAction:
        return DashboardAction(
            application_id=application.id,
            job_id=application.job_id,
            status=application.status,
            next_action_at=application.next_action_at,
        )
