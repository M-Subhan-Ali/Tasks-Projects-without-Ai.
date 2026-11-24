"""create accounts table

Revision ID: 0003
Revises: 0002
Create Date: 2026-11-24 17:28:22.874247

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '0003'
down_revision: Union[str, Sequence[str], None] = '0002'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Login accounts for Day 5 auth. Constraints are named so later batch
    # migrations (SQLite copies the table to alter it) can refer to them.
    op.create_table('accounts',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('email', sa.String(length=100), nullable=False),
    sa.Column('hashed_password', sa.String(length=255), nullable=False),
    sa.Column('role', sa.String(length=20), server_default='viewer', nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
    sa.CheckConstraint("role IN ('admin', 'viewer')", name='ck_accounts_role'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('email', name='uq_accounts_email')
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table('accounts')
