# JobTrack project interview guide

## Two-minute introduction

JobTrack is a production-oriented backend for managing target companies, open
roles, job applications, status history, interviews, and a personal dashboard.
I built the business domain on top of an existing FastAPI production template,
retaining its authentication and operational foundation while replacing unsafe
teaching placeholders and adding owner-scoped domain modules.

The main engineering focus is not CRUD volume. It is preserving business
invariants under authorization failures, database conflicts, concurrent state
changes, and Redis outages. The application uses PostgreSQL, synchronous
SQLAlchemy, explicit Service transactions, Alembic, short-TTL Redis caching,
structured logs, Prometheus metrics, and real PostgreSQL integration tests.

## What came from the template?

The retained foundation includes JWT access tokens, rotating refresh tokens,
sessions, RBAC, email lifecycle flows, optional MFA/OIDC, PostgreSQL/Alembic,
Redis infrastructure, logging, metrics, tracing, Docker, and CI.

The JobTrack work adds Companies, Jobs, Applications, status history,
Interviews, Dashboard aggregation/cache, owner isolation, state machines,
time-conflict detection, query/index analysis, per-user write limits, business
telemetry, demo tooling, and the related migrations and tests.

## Architecture talking points

### Why separate Schema and ORM Model?

Pydantic schemas define untrusted HTTP input and public output. ORM models
define persistence. Keeping them separate prevents clients from supplying
`owner_id`, avoids accidentally returning password or internal fields, and lets
API contracts evolve independently from database mappings.

### Where is authorization enforced?

JWT answers who the caller is. It does not grant access to every row. Routers
resolve the current user, Services pass the user ID, and Repositories include
`resource.id = ? AND resource.owner_id = ?`. Missing and foreign resources both
return `404` to avoid ID-existence disclosure.

### Why does Service commit while Repository only flushes?

A business transaction may span multiple repository operations. Application
status and status history must commit atomically. If a Repository committed
internally, the Service could not roll back the whole invariant. See
[ADR 0002](docs/decisions/0002-service-owns-transactions.md).

### How are concurrent status changes handled?

The status Service reads the owner-scoped Application with `FOR UPDATE`, then
validates the transition and writes history in the same transaction. A second
request waits, observes the new status, and is revalidated. A real two-session
integration test proves that duplicate transitions produce one history row.

Interview scheduling uses a different database primitive. The Service performs
an early overlap check for a useful `409`, while a partial PostgreSQL GiST
exclusion constraint protects the final invariant across processes. Scheduled
time windows use half-open ranges, so one Interview may start exactly when the
previous one ends.

Creating an Interview also locks and validates its owner-scoped Application.
Only `screening`, `interview`, and `offer` represent an active recruitment
stage where a new round makes sense. The lock serializes creation against a
concurrent Application status change. Existing Interviews remain manageable
after rejection, withdrawal, or archival so operators can still complete or
cancel a round without creating a dead end.

### Why synchronous SQLAlchemy?

The project has bounded synchronous transactions and no representative evidence
that async would improve its SLO enough to justify converting every layer.
There is an isolated sync/async benchmark harness and an explicit adoption
gate. See [ADR 0001](docs/decisions/0001-keep-sync-sqlalchemy.md).

### Why cache only Dashboard?

Dashboard is an expensive, read-heavy aggregate with an acceptable short stale
window. CRUD remains source-of-truth traffic to PostgreSQL. Cache-aside uses one
HMAC-keyed entry per user, a short TTL, validation on read, and write-triggered
invalidation. Redis errors fall back to PostgreSQL.

## Common follow-up questions

### Why duplicate `owner_id` on child tables?

It makes every public query independently owner-scoped and supports useful
compound indexes. The Service still validates parent ownership. The trade-off
is duplicated ownership data, so clients can never set it and all writes derive
it from the authenticated user.

### Why strings and checks instead of PostgreSQL enums?

Python enums and Pydantic provide API validation while database check
constraints protect storage. String checks are easier to evolve and downgrade
than PostgreSQL enum types for this project.

### Why integers for salary?

Salary uses minor currency units, avoiding binary floating-point rounding.
Currency remains an explicit three-letter code.

### What happens if Redis is down?

Dashboard reads query PostgreSQL and cache invalidation becomes a no-op. The
business-write limiter defaults to fail-open, while the global limiter has an
explicit configurable policy. Readiness requires Redis only for configured
features where operators choose that dependency.

### How do indexes match queries?

Default lists filter first by owner and then order/filter by creation, status,
update time, scheduled time, or next-action time. Compound indexes follow those
prefixes. `EXPLAIN ANALYZE` confirmed index eligibility; representative data is
still required before making production latency claims.

### How would this scale to many users?

Use multiple stateless API containers, Redis-backed shared limits/cache, and a
managed PostgreSQL primary with connection budgets aligned to worker counts.
Move from offset pagination to cursor pagination when deep pages become common,
and validate index plans on production-like distributions.

### What would you build next?

- resume/document references stored in object storage;
- notifications through the existing transactional outbox;
- cursor pagination for high-volume histories;
- passkeys for phishing-resistant authentication;
- retention/export/delete workflows for user data;
- production SLOs and representative load-test baselines.

## Evidence checklist

- `366` automated tests at the completion of hardening, above 90% coverage.
- Alembic upgrade/downgrade checks for all JobTrack schema stages.
- Cross-user authorization tests for every business resource.
- Database rollback, Redis outage, cache invalidation, and concurrent lock tests.
- Query-plan record in [JOBTRACK_HARDENING.md](JOBTRACK_HARDENING.md).
- Reproducible authenticated CRUD profile in [LOAD_TESTING.md](LOAD_TESTING.md).
