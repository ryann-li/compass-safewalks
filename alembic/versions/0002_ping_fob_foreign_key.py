"""Simplify fobs PK, remove towers, pings store lat/lng directly

Revision ID: 0002_ping_fob_fk
Revises: 0001_initial
Create Date: 2026-02-08 00:00:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "0002_ping_fob_fk"
down_revision: Union[str, None] = "0001_initial"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── pings: drop old indexes ──
    op.drop_index("ix_pings_fob_uid_received_at_desc", table_name="pings")
    op.drop_index("ix_pings_received_at_desc", table_name="pings")

    # ── pings: replace UUID PK with serial integer ──
    op.execute("ALTER TABLE pings DROP CONSTRAINT pings_pkey")
    op.drop_column("pings", "id")
    op.execute("ALTER TABLE pings ADD COLUMN id SERIAL PRIMARY KEY")

    # ── pings: drop tower-related and rssi columns ──
    op.drop_column("pings", "tower_id")
    op.drop_column("pings", "rssi")
    op.drop_column("pings", "tower_reported_at")

    # ── pings: add lat/lng columns ──
    op.add_column("pings", sa.Column("lat", sa.Float(precision=53), nullable=True))
    op.add_column("pings", sa.Column("lng", sa.Float(precision=53), nullable=True))
    # Backfill from towers if possible
    op.execute(
        """
        UPDATE pings SET lat = 0, lng = 0 WHERE lat IS NULL
        """
    )
    op.alter_column("pings", "lat", nullable=False)
    op.alter_column("pings", "lng", nullable=False)

    # ── fobs: make fob_uid the PK, drop UUID id ──
    op.execute("ALTER TABLE fobs DROP CONSTRAINT fobs_pkey")
    op.drop_column("fobs", "id")
    op.execute("ALTER TABLE fobs DROP CONSTRAINT IF EXISTS fobs_fob_uid_key")
    op.execute("ALTER TABLE fobs ADD PRIMARY KEY (fob_uid)")

    # ── pings: delete orphans then add FK to fobs ──
    op.execute(
        "DELETE FROM pings WHERE fob_uid NOT IN (SELECT fob_uid FROM fobs)"
    )
    op.create_foreign_key(
        "fk_pings_fob_uid",
        "pings",
        "fobs",
        ["fob_uid"],
        ["fob_uid"],
        ondelete="CASCADE",
    )

    # ── pings: re-create indexes ──
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

    # ── drop towers table ──
    op.drop_table("towers")


def downgrade() -> None:
    # ── restore towers table ──
    op.create_table(
        "towers",
        sa.Column("id", sa.Text(), primary_key=True),
        sa.Column("name", sa.Text(), nullable=True),
        sa.Column("lat", sa.Float(precision=53), nullable=False),
        sa.Column("lng", sa.Float(precision=53), nullable=False),
        sa.Column(
            "active", sa.Boolean(), nullable=False, server_default=sa.text("true")
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )
    op.execute(
        """
        INSERT INTO towers (id, name, lat, lng)
        VALUES
            ('tower-1', 'Tower 1', 43.6500, -79.3800),
            ('tower-2', 'Tower 2', 43.6600, -79.4000)
        ON CONFLICT (id) DO NOTHING;
        """
    )

    # ── pings: drop indexes ──
    op.drop_index("ix_pings_received_at_desc", table_name="pings")
    op.drop_index("ix_pings_fob_uid_received_at_desc", table_name="pings")

    # ── pings: drop FK to fobs ──
    op.drop_constraint("fk_pings_fob_uid", "pings", type_="foreignkey")

    # ── fobs: restore UUID id as PK ──
    op.execute("ALTER TABLE fobs DROP CONSTRAINT fobs_pkey")
    op.execute(
        "ALTER TABLE fobs ADD COLUMN id UUID NOT NULL DEFAULT gen_random_uuid()"
    )
    op.execute("ALTER TABLE fobs ADD PRIMARY KEY (id)")
    op.execute(
        "ALTER TABLE fobs ADD CONSTRAINT fobs_fob_uid_key UNIQUE (fob_uid)"
    )

    # ── pings: drop lat/lng, restore tower_id, rssi, tower_reported_at ──
    op.drop_column("pings", "lat")
    op.drop_column("pings", "lng")
    op.add_column(
        "pings",
        sa.Column("tower_id", sa.Text(), nullable=True),
    )
    op.add_column(
        "pings",
        sa.Column("rssi", sa.Integer(), nullable=True),
    )
    op.add_column(
        "pings",
        sa.Column("tower_reported_at", sa.DateTime(timezone=True), nullable=True),
    )

    # ── pings: restore UUID PK ──
    op.execute("ALTER TABLE pings DROP CONSTRAINT pings_pkey")
    op.drop_column("pings", "id")
    op.execute(
        "ALTER TABLE pings ADD COLUMN id UUID NOT NULL DEFAULT gen_random_uuid() PRIMARY KEY"
    )

    # ── pings: restore indexes ──
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
