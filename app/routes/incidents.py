from datetime import datetime

from fastapi import APIRouter, Depends, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ..db import get_db
from ..deps import get_current_user
from ..models import Incident, User


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
