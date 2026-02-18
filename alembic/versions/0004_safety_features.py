"""Add safety features: user profile fields, friendship sharing toggle,
ping status, incidents table.

Revision ID: 0004_safety_features
Revises: 0003_fob_owner_nullable
Create Date: 2026-02-17 00:00:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "0004_safety_features"
down_revision: Union[str, None] = "0003_fob_owner_nullable"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # --- Users: add display_name and profile_picture_url ---
    op.add_column("users", sa.Column("display_name", sa.Text(), nullable=True))
    op.add_column("users", sa.Column("profile_picture_url", sa.Text(), nullable=True))

    # --- Friendships: add is_sharing_location ---
    op.add_column(
        "friendships",
        sa.Column(
            "is_sharing_location",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("true"),
        ),
    )

    # --- Pings: add status (0=Safe, 1=Not Safe, 2=SOS) ---
    op.add_column(
        "pings",
        sa.Column(
            "status",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("0"),
        ),
    )

    # --- Incidents table ---
    op.create_table(
        "incidents",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=False),
            server_default=sa.text("gen_random_uuid()"),
            primary_key=True,
        ),
        sa.Column(
            "reporter_id",
            postgresql.UUID(as_uuid=False),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("lat", sa.Float(precision=53), nullable=False),
        sa.Column("lng", sa.Float(precision=53), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )
    op.create_index("ix_incidents_reporter_id", "incidents", ["reporter_id"])


def downgrade() -> None:
    op.drop_index("ix_incidents_reporter_id", table_name="incidents")
    op.drop_table("incidents")
    op.drop_column("pings", "status")
    op.drop_column("friendships", "is_sharing_location")
    op.drop_column("users", "profile_picture_url")
    op.drop_column("users", "display_name")
