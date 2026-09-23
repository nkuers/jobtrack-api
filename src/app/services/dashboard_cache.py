import hashlib
import hmac
import logging
from dataclasses import dataclass
from typing import Literal

from pydantic import ValidationError
from redis import Redis
from redis.exceptions import RedisError

from app.core.config import settings
from app.core.metrics import DASHBOARD_CACHE_OPERATIONS_TOTAL
from app.core.redis import get_sync_redis_client
from app.schemas.dashboard import DashboardResponse

logger = logging.getLogger("jobtrack-api.dashboard_cache")

CACHE_NAMESPACE = "jobtrack-api:dashboard:v1"
CacheOutcome = Literal["hit", "miss", "invalid", "error", "disabled"]


@dataclass(frozen=True)
class DashboardCacheRead:
    value: DashboardResponse | None
    outcome: CacheOutcome


class DashboardCache:
    def __init__(self, redis: Redis | None = None):
        self.redis = redis
        self.enabled = settings.DASHBOARD_CACHE_BACKEND == "redis"

    @staticmethod
    def key(owner_id: int) -> str:
        secret = settings.SECRET_KEY.encode("utf-8")
        identifier = f"dashboard:v1:{owner_id}".encode("ascii")
        digest = hmac.new(secret, identifier, hashlib.sha256).hexdigest()
        return f"{CACHE_NAMESPACE}:{digest}"

    def read(self, owner_id: int) -> DashboardCacheRead:
        if not self.enabled:
            return DashboardCacheRead(None, "disabled")
        try:
            payload = self._client().get(self.key(owner_id))
        except (RedisError, OSError, TimeoutError, ValueError):
            self._record("error")
            self._warning("read_error")
            return DashboardCacheRead(None, "error")
        if payload is None:
            self._record("miss")
            return DashboardCacheRead(None, "miss")
        if len(payload) > settings.DASHBOARD_CACHE_MAX_BYTES:
            self._discard(owner_id)
            return DashboardCacheRead(None, "invalid")
        try:
            value = DashboardResponse.model_validate_json(payload)
        except (ValidationError, ValueError):
            self._discard(owner_id)
            return DashboardCacheRead(None, "invalid")
        self._record("hit")
        return DashboardCacheRead(value, "hit")

    def write(self, owner_id: int, value: DashboardResponse) -> bool:
        if not self.enabled:
            return False
        payload = value.model_dump_json().encode("utf-8")
        if len(payload) > settings.DASHBOARD_CACHE_MAX_BYTES:
            self._record("invalid")
            return False
        try:
            self._client().set(
                self.key(owner_id),
                payload,
                ex=settings.DASHBOARD_CACHE_TTL_SECONDS,
            )
        except (RedisError, OSError, TimeoutError, ValueError):
            self._record("error")
            self._warning("write_error")
            return False
        self._record("write")
        return True

    def invalidate(self, owner_id: int) -> bool:
        if not self.enabled:
            return False
        try:
            self._client().delete(self.key(owner_id))
        except (RedisError, OSError, TimeoutError, ValueError):
            self._record("error")
            self._warning("invalidation_error")
            return False
        self._record("invalidated")
        return True

    def _discard(self, owner_id: int) -> None:
        self._record("invalid")
        try:
            self._client().delete(self.key(owner_id))
        except (RedisError, OSError, TimeoutError, ValueError):
            self._warning("invalid_entry_delete_error")

    def _client(self) -> Redis:
        if self.redis is None:
            self.redis = get_sync_redis_client()
        return self.redis

    @staticmethod
    def _record(outcome: str) -> None:
        DASHBOARD_CACHE_OPERATIONS_TOTAL.labels(outcome=outcome).inc()

    @staticmethod
    def _warning(event: str) -> None:
        logger.warning("dashboard_cache_event", extra={"dashboard_cache_event": event})


def invalidate_dashboard_cache(owner_id: int) -> None:
    try:
        DashboardCache().invalidate(owner_id)
    except Exception:
        logger.error("dashboard_cache_invalidation_unexpected_error")
