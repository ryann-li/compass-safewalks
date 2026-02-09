from fastapi import APIRouter, Depends, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ..db import get_db
from ..deps import verify_tower_key
from ..models import Ping, Fob


router = APIRouter(prefix="/tower", tags=["tower"])


class TowerPingRequest(BaseModel):
    fob_uid: str
    lat: float
    lng: float


class TowerPingResponse(BaseModel):
    stored: bool


@router.post("/pings", response_model=TowerPingResponse, status_code=status.HTTP_201_CREATED)
def ingest_ping(
    payload: TowerPingRequest,
    _: bool = Depends(verify_tower_key),
    db: Session = Depends(get_db),
):
    # Auto-register fob if it doesn't exist yet
    fob = db.get(Fob, payload.fob_uid)
    if not fob:
        fob = Fob(fob_uid=payload.fob_uid)
        db.add(fob)
        db.flush()

    ping = Ping(
        fob_uid=payload.fob_uid,
        lat=payload.lat,
        lng=payload.lng,
    )
    db.add(ping)
    db.commit()
    return TowerPingResponse(stored=True)

