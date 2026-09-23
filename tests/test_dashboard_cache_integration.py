import os
from datetime import UTC, datetime
from uuid import uuid4

import pytest
from redis import Redis

from app.core.config import settings
from app.schemas.application import ApplicationStatus
from app.schemas.dashboard import DashboardResponse
from app.services.dashboard_cache import DashboardCache

REDIS_TEST_URL = os.environ.get("REDIS_TEST_URL")
pytestmark = pytest.mark.skipif(
    not REDIS_TEST_URL,
    reason="REDIS_TEST_URL is required for Redis integration tests",
)


def test_dashboard_cache_is_shared_ttl_bounded_and_invalidatable(monkeypatch):
    redis = Redis.from_url(REDIS_TEST_URL, decode_responses=False)
    monkeypatch.setattr(settings, "DASHBOARD_CACHE_BACKEND", "redis")
    monkeypatch.setattr(settings, "DASHBOARD_CACHE_TTL_SECONDS", 60)
    owner_id = int(uuid4().int % 1_000_000_000) + 1
    first = DashboardCache(redis)
    second = DashboardCache(redis)
    key = first.key(owner_id)
    value = DashboardResponse(
        company_count=1,
        job_count=2,
        application_status_counts={status: 0 for status in ApplicationStatus},
        applications_last_7_days=0,
        offer_conversion_rate=0,
        upcoming_interviews=[],
        overdue_actions=[],
        upcoming_actions=[],
        generated_at=datetime.now(UTC),
    )

    redis.delete(key)
    try:
        assert first.write(owner_id, value) is True
        assert second.read(owner_id).value == value
        assert 0 < redis.ttl(key) <= 60
        assert str(owner_id) not in key
        assert second.invalidate(owner_id) is True
        assert redis.get(key) is None
    finally:
        redis.delete(key)
        redis.close()
