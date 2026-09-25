from datetime import UTC, datetime, timedelta
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient
from redis.exceptions import ConnectionError

from app.auth.jwt import create_access_token
from app.core.config import settings
from app.schemas.application import ApplicationStatus
from app.schemas.dashboard import DashboardResponse
from app.services.dashboard_cache import CACHE_NAMESPACE, DashboardCache
from app.services.dashboard_service import DashboardService


class MemoryRedis:
    def __init__(self):
        self.values: dict[str, bytes] = {}
        self.ttls: dict[str, int] = {}

    def get(self, key):
        return self.values.get(key)

    def set(self, key, value, *, ex=None):
        self.values[key] = value
        self.ttls[key] = ex
        return True

    def delete(self, key):
        existed = key in self.values
        self.values.pop(key, None)
        self.ttls.pop(key, None)
        return int(existed)


class BrokenRedis:
    def __getattr__(self, name):
        def fail(*args, **kwargs):
            raise ConnectionError("redis unavailable")

        return fail


@pytest.fixture
def dashboard_cache_settings(monkeypatch):
    monkeypatch.setattr(settings, "DASHBOARD_CACHE_BACKEND", "redis")
    monkeypatch.setattr(settings, "DASHBOARD_CACHE_TTL_SECONDS", 60)
    monkeypatch.setattr(settings, "DASHBOARD_CACHE_MAX_BYTES", 262144)


def sample_dashboard(now: datetime | None = None) -> DashboardResponse:
    return DashboardResponse(
        company_count=2,
        job_count=3,
        application_status_counts={status: 0 for status in ApplicationStatus},
        applications_last_7_days=1,
        offer_conversion_rate=0.5,
        upcoming_interviews=[],
        overdue_actions=[],
        upcoming_actions=[],
        generated_at=now or datetime.now(UTC),
    )


def test_dashboard_cache_miss_then_hit_avoids_second_aggregation(
    dashboard_cache_settings,
):
    redis = MemoryRedis()
    service = DashboardService(MagicMock(), cache=DashboardCache(redis))
    service.repository = MagicMock()
    expected = sample_dashboard()
    service.repository.aggregate.return_value = expected

    first = service.get(42)
    second = service.get(42)

    assert first == expected
    assert second == expected
    service.repository.aggregate.assert_called_once()
    assert redis.ttls[DashboardCache.key(42)] == 60


def test_dashboard_cache_keys_are_private_versioned_and_user_scoped(
    dashboard_cache_settings,
):
    first = DashboardCache.key(123456789)
    second = DashboardCache.key(987654321)

    assert first.startswith(f"{CACHE_NAMESPACE}:")
    assert first != second
    assert "123456789" not in first
    assert len(first) <= 128


def test_dashboard_redis_outage_falls_back_to_database(
    dashboard_cache_settings,
):
    service = DashboardService(MagicMock(), cache=DashboardCache(BrokenRedis()))
    service.repository = MagicMock()
    expected = sample_dashboard()
    service.repository.aggregate.return_value = expected

    assert service.get(7) == expected
    service.repository.aggregate.assert_called_once()


def test_dashboard_cache_rejects_invalid_payload(dashboard_cache_settings):
    redis = MemoryRedis()
    cache = DashboardCache(redis)
    redis.set(cache.key(1), b'{"company_count":"poisoned"}', ex=60)

    result = cache.read(1)

    assert result.outcome == "invalid"
    assert result.value is None
    assert cache.key(1) not in redis.values


def _create_company(client: TestClient, headers: dict[str, str], name: str) -> dict:
    response = client.post(
        "/api/v1/companies",
        headers=headers,
        json={"name": name},
    )
    assert response.status_code == 201, response.text
    return response.json()


def _create_job(
    client: TestClient,
    headers: dict[str, str],
    company_id: int,
    title: str,
) -> dict:
    response = client.post(
        "/api/v1/jobs",
        headers=headers,
        json={"company_id": company_id, "title": title},
    )
    assert response.status_code == 201, response.text
    return response.json()


def _create_application(
    client: TestClient,
    headers: dict[str, str],
    job_id: int,
    **values,
) -> dict:
    response = client.post(
        "/api/v1/applications",
        headers=headers,
        json={"job_id": job_id, **values},
    )
    assert response.status_code == 201, response.text
    return response.json()


