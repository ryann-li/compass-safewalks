from fastapi import APIRouter, Depends, status, File, Form, UploadFile
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


class ProfileOut(BaseModel):
    id: str
    username: str
    display_name: str | None = None
    profile_picture_url: str | None = None


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


@router.get("/me", response_model=ProfileOut)
def get_profile(
    current_user: User = Depends(get_current_user),
):
    """Get the current user's profile."""
    return ProfileOut(
        id=current_user.id,
        username=current_user.username,
        display_name=current_user.display_name,
        profile_picture_url=current_user.profile_picture_url,
    )


@router.patch("/me", response_model=ProfileOut)
async def update_profile(
    display_name: str | None = Form(None),
    profile_picture: UploadFile | None = File(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Update the current user's display_name and/or profile_picture via multipart/form-data."""
    import time
    from urllib.parse import quote
    import httpx
    
    # Handle profile picture upload if provided
    if profile_picture is not None:
        settings = get_settings()
        token = settings.BLOB_READ_WRITE_TOKEN
        if not token:
            error_response(
                status.HTTP_503_SERVICE_UNAVAILABLE,
                "STORAGE_UNAVAILABLE",
                "Blob storage is not configured",
            )

        # Validate file type
        allowed_types = {"image/jpeg", "image/png", "image/webp"}
        if not profile_picture.content_type or profile_picture.content_type not in allowed_types:
            error_response(
                status.HTTP_400_BAD_REQUEST,
                "INVALID_FILE_TYPE",
                "File must be an image (JPEG, PNG, or WebP)",
            )
        
        # Validate file size (max 5MB)
        MAX_FILE_SIZE = 5 * 1024 * 1024  # 5MB
        file_content = await profile_picture.read()
        if len(file_content) > MAX_FILE_SIZE:
            error_response(
                status.HTTP_400_BAD_REQUEST,
                "FILE_TOO_LARGE",
                "File size must be less than 5MB",
            )
        
        try:
            # Generate unique filename with timestamp
            timestamp = int(time.time())
            file_ext = profile_picture.filename.split(".")[-1] if "." in profile_picture.filename else "jpg"
            safe_filename = f"{current_user.id}_{timestamp}.{file_ext}"
            blob_filename = f"avatars/{safe_filename}"
            
            # Server-side upload directly to Vercel Blob using httpx
            blob_url = f"https://blob.vercel-storage.com/{quote(blob_filename)}"
            
            async with httpx.AsyncClient() as client:
                upload_response = await client.put(
                    blob_url,
                    content=file_content,
                    headers={
                        "Authorization": f"Bearer {token}",
                        "Content-Type": profile_picture.content_type,
                        "x-content-type": profile_picture.content_type,
                    },
                    timeout=30.0
                )
            
            if upload_response.status_code in [200, 201]:
                # Generate the public URL and update user profile
                public_blob_url = f"https://public.blob.vercel-storage.com/{blob_filename}"
                current_user.profile_picture_url = public_blob_url
            else:
                error_response(
                    status.HTTP_502_BAD_GATEWAY,
                    "UPLOAD_FAILED",
                    f"Failed to upload to blob storage: {upload_response.status_code} {upload_response.text}",
                )
                
        except Exception as e:
            error_response(
                status.HTTP_500_INTERNAL_SERVER_ERROR,
                "UPLOAD_ERROR",
                f"Upload failed: {str(e)}",
            )

    # Update display name if provided
    if display_name is not None:
        current_user.display_name = display_name

    # Save changes to database
    db.add(current_user)
    db.commit()
    db.refresh(current_user)

    return ProfileOut(
        id=current_user.id,
        username=current_user.username,
        display_name=current_user.display_name,
        profile_picture_url=current_user.profile_picture_url,
    )

