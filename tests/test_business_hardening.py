import asyncio
import json
import logging
from datetime import UTC, datetime, timedelta

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from redis.exceptions import ConnectionError
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.auth.jwt import create_access_token
from app.core.business_observability import record_business_operation
from app.core.logging import JsonFormatter
from app.core.metrics import BUSINESS_OPERATIONS_TOTAL
from app.dependencies import business_rate_limit
from app.middlewares.rate_limit import RateLimiter
from app.models.application import Application
from app.models.company import Company
from app.models.interview import Interview
from app.models.job import Job
from app.models.user import User


def test_business_write_limit_is_per_user_and_does_not_limit_reads(
    client: TestClient,
    auth_headers: dict[str, str],
    second_user: User,
    monkeypatch,
):
    monkeypatch.setattr(business_rate_limit.settings, "RATE_LIMIT_BACKEND", "memory")
    monkeypatch.setattr(
        business_rate_limit,
        "business_write_limiter",
        RateLimiter(limit=2, window=60),
    )

    assert (
        client.post(
            "/api/v1/companies",
            headers=auth_headers,
            json={"name": "Rate One"},
        ).status_code
        == 201
    )
    assert (
        client.post(
            "/api/v1/companies",
            headers=auth_headers,
            json={"name": "Rate Two"},
        ).status_code
        == 201
    )
    blocked = client.post(
        "/api/v1/companies",
        headers=auth_headers,
        json={"name": "Rate Three"},
    )
    assert blocked.status_code == 429
    assert blocked.json() == {"detail": "Too many write requests"}
    assert int(blocked.headers["retry-after"]) >= 1
    assert client.get("/api/v1/companies", headers=auth_headers).status_code == 200

    second_headers = {
        "Authorization": f"Bearer {create_access_token({'sub': second_user.username})}"
    }
    assert (
        client.post(
            "/api/v1/companies",
            headers=second_headers,
            json={"name": "Other User Write"},
        ).status_code
        == 201
    )


def test_business_write_redis_failure_is_explicitly_fail_open(monkeypatch):
    class BrokenLimiter:
        async def check(self, subject: str):
            raise ConnectionError("private backend detail")

    monkeypatch.setattr(business_rate_limit.settings, "RATE_LIMIT_BACKEND", "redis")
    monkeypatch.setattr(
        business_rate_limit.settings,
        "BUSINESS_WRITE_RATE_LIMIT_FAILURE_MODE",
        "open",
    )
    monkeypatch.setattr(business_rate_limit, "_redis_limiter", BrokenLimiter)

    result = asyncio.run(
        business_rate_limit.enforce_business_write_rate_limit(
            current_user=User(id=11, username="limited", password="unused")
        )
    )

    assert result is None


def test_business_write_redis_failure_can_fail_closed(monkeypatch):
    class BrokenLimiter:
        async def check(self, subject: str):
            raise ConnectionError("private backend detail")

    monkeypatch.setattr(business_rate_limit.settings, "RATE_LIMIT_BACKEND", "redis")
    monkeypatch.setattr(
        business_rate_limit.settings,
        "BUSINESS_WRITE_RATE_LIMIT_FAILURE_MODE",
        "closed",
    )
    monkeypatch.setattr(business_rate_limit, "_redis_limiter", BrokenLimiter)

    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(
            business_rate_limit.enforce_business_write_rate_limit(
                current_user=User(id=11, username="limited", password="unused")
            )
        )

    assert exc_info.value.status_code == 503


def test_business_metrics_and_logs_use_only_bounded_safe_fields(caplog):
    caplog.set_level(logging.INFO, logger="jobtrack-api.business")

    record_business_operation("application", "status_change", "conflict")

    record = caplog.records[-1]
    payload = json.loads(JsonFormatter().format(record))
    assert payload["resource_type"] == "application"
    assert payload["resource_operation"] == "status_change"
    assert payload["resource_outcome"] == "conflict"
    assert "owner" not in payload
    assert "notes" not in payload
    assert "email" not in payload
    assert BUSINESS_OPERATIONS_TOTAL._labelnames == (
        "resource",
        "operation",
        "outcome",
    )


