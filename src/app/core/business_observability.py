import logging
from collections.abc import Callable
from functools import wraps
from typing import Literal, ParamSpec, TypeVar

from app.core.metrics import BUSINESS_OPERATIONS_TOTAL
from app.exceptions.domain import ResourceConflictError

BusinessResource = Literal["company", "job", "application", "interview"]
BusinessOperation = Literal["create", "update", "delete", "status_change"]
BusinessOutcome = Literal["success", "conflict", "error"]

logger = logging.getLogger("jobtrack-api.business")
P = ParamSpec("P")
R = TypeVar("R")


def record_business_operation(
    resource: BusinessResource,
    operation: BusinessOperation,
    outcome: BusinessOutcome,
) -> None:
    BUSINESS_OPERATIONS_TOTAL.labels(
        resource=resource,
        operation=operation,
        outcome=outcome,
    ).inc()
    level = {
        "success": logging.INFO,
        "conflict": logging.WARNING,
        "error": logging.ERROR,
    }[outcome]
    logger.log(
        level,
        "business_operation",
        extra={
            "resource_type": resource,
            "resource_operation": operation,
            "resource_outcome": outcome,
        },
    )


def observe_business_write(
    resource: BusinessResource,
    operation: BusinessOperation,
) -> Callable[[Callable[P, R]], Callable[P, R]]:
    def decorator(function: Callable[P, R]) -> Callable[P, R]:
        @wraps(function)
        def wrapped(*args: P.args, **kwargs: P.kwargs) -> R:
            try:
                result = function(*args, **kwargs)
            except ResourceConflictError:
                record_business_operation(resource, operation, "conflict")
                raise
            except Exception:
                record_business_operation(resource, operation, "error")
                raise
            record_business_operation(resource, operation, "success")
            return result

        return wrapped

    return decorator
