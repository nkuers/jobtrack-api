import importlib.util
import sys
from datetime import UTC, datetime
from pathlib import Path

import pytest
from sqlalchemy import func, select

from app.models.application import Application
from app.models.application_status_history import ApplicationStatusHistory
from app.models.company import Company
from app.models.interview import Interview
from app.models.job import Job
from app.models.user import User

SCRIPT_PATH = Path(__file__).resolve().parents[1] / "scripts" / "seed_demo.py"
SPEC = importlib.util.spec_from_file_location("seed_demo_script", SCRIPT_PATH)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError(f"Unable to load demonstration seed script from {SCRIPT_PATH}")
seed_demo = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = seed_demo
SPEC.loader.exec_module(seed_demo)


@pytest.mark.parametrize(
    ("database_url", "expected"),
    [
        ("postgresql+psycopg://user:pass@localhost/jobtrack", True),
        ("postgresql://user:pass@postgres/fastapi_test", True),
        ("postgresql://user:pass@db.example.com/jobtrack", False),
        ("postgresql://user:pass@localhost/production", False),
        ("sqlite:///jobtrack.db", False),
    ],
)
def test_demo_database_allowlist(database_url, expected):
    assert seed_demo.is_safe_demo_database(database_url) is expected


def test_demo_seed_creates_a_complete_jobtrack_story(db_session):
    now = datetime(2026, 9, 22, 8, 0, tzinfo=UTC)

    result = seed_demo.seed_demo_data(
        db_session,
        username="demo_candidate",
        password="DemoPassword123!",
        now=now,
    )
    db_session.commit()

    assert (result.companies, result.jobs, result.applications, result.interviews) == (
        2,
        4,
        4,
        2,
    )
    assert (
        db_session.scalar(
            select(func.count())
            .select_from(Company)
            .where(Company.owner_id == result.user_id)
        )
        == 2
    )
    assert (
        db_session.scalar(
            select(func.count()).select_from(Job).where(Job.owner_id == result.user_id)
        )
        == 4
    )
    assert (
        db_session.scalar(
            select(func.count())
            .select_from(Application)
            .where(Application.owner_id == result.user_id)
        )
        == 4
    )
    assert (
        db_session.scalar(
            select(func.count())
            .select_from(Interview)
            .where(Interview.owner_id == result.user_id)
        )
        == 2
    )
    assert (
        db_session.scalar(select(func.count()).select_from(ApplicationStatusHistory))
        == 9
    )


def test_demo_seed_rejects_an_existing_username(db_session):
    db_session.add(User(username="demo_taken", password="not-used-by-this-test"))
    db_session.commit()

    with pytest.raises(ValueError, match="already exists"):
        seed_demo.seed_demo_data(
            db_session,
            username="demo_taken",
            password="DemoPassword123!",
        )
