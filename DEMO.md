# JobTrack demonstration guide

This walkthrough presents the business system, its security boundary, and its
operational evidence in about 10–15 minutes.

## Prepare the local stack

```bash
python scripts/dev.py stack-up
```

Compose waits for PostgreSQL and Redis, runs `alembic upgrade head` in the
one-shot `migrate` service, and starts the API only after migration succeeds.
It also serves the Web client from the non-root frontend container. Open
<http://127.0.0.1:3000> and confirm <http://127.0.0.1:8000/health/ready> is healthy.

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

For frontend hot reload instead of the Compose frontend, stop that service and
start Vite in another terminal:

```bash
cd frontend
npm run dev
```

Sign in at <http://127.0.0.1:3000> with the disposable demo credentials.
The Dashboard badge makes it clear that this account contains seeded data.

## Web product walkthrough

Use the browser UI for the main interview story:

1. Start on **Dashboard** and explain that every KPI, status count, interview,
   and action comes from `GET /api/v1/dashboard`; no trend data is invented in
   the browser.
2. Open a status row or KPI card to show URL-backed filtering, then open an
   Application and its server-backed status timeline.
3. Follow the linked Job and Company summaries to show that list and dashboard
   read models avoid client-side N+1 requests.
4. Open **Applications → Board** and perform one legal status transition. Point
   out that available actions follow the backend state machine.
5. Open **Interviews**, switch between month/week/list views, and create an
   interview. An overlapping time returns a visible `409` without leaving a
   phantom event in the calendar.
6. Open **Settings → Security** to show the real MFA status and active device
   sessions. The UI deliberately does not guess which session is the current
   device because the API does not expose that fact.
7. Toggle the dark theme and narrow the browser once to demonstrate responsive
   navigation and mobile-friendly cards.

For the complete MFA story, use a disposable account: enter the current
password, scan the browser-generated QR code, confirm a TOTP, and save the
one-time recovery codes before closing the dialog. The TOTP secret never goes
to an external QR service. Regenerating recovery codes lets the user save the
new codes before the UI clears local authentication; disabling MFA or revoking
all sessions returns to login immediately. A single-session revoke always asks
for confirmation and refreshes the list without falsely labeling a current
device.

Keep Swagger for the lower-level security and operations evidence below; the
Web UI is the primary product demonstration.

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
audit, package build, Playwright real-browser flow, failure artifacts, non-root
API/frontend image builds, SPA fallback, security headers, and container health
smoke tests.

## Cleanup

Stop containers without deleting their volumes:

```bash
python scripts/dev.py db-down
```

Use a disposable database when you need automatic cleanup. The demo command
deliberately provides no hidden reset or production deletion behavior.
