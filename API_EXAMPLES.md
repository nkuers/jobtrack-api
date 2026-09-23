# API usage examples

These examples exercise the public authentication lifecycle and operational
endpoints against a local server. Start the application with `python
scripts/dev.py serve` and use `http://127.0.0.1:8000` as the base URL.

The generated OpenAPI document at `/docs` remains the source of truth for all
request and response schemas.

## Register a user

```bash
curl --request POST http://127.0.0.1:8000/register/ \
  --header "Content-Type: application/json" \
  --data '{"username":"alice","password":"replace-this-password","email":"alice@example.com"}'
```

Example response:

```json
{
  "id": 1,
  "username": "alice",
  "role": "user",
  "email": "alice@example.com",
  "email_verified_at": null
}
```

Email is optional, normalized to lowercase, and unique when supplied. Usernames
must also be unique. Treat passwords used in examples as disposable local
values, never production credentials.

## Verify an email address

Email delivery is disabled by default. After configuring SMTP, request a
verification message with the same response for known, unknown, and already
verified addresses:

```bash
curl --request POST http://127.0.0.1:8000/auth/email-verification/request \
  --header "Content-Type: application/json" \
  --data '{"email":"alice@example.com"}'
```

The email contains a time-limited opaque token. The API never returns that raw
token. The frontend submits the token from the link:

```bash
curl --request POST http://127.0.0.1:8000/auth/email-verification/confirm \
  --header "Content-Type: application/json" \
  --data '{"token":"paste-token-from-verification-link"}'
```

Successful confirmation is single use. Expired, consumed, unknown, and
wrong-purpose tokens all receive the same generic `400` response.

## Reset a forgotten password

Password recovery is available only for active accounts with a verified email,
but the request endpoint always returns the same `202` response. This prevents
clients from discovering which accounts exist:

```bash
curl --request POST http://127.0.0.1:8000/auth/password-reset/request \
  --header "Content-Type: application/json" \
  --data '{"email":"alice@example.com"}'
```

The reset email contains an opaque, time-limited token. Submit it with a new
password of at least 12 characters and no more than 72 UTF-8 bytes:

```bash
curl --request POST http://127.0.0.1:8000/auth/password-reset/confirm \
  --header "Content-Type: application/json" \
  --data '{"token":"paste-token-from-reset-link","new_password":"replace-with-a-long-new-password"}'
```

A successful reset consumes all outstanding password-reset tokens and revokes
every refresh token for the account. It does not issue a new session. Existing
JWT access tokens are stateless and remain valid until their configured expiry.

## Log in

The login endpoint follows the OAuth2 password form convention, so its body is
form encoded rather than JSON:

```bash
curl --request POST http://127.0.0.1:8000/login/ \
  --header "Content-Type: application/x-www-form-urlencoded" \
  --header "X-Device-Name: Work laptop" \
  --data-urlencode "username=alice" \
  --data-urlencode "password=replace-this-password"
```

Example response:

```json
{
  "access_token": "eyJ...",
  "refresh_token": "opaque-random-value",
  "token_type": "bearer"
}
```

Set the returned values in your shell for the next examples:

```bash
ACCESS_TOKEN="paste-access-token"
REFRESH_TOKEN="paste-refresh-token"
```

Access tokens are JWTs and are short lived. Refresh tokens are opaque secrets;
the database stores only their hashes. Each login creates a separate device
session, and refresh-token rotation remains inside that session family.

## Enroll and use TOTP MFA

MFA is disabled by default. After the operator configures `MFA_ENABLED=true`
and a dedicated `MFA_ENCRYPTION_KEY`, an authenticated user begins enrollment:

```bash
curl --request POST http://127.0.0.1:8000/auth/mfa/totp/enroll \
  --header "Authorization: Bearer ${ACCESS_TOKEN}" \
  --header "Content-Type: application/json" \
  --data '{"password":"replace-this-password"}'
```

