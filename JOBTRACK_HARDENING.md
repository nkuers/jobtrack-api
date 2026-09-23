# JobTrack security and performance audit

This record documents the stage 7 review of the JobTrack business modules. It
is evidence for the current query and concurrency design, not a substitute for
measurements against production-sized data.

## Ownership boundary

Every externally reachable business resource query includes the authenticated
`owner_id`. A resource belonging to another user follows the same `404` path as
a missing resource.

| Repository | Owner-scoped paths |
| --- | --- |
| Company | detail, normalized-name lookup, list, and child-existence check |
| Job | detail, list, and Application-existence check |
| Application | detail, locked detail, job lookup, list, and Interview-existence check |
| Interview | detail, list, upcoming list, and overlap candidates |
| Dashboard | every Company, Job, Application, history join, Interview, and action aggregate |

`ApplicationStatusHistory` deliberately has no public top-level lookup. Its
Service first resolves the parent Application with both application ID and
owner ID, then queries history by the authorized parent ID.

Integration tests exercise cross-user reads and writes for all four resources.
All paginated business endpoints reject `page_size > 100`; upcoming Interviews
also rejects `limit > 100`.

## Query-plan evidence

On 2026-09-22, the common owner-scoped queries were run on PostgreSQL 17 using
`EXPLAIN (ANALYZE, BUFFERS)`. The isolated test database was empty after test
cleanup, so `SET LOCAL enable_seqscan=off` was used only to confirm that each
query is eligible for its intended index. These sub-millisecond empty-table
times are not production latency evidence.

| Query shape | Selected index | Plan note |
| --- | --- | --- |
| Company owner list ordered by creation | `ix_companies_owner_created_at` | backward index scan, bounded incremental sort on `id` |
| Job owner/status list ordered by update | `ix_jobs_owner_status_updated_at` | backward index scan, bounded incremental sort on `id` |
| Application owner/status list ordered by update | `ix_applications_owner_status_updated_at` | backward index scan, bounded incremental sort on `id` |
| Future scheduled Interviews | `ix_interviews_owner_status_scheduled` | range index scan on `scheduled_at` |
| Dashboard upcoming actions | `ix_applications_owner_next_action_at` | bounded range index scan |

The stable `id` secondary sort can require an incremental sort when timestamps
tie. With a maximum response size of 100 (20 for Dashboard lists), this is a
bounded operation and does not justify wider duplicate indexes yet. Revisit
with representative row counts and retained `EXPLAIN` output before changing
the schema.

Reproduce the eligibility check inside a transaction so the planner setting is
not persisted:

```sql
BEGIN;
SET LOCAL enable_seqscan=off;
EXPLAIN (ANALYZE, BUFFERS)
SELECT id FROM applications
WHERE owner_id = 1 AND status = 'applied'
ORDER BY updated_at DESC, id DESC LIMIT 20;
ROLLBACK;
```

## Write protection and observability

Company, Job, Application, and Interview mutations have a separate per-user
fixed-window limit. The default is 30 writes per 60 seconds. Memory mode is
appropriate for one local process; Redis mode shares the quota across workers
and stores only an HMAC-derived identifier. The business limit defaults to
fail-open during a Redis outage so core writes remain available; deployments
with a stricter abuse model can select `closed`.

Business metrics use only bounded labels: resource type, operation, and result.
Structured business logs contain those same fields plus the request ID supplied
by the logging context. They never include user IDs, tokens, email addresses,
notes, feedback, job descriptions, or request bodies.

## Concurrent status changes

Application status transitions use `SELECT ... FOR UPDATE`. Two concurrent
requests for the same Application serialize at the row: one transition commits
with its history row, then the second re-evaluates the new state. A concurrent
duplicate transition receives `409` and creates no second history row. The
integration test uses independent database sessions to verify this behavior.

This pessimistic row lock protects the only current high-contention state
machine, so a version column would add client and migration complexity without
improving the present invariant. Reconsider optimistic locking if ordinary
metadata updates need conflict detection or lock wait time becomes measurable.

## Failure behavior

- Service transaction tests verify rollback on database and history-write
  failures.
- Dashboard Redis failures fall back to PostgreSQL.
- Dashboard invalidation failures cannot roll back committed business writes.
- Business-rate-limit Redis failures follow an explicit open/closed policy.
- Tracing setup/export failures are isolated from request correctness.
- Expected and unexpected HTTP failures retain an `X-Request-ID`; rate-limit
  responses also retain `Retry-After`.

The authenticated `crud` k6 profile exercises Company → Job → Application →
status → Interview → Dashboard. Run it only against an isolated or authorized
environment as described in [LOAD_TESTING.md](LOAD_TESTING.md).
