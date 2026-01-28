from fastapi import APIRouter, Depends, status
from pydantic import BaseModel
from sqlalchemy import select, delete
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


class FriendAddResponse(BaseModel):
    added: bool
    friend: FriendOut


class FriendRemoveResponse(BaseModel):
    removed: bool


class FriendListResponse(BaseModel):
    friends: list[FriendOut]


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
        friend=FriendOut(id=friend.id, username=friend.username),
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
    stmt = (
        select(User)
        .join(Friendship, Friendship.friend_id == User.id)
        .where(Friendship.user_id == current_user.id)
        .order_by(User.username)
    )
    rows = db.scalars(stmt).all()
    friends = [FriendOut(id=u.id, username=u.username) for u in rows]
    return FriendListResponse(friends=friends)

