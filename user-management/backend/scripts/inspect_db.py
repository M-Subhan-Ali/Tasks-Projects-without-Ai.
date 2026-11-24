"""Print the users table schema, row counts and Alembic revision of a SQLite file.

Run from the backend folder:  python -m scripts.inspect_db [path-to-db]
Default path: users.db
"""

import sqlite3
import sys
from pathlib import Path


def inspect(db_path: Path) -> None:
    if not db_path.exists():
        print(f"{db_path} does not exist")
        return

    with sqlite3.connect(db_path) as connection:
        tables = [row[0] for row in connection.execute(
            "SELECT name FROM sqlite_master WHERE type = 'table' ORDER BY name"
        )]
        print(f"Database: {db_path}")
        print(f"Tables:   {tables}")

        if "alembic_version" in tables:
            revision = connection.execute("SELECT version_num FROM alembic_version").fetchall()
            print(f"Alembic revision: {revision}")
        else:
            print("Alembic revision: (no alembic_version table)")

        if "users" not in tables:
            return

        columns = [row[1] for row in connection.execute("PRAGMA table_info(users)")]
        total = connection.execute("SELECT COUNT(*) FROM users").fetchone()[0]
        print(f"users columns: {columns}")
        print(f"users rows:    {total}")

        if "city" in columns:
            null_city = connection.execute(
                "SELECT COUNT(*) FROM users WHERE city IS NULL"
            ).fetchone()[0]
            print(f"rows with city IS NULL: {null_city}")


if __name__ == "__main__":
    inspect(Path(sys.argv[1] if len(sys.argv) > 1 else "users.db"))
