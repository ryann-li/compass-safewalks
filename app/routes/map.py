from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.orm import Session

from ..db import get_db
from ..deps import get_current_user
from ..models import User


router = APIRouter(prefix="/map", tags=["map"])


class FriendInfo(BaseModel):
    id: str
    username: str


class LocationInfo(BaseModel):
    lat: float
    lng: float
    status: int  # 0=Safe, 1=Not Safe, 2=SOS
    received_at: datetime


class MapResult(BaseModel):
    friend: FriendInfo
    fob_uid: str
    location: LocationInfo


class MapLatestResponse(BaseModel):
    window_minutes: Optional[int] = None
    results: list[MapResult]


@router.get("/latest", response_model=MapLatestResponse)
def latest_map(
    window_minutes: Optional[int] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    # Compute time cutoff if provided and > 0
    cutoff: Optional[datetime] = None
    if window_minutes is not None and window_minutes > 0:
        cutoff = datetime.now(timezone.utc) - timedelta(minutes=window_minutes)

    # Use DISTINCT ON(fobs.fob_uid) to get latest ping per fob.
    # Only return friends where is_sharing_location is TRUE.
    # The viewer's row is friendships(user_id=viewer, friend_id=friend).
    # The friend's sharing preference lives on the *reverse* row:
    #   friendships(user_id=friend, friend_id=viewer).is_sharing_location
    # That row answers: "does the friend share their location with the viewer?"
    sql = """
    SELECT DISTINCT ON (fobs.fob_uid)
        friend.id AS friend_id,
        friend.username AS friend_username,
        fobs.fob_uid AS fob_uid,
        pings.lat AS lat,
        pings.lng AS lng,
        pings.status AS status,
        pings.received_at AS received_at
    FROM friendships AS viewer_fs
    JOIN users AS friend ON friend.id = viewer_fs.friend_id
    JOIN friendships AS friend_fs
         ON friend_fs.user_id = friend.id
        AND friend_fs.friend_id = viewer_fs.user_id
    JOIN fobs ON fobs.owner_user_id = friend.id
    JOIN pings ON pings.fob_uid = fobs.fob_uid
    WHERE viewer_fs.user_id = :current_user_id
      AND friend_fs.is_sharing_location = true
    """

    params: dict = {"current_user_id": current_user.id}
    if cutoff is not None:
        sql += " AND pings.received_at >= :cutoff"
        params["cutoff"] = cutoff

    sql += " ORDER BY fobs.fob_uid, pings.received_at DESC"

    rows = db.execute(text(sql), params).mappings().all()

    results: list[MapResult] = []
    for row in rows:
        results.append(
            MapResult(
                friend=FriendInfo(
                    id=str(row["friend_id"]),
                    username=row["friend_username"],
                ),
                fob_uid=row["fob_uid"],
                location=LocationInfo(
                    lat=row["lat"],
                    lng=row["lng"],
                    status=row["status"],
                    received_at=row["received_at"],
                ),
            )
        )

    # Normalize window_minutes in response: null for infinite window
    window_value = window_minutes if (window_minutes is not None and window_minutes > 0) else None
    return MapLatestResponse(window_minutes=window_value, results=results)

