import logging

from fastapi import APIRouter, Depends, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ..db import get_db
from ..deps import verify_tower_key
from ..models import Ping, Fob, Incident


logger = logging.getLogger("compass.tower")

router = APIRouter(prefix="/tower", tags=["tower"])


class TowerPingRequest(BaseModel):
    fob_uid: str
    lat: float
    lng: float
    status: int = 0  # 0=Safe, 1=Not Safe, 2=SOS


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
        status=payload.status,
    )
    db.add(ping)
    
    # If SOS, log a prominent warning and create incident if fob is registered
    if payload.status == 2:
        owner_id = fob.owner_user_id or "unregistered"
        logger.warning(
            "🚨 SOS ALERT: User %s at %s, %s",
            owner_id,
            payload.lat,
            payload.lng,
        )
        
        # Create an incident if the fob is registered to a user
        if fob.owner_user_id:
            incident = Incident(
                reporter_id=fob.owner_user_id,
                lat=payload.lat,
                lng=payload.lng,
                description=f"🚨 FOB SOS ALERT from fob {payload.fob_uid}",
            )
            db.add(incident)
    
    db.commit()

    return TowerPingResponse(stored=True)

