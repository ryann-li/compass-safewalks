"""Make fobs.owner_user_id nullable so fobs can be auto-registered
by tower pings before a user claims them.

Revision ID: 0003_fob_owner_nullable
Revises: 0002_ping_fob_fk
Create Date: 2026-02-09 00:00:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0003_fob_owner_nullable"
down_revision: Union[str, None] = "0002_ping_fob_fk"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.alter_column("fobs", "owner_user_id", existing_type=sa.Text(), nullable=True)


def downgrade() -> None:
    # Remove unclaimed fobs before making column non-nullable again
    op.execute("DELETE FROM fobs WHERE owner_user_id IS NULL")
    op.alter_column("fobs", "owner_user_id", existing_type=sa.Text(), nullable=False)
