# ruff: noqa: E402

import os
from collections.abc import Callable, Generator
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.engine import make_url
from sqlalchemy.exc import OperationalError, ProgrammingError
from sqlalchemy.orm import Session

DEFAULT_TEST_DATABASE_URL = (
    "postgresql+psycopg://fastapi_user:fastapi_password@localhost:5433/fastapi_test"
)


def _is_explicit_test_database(database_url: str) -> bool:
    url = make_url(database_url)
    database_name = (url.database or "").lower()
    return url.get_backend_name() == "postgresql" and (
        database_name == "test" or database_name.endswith("_test")
    )


configured_database_url = os.environ.get("DATABASE_URL", "")
test_database_url = os.environ.get("TEST_DATABASE_URL")
if test_database_url is None and _is_explicit_test_database(configured_database_url):
    test_database_url = configured_database_url
if test_database_url is None:
    test_database_url = DEFAULT_TEST_DATABASE_URL
if not _is_explicit_test_database(test_database_url):
    raise RuntimeError(
        "Tests require a PostgreSQL database named 'test' or ending in '_test'; "
        "set TEST_DATABASE_URL to an isolated test database."
    )

# This must happen before importing application modules, because the engine is
# constructed when app.db.session is imported.
os.environ["DATABASE_URL"] = test_database_url
os.environ["DASHBOARD_CACHE_BACKEND"] = "none"

from app.auth.jwt import create_access_token
from app.auth.security import hash_password
from app.db.dependency import get_db
from app.db.session import SessionLocal, engine
from app.dependencies.business_rate_limit import business_write_limiter
from app.main import app
from app.middlewares.rate_limit import rate_limiter
from app.models import (  # noqa: F401 - imports populate Base.metadata
    AccountActionToken,
    Application,
    ApplicationStatusHistory,
    Company,
    ExternalIdentity,
    Interview,
    Job,
    MFARecoveryCode,
    OIDCTransaction,
    OutboxMessage,
    RefreshToken,
)
from app.models.user import User

ADMIN_USERNAME = "houngdev"
ADMIN_PASSWORD = "secret123"
ADMIN_PASSWORD_HASH = hash_password(ADMIN_PASSWORD)


def _truncate_database() -> None:
    table_names = ", ".join(
        f'"{table.name}"' for table in reversed(User.metadata.sorted_tables)
    )
    with engine.begin() as connection:
        connection.execute(
            text(f"TRUNCATE TABLE {table_names} RESTART IDENTITY CASCADE")
        )


@pytest.fixture(scope="session", autouse=True)
def verify_test_database() -> Generator[None]:
    if not _is_explicit_test_database(str(engine.url)):
        raise RuntimeError("Refusing to run tests against a non-test database")

    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
        _truncate_database()
    except (OperationalError, ProgrammingError) as exc:
        raise RuntimeError(
            "The isolated test database is unavailable or has not been migrated. "
            "Run: python scripts/dev.py test"
        ) from exc

    yield
    _truncate_database()


@pytest.fixture(autouse=True)
def clean_database() -> Generator[None]:
    _truncate_database()
    with SessionLocal() as db:
        db.add(
            User(
                username=ADMIN_USERNAME,
                password=ADMIN_PASSWORD_HASH,
                role="admin",
            )
        )
        db.commit()

    yield
    _truncate_database()


@pytest.fixture(autouse=True)
def reset_process_local_rate_limiter() -> Generator[None]:
    rate_limiter.requests.clear()
    business_write_limiter.requests.clear()
    yield
    rate_limiter.requests.clear()
    business_write_limiter.requests.clear()


@pytest.fixture
def db_session() -> Generator[Session]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.rollback()
        db.close()


@pytest.fixture
def client(db_session: Session) -> Generator[TestClient]:
    def override_get_db() -> Generator[Session]:
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    try:
        with TestClient(app) as test_client:
            yield test_client
    finally:
        app.dependency_overrides.pop(get_db, None)


@pytest.fixture
def user_factory(db_session: Session) -> Callable[..., User]:
    def create_user(
        *,
        username: str | None = None,
        password: str = "secret123",
        role: str = "user",
        email: str | None = None,
        is_active: bool = True,
    ) -> User:
        suffix = uuid4().hex
        user = User(
            username=username or f"user_{suffix[:12]}",
            password=hash_password(password),
            role=role,
            email=email or f"user_{suffix[:12]}@example.com",
            is_active=is_active,
        )
        db_session.add(user)
        db_session.commit()
        db_session.refresh(user)
        return user

    return create_user


@pytest.fixture
def user(user_factory: Callable[..., User]) -> User:
    return user_factory()


@pytest.fixture
def second_user(user_factory: Callable[..., User]) -> User:
    return user_factory()


@pytest.fixture
def auth_headers(user: User) -> dict[str, str]:
    token = create_access_token({"sub": user.username})
    return {"Authorization": f"Bearer {token}"}
