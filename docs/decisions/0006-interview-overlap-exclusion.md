# ADR 0006: Enforce Interview overlap in PostgreSQL

Date: 2026-09-23

Status: Accepted

## Context

The API must prevent one user from holding overlapping scheduled Interviews.
A Service query gives a clear early conflict, but two transactions can both
observe an empty time slot before either inserts. Process-local locks do not
protect multiple API replicas, and a distributed Redis lock would make a cache
part of a database consistency boundary.

## Decision

Store the derived `scheduled_end_at` alongside `scheduled_at` and
`duration_minutes`. A check constraint keeps those values consistent.

Enable PostgreSQL `btree_gist` and add a partial GiST exclusion constraint over
`owner_id` and the half-open `tstzrange(scheduled_at, scheduled_end_at, '[)')`
when status is `scheduled`. Keep the Service pre-check for an inexpensive,
readable `409`; translate a constraint race into the same conflict response.

## Consequences

- Concurrent inserts and reschedules cannot violate the overlap invariant.
- Adjacent Interviews are allowed, and cancelled/completed rows release slots.
- The migration requires `btree_gist`; managed deployments may need a database
  administrator to install the extension first.
- Existing overlapping scheduled rows must be resolved before migration.
- Every write path must maintain the derived end time, with the database check
  acting as the final consistency guard.