Scan the returned `provisioning_uri`, then confirm with the current six-digit
code. The response displays recovery codes exactly once; store them securely.

```bash
curl --request POST http://127.0.0.1:8000/auth/mfa/totp/confirm \
  --header "Authorization: Bearer ${ACCESS_TOKEN}" \
  --header "Content-Type: application/json" \
  --data '{"code":"123456"}'
```

Subsequent password login returns `mfa_required` and a short-lived
`challenge_token`, not access or refresh tokens. Complete it with either a new
TOTP code or one unused recovery code:

```bash
curl --request POST http://127.0.0.1:8000/auth/mfa/challenge/verify \
  --header "Content-Type: application/json" \
  --data '{"challenge_token":"paste-opaque-challenge","code":"123456"}'
```

Use `GET /auth/mfa/status`, `POST /auth/mfa/recovery-codes/regenerate`, and
`POST /auth/mfa/disable` for lifecycle management. Regeneration and disable
require the current password plus a factor and revoke refresh sessions. A
recovery code is single use. A refreshed access token does not retain recent
MFA status. TOTP is not phishing resistant; prefer WebAuthn/passkeys when that
property is required.

## Sign in and link accounts with OpenID Connect

After registering the exact callback URI with a provider and enabling OIDC,
open the authorization endpoint in a browser:

```bash
curl --include http://127.0.0.1:8000/auth/oidc/authorize
```

The API returns a `303` redirect to the configured provider and sets a
short-lived HttpOnly browser-binding cookie. The authorization request uses a
transaction-specific `state`, nonce, and PKCE S256 challenge. The provider
redirects the same browser to `/auth/oidc/callback`; the API validates and
consumes the transaction before returning local access and refresh tokens.

To link a provider identity to an existing account, begin from a recently
authenticated access token:

```bash
curl --request POST --include \
  http://127.0.0.1:8000/auth/oidc/link/authorize \
  --header "Authorization: Bearer ${ACCESS_TOKEN}"
```

A refresh-issued access token cannot begin linking. The callback binds the
provider's immutable issuer and subject to the authenticated user. A matching
email never silently links an existing account. List or unlink identities with:

```bash
curl http://127.0.0.1:8000/auth/oidc/identities \
  --header "Authorization: Bearer ${ACCESS_TOKEN}"

curl --request DELETE \
  http://127.0.0.1:8000/auth/oidc/identities/1 \
  --header "Authorization: Bearer ${ACCESS_TOKEN}"
```

Link and unlink operations revoke refresh sessions. The last sign-in method of
an OIDC-only account cannot be removed. If local MFA is enabled, a successful
OIDC callback still returns an MFA challenge rather than bypassing the second
factor.

## Read the current user

```bash
curl http://127.0.0.1:8000/auth/me \
  --header "Authorization: Bearer ${ACCESS_TOKEN}"
```

Example response:

```json
{
  "id": 1,
  "username": "alice",
  "role": "user"
}
```

Missing, malformed, expired, or otherwise invalid access tokens return `401`.

## Manage companies

Create a company owned by the authenticated user. Ownership always comes from
the access token; clients cannot submit `owner_id`.

```bash
curl --request POST http://127.0.0.1:8000/api/v1/companies \
  --header "Authorization: Bearer ${ACCESS_TOKEN}" \
  --header "Content-Type: application/json" \
  --data '{"name":"Acme","website":"https://example.com/careers","industry":"Technology","location":"Shanghai","notes":"Target company"}'
```

List and filter the current user's companies:

```bash
curl "http://127.0.0.1:8000/api/v1/companies?keyword=acme&industry=Technology&page=1&page_size=20" \
  --header "Authorization: Bearer ${ACCESS_TOKEN}"
```

The list response contains `items`, `total`, `page`, and `page_size`. Company
names are unique per user after trimming and case normalization. Reading,
updating, or deleting a missing company or another user's company returns the
same `404` response.