def test_dashboard_aggregates_owner_scoped_business_metrics(
    client: TestClient,
    auth_headers: dict[str, str],
    second_user,
):
    now = datetime.now(UTC)
    first_company = _create_company(client, auth_headers, "Dashboard One")
    second_company = _create_company(client, auth_headers, "Dashboard Two")
    first_job = _create_job(
        client,
        auth_headers,
        first_company["id"],
        "Backend Engineer",
    )
    second_job = _create_job(
        client,
        auth_headers,
        second_company["id"],
        "Platform Engineer",
    )
    third_job = _create_job(
        client,
        auth_headers,
        second_company["id"],
        "Data Engineer",
    )

    offered = _create_application(
        client,
        auth_headers,
        first_job["id"],
        status="applied",
    )
    for target in ("screening", "interview", "offer", "archived"):
        response = client.patch(
            f"/api/v1/applications/{offered['id']}/status",
            headers=auth_headers,
            json={"status": target},
        )
        assert response.status_code == 200, response.text

    active = _create_application(
        client,
        auth_headers,
        second_job["id"],
        status="applied",
        next_action_at=(now + timedelta(days=2)).isoformat(),
    )
    active_response = client.patch(
        f"/api/v1/applications/{active['id']}/status",
        headers=auth_headers,
        json={"status": "screening"},
    )
    assert active_response.status_code == 200, active_response.text
    active = active_response.json()
    overdue = _create_application(
        client,
        auth_headers,
        third_job["id"],
        next_action_at=(now - timedelta(days=1)).isoformat(),
    )

    interview = client.post(
        "/api/v1/interviews",
        headers=auth_headers,
        json={
            "application_id": active["id"],
            "interview_type": "technical",
            "scheduled_at": (now + timedelta(days=3)).isoformat(),
            "duration_minutes": 60,
        },
    )
    assert interview.status_code == 201, interview.text

    other_headers = {
        "Authorization": f"Bearer {create_access_token({'sub': second_user.username})}"
    }
    _create_company(client, other_headers, "Other User Company")

    response = client.get("/api/v1/dashboard", headers=auth_headers)
    assert response.status_code == 200
    payload = response.json()
    assert payload["company_count"] == 2
    assert payload["job_count"] == 3
    assert payload["application_status_counts"]["archived"] == 1
    assert payload["application_status_counts"]["screening"] == 1
    assert payload["application_status_counts"]["saved"] == 1
    assert payload["applications_last_7_days"] == 3
    assert payload["offer_conversion_rate"] == 0.5
    assert [item["id"] for item in payload["upcoming_interviews"]] == [
        interview.json()["id"]
    ]
    assert (
        payload["upcoming_interviews"][0]["application_summary"]["job_summary"]
        == active["job_summary"]
    )
    assert [item["application_id"] for item in payload["overdue_actions"]] == [
        overdue["id"]
    ]
    assert payload["overdue_actions"][0]["job_summary"] == overdue["job_summary"]
    assert [item["application_id"] for item in payload["upcoming_actions"]] == [
        active["id"]
    ]
    assert payload["upcoming_actions"][0]["job_summary"] == active["job_summary"]


def test_business_writes_invalidate_the_owner_dashboard(
    client: TestClient,
    auth_headers: dict[str, str],
    user,
    monkeypatch,
):
    invalidations: list[tuple[str, int]] = []
    modules = (
        "app.services.company_service.invalidate_dashboard_cache",
        "app.services.job_service.invalidate_dashboard_cache",
        "app.services.application_service.invalidate_dashboard_cache",
        "app.services.interview_service.invalidate_dashboard_cache",
    )
    for path in modules:
        label = path.split(".")[-2]
        monkeypatch.setattr(
            path,
            lambda owner_id, label=label: invalidations.append((label, owner_id)),
        )

    company = _create_company(client, auth_headers, "Invalidation")
    job = _create_job(client, auth_headers, company["id"], "Invalidation Job")
    application = _create_application(
        client,
        auth_headers,
        job["id"],
        status="applied",
    )
    application_response = client.patch(
        f"/api/v1/applications/{application['id']}/status",
        headers=auth_headers,
        json={"status": "screening"},
    )
    assert application_response.status_code == 200, application_response.text
    application = application_response.json()
    response = client.post(
        "/api/v1/interviews",
        headers=auth_headers,
        json={
            "application_id": application["id"],
            "interview_type": "technical",
            "scheduled_at": (datetime.now(UTC) + timedelta(days=1)).isoformat(),
        },
    )
    assert response.status_code == 201
    assert invalidations == [
        ("company_service", user.id),
        ("job_service", user.id),
        ("application_service", user.id),
        ("application_service", user.id),
        ("interview_service", user.id),
    ]


def test_dashboard_requires_authentication(client: TestClient):
    assert client.get("/api/v1/dashboard").status_code == 401
