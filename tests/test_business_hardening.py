import asyncio
import json
import logging

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from redis.exceptions import ConnectionError

from app.auth.jwt import create_access_token
from app.core.business_observability import record_business_operation
from app.core.logging import JsonFormatter
from app.core.metrics import BUSINESS_OPERATIONS_TOTAL
from app.dependencies import business_rate_limit
from app.middlewares.rate_limit import RateLimiter
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
