# ADR 0008: Require distributed fail-closed rate limiting in production

Date: 2026-09-23

Status: Accepted

## Context

The in-memory limiter is convenient for one local process, but each production
worker would maintain an independent counter. Effective quotas would therefore
grow with replica count and reset on every restart. Redis provides shared,
atomic counters, but a fail-open outage policy would remove request and
business-write protection at the same time the protection backend is failing.

The readiness endpoint already treats Redis as required when distributed rate
limiting is enabled. Allowing production to start with a weaker backend or
failure policy would conflict with that operational contract.

## Decision

When `ENVIRONMENT=production`, configuration validation requires:

- `RATE_LIMIT_BACKEND=redis`;
- `RATE_LIMIT_FAILURE_MODE=closed`;
- `BUSINESS_WRITE_RATE_LIMIT_FAILURE_MODE=closed`.

The Redis URL and dedicated HMAC key retain their existing validation. Memory
and fail-open modes remain available outside production for local development
and explicit failure-path testing.

## Consequences

- Quotas remain consistent across workers and replicas.
- A Redis outage returns `503` for protected traffic and fails readiness rather
  than silently reducing abuse protection.
- Redis is a production availability dependency and must be monitored,
  replicated, capacity-planned, and restored instead of bypassed.
- Unsafe production combinations fail during startup rather than after traffic
  reaches the service.
