# ADR 0004: Return 404 for missing and unauthorized resources

- Status: accepted
- Date: 2026-09-22
- Decision owners: JobTrack maintainers

## Context

Business resources are private to one user. Returning `403` after first looking
up a resource by global ID would reveal that another user's Company, Job,
Application, or Interview exists.

## Decision

Repository detail, update, and delete queries include both resource ID and the
authenticated `owner_id`. If no row matches, services return the same `404`
used for a nonexistent ID.

Child creation also resolves the parent with its owner condition before
inserting. Clients can never supply or change `owner_id`.

## Consequences

- ID probing does not distinguish absence from another user's ownership.
- Authorization is enforced in the database query rather than after loading.
- API clients receive a simpler, consistent resource-not-found contract.
- Cross-user integration tests are required for every business resource.
