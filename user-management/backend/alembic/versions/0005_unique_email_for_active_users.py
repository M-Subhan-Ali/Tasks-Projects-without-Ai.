"""unique email for active users only

Revision ID: 0005
Revises: 0004
Create Date: 2026-11-26 12:00:00.000000

Before: UNIQUE(email) on every row, so a soft-deleted user kept their email
reserved forever and reusing it gave 409.
After:  a partial unique index, uq_users_email_active, that covers only the
rows WHERE is_deleted = 0. Two active users still can't share an email, but
deleted users' emails can be used again.

No rows are changed. SQLite can't drop a constraint in place, so batch mode
copies the table (every row, as it is) without the old constraint and swaps
the copy in.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '0005'
down_revision: Union[str, Sequence[str], None] = '0004'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

INDEX_NAME = "uq_users_email_active"
OLD_CONSTRAINT_NAME = "uq_users_email"

# 0001 created the constraint WITHOUT a name (unique=True on the column), so
# there is no name to drop. This naming convention makes batch mode give the
# reflected, unnamed constraint the name "uq_users_email", which drop_constraint
# can then use.
NAMING_CONVENTION = {"uq": "uq_%(table_name)s_%(column_0_name)s"}


def upgrade() -> None:
    """Swap the full UNIQUE(email) for a partial unique index on active users."""
    with op.batch_alter_table(
        "users", schema=None, naming_convention=NAMING_CONVENTION
    ) as batch_op:
        batch_op.drop_constraint(OLD_CONSTRAINT_NAME, type_="unique")

    op.create_index(
        INDEX_NAME,
        "users",
        ["email"],
        unique=True,
        sqlite_where=sa.text("is_deleted = 0"),
        postgresql_where=sa.text("is_deleted = false"),
    )


def downgrade() -> None:
    """Put back UNIQUE(email) on every row.

    Refused if an email has been reused (a deleted and an active user share
    it): the old rule can't hold for that data, and deleting or editing rows
    to make it fit would lose data. Fix or remove those rows first.

    The check runs BEFORE any change. SQLite schema changes are not reliably
    rolled back here, so failing halfway could leave the table with no email
    protection at all.
    """
    reused = op.get_bind().execute(
        sa.text(
            "SELECT COUNT(*) FROM "
            "(SELECT email FROM users GROUP BY email HAVING COUNT(*) > 1)"
        )
    ).scalar_one()
    if reused:
        # The count only, never the emails themselves (personal data in logs).
        raise RuntimeError(
            f"Cannot downgrade: {reused} email(s) are shared by more than one user "
            "(a deleted user and an active one). Remove or change those rows first."
        )

    op.drop_index(INDEX_NAME, table_name="users")

    with op.batch_alter_table("users", schema=None) as batch_op:
        batch_op.create_unique_constraint(OLD_CONSTRAINT_NAME, ["email"])
