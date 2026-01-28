from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ..db import get_db
from ..deps import verify_tower_key, get_active_tower_or_error
from ..models import Ping


router = APIRouter(prefix="/tower", tags=["tower"])


class TowerPingRequest(BaseModel):
    tower_id: str
    fob_uid: str
    tower_reported_at: Optional[datetime] = None
    rssi: Optional[int] = None


class TowerPingResponse(BaseModel):
    stored: bool


@router.post("/pings", response_model=TowerPingResponse, status_code=status.HTTP_201_CREATED)
def ingest_ping(
    payload: TowerPingRequest,
    _: bool = Depends(verify_tower_key),
    db: Session = Depends(get_db),
):
    # Validate tower exists and active
    get_active_tower_or_error(payload.tower_id, db)

    ping = Ping(
        fob_uid=payload.fob_uid,
        tower_id=payload.tower_id,
        rssi=payload.rssi,
        tower_reported_at=payload.tower_reported_at,
    )
    db.add(ping)
    db.commit()
    return TowerPingResponse(stored=True)

