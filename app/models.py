from datetime import datetime
from typing import Optional

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Integer, Text, Index, text, Float, desc
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

    fob_uid: Mapped[str] = mapped_column(Text, primary_key=True)
    owner_user_id: Mapped[Optional[str]] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("users.id", ondelete="CASCADE"),
        unique=True,
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )

    owner: Mapped[Optional[User]] = relationship("User")
    pings: Mapped[list["Ping"]] = relationship(
        "Ping", back_populates="fob", cascade="all, delete-orphan"
    )


class Ping(Base):
    __tablename__ = "pings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    fob_uid: Mapped[str] = mapped_column(
        Text, ForeignKey("fobs.fob_uid", ondelete="CASCADE"), nullable=False
    )
    lat: Mapped[float] = mapped_column(Float(precision=53), nullable=False)
    lng: Mapped[float] = mapped_column(Float(precision=53), nullable=False)
    received_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )

    fob: Mapped["Fob"] = relationship("Fob", back_populates="pings")

    __table_args__ = (
        Index("ix_pings_fob_uid_received_at_desc", "fob_uid", desc("received_at")),
        Index("ix_pings_received_at_desc", desc("received_at")),
    )

