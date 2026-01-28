from fastapi import APIRouter, Depends, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..auth import hash_password, verify_password, create_access_token
from ..db import get_db
from ..deps import error_response
from ..models import User


router = APIRouter(prefix="/auth", tags=["auth"])


class SignupRequest(BaseModel):
    username: str
    password: str


class UserOut(BaseModel):
    id: str
    username: str


class AuthResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut


@router.post("/signup", response_model=AuthResponse, status_code=status.HTTP_201_CREATED)
def signup(payload: SignupRequest, db: Session = Depends(get_db)):
    existing = db.scalar(select(User).where(User.username == payload.username))
    if existing:
        error_response(status.HTTP_409_CONFLICT, "USERNAME_TAKEN", "Username already exists")

    user = User(username=payload.username, password_hash=hash_password(payload.password))
    db.add(user)
    db.commit()
    db.refresh(user)

    token = create_access_token(user_id=user.id, username=user.username)
    return AuthResponse(access_token=token, user=UserOut(id=user.id, username=user.username))


@router.post("/login", response_model=AuthResponse)
def login(payload: SignupRequest, db: Session = Depends(get_db)):
    user = db.scalar(select(User).where(User.username == payload.username))
    if not user or not verify_password(payload.password, user.password_hash):
        error_response(status.HTTP_401_UNAUTHORIZED, "INVALID_CREDENTIALS", "Invalid username or password")

    token = create_access_token(user_id=user.id, username=user.username)
    return AuthResponse(access_token=token, user=UserOut(id=user.id, username=user.username))

