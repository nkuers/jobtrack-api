import logging

from fastapi import Depends, HTTPException, status
from redis.exceptions import RedisError

from app.auth.current_user import get_current_user
from app.core.config import settings
from app.core.metrics import (
    RATE_LIMIT_BACKEND_ERRORS_TOTAL,
    RATE_LIMIT_DECISIONS_TOTAL,
)
from app.middlewares.rate_limit import RateLimiter, RedisRateLimiter
from app.models.user import User

logger = logging.getLogger("jobtrack-api.business_rate_limit")

business_write_limiter = RateLimiter(
    limit=settings.BUSINESS_WRITE_RATE_LIMIT,
    window=settings.BUSINESS_WRITE_RATE_LIMIT_WINDOW_SECONDS,
)


def _redis_limiter() -> RedisRateLimiter:
    return RedisRateLimiter(
        limit=settings.BUSINESS_WRITE_RATE_LIMIT,
        window=settings.BUSINESS_WRITE_RATE_LIMIT_WINDOW_SECONDS,
        key_secret=settings.RATE_LIMIT_KEY_SECRET.get_secret_value().encode("utf-8"),
    )


async def enforce_business_write_rate_limit(
    current_user: User = Depends(get_current_user),
) -> None:
    backend = settings.RATE_LIMIT_BACKEND
    subject = f"business-write:user:{current_user.id}"
    try:
        if backend == "redis":
            decision = await _redis_limiter().check(subject)
        else:
            decision = business_write_limiter.check(subject)
    except (RedisError, OSError, TimeoutError):
        RATE_LIMIT_BACKEND_ERRORS_TOTAL.labels(
            backend="redis",
            operation="business_write",
        ).inc()
        if settings.BUSINESS_WRITE_RATE_LIMIT_FAILURE_MODE == "open":
            RATE_LIMIT_DECISIONS_TOTAL.labels(
                backend="redis",
                outcome="business_write_fail_open",
            ).inc()
            logger.warning(
                "business_write_rate_limit_unavailable",
                extra={
                    "rate_limit_backend": "redis",
                    "rate_limit_policy": "open",
                    "rate_limit_operation": "business_write",
                },
            )
            return
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Rate limit service unavailable",
            headers={"Retry-After": "1"},
        ) from None

    outcome = "business_write_allowed" if decision.allowed else "business_write_blocked"
    RATE_LIMIT_DECISIONS_TOTAL.labels(backend=backend, outcome=outcome).inc()
    if not decision.allowed:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many write requests",
            headers={"Retry-After": str(decision.retry_after)},
        )