```bash
COMPANY_ID=1

curl --request PATCH \
  "http://127.0.0.1:8000/api/v1/companies/${COMPANY_ID}" \
  --header "Authorization: Bearer ${ACCESS_TOKEN}" \
  --header "Content-Type: application/json" \
  --data '{"location":"Beijing","notes":null}'

curl --request DELETE \
  "http://127.0.0.1:8000/api/v1/companies/${COMPANY_ID}" \
  --header "Authorization: Bearer ${ACCESS_TOKEN}"
```

## Manage jobs

Salary amounts use integer minor currency units. For example, `2000000` with
`CNY` means CNY 20,000.00 when the currency uses two decimal places.

```bash
curl --request POST http://127.0.0.1:8000/api/v1/jobs \
  --header "Authorization: Bearer ${ACCESS_TOKEN}" \
  --header "Content-Type: application/json" \
  --data "{\"company_id\":${COMPANY_ID},\"title\":\"Backend Engineer\",\"employment_type\":\"full_time\",\"work_mode\":\"hybrid\",\"location\":\"Shanghai\",\"salary_min\":2000000,\"salary_max\":3000000,\"salary_currency\":\"CNY\"}"
```

The referenced company must belong to the authenticated user. List jobs with
owner-scoped filters and a sort-field whitelist:

```bash
curl "http://127.0.0.1:8000/api/v1/jobs?company_id=${COMPANY_ID}&status=open&work_mode=hybrid&sort_by=salary_min&sort_order=asc&page=1&page_size=20" \
  --header "Authorization: Bearer ${ACCESS_TOKEN}"
```

```bash
JOB_ID=1

curl --request PATCH "http://127.0.0.1:8000/api/v1/jobs/${JOB_ID}" \
  --header "Authorization: Bearer ${ACCESS_TOKEN}" \
  --header "Content-Type: application/json" \
  --data '{"status":"paused","work_mode":"remote"}'

curl --request DELETE "http://127.0.0.1:8000/api/v1/jobs/${JOB_ID}" \
  --header "Authorization: Bearer ${ACCESS_TOKEN}"
```

A company with jobs cannot be deleted. Delete or move its jobs first; otherwise
the company deletion endpoint returns `409`.

## Manage applications

Create one application per job. New records may start as `saved` or `applied`;
when an application first enters `applied`, the API defaults `applied_at` to
the current UTC date if it was omitted.

```bash
curl --request POST http://127.0.0.1:8000/api/v1/applications \
  --header "Authorization: Bearer ${ACCESS_TOKEN}" \
  --header "Content-Type: application/json" \
  --data "{\"job_id\":${JOB_ID},\"status\":\"saved\",\"priority\":4,\"deadline\":\"2026-10-15\",\"next_action_at\":\"2026-09-25T09:00:00+08:00\",\"notes\":\"Tailor the resume\"}"
```

List the current user's applications with owner-scoped filters and a
sort-field whitelist:

```bash
curl "http://127.0.0.1:8000/api/v1/applications?company_id=${COMPANY_ID}&status=applied&priority=4&sort_by=next_action_at&sort_order=asc&page=1&page_size=20" \
  --header "Authorization: Bearer ${ACCESS_TOKEN}"
```

Metadata and status use separate endpoints so an ordinary update cannot bypass
the status machine. Status changes and their history entries commit in the
same database transaction.

```bash
APPLICATION_ID=1

curl --request PATCH \
  "http://127.0.0.1:8000/api/v1/applications/${APPLICATION_ID}" \
  --header "Authorization: Bearer ${ACCESS_TOKEN}" \
  --header "Content-Type: application/json" \
  --data '{"priority":5,"notes":"Recruiter replied"}'

curl --request PATCH \
  "http://127.0.0.1:8000/api/v1/applications/${APPLICATION_ID}/status" \
  --header "Authorization: Bearer ${ACCESS_TOKEN}" \
  --header "Content-Type: application/json" \
  --data '{"status":"applied"}'

curl --request PATCH \
  "http://127.0.0.1:8000/api/v1/applications/${APPLICATION_ID}/status" \
  --header "Authorization: Bearer ${ACCESS_TOKEN}" \
  --header "Content-Type: application/json" \
  --data '{"status":"screening"}'

curl \
  "http://127.0.0.1:8000/api/v1/applications/${APPLICATION_ID}/history" \
  --header "Authorization: Bearer ${ACCESS_TOKEN}"
```

