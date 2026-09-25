from datetime import datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.orm import Session, joinedload

from app.models.application import Application
from app.models.interview import Interview
from app.models.job import Job


class InterviewRepository:
    MAX_DURATION = timedelta(minutes=480)

    def __init__(self, db: Session):
        self.db = db

    def create(self, interview: Interview) -> Interview:
        self.db.add(interview)
        self.db.flush()
        return interview

    def get_owned(self, interview_id: int, owner_id: int) -> Interview | None:
        return self.db.scalar(
            select(Interview)
            .options(self._read_model_options())
            .where(
                Interview.id == interview_id,
                Interview.owner_id == owner_id,
            )
        )

    def list_owned(
        self,
        owner_id: int,
        *,
        application_id: int | None,
        status: str | None,
        scheduled_from: datetime | None,
        scheduled_to: datetime | None,
        page: int,
        page_size: int,
    ) -> tuple[list[Interview], int]:
        filters = [Interview.owner_id == owner_id]
        if application_id is not None:
            filters.append(Interview.application_id == application_id)
        if status is not None:
            filters.append(Interview.status == status)
        if scheduled_from is not None:
            filters.append(Interview.scheduled_end_at > scheduled_from)
        if scheduled_to is not None:
            filters.append(Interview.scheduled_at < scheduled_to)

        total = self.db.scalar(
            select(func.count()).select_from(Interview).where(*filters)
        )
        statement = (
            select(Interview)
            .options(self._read_model_options())
            .where(*filters)
            .order_by(Interview.scheduled_at.asc(), Interview.id.asc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        return list(self.db.scalars(statement).all()), int(total or 0)

    def list_upcoming(
        self,
        owner_id: int,
        *,
        now: datetime,
        until: datetime | None,
        limit: int,
    ) -> list[Interview]:
        filters = [
            Interview.owner_id == owner_id,
            Interview.status == "scheduled",
            Interview.scheduled_at >= now,
        ]
        if until is not None:
            filters.append(Interview.scheduled_at <= until)
        statement = (
            select(Interview)
            .options(self._read_model_options())
            .where(*filters)
            .order_by(Interview.scheduled_at.asc(), Interview.id.asc())
            .limit(limit)
        )
        return list(self.db.scalars(statement).all())

    def has_overlap(
        self,
        owner_id: int,
        *,
        scheduled_at: datetime,
        duration_minutes: int,
        exclude_id: int | None = None,
    ) -> bool:
        end_at = scheduled_at + timedelta(minutes=duration_minutes)
        filters = [
            Interview.owner_id == owner_id,
            Interview.status == "scheduled",
            Interview.scheduled_at < end_at,
            Interview.scheduled_at > scheduled_at - self.MAX_DURATION,
        ]
        if exclude_id is not None:
            filters.append(Interview.id != exclude_id)
        candidates = self.db.scalars(select(Interview).where(*filters)).all()
        return any(
            candidate.scheduled_at + timedelta(minutes=candidate.duration_minutes)
            > scheduled_at
            for candidate in candidates
        )

    def update(self, interview: Interview, values: dict[str, object]) -> Interview:
        for field, value in values.items():
            setattr(interview, field, value)
        self.db.flush()
        return interview

    def delete(self, interview: Interview) -> None:
        self.db.delete(interview)
        self.db.flush()

    @staticmethod
    def _read_model_options():
        return (
            joinedload(Interview.application, innerjoin=True)
            .joinedload(
                Application.job,
                innerjoin=True,
            )
            .joinedload(
                Job.company,
                innerjoin=True,
            )
        )
