from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, status
from pydantic import BaseModel
from sqlalchemy import select, delete, text
from sqlalchemy.orm import Session

from ..db import get_db
from ..deps import error_response, get_current_user
from ..models import Friendship, User


router = APIRouter(prefix="/friends", tags=["friends"])


class FriendUsernameRequest(BaseModel):
    username: str


class FriendOut(BaseModel):
    id: str
    username: str
    display_name: str | None = None
    profile_picture_url: str | None = None
    latest_ping_received_at: datetime | None = None


class FriendAddResponse(BaseModel):
    added: bool
    friend: FriendOut


class FriendRemoveResponse(BaseModel):
    removed: bool


class FriendListResponse(BaseModel):
    friends: list[FriendOut]


class ShareLocationRequest(BaseModel):
    username: str
    enabled: bool


class ShareLocationResponse(BaseModel):
    updated: bool
    username: str
    is_sharing_location: bool


@router.post("/add", response_model=FriendAddResponse)
def add_friend(
    payload: FriendUsernameRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if payload.username == current_user.username:
        error_response(status.HTTP_400_BAD_REQUEST, "CANNOT_FRIEND_SELF", "Cannot add yourself as a friend")

    friend = db.scalar(select(User).where(User.username == payload.username))
    if not friend:
        error_response(status.HTTP_404_NOT_FOUND, "USER_NOT_FOUND", "Friend user not found")

    # Idempotent: merge rows; if exist, nothing changes
    for (user_id, friend_id) in ((current_user.id, friend.id), (friend.id, current_user.id)):
        exists = db.get(Friendship, {"user_id": user_id, "friend_id": friend_id})
        if not exists:
            db.add(Friendship(user_id=user_id, friend_id=friend_id))

    db.commit()
    return FriendAddResponse(
        added=True,
        friend=FriendOut(
            id=friend.id,
            username=friend.username,
            display_name=friend.display_name,
            profile_picture_url=friend.profile_picture_url,
        ),
    )


@router.post("/remove", response_model=FriendRemoveResponse)
def remove_friend(
    payload: FriendUsernameRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    friend = db.scalar(select(User).where(User.username == payload.username))
    if not friend:
        error_response(status.HTTP_404_NOT_FOUND, "USER_NOT_FOUND", "Friend user not found")

    stmt = delete(Friendship).where(
        (Friendship.user_id == current_user.id) & (Friendship.friend_id == friend.id)
        | (Friendship.user_id == friend.id) & (Friendship.friend_id == current_user.id)
    )
    db.execute(stmt)
    db.commit()
    return FriendRemoveResponse(removed=True)


@router.get("", response_model=FriendListResponse)
def list_friends(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    # Join friends with their latest ping received_at via fobs -> pings
    sql = """
    SELECT
        u.id,
        u.username,
        u.display_name,
        u.profile_picture_url,
        latest_ping.received_at AS latest_ping_received_at
    FROM friendships f
    JOIN users u ON u.id = f.friend_id
    LEFT JOIN LATERAL (
        SELECT p.received_at
        FROM fobs
        JOIN pings p ON p.fob_uid = fobs.fob_uid
        WHERE fobs.owner_user_id = u.id
        ORDER BY p.received_at DESC
        LIMIT 1
    ) latest_ping ON true
    WHERE f.user_id = :current_user_id
    ORDER BY u.username
    """
    rows = db.execute(text(sql), {"current_user_id": current_user.id}).mappings().all()

    friends = [
        FriendOut(
            id=str(row["id"]),
            username=row["username"],
            display_name=row["display_name"],
            profile_picture_url=row["profile_picture_url"],
            latest_ping_received_at=row["latest_ping_received_at"],
        )
        for row in rows
    ]
    return FriendListResponse(friends=friends)


@router.patch("/share-location", response_model=ShareLocationResponse)
def toggle_share_location(
    payload: ShareLocationRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Toggle location sharing for a specific friend relationship."""
    friend = db.scalar(select(User).where(User.username == payload.username))
    if not friend:
        error_response(status.HTTP_404_NOT_FOUND, "USER_NOT_FOUND", "Friend user not found")

    friendship = db.get(Friendship, {"user_id": current_user.id, "friend_id": friend.id})
    if not friendship:
        error_response(status.HTTP_404_NOT_FOUND, "FRIENDSHIP_NOT_FOUND", "Friendship does not exist")

    friendship.is_sharing_location = payload.enabled
    db.add(friendship)
    db.commit()
    db.refresh(friendship)

    return ShareLocationResponse(
        updated=True,
        username=friend.username,
        is_sharing_location=friendship.is_sharing_location,
    )

