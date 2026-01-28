from datetime import datetime
from typing import Optional

from sqlalchemy import Boolean, CheckConstraint, DateTime, ForeignKey, Integer, Text, Index, text, Float, desc
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship, Mapped, mapped_column

from .db import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    username: Mapped[str] = mapped_column(Text, unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )

    friends: Mapped[list["Friendship"]] = relationship(
        "Friendship",
        foreign_keys="Friendship.user_id",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )


class Friendship(Base):
    __tablename__ = "friendships"

    user_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("users.id", ondelete="CASCADE"),
        primary_key=True,
    )
    friend_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("users.id", ondelete="CASCADE"),
        primary_key=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )

    __table_args__ = (
        CheckConstraint("user_id <> friend_id", name="friend_not_self"),
        Index("ix_friendships_user_id", "user_id"),
    )


class Fob(Base):
    __tablename__ = "fobs"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    fob_uid: Mapped[str] = mapped_column(Text, unique=True, nullable=False)
    owner_user_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("users.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )

    owner: Mapped[User] = relationship("User")


class Tower(Base):
    __tablename__ = "towers"

    id: Mapped[str] = mapped_column(Text, primary_key=True)
    name: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    lat: Mapped[float] = mapped_column(Float(precision=53), nullable=False)
    lng: Mapped[float] = mapped_column(Float(precision=53), nullable=False)
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("true"))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )


class Ping(Base):
    __tablename__ = "pings"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    fob_uid: Mapped[str] = mapped_column(Text, nullable=False, index=False)
    tower_id: Mapped[str] = mapped_column(
        Text, ForeignKey("towers.id", ondelete="RESTRICT"), nullable=False
    )
    received_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )
    rssi: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    tower_reported_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    tower: Mapped["Tower"] = relationship("Tower")

    __table_args__ = (
        Index("ix_pings_fob_uid_received_at_desc", "fob_uid", desc("received_at")),
        Index("ix_pings_received_at_desc", desc("received_at")),
    )

