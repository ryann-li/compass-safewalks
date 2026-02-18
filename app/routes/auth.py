from fastapi import APIRouter, Depends, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..auth import hash_password, verify_password, create_access_token
from ..db import get_db
from ..deps import error_response, get_current_user
from ..models import User
from ..settings import get_settings


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


class UpdateProfileRequest(BaseModel):
    display_name: str | None = None
    profile_picture_url: str | None = None


class ProfileOut(BaseModel):
    id: str
    username: str
    display_name: str | None = None
    profile_picture_url: str | None = None


class UploadUrlResponse(BaseModel):
    upload_url: str
    blob_url: str


_ALLOWED_BLOB_HOSTS = {"public.blob.vercel-storage.com", "blob.vercel-storage.com"}


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


@router.get("/storage/upload-url", response_model=UploadUrlResponse)
def get_upload_url(
    filename: str,
    current_user: User = Depends(get_current_user),
):
    """Generate a signed client-upload URL for Vercel Blob storage."""
    import hashlib, time, hmac
    from urllib.parse import quote

    settings = get_settings()
    token = settings.BLOB_READ_WRITE_TOKEN
    if not token:
        error_response(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            "STORAGE_UNAVAILABLE",
            "Blob storage is not configured",
        )

    # Build a unique pathname scoped to the user
    safe_filename = quote(filename, safe="")
    pathname = f"avatars/{current_user.id}/{safe_filename}"

    # Use the vercel_blob client-upload helper when available, otherwise
    # construct a minimal signed upload URL ourselves.
    try:
        from vercel_blob import put

        result = put(
            pathname,
            data=b"",  # placeholder; client will PUT the real data
            options={
                "access": "public",
                "token": token,
                "multipart": True,
                "addRandomSuffix": True,
            },
        )
        return UploadUrlResponse(upload_url=result["url"], blob_url=result["url"])
    except ImportError:
        pass

    # Fallback: construct a simple pre-signed URL using HMAC
    ts = str(int(time.time()))
    mac = hmac.new(token.encode(), f"{pathname}:{ts}".encode(), hashlib.sha256).hexdigest()
    upload_url = f"https://blob.vercel-storage.com/{pathname}?signature={mac}&t={ts}"
    blob_url = f"https://public.blob.vercel-storage.com/{pathname}"
    return UploadUrlResponse(upload_url=upload_url, blob_url=blob_url)


@router.patch("/me", response_model=ProfileOut)
def update_profile(
    payload: UpdateProfileRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Update the current user's display_name and/or profile_picture_url."""
    from urllib.parse import urlparse

    if payload.profile_picture_url is not None:
        parsed = urlparse(payload.profile_picture_url)
        if parsed.hostname not in _ALLOWED_BLOB_HOSTS:
            error_response(
                status.HTTP_400_BAD_REQUEST,
                "INVALID_URL",
                "profile_picture_url must be hosted on Vercel Blob storage",
            )
        current_user.profile_picture_url = payload.profile_picture_url

    if payload.display_name is not None:
        current_user.display_name = payload.display_name

    db.add(current_user)
    db.commit()
    db.refresh(current_user)

    return ProfileOut(
        id=current_user.id,
        username=current_user.username,
        display_name=current_user.display_name,
        profile_picture_url=current_user.profile_picture_url,
    )

