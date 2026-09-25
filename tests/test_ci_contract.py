from pathlib import Path


def test_ci_covers_the_release_quality_gates():
    workflow = (
        Path(__file__).resolve().parents[1] / ".github" / "workflows" / "ci.yml"
    ).read_text(encoding="utf-8")

    for required_command in (
        "ruff check .",
        "ruff format --check .",
        "alembic upgrade head",
        "pytest --cov-report=xml",
        "pip-audit",
        "uv build",
        "docker build",
        "/health/live",
        "/health/ready",
        "npm ci",
        "npm run generate:api",
        "npm run lint",
        "npm run format:check",
        "npm run typecheck",
        "npm run test:run",
        "npm run build",
    ):
        assert required_command in workflow
