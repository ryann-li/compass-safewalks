"""initial schema and seed towers

Revision ID: 0001_initial
Revises: 
Create Date: 2026-01-28 00:00:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "0001_initial"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Extensions
    op.execute("CREATE EXTENSION IF NOT EXISTS pgcrypto;")

    # users
    op.create_table(
        "users",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=False),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("username", sa.Text(), nullable=False, unique=True),
        sa.Column("password_hash", sa.Text(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )

    # friendships
    op.create_table(
        "friendships",
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=False),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column(
            "friend_id",
            postgresql.UUID(as_uuid=False),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.CheckConstraint("user_id <> friend_id", name="friend_not_self"),
    )
    op.create_index(
        "ix_friendships_user_id",
        "friendships",
        ["user_id"],
    )

    # fobs
    op.create_table(
        "fobs",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=False),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("fob_uid", sa.Text(), nullable=False, unique=True),
        sa.Column(
            "owner_user_id",
            postgresql.UUID(as_uuid=False),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
            unique=True,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )

    # towers
    op.create_table(
        "towers",
        sa.Column("id", sa.Text(), primary_key=True),
        sa.Column("name", sa.Text(), nullable=True),
        sa.Column("lat", sa.Float(precision=53), nullable=False),
        sa.Column("lng", sa.Float(precision=53), nullable=False),
        sa.Column(
            "active",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("true"),
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )

    # pings
    op.create_table(
        "pings",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=False),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("fob_uid", sa.Text(), nullable=False),
        sa.Column(
            "tower_id",
            sa.Text(),
            sa.ForeignKey("towers.id"),
            nullable=False,
        ),
        sa.Column(
            "received_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column("rssi", sa.Integer(), nullable=True),
        sa.Column("tower_reported_at", sa.DateTime(timezone=True), nullable=True),
    )

    op.create_index(
        "ix_pings_fob_uid_received_at_desc",
        "pings",
        ["fob_uid", sa.text("received_at DESC")],
    )
    op.create_index(
        "ix_pings_received_at_desc",
        "pings",
        [sa.text("received_at DESC")],
    )

    # Seed towers
    op.execute(
        """
        INSERT INTO towers (id, name, lat, lng)
        VALUES
            ('tower-1', 'Tower 1', 43.6500, -79.3800),
            ('tower-2', 'Tower 2', 43.6600, -79.4000)
        ON CONFLICT (id) DO NOTHING;
        """
    )


def downgrade() -> None:
    op.drop_index("ix_pings_received_at_desc", table_name="pings")
    op.drop_index("ix_pings_fob_uid_received_at_desc", table_name="pings")
    op.drop_table("pings")
    op.drop_table("towers")
    op.drop_table("fobs")
    op.drop_index("ix_friendships_user_id", table_name="friendships")
    op.drop_table("friendships")
    op.drop_table("users")

