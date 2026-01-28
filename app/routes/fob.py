from fastapi import APIRouter, Depends, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ..db import get_db
from ..deps import error_response, get_current_user
from ..models import Fob, User


router = APIRouter(prefix="/fob", tags=["fob"])


class FobClaimRequest(BaseModel):
    fob_uid: str


class FobResponse(BaseModel):
    fob_uid: str


@router.post("/claim", response_model=FobResponse, status_code=status.HTTP_201_CREATED)
def claim_fob(
    payload: FobClaimRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    existing_for_user = db.scalar(select(Fob).where(Fob.owner_user_id == current_user.id))
    if existing_for_user:
        error_response(status.HTTP_409_CONFLICT, "FOB_ALREADY_CLAIMED", "User already has a fob")

    fob = Fob(fob_uid=payload.fob_uid, owner_user_id=current_user.id)
    db.add(fob)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        error_response(status.HTTP_409_CONFLICT, "FOB_CONFLICT", "Fob already claimed")
    db.refresh(fob)
    return FobResponse(fob_uid=fob.fob_uid)


@router.get("/me", response_model=FobResponse)
def get_my_fob(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    fob = db.scalar(select(Fob).where(Fob.owner_user_id == current_user.id))
    if not fob:
        error_response(status.HTTP_404_NOT_FOUND, "FOB_NOT_FOUND", "No fob for user")
    return FobResponse(fob_uid=fob.fob_uid)

