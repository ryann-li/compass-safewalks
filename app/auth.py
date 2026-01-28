from datetime import datetime, timedelta, timezone
from typing import Optional

from jose import jwt, JWTError
from passlib.context import CryptContext

from .settings import get_settings


# Use Argon2 for password hashing to avoid bcrypt backend issues and
# 72-byte length limits while still using passlib, as allowed by spec.
pwd_context = CryptContext(schemes=["argon2"], deprecated="auto")


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain_password: str, password_hash: str) -> bool:
    return pwd_context.verify(plain_password, password_hash)


def create_access_token(user_id: str, username: str, expires_seconds: Optional[int] = None) -> str:
    settings = get_settings()
    if expires_seconds is None:
        expires_seconds = settings.JWT_EXP_SECONDS

    now = datetime.now(timezone.utc)
    expire = now + timedelta(seconds=expires_seconds)
    payload = {
        "sub": user_id,
        "username": username,
        "iat": int(now.timestamp()),
        "exp": int(expire.timestamp()),
    }
    token = jwt.encode(payload, settings.JWT_SECRET, algorithm="HS256")
    return token


def decode_token(token: str) -> Optional[dict]:
    try:
        payload = jwt.decode(token, get_settings().JWT_SECRET, algorithms=["HS256"])
        return payload
    except JWTError:
        return None

