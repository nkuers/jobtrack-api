import re
from pathlib import Path
from urllib.parse import unquote

from fastapi.testclient import TestClient

from app.main import app

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DOCUMENTS = [
    PROJECT_ROOT / name
    for name in (
        "API_EXAMPLES.md",
        "ARCHITECTURE.md",
        "CHANGELOG.md",
        "CODE_OF_CONDUCT.md",
        "CONTRIBUTING.md",
        "DATABASE_BENCHMARKS.md",
        "DEMO.md",
        "INTERVIEW_GUIDE.md",
        "LOAD_TESTING.md",
        "JOBTRACK_HARDENING.md",
        "DEPLOYMENT.md",
        "DEVELOPMENT.md",
        "MONITORING.md",
        "README.md",
        "RELEASE_CHECKLIST.md",
        "ROADMAP.md",
        "SECURITY.md",
    )
]
DOCUMENTS.extend(
    PROJECT_ROOT / "docs" / "decisions" / name
    for name in (
        "0001-keep-sync-sqlalchemy.md",
        "0002-service-owns-transactions.md",
        "0003-dashboard-cache-aside.md",
        "0004-owner-scoped-not-found.md",
        "0005-application-status-locking.md",
        "0006-interview-overlap-exclusion.md",
        "0007-composite-owner-foreign-keys.md",
        "0008-production-rate-limit-policy.md",
    )
)
MARKDOWN_LINK = re.compile(r"(?<!!)\[[^]]+\]\(([^)]+)\)")
DOCUMENTED_API_PATHS = {
    "/api/v1/applications",
    "/api/v1/applications/{application_id}",
    "/api/v1/applications/{application_id}/history",
    "/api/v1/applications/{application_id}/status",
    "/api/v1/companies",
    "/api/v1/companies/{company_id}",
    "/api/v1/dashboard",
    "/api/v1/interviews",
    "/api/v1/interviews/upcoming",
    "/api/v1/interviews/{interview_id}",
    "/api/v1/jobs",
    "/api/v1/jobs/{job_id}",
    "/admin/users",
    "/admin/users/{user_id}/role",
    "/admin/users/{user_id}/status",
    "/auth/logout",
    "/auth/email-verification/confirm",
    "/auth/email-verification/request",
    "/auth/me",
    "/auth/mfa/challenge/verify",
    "/auth/mfa/disable",
    "/auth/mfa/recovery-codes/regenerate",
    "/auth/mfa/status",
    "/auth/mfa/totp/confirm",
    "/auth/mfa/totp/enroll",
    "/auth/oidc/authorize",
    "/auth/oidc/callback",
    "/auth/oidc/identities",
    "/auth/oidc/identities/{identity_id}",
    "/auth/oidc/link/authorize",
    "/auth/password-reset/confirm",
    "/auth/password-reset/request",
    "/auth/refresh",
    "/auth/sessions",
    "/auth/sessions/{session_id}",
    "/health/live",
    "/health/ready",
    "/login/",
    "/metrics",
    "/register/",
}
OPENAPI_API_PATHS = DOCUMENTED_API_PATHS - {"/metrics"}


def local_link_targets(document: Path):
    for match in MARKDOWN_LINK.finditer(document.read_text(encoding="utf-8")):
        destination = match.group(1).strip()
        if destination.startswith(("#", "http://", "https://", "mailto:")):
            continue

        path_text = unquote(destination.split("#", 1)[0])
        if path_text:
            yield (document.parent / path_text).resolve()


def test_documentation_links_resolve_to_files():
    missing = []

    for document in DOCUMENTS:
        assert document.is_file(), f"Missing documentation file: {document.name}"
        for target in local_link_targets(document):
            if not target.is_file():
                missing.append(f"{document.name} -> {target.name}")

    assert not missing, "Broken documentation links:\n" + "\n".join(missing)


def test_readme_indexes_the_task_guides():
    readme = (PROJECT_ROOT / "README.md").read_text(encoding="utf-8")

    for guide in (
        "API_EXAMPLES.md",
        "ARCHITECTURE.md",
        "DATABASE_BENCHMARKS.md",
        "DEMO.md",
        "INTERVIEW_GUIDE.md",
        "LOAD_TESTING.md",
        "JOBTRACK_HARDENING.md",
        "DEPLOYMENT.md",
        "DEVELOPMENT.md",
        "MONITORING.md",
    ):
        assert f"]({guide})" in readme


def test_documented_application_routes_exist_in_openapi_schema():
    openapi_paths = set(app.openapi()["paths"])

    assert OPENAPI_API_PATHS <= openapi_paths
    assert "/metrics" not in openapi_paths


def test_hidden_documented_metrics_endpoint_is_reachable():
    response = TestClient(app).get("/metrics")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/plain")
