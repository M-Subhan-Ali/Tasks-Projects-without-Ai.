"""Shared test setup: every test gets a fresh, empty in-memory database.

The real users.db is never used:
- DATABASE_URL is pointed at an in-memory database BEFORE the app is
  imported (load_dotenv does not override a variable that is already set);
- get_db is overridden so every request uses the test session;
- a session-level guard fails the run if users.db is modified.
"""

import os

os.environ["DATABASE_URL"] = "sqlite://"
os.environ["JWT_SECRET"] = "test-secret-that-is-at-least-32-characters-long"

from collections.abc import Generator, Iterator  # noqa: E402
from pathlib import Path  # noqa: E402
from typing import Any  # noqa: E402

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import Engine, create_engine  # noqa: E402
from sqlalchemy.orm import Session, sessionmaker  # noqa: E402
from sqlalchemy.pool import StaticPool  # noqa: E402

from app.database import Base, get_db  # noqa: E402
from app.main import app  # noqa: E402
from app.models import Account, Role  # noqa: E402
from app.security import create_access_token  # noqa: E402
from tests.factories import user_payload  # noqa: E402

REAL_DB_PATH = Path(__file__).resolve().parents[1] / "users.db"


@pytest.fixture(scope="session", autouse=True)
def real_database_is_untouched() -> Iterator[None]:
    """Fail the test run if anything wrote to the real users.db."""
    before = REAL_DB_PATH.stat().st_mtime if REAL_DB_PATH.exists() else None
    yield
    after = REAL_DB_PATH.stat().st_mtime if REAL_DB_PATH.exists() else None
    assert before == after, "Tests modified the real users.db"


@pytest.fixture
def engine() -> Iterator[Engine]:
    # In-memory SQLite normally gives every connection its own empty database.
    # StaticPool makes all sessions share ONE connection, so the tables we
    # create here are visible to the app during the test.
    test_engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    # Tests build the schema straight from the models: fast, and the
    # migrations themselves are checked separately with `alembic check`.
    Base.metadata.create_all(test_engine)
    yield test_engine
    Base.metadata.drop_all(test_engine)
    test_engine.dispose()


@pytest.fixture
def db_session(engine: Engine) -> Iterator[Session]:
    session = sessionmaker(bind=engine, autoflush=False)()
    yield session
    session.close()


@pytest.fixture
def client(engine: Engine) -> Iterator[TestClient]:
    testing_session = sessionmaker(bind=engine, autoflush=False)

    def override_get_db() -> Generator[Session, None, None]:
        session = testing_session()
        try:
            yield session
        finally:
            session.close()

    app.dependency_overrides[get_db] = override_get_db
    # raise_server_exceptions=False: let the app turn crashes into 500s,
    # like it does for real clients, instead of re-raising inside the test.
    # This client sends NO token: use it to test 401 responses.
    with TestClient(app, raise_server_exceptions=False) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def _auth_headers(db_session: Session, email: str, role: Role) -> dict[str, str]:
    """Create an account straight in the test database and sign a token for it.

    Skips register/login on purpose: Argon2 is slow, and these fixtures are for
    testing /users, not the login flow (tests/test_auth.py covers that).
    """
    account = Account(email=email, hashed_password="not-a-real-hash", role=role.value)
    db_session.add(account)
    db_session.commit()
    token = create_access_token(account.id, account.role)
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def admin_headers(db_session: Session) -> dict[str, str]:
    return _auth_headers(db_session, "admin@test.com", Role.ADMIN)


@pytest.fixture
def viewer_headers(db_session: Session) -> dict[str, str]:
    return _auth_headers(db_session, "viewer@test.com", Role.VIEWER)


@pytest.fixture
def admin_client(client: TestClient, admin_headers: dict[str, str]) -> TestClient:
    """A client that sends an admin token with every request.

    Depends on `client` so the get_db override is in place.
    """
    return TestClient(app, raise_server_exceptions=False, headers=admin_headers)


@pytest.fixture
def viewer_client(client: TestClient, viewer_headers: dict[str, str]) -> TestClient:
    """A client that sends a viewer token with every request."""
    return TestClient(app, raise_server_exceptions=False, headers=viewer_headers)


@pytest.fixture
def create_user(admin_client: TestClient) -> Any:
    """Create a user through the API (as an admin) and return the response JSON."""

    def _create(**overrides: Any) -> dict[str, Any]:
        response = admin_client.post("/users", json=user_payload(**overrides))
        assert response.status_code == 201, response.text
        return response.json()

    return _create
