# ADR 0003: Use short-TTL cache-aside for Dashboard

- Status: accepted
- Date: 2026-09-22
- Decision owners: JobTrack maintainers

## Context

Dashboard combines several owner-scoped counts and time-window queries. It is
read frequently relative to underlying business writes, but Company, Job,
Application, and Interview CRUD must remain available when Redis is unhealthy.

## Decision

Cache only the complete Dashboard response in Redis using cache-aside. Use one
versioned HMAC-derived key per user, a default TTL of 60 seconds, bounded list
sizes, schema validation on reads, and active invalidation after successful
business commits.

On a miss or Redis error, query PostgreSQL. Redis write and invalidation errors
do not fail the request or roll back committed data.

## Consequences

- Repeated Dashboard reads avoid duplicate aggregate queries.
- Raw user IDs are not exposed in Redis keys and key growth is bounded.
- A small stale-data window is accepted if invalidation races or fails.
- PostgreSQL remains the source of truth and availability dependency.
- Cache hit/miss/error metrics use bounded labels without user identifiers.