Invalid transitions and duplicate applications return `409`. A job with an
application cannot be deleted until the application is deleted.

## Manage interviews

Schedule an interview for an application owned by the authenticated user. The
application must be in `screening`, `interview`, or `offer`; attempts from
`saved`, `applied`, or a terminal state return `409`. Times must include a UTC
offset; the API normalizes them to UTC. Durations may be between 15 and 480
minutes.

```bash
curl --request POST http://127.0.0.1:8000/api/v1/interviews \
  --header "Authorization: Bearer ${ACCESS_TOKEN}" \
  --header "Content-Type: application/json" \
  --data "{\"application_id\":${APPLICATION_ID},\"interview_type\":\"technical\",\"scheduled_at\":\"2026-10-08T14:00:00+08:00\",\"duration_minutes\":60,\"meeting_url\":\"https://meet.example.com/round-1\"}"
```

Scheduled interviews for the same user cannot overlap. Adjacent interviews
whose end and start times are equal are allowed. List all future scheduled
interviews in ascending time order:

```bash
curl "http://127.0.0.1:8000/api/v1/interviews/upcoming?limit=20" \
  --header "Authorization: Bearer ${ACCESS_TOKEN}"
```

Complete an interview and add optional feedback in one update, or set its
status to `cancelled`. Completed and cancelled interviews cannot transition
back to `scheduled`.

```bash
INTERVIEW_ID=1

curl --request PATCH \
  "http://127.0.0.1:8000/api/v1/interviews/${INTERVIEW_ID}" \
  --header "Authorization: Bearer ${ACCESS_TOKEN}" \
  --header "Content-Type: application/json" \
  --data '{"status":"completed","feedback":"Strong technical discussion"}'
```

An application with interviews cannot be deleted until its interviews are
deleted.

## View the dashboard

Read the current user's owner-scoped summary:

```bash
curl http://127.0.0.1:8000/api/v1/dashboard \
  --header "Authorization: Bearer ${ACCESS_TOKEN}"
```

The response includes company and job totals, a count for every application
status, applications created in the last seven days, Offer conversion rate,
the next seven days of scheduled interviews, overdue actions, and actions due
in the next seven days. Lists are time ordered and capped at 20 items.

Offer conversion is the number of applied applications that have ever reached
`offer`, divided by all applications with an `applied_at` date. An archived
offer therefore remains part of the numerator.

The aggregate uses a short-lived per-user Redis cache. Successful writes to
companies, jobs, applications, or interviews invalidate only that user's
entry. If Redis is unavailable, the endpoint recomputes from PostgreSQL.

## Rotate a refresh token

```bash
curl --request POST http://127.0.0.1:8000/auth/refresh \
  --header "Content-Type: application/json" \
  --data "{\"refresh_token\":\"${REFRESH_TOKEN}\"}"
```

The response has the same shape as login. Replace both local token variables
with the new values. A successful rotation revokes the submitted refresh token,
so replaying it returns `401`.

## Log out

```bash
curl --request POST http://127.0.0.1:8000/auth/logout \
  --header "Content-Type: application/json" \
  --data "{\"refresh_token\":\"${REFRESH_TOKEN}\"}"
```

Logout revokes the refresh token. Existing access tokens remain valid until
their configured expiration; clients should discard both tokens locally. The
server revokes the submitted token's complete rotation family.

## Manage device sessions

List active refresh-token families for the authenticated user:

```bash
curl http://127.0.0.1:8000/auth/sessions \
  --header "Authorization: Bearer ${ACCESS_TOKEN}"
```

