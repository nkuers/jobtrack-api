# ADR 0007: Enforce parent ownership with composite foreign keys

Date: 2026-09-23

Status: Accepted

## Context

Jobs, Applications, and Interviews duplicate `owner_id` from their parent so
every public query can be scoped directly to the authenticated user. Services
validate the parent with the same owner before writing. However, independent
foreign keys to `users.id` and a parent's single-column ID do not prove that
both references belong to the same user. A direct SQL write, faulty seed, or
future import path could therefore create a cross-owner hierarchy.

## Decision

Add unique parent keys on `(owner_id, id)` and replace each single-column
business-parent foreign key with a composite one:

- `jobs(owner_id, company_id)` references `companies(owner_id, id)`;
- `applications(owner_id, job_id)` references `jobs(owner_id, id)`;
- `interviews(owner_id, application_id)` references
  `applications(owner_id, id)`.

Keep the direct `owner_id -> users.id` foreign keys and their delete behavior.
Keep Service ownership checks as well, because they produce stable owner-scoped
`404` responses before persistence and remain part of the authorization model.

## Consequences

- Cross-owner business hierarchies are rejected even outside the API.
- Authorization checks and database integrity provide independent layers.
- The parent tables gain small unique indexes and writes maintain them.
- The migration fails if legacy cross-owner rows exist; those rows must be
  audited and repaired rather than silently reassigned.
- User deletion still cascades through the hierarchy and is covered by an
  integration test.
