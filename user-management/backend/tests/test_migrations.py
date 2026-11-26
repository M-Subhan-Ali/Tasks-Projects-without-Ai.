"""Migration 0005 (unique email for active users only), run on a real SQLite file.

The other tests build the schema straight from the models. These run the
actual Alembic scripts against a temporary database file that already holds
users, to prove that the upgrade keeps every row as it was and that the
constraint really changes. The real users.db is never touched.
"""

import sqlite3
from collections.abc import Iterator
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config

BACKEND_DIR = Path(__file__).resolve().parents[1]
COLUMNS = "id, name, email, phone, city, company_name, is_deleted, deleted_at"

# One active user and one soft-deleted user, as they would exist before 0005.
EXISTING_USERS = [
    (1, "Ali Raza", "ali@example.com", "0321-1234567", "Lahore", "Cloud Pacer", 0, None),
    (2, "Sara Khan", "sara@example.com", "0300-7654321", None, "Tech Life", 1, "2026-11-20 10:00:00"),
]


@pytest.fixture
def db_file(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    path = tmp_path / "migration_test.db"
    # alembic/env.py reads DATABASE_URL; load_dotenv does not override it.
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{path.as_posix()}")
    return path


@pytest.fixture
def alembic_config(db_file: Path) -> Config:
    # Built in code, without alembic.ini, so env.py skips fileConfig(): that
    # would reconfigure logging for the whole test run and break test_logging.
    config = Config()
    config.set_main_option("script_location", str(BACKEND_DIR / "alembic"))
    return config


@pytest.fixture
def connect(db_file: Path) -> Iterator[sqlite3.Connection]:
    connection = sqlite3.connect(db_file)
    yield connection
    connection.close()


def insert_user(connection: sqlite3.Connection, email: str, is_deleted: int) -> None:
    try:
        connection.execute(
            "INSERT INTO users (name, email, phone, company_name, is_deleted) VALUES (?, ?, ?, ?, ?)",
            ("New User", email, "0321-1234567", "Co", is_deleted),
        )
        connection.commit()
    except sqlite3.IntegrityError:
        # Close the failed transaction, or its lock would block Alembic's next step.
        connection.rollback()
        raise


def all_users(connection: sqlite3.Connection) -> list[tuple]:
    return connection.execute(f"SELECT {COLUMNS} FROM users ORDER BY id").fetchall()


def revision(connection: sqlite3.Connection) -> str:
    return connection.execute("SELECT version_num FROM alembic_version").fetchone()[0]


def index_sql(connection: sqlite3.Connection) -> str | None:
    row = connection.execute(
        "SELECT sql FROM sqlite_master WHERE type = 'index' AND name = 'uq_users_email_active'"
    ).fetchone()
    return row[0] if row else None


def test_upgrade_keeps_existing_rows_and_allows_reuse(
    alembic_config: Config, connect: sqlite3.Connection
) -> None:
    command.upgrade(alembic_config, "0004")
    connect.executemany(f"INSERT INTO users ({COLUMNS}) VALUES (?, ?, ?, ?, ?, ?, ?, ?)", EXISTING_USERS)
    connect.commit()
    # Before 0005, the deleted user's email is still reserved.
    with pytest.raises(sqlite3.IntegrityError):
        insert_user(connect, "sara@example.com", is_deleted=0)

    command.upgrade(alembic_config, "head")

    assert revision(connect) == "0005"
    # Every row is still there, unchanged.
    assert all_users(connect) == EXISTING_USERS
    # The new rule is a PARTIAL unique index.
    sql = index_sql(connect)
    assert sql is not None and "UNIQUE" in sql.upper() and "is_deleted = 0" in sql
    # The deleted user's email can be reused...
    insert_user(connect, "sara@example.com", is_deleted=0)
    # ...but an active user's email still can't.
    with pytest.raises(sqlite3.IntegrityError, match="users.email"):
        insert_user(connect, "ali@example.com", is_deleted=0)


def test_downgrade_restores_unique_email_for_every_row(
    alembic_config: Config, connect: sqlite3.Connection
) -> None:
    command.upgrade(alembic_config, "head")
    connect.executemany(f"INSERT INTO users ({COLUMNS}) VALUES (?, ?, ?, ?, ?, ?, ?, ?)", EXISTING_USERS)
    connect.commit()

    command.downgrade(alembic_config, "0004")

    assert revision(connect) == "0004"
    assert all_users(connect) == EXISTING_USERS
    assert index_sql(connect) is None
    # Back to the old rule: the deleted user's email is reserved again.
    with pytest.raises(sqlite3.IntegrityError):
        insert_user(connect, "sara@example.com", is_deleted=0)


def test_downgrade_is_refused_when_an_email_was_reused(
    alembic_config: Config, connect: sqlite3.Connection
) -> None:
    command.upgrade(alembic_config, "head")
    connect.executemany(f"INSERT INTO users ({COLUMNS}) VALUES (?, ?, ?, ?, ?, ?, ?, ?)", EXISTING_USERS)
    connect.commit()
    insert_user(connect, "sara@example.com", is_deleted=0)  # reuse the deleted user's email
    before = all_users(connect)

    with pytest.raises(RuntimeError, match="Cannot downgrade"):
        command.downgrade(alembic_config, "0004")

    # Nothing changed: same revision, same rows, partial index still in place.
    assert revision(connect) == "0005"
    assert all_users(connect) == before
    assert index_sql(connect) is not None