@pytest.mark.parametrize(
    "path",
    (
        "/api/v1/companies",
        "/api/v1/jobs",
        "/api/v1/applications",
        "/api/v1/interviews",
    ),
)
def test_business_lists_reject_page_sizes_above_global_maximum(
    client: TestClient,
    auth_headers: dict[str, str],
    path: str,
):
    response = client.get(path, headers=auth_headers, params={"page_size": 101})
    assert response.status_code == 422


def test_upcoming_interviews_reject_limit_above_global_maximum(
    client: TestClient,
    auth_headers: dict[str, str],
):
    response = client.get(
        "/api/v1/interviews/upcoming",
        headers=auth_headers,
        params={"limit": 101},
    )
    assert response.status_code == 422


def test_database_rejects_job_with_foreign_owned_company(
    db_session: Session,
    user: User,
    second_user: User,
):
    company = Company(owner_id=second_user.id, name="Other Owner Company")
    db_session.add(company)
    db_session.commit()

    db_session.add(
        Job(
            owner_id=user.id,
            company_id=company.id,
            title="Invalid Cross-owner Job",
        )
    )

    with pytest.raises(IntegrityError) as exc_info:
        db_session.commit()
    db_session.rollback()
    assert exc_info.value.orig.diag.constraint_name == "fk_jobs_owner_company"


def test_database_rejects_application_with_foreign_owned_job(
    db_session: Session,
    user: User,
    second_user: User,
):
    company = Company(owner_id=user.id, name="Application Parent")
    db_session.add(company)
    db_session.flush()
    job = Job(owner_id=user.id, company_id=company.id, title="Application Parent")
    db_session.add(job)
    db_session.commit()

    db_session.add(
        Application(
            owner_id=second_user.id,
            job_id=job.id,
            status="saved",
        )
    )

    with pytest.raises(IntegrityError) as exc_info:
        db_session.commit()
    db_session.rollback()
    assert exc_info.value.orig.diag.constraint_name == "fk_applications_owner_job"


def test_database_rejects_interview_with_foreign_owned_application(
    db_session: Session,
    user: User,
    second_user: User,
):
    company = Company(owner_id=user.id, name="Interview Parent")
    db_session.add(company)
    db_session.flush()
    job = Job(owner_id=user.id, company_id=company.id, title="Interview Parent")
    db_session.add(job)
    db_session.flush()
    application = Application(
        owner_id=user.id,
        job_id=job.id,
        status="screening",
    )
    db_session.add(application)
    db_session.commit()
    scheduled_at = datetime.now(UTC) + timedelta(days=1)

    db_session.add(
        Interview(
            owner_id=second_user.id,
            application_id=application.id,
            interview_type="technical",
            status="scheduled",
            scheduled_at=scheduled_at,
            scheduled_end_at=scheduled_at + timedelta(hours=1),
            duration_minutes=60,
        )
    )

    with pytest.raises(IntegrityError) as exc_info:
        db_session.commit()
    db_session.rollback()
    assert exc_info.value.orig.diag.constraint_name == "fk_interviews_owner_application"


def test_user_deletion_still_cascades_through_business_hierarchy(
    db_session: Session,
    user: User,
):
    company = Company(owner_id=user.id, name="Cascade Company")
    db_session.add(company)
    db_session.flush()
    job = Job(owner_id=user.id, company_id=company.id, title="Cascade Job")
    db_session.add(job)
    db_session.flush()
    application = Application(
        owner_id=user.id,
        job_id=job.id,
        status="screening",
    )
    db_session.add(application)
    db_session.flush()
    scheduled_at = datetime.now(UTC) + timedelta(days=1)
    interview = Interview(
        owner_id=user.id,
        application_id=application.id,
        interview_type="technical",
        status="scheduled",
        scheduled_at=scheduled_at,
        scheduled_end_at=scheduled_at + timedelta(hours=1),
        duration_minutes=60,
    )
    db_session.add(interview)
    db_session.commit()
    ids = (company.id, job.id, application.id, interview.id)

    db_session.delete(user)
    db_session.commit()
    db_session.expire_all()

    assert db_session.get(Company, ids[0]) is None
    assert db_session.get(Job, ids[1]) is None
    assert db_session.get(Application, ids[2]) is None
    assert db_session.get(Interview, ids[3]) is None
