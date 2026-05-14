import uuid
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, status
from sqlalchemy.orm import Session
from ..database import get_db
from ..models.user import User
from ..schemas.auth import UserResponse, UserUpdateRequest
from ..core.dependencies import get_current_user
from ..storage import upload_avatar

router = APIRouter(prefix="/api/users", tags=["users"])


@router.get("/me", response_model=UserResponse)
def get_me(current_user: User = Depends(get_current_user)):
    return current_user


@router.patch("/profile", response_model=UserResponse)
def update_profile(
    payload: UserUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # 1. Check if ANY fields are provided
    update_data = payload.model_dump(exclude_unset=True)
    if not update_data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No fields provided for update."
        )

    # 2. Handle phone_number uniqueness
    if payload.phone_number is not None:
        existing = db.query(User).filter(
            User.phone_number == payload.phone_number,
            User.id != current_user.id
        ).first()
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="This phone number is already registered to another account."
            )
        current_user.phone_number = payload.phone_number

    # 3. Handle home_address (sanitization)
    if payload.home_address is not None:
        # SQLAlchemy handles SQL injection via bind parameters
        clean_address = payload.home_address.strip()
        current_user.home_address = clean_address

    # 4. Handle other fields if present
    if payload.first_name: current_user.first_name = payload.first_name
    if payload.last_name: current_user.last_name = payload.last_name
    if payload.email: current_user.email = payload.email
    if payload.date_of_birth: current_user.date_of_birth = payload.date_of_birth

    db.commit()
    db.refresh(current_user)
    return current_user


@router.put("/me", response_model=UserResponse)
def update_me(
    payload: UserUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # Redirect to update_profile for consistency
    return update_profile(payload, current_user, db)


@router.post("/me/avatar", response_model=UserResponse)
async def upload_avatar_endpoint(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="File must be an image")

    # Generate unique, collision-safe filename using user ID
    ext = file.filename.rsplit(".", 1)[-1].lower() if "." in file.filename else "jpg"
    unique_filename = f"{current_user.id}_{uuid.uuid4().hex}.{ext}"

    # Read file bytes
    file_bytes = await file.read()

    # Upload to Supabase Storage — returns full public URL or None on failure
    public_url = upload_avatar(
        file_bytes=file_bytes,
        filename=unique_filename,
        content_type=file.content_type,
    )

    if not public_url:
        raise HTTPException(status_code=500, detail="Failed to upload avatar to storage")

    # Persist full Supabase public URL to user record
    current_user.profile_image_url = public_url
    db.add(current_user)
    db.commit()
    db.refresh(current_user)
    return current_user
