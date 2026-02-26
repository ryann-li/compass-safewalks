import logging
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import APIRouter, Depends, status, Query
from pydantic import BaseModel
from sqlalchemy import desc
from sqlalchemy.orm import Session

from ..db import get_db
from ..deps import get_current_user
from ..models import Incident, User
# from ..sms import send_sos_sms


logger = logging.getLogger("compass.incidents")

router = APIRouter(prefix="/incidents", tags=["incidents"])


class IncidentCreateRequest(BaseModel):
    lat: float
    lng: float
    description: str


class IncidentOut(BaseModel):
    id: str
    reporter_id: str
    lat: float
    lng: float
    description: str
    created_at: datetime


class IncidentWithReporterOut(BaseModel):
    id: str
    reporter: dict  # {"id": str, "username": str, "display_name": str | None}
    lat: float
    lng: float
    description: str
    created_at: datetime


class IncidentsResponse(BaseModel):
    window_hours: Optional[int] = None
    incidents: list[IncidentWithReporterOut]


class SOSRequest(BaseModel):
    lat: float
    lng: float
    message: Optional[str] = None  # Optional message for context


class SOSResponse(BaseModel):
    id: str
    lat: float
    lng: float
    message: Optional[str]
    created_at: datetime


@router.post("", response_model=IncidentOut, status_code=status.HTTP_201_CREATED)
def create_incident(
    payload: IncidentCreateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Report a community safety incident at a given location."""
    incident = Incident(
        reporter_id=current_user.id,
        lat=payload.lat,
        lng=payload.lng,
        description=payload.description,
    )
    db.add(incident)
    db.commit()
    db.refresh(incident)

    return IncidentOut(
        id=incident.id,
        reporter_id=incident.reporter_id,
        lat=incident.lat,
        lng=incident.lng,
        description=incident.description,
        created_at=incident.created_at,
    )


@router.get("", response_model=IncidentsResponse)
def get_incidents(
    window_hours: Optional[int] = Query(None, description="Filter incidents to those created within the last N hours. If not provided, returns all incidents."),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get community safety incidents with optional time filtering."""
    query = db.query(Incident).join(Incident.reporter)
    
    # Apply time filter if specified
    if window_hours is not None and window_hours > 0:
        cutoff = datetime.now(timezone.utc) - timedelta(hours=window_hours)
        query = query.filter(Incident.created_at >= cutoff)
    
    # Order by most recent first
    incidents = query.order_by(desc(Incident.created_at)).all()
    
    incidents_out = []
    for incident in incidents:
        incidents_out.append(
            IncidentWithReporterOut(
                id=incident.id,
                reporter={
                    "id": incident.reporter_id,
                    "username": incident.reporter.username,
                    "display_name": incident.reporter.display_name,
                },
                lat=incident.lat,
                lng=incident.lng,
                description=incident.description,
                created_at=incident.created_at,
            )
        )
    
    # Normalize window_hours in response: null for infinite window  
    window_value = window_hours if (window_hours is not None and window_hours > 0) else None
    return IncidentsResponse(window_hours=window_value, incidents=incidents_out)


@router.post("/sos", response_model=SOSResponse, status_code=status.HTTP_201_CREATED)
def create_user_sos(
    payload: SOSRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Create an SOS alert from a user (without requiring a fob)."""
    # Create an incident with a special SOS prefix in description
    sos_description = f"🚨 USER SOS ALERT"
    if payload.message:
        sos_description += f": {payload.message}"
    
    incident = Incident(
        reporter_id=current_user.id,
        lat=payload.lat,
        lng=payload.lng,
        description=sos_description,
    )
    db.add(incident)
    db.commit()
    db.refresh(incident)
    
    # Log prominently for operations team (similar to tower SOS)    
    logger.warning(
        "🚨 USER SOS ALERT: User %s (%s) at %s, %s - Message: %s",
        current_user.id,
        current_user.username,
        payload.lat,
        payload.lng,
        payload.message or "No message provided",
    )
    
    # Check if user has recent SOS incidents (within last 10 minutes) to avoid SMS spam
    from sqlalchemy import desc
    ten_minutes_ago = datetime.now(timezone.utc) - timedelta(minutes=10)
    recent_sos = db.query(Incident).filter(
        Incident.reporter_id == current_user.id,
        Incident.description.like("🚨%SOS%"),
        Incident.created_at >= ten_minutes_ago
    ).first()
    
    should_send_sms = recent_sos is None
    
    # Send SMS alert via Twilio only if no recent SOS
    if should_send_sms:
        user_info = f"{current_user.username} (ID: {current_user.id})"
        # sms_success = send_sos_sms(
        #     user_info=user_info,
        #     lat=payload.lat,
        #     lng=payload.lng,
        #     message=payload.message,
        #     alert_type="USER SOS"
        # )
        sms_success = True  # Mock success for now
        
        if not sms_success:
            logger.error("Failed to send SOS SMS alert")
    else:
        logger.info(f"Skipping SMS - User {current_user.username} already has recent SOS alert")
    
    return SOSResponse(
        id=incident.id,
        lat=incident.lat,
        lng=incident.lng,
        message=payload.message,
        created_at=incident.created_at,
    )