The response contains a server-generated session ID, bounded device label, and
created/last-used/expiry timestamps. It never contains raw tokens, token hashes,
or IP addresses. Revoke one family idempotently:

```bash
SESSION_ID="paste-session-id"
curl --request DELETE "http://127.0.0.1:8000/auth/sessions/${SESSION_ID}" \
  --header "Authorization: Bearer ${ACCESS_TOKEN}"
```

Revoke every refresh-token session:

```bash
curl --request DELETE http://127.0.0.1:8000/auth/sessions \
  --header "Authorization: Bearer ${ACCESS_TOKEN}"
```

Replaying a refresh token already consumed by rotation revokes the live token
in that family. Session revocation does not immediately invalidate stateless
JWT access tokens; they remain valid until their configured expiry.

## Call an admin endpoint

Admin routes require an access token whose current database user has the
`admin` role. Registration never grants this role and the API does not provide
a public self-promotion path.

```bash
ADMIN_ACCESS_TOKEN="paste-admin-access-token"

curl http://127.0.0.1:8000/admin/users \
  --header "Authorization: Bearer ${ADMIN_ACCESS_TOKEN}"
```

To change an existing user's role as an admin:

```bash
curl --request PATCH http://127.0.0.1:8000/admin/users/1/role \
  --header "Authorization: Bearer ${ADMIN_ACCESS_TOKEN}" \
  --header "Content-Type: application/json" \
  --data '{"role":"admin"}'
```

To disable an account and atomically revoke its refresh-token sessions:

```bash
curl --request PATCH http://127.0.0.1:8000/admin/users/1/status \
  --header "Authorization: Bearer ${ADMIN_ACCESS_TOKEN}" \
  --header "Content-Type: application/json" \
  --data '{"is_active":false}'
```

Set `is_active` to `true` to allow new authentication again. Re-enabling an
account does not restore revoked sessions; the user must sign in again.

Non-admin users receive `403`; an unknown user ID returns `404`.

## Inspect health and metrics

```bash
curl --fail http://127.0.0.1:8000/health/live
curl --fail http://127.0.0.1:8000/health/ready
curl --fail http://127.0.0.1:8000/metrics
```

Liveness confirms that the process can respond. Readiness additionally checks
database connectivity. Restrict `/metrics` to trusted monitoring networks in
production.

## Trace a request with a correlation ID

```bash
curl --include http://127.0.0.1:8000/health/live \
  --header "X-Request-ID: docs-example-001"
```

The response includes the validated `X-Request-ID`, and the same value appears
in the structured request log. Invalid IDs are replaced rather than trusted.

## PowerShell authentication flow

```powershell
$baseUrl = "http://127.0.0.1:8000"

Invoke-RestMethod -Method Post -Uri "$baseUrl/register/" `
  -ContentType "application/json" `
  -Body '{"username":"alice","password":"replace-this-password"}'

$tokens = Invoke-RestMethod -Method Post -Uri "$baseUrl/login/" `
  -ContentType "application/x-www-form-urlencoded" `
  -Body @{ username = "alice"; password = "replace-this-password" }

$headers = @{ Authorization = "Bearer $($tokens.access_token)" }
Invoke-RestMethod -Uri "$baseUrl/auth/me" -Headers $headers

$rotated = Invoke-RestMethod -Method Post -Uri "$baseUrl/auth/refresh" `
  -ContentType "application/json" `
  -Body (@{ refresh_token = $tokens.refresh_token } | ConvertTo-Json)

Invoke-RestMethod -Method Post -Uri "$baseUrl/auth/password-reset/request" `
  -ContentType "application/json" `
  -Body '{"email":"alice@example.com"}'
```

## Error response conventions

Expected client errors use a JSON `detail` field and include `X-Request-ID`:

```json
{
  "detail": "Invalid username or password"
}
```

Unexpected errors return a generic `500` response without leaking internal
exception details. Use the correlation ID to locate the matching structured
log entry.
