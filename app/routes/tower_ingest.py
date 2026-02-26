import logging

from fastapi import APIRouter, Depends, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ..db import get_db
from ..deps import verify_tower_key
from ..models import Ping, Fob, Incident
# from ..sms import send_sos_sms


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
    # 1. STANDARDIZE THE ID
    # This prevents 'CD:CE...' from the hardware failing to match 'cd:ce...' in the DB
    clean_uid = payload.fob_uid.lower().strip()

    # Auto-register fob if it doesn't exist yet
    fob = db.get(Fob, clean_uid)
    if not fob:
        fob = Fob(fob_uid=clean_uid)
        db.add(fob)
        # Flush here to ensure the Fob exists for the Ping's Foreign Key
        db.flush()

    # 2. CREATE THE PING
    ping = Ping(
        fob_uid=clean_uid,
        lat=payload.lat,
        lng=payload.lng,
        status=payload.status,
    )
    db.add(ping)
    
    # 3. PUSH TO DB IMMEDIATELY
    # This ensures the SOS check below can actually "see" the record in the table
    db.flush() 
    
    if payload.status == 2:
        # We query the DB for the PREVIOUS ping to see if status changed
        # Since we just added the current ping, we look for the second most recent
        from sqlalchemy import desc
        previous_ping = db.query(Ping).filter(
            Ping.fob_uid == clean_uid,
            Ping.id != ping.id  # Exclude the one we just created
        ).order_by(desc(Ping.received_at)).first()
        
        should_send_sms = previous_ping is None or previous_ping.status != 2
        
        owner_id = fob.owner_user_id or "unregistered"
        logger.warning("🚨 SOS ALERT: User %s", owner_id)
        
        if should_send_sms:
            # SOS logic (SMS/Incidents) goes here...
            if fob.owner_user_id:
                from ..models import User
                user = db.get(User, fob.owner_user_id)
                user_info = f"{user.username}" if user else f"ID: {owner_id}"
                
                # Create Incident
                incident = Incident(
                    reporter_id=fob.owner_user_id,
                    lat=payload.lat,
                    lng=payload.lng,
                    description=f"🚨 FOB SOS ALERT from {clean_uid}",
                )
                db.add(incident)
                
                # send_sos_sms(user_info=user_info, lat=payload.lat, lng=payload.lng)
            else:
                # Unregistered fob - still send SMS but with fob ID
                # send_sos_sms(user_info=f"Unregistered FOB {clean_uid}", lat=payload.lat, lng=payload.lng)
                pass

    # 4. FINAL COMMIT
    db.commit()
    return TowerPingResponse(stored=True)