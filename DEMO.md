# JobTrack demonstration guide

This walkthrough presents the business system, its security boundary, and its
operational evidence in about 10–15 minutes.

## Prepare the local stack

```bash
python scripts/dev.py stack-up
```

Compose waits for PostgreSQL and Redis, runs `alembic upgrade head` in the
one-shot `migrate` service, and starts the API only after migration succeeds.
Open <http://127.0.0.1:8000/docs> and confirm `/health/ready` is healthy.

Optional demo data is never created during application startup or migration.
Create it only with the explicit command:

```bash
python scripts/dev.py demo-data --confirm
```

The command refuses production, remote databases, unsafe database names, and
an existing `jobtrack_demo` user. Its local credentials are:

```text
username: jobtrack_demo
password: JobTrackDemo123!
```

Use `--username` and `--password` directly with `scripts/seed_demo.py` when a
different disposable identity is required.

## Business walkthrough

For a clean manual flow, register a new disposable user in Swagger:

1. `POST /register/`
2. `POST /login/` using form fields, then copy `access_token`.
3. Click **Authorize** in Swagger and enter `Bearer <access_token>`.
4. `GET /auth/me` to establish the authenticated identity.
5. `POST /api/v1/companies` to create a target company.
6. `POST /api/v1/jobs` with that `company_id`.
7. `POST /api/v1/applications` with the `job_id` and status `saved`.
8. `PATCH /api/v1/applications/{id}/status` through `applied`, `screening`,
   and `interview`.
9. `GET /api/v1/applications/{id}/history` to show atomic state history.
10. `POST /api/v1/interviews` using an ISO 8601 time with an explicit offset.
11. `GET /api/v1/interviews/upcoming` to show normalized UTC ordering.
12. `GET /api/v1/dashboard` twice to demonstrate cache-aside behavior.

Detailed curl payloads are available in [API_EXAMPLES.md](API_EXAMPLES.md).

## Security and correctness evidence

Show the following tests rather than relying only on verbal claims:

```bash
TEST_DATABASE_URL='postgresql+psycopg://fastapi_user:fastapi_password@localhost:5433/fastapi_test' \
uv run pytest --no-cov -q \
  tests/test_companies.py \
  tests/test_applications.py::test_concurrent_status_updates_are_serialized_by_row_lock \
  tests/test_transaction_rollbacks.py \
  tests/test_dashboard_cache_integration.py
```

Explain these outcomes:

- another user's resource ID returns the same `404` as a missing ID;
- a failed history insert rolls back the Application status;
- concurrent duplicate status transitions produce one success and one `409`;
- Redis failure falls back to PostgreSQL for Dashboard;
- business writes are limited per authenticated user without putting IDs into
  metric labels or Redis keys.

## Operations evidence

Make one request with a caller-provided correlation ID:

```bash
curl --include http://127.0.0.1:8000/api/v1/dashboard \
  --header "Authorization: Bearer ${ACCESS_TOKEN}" \
  --header "X-Request-ID: jobtrack-demo-001"
```

Point out the same request ID in the response and JSON logs. Then open
`/metrics` and show request latency/count metrics, business operation results,
and Dashboard cache outcomes. Metrics never use user IDs as labels.

Finally, open [.github/workflows/ci.yml](.github/workflows/ci.yml) and show the
PostgreSQL/Redis services, migration, Ruff, pytest coverage gate, dependency
audit, package build, non-root image build, and container health smoke test.

## Cleanup

Stop containers without deleting their volumes:

```bash
python scripts/dev.py db-down
```

Use a disposable database when you need automatic cleanup. The demo command
deliberately provides no hidden reset or production deletion behavior.
