from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..db import get_db
from ..deps import get_current_user
from ..models import Tower


router = APIRouter(prefix="/towers", tags=["towers"])


class TowerOut(BaseModel):
    id: str
    lat: float
    lng: float


class TowersResponse(BaseModel):
    towers: list[TowerOut]


@router.get("", response_model=TowersResponse)
def list_towers(
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    rows = db.scalars(select(Tower).where(Tower.active.is_(True)).order_by(Tower.id)).all()
    towers = [TowerOut(id=t.id, lat=t.lat, lng=t.lng) for t in rows]
    return TowersResponse(towers=towers)

