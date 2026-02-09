from fastapi import Depends, Header
from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from .auth import decode_token
from .db import get_db
from .models import User
from .settings import get_settings


def error_response(status_code: int, code: str, message: str, details: dict | None = None):
    body = {"error": {"code": code, "message": message}}
    if details is not None:
        body["error"]["details"] = details
    raise HTTPException(status_code=status_code, detail=body)


def get_current_user(
    authorization: str | None = Header(None, alias="Authorization"),
    db: Session = Depends(get_db),
) -> User:
    if not authorization or not authorization.lower().startswith("bearer "):
        error_response(status.HTTP_401_UNAUTHORIZED, "UNAUTHORIZED", "Missing bearer token")

    token = authorization.split(" ", 1)[1]
    payload = decode_token(token)
    if not payload:
        error_response(status.HTTP_401_UNAUTHORIZED, "UNAUTHORIZED", "Invalid token")

    user_id = payload.get("sub")
    username = payload.get("username")
    if not user_id or not username:
        error_response(status.HTTP_401_UNAUTHORIZED, "UNAUTHORIZED", "Invalid token payload")

    user = db.get(User, user_id)
    if not user:
        error_response(status.HTTP_401_UNAUTHORIZED, "UNAUTHORIZED", "User not found")
    return user


def verify_tower_key(
    x_tower_key: str | None = Header(None, alias="X-Tower-Key"),
    db: Session = Depends(get_db),
):
    settings = get_settings()
    if not x_tower_key or x_tower_key != settings.TOWER_SHARED_KEY:
        error_response(status.HTTP_401_UNAUTHORIZED, "TOWER_UNAUTHORIZED", "Invalid tower key")
    # This dependency just validates the shared key; individual routes still validate tower_id etc.
    return True

