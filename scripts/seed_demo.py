"""Create an explicit, local-only JobTrack demonstration dataset."""

from __future__ import annotations

import argparse
import re
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session

from app.auth.security import hash_password
from app.core.config import settings
from app.db.session import SessionLocal
from app.models.application import Application
from app.models.application_status_history import ApplicationStatusHistory
from app.models.company import Company
from app.models.interview import Interview
from app.models.job import Job
from app.models.user import User

SAFE_DATABASE_NAMES = {"fastapi_db", "jobtrack", "jobtrack_dev", "jobtrack_local"}
SAFE_DATABASE_HOSTS = {"localhost", "127.0.0.1", "::1", "postgres"}


@dataclass(frozen=True)
class DemoSeedResult:
    user_id: int
    companies: int
    jobs: int
    applications: int
    interviews: int


def is_safe_demo_database(database_url: str) -> bool:
    url = make_url(database_url)
    database_name = (url.database or "").casefold()
    return (
        url.get_backend_name() == "postgresql"
        and (url.host or "") in SAFE_DATABASE_HOSTS
        and (
            database_name in SAFE_DATABASE_NAMES
            or database_name.endswith(("_test", "_dev", "_local"))
        )
    )


def seed_demo_data(
    db: Session,
    *,
    username: str,
    password: str,
    now: datetime | None = None,
) -> DemoSeedResult:
    if re.fullmatch(r"[A-Za-z0-9_-]{3,40}", username) is None:
        raise ValueError("Username must contain 3-40 letters, digits, '_' or '-'.")
    if len(password) < 12 or len(password.encode("utf-8")) > 72:
        raise ValueError("Password must contain 12-72 UTF-8 bytes.")
    if db.scalar(select(User.id).where(User.username == username)) is not None:
        raise ValueError(
            f"User {username!r} already exists; choose another --username."
        )

    current_time = now or datetime.now(UTC)
    today = current_time.date()
    user = User(
        username=username,
        password=hash_password(password),
        email=f"{username}@example.test",
        email_verified_at=current_time,
    )
    db.add(user)
    db.flush()

    companies = [
        Company(
            owner_id=user.id,
            name="Northstar Labs",
            industry="Developer Tools",
            location="Shanghai",
            website="https://example.test/northstar",
            notes="High-priority product company",
        ),
        Company(
            owner_id=user.id,
            name="Cloud Harbor",
            industry="Cloud Infrastructure",
            location="Remote",
            website="https://example.test/cloud-harbor",
        ),
    ]
    db.add_all(companies)
    db.flush()

    jobs = [
        Job(
            owner_id=user.id,
            company_id=companies[0].id,
            title="Senior Backend Engineer",
            work_mode="hybrid",
            location="Shanghai",
            source="Referral",
            salary_min=3_000_000,
            salary_max=4_000_000,
            salary_currency="CNY",
            description="Build reliable APIs and data-intensive services.",
        ),
        Job(
            owner_id=user.id,
            company_id=companies[1].id,
            title="Platform Engineer",
            work_mode="remote",
            location="Remote",
            source="Company careers page",
            salary_min=3_200_000,
            salary_max=4_500_000,
            salary_currency="CNY",
        ),
        Job(
            owner_id=user.id,
            company_id=companies[0].id,
            title="API Engineer",
            work_mode="onsite",
            location="Shanghai",
            source="Job board",
            status="paused",
        ),
        Job(
            owner_id=user.id,
            company_id=companies[1].id,
            title="Distributed Systems Engineer",
            work_mode="remote",
            location="Remote",
            source="Recruiter",
        ),
    ]
    db.add_all(jobs)
    db.flush()

    applications = [
        Application(
            owner_id=user.id,
            job_id=jobs[0].id,
            status="interview",
            priority=5,
            applied_at=today - timedelta(days=10),
            deadline=today + timedelta(days=5),
            next_action_at=current_time + timedelta(days=1),
            notes="Prepare system-design examples",
        ),
        Application(
            owner_id=user.id,
            job_id=jobs[1].id,
            status="offer",
            priority=5,
            applied_at=today - timedelta(days=20),
            next_action_at=current_time + timedelta(days=2),
            notes="Review compensation package",
        ),
        Application(
            owner_id=user.id,
            job_id=jobs[2].id,
            status="rejected",
            priority=2,
            applied_at=today - timedelta(days=30),
            notes="Keep feedback for future preparation",
        ),
        Application(
            owner_id=user.id,
            job_id=jobs[3].id,
            status="saved",
            priority=4,
            deadline=today + timedelta(days=7),
            next_action_at=current_time - timedelta(hours=6),
            notes="Tailor resume before applying",
        ),
    ]
    db.add_all(applications)
    db.flush()

    transitions = (
        (applications[0], ("saved", "applied", "screening", "interview")),
        (
            applications[1],
            ("saved", "applied", "screening", "interview", "offer"),
        ),
        (applications[2], ("saved", "applied", "rejected")),
    )
    history_rows = []
    sequence = 0
    for application, states in transitions:
        for from_status, to_status in zip(states, states[1:]):
            sequence += 1
            history_rows.append(
                ApplicationStatusHistory(
                    application_id=application.id,
                    from_status=from_status,
                    to_status=to_status,
                    changed_at=current_time - timedelta(days=40 - sequence),
                )
            )
    db.add_all(history_rows)

    interviews = [
        Interview(
            owner_id=user.id,
            application_id=applications[0].id,
            interview_type="system_design",
            status="scheduled",
            scheduled_at=current_time + timedelta(days=2),
            duration_minutes=60,
            meeting_url="https://meet.example.test/system-design",
            notes="Review scaling and consistency trade-offs",
        ),
        Interview(
            owner_id=user.id,
            application_id=applications[1].id,
            interview_type="hiring_manager",
            status="completed",
            scheduled_at=current_time - timedelta(days=2),
            duration_minutes=45,
            location="Video call",
            feedback="Strong alignment on ownership and execution",
        ),
    ]
    db.add_all(interviews)
    db.flush()

    return DemoSeedResult(
        user_id=user.id,
        companies=len(companies),
        jobs=len(jobs),
        applications=len(applications),
        interviews=len(interviews),
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Create a local-only JobTrack demo user and dataset."
    )
    parser.add_argument("--confirm", action="store_true", help="Confirm the write.")
    parser.add_argument("--username", default="jobtrack_demo")
    parser.add_argument("--password", default="JobTrackDemo123!")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if not args.confirm:
        raise SystemExit("Refusing to write without --confirm.")
    if settings.ENVIRONMENT.casefold() == "production":
        raise SystemExit("Refusing to seed demo data in production.")
    if not is_safe_demo_database(settings.DATABASE_URL):
        raise SystemExit("Refusing a non-local or non-demo PostgreSQL database.")

    with SessionLocal() as db:
        try:
            result = seed_demo_data(
                db,
                username=args.username,
                password=args.password,
            )
            db.commit()
        except Exception:
            db.rollback()
            raise

    print(
        "Created JobTrack demo data: "
        f"user_id={result.user_id}, companies={result.companies}, "
        f"jobs={result.jobs}, applications={result.applications}, "
        f"interviews={result.interviews}."
    )
    print(f"Login username: {args.username}")
    print("Use the password supplied to --password (or the documented local default).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
