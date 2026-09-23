# ADR 0002: Services own business transactions

- Status: accepted
- Date: 2026-09-22
- Decision owners: JobTrack maintainers

## Context

JobTrack writes often span business checks and multiple tables. Application
status changes, for example, update the Application and insert a status-history
row atomically. Repositories are also reused by services that need different
transaction boundaries.

## Decision

Services define transaction boundaries and call `commit` or `rollback`.
Repositories may construct queries, add rows, mutate mapped objects, and
`flush`, but they never commit independently.

Routers remain responsible only for HTTP contracts and dependency composition.

## Consequences

- Multi-table invariants commit or roll back together.
- Services can translate database integrity failures into stable domain errors.
- Repository methods remain composable inside larger use cases.
- Every write service needs explicit success and failure-path tests.
- A repository call does not imply durability until its service commits.
