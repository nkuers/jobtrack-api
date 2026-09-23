# ADR 0005: Serialize Application status transitions with row locks

- Status: accepted
- Date: 2026-09-22
- Decision owners: JobTrack maintainers

## Context

Two requests can attempt to change the same Application status concurrently.
Both must validate against the latest state, and exactly one history row must
be written for each successful transition.

## Decision

Load an Application status transition with PostgreSQL `SELECT ... FOR UPDATE`.
After obtaining the lock, validate the explicit state map, update the row, and
insert history in the same Service transaction.

Do not add a version column yet. Ordinary metadata edits do not currently need
client-visible compare-and-swap semantics, and the status row lock directly
protects the important invariant.

## Consequences

- Concurrent transitions for one Application serialize safely.
- A second duplicate transition observes the committed state and returns `409`.
- Status updates may wait briefly on another transaction holding the same row.
- Lock wait and transaction duration should be monitored before reconsidering
  optimistic locking.
