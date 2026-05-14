import secrets
from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks, Request
from sqlalchemy.orm import Session
from sqlalchemy import func
from ..database import get_db
from ..models.user import User
from ..models.account import Account
from ..models.security_attempt import SecurityAttempt
from ..schemas.auth import RegisterRequest, LoginRequest, TokenResponse, SetPinRequest, UserResponse, ChangePasswordRequest, ChangePinRequest, PinVerifySchema
from ..core.security import hash_password, verify_password, create_access_token
from ..core.dependencies import get_current_user
from ..services.account_service import create_account_for_user
from ..services.email_service import email_service

router = APIRouter(prefix="/api/auth", tags=["auth"])

def check_rate_limit(db: Session, user_id: int, attempt_type: str):
    fifteen_mins_ago = datetime.now(timezone.utc) - timedelta(minutes=15)
    attempts = db.query(SecurityAttempt).filter(
        SecurityAttempt.user_id == user_id,
        SecurityAttempt.type == attempt_type,
        SecurityAttempt.is_successful == False,
        SecurityAttempt.timestamp >= fifteen_mins_ago
    ).count()
    
    if attempts >= 5:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many failed attempts. Please try again in 15 minutes."
        )


@router.post("/register", status_code=status.HTTP_201_CREATED)
def register(payload: RegisterRequest, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    # 1. Advanced Email Validation (Format + MX)
    if not email_service.validate_mx_record(payload.email):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="The email domain is invalid or does not exist. Please check your email address."
        )

    existing = db.query(User).filter(User.email == payload.email).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An account with this email already exists.",
        )
    
    token = secrets.token_urlsafe(32)
    expiry = datetime.utcnow() + timedelta(hours=24)
    
    user = User(
        first_name=payload.first_name,
        last_name=payload.last_name,
        email=payload.email,
        password_hash=hash_password(payload.password),
        role="user",
        is_suspended=False,
        is_verified=False,
        verification_token=token,
        token_expiry=expiry,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    create_account_for_user(db, user.id)
    
    # 2. Send verification email in background to avoid 504 timeouts
    background_tasks.add_task(email_service.send_verification_email, user.email, token)
    
    return {"message": "Account created! Please check your email to verify your account before logging in."}


@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == payload.email, User.is_deleted == False).first()
    if not user or not verify_password(payload.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password.",
        )
    
    if not user.is_verified:
        # Resend verification email if token expired or missing
        if not user.verification_token or (user.token_expiry and user.token_expiry < datetime.utcnow()):
            user.verification_token = secrets.token_urlsafe(32)
            user.token_expiry = datetime.utcnow() + timedelta(hours=24)
            db.commit()
        
        email_service.send_verification_email(user.email, user.verification_token)
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Email not verified. A new verification link has been sent to your inbox."
        )

    if user.is_suspended:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Your account has been suspended. Please contact support."
        )

    user.login_count += 1
    db.commit()

    token = create_access_token({"sub": str(user.id), "role": user.role})
    return TokenResponse(
        access_token=token,
        pin_required=(user.role == "user"),
        is_pin_set=user.is_pin_set,
        user={
            "full_name": user.full_name,
            "profile_image_url": user.profile_image_url
        }
    )


@router.get("/me", response_model=UserResponse)
def get_me(current_user: User = Depends(get_current_user)):
    return current_user


@router.post("/set-pin")
def set_pin(
    payload: SetPinRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    current_user.transaction_pin = hash_password(payload.pin)
    db.commit()
    return {"message": "Transaction PIN set successfully."}


@router.post("/verify-pin")
def verify_pin(
    payload: PinVerifySchema,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    check_rate_limit(db, current_user.id, "pin")
    
    if not current_user.transaction_pin or not verify_password(payload.pin, current_user.transaction_pin):
        attempt = SecurityAttempt(
            user_id=current_user.id,
            type="pin",
            is_successful=False,
            ip_address=request.client.host
        )
        db.add(attempt)
        db.commit()
        
        fifteen_mins_ago = datetime.now(timezone.utc) - timedelta(minutes=15)
        attempts = db.query(SecurityAttempt).filter(
            SecurityAttempt.user_id == current_user.id,
            SecurityAttempt.type == "pin",
            SecurityAttempt.is_successful == False,
            SecurityAttempt.timestamp >= fifteen_mins_ago
        ).count()
        attempts_remaining = max(0, 5 - attempts)
        
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Incorrect PIN. You have {attempts_remaining} attempts remaining before a 15-minute lockout." if attempts_remaining > 0 else "Too many failed attempts. Please try again in 15 minutes."
        )
        
    return {"verified": True}


@router.get("/verify")
def verify_email(token: str, email: str, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == email, User.verification_token == token).first()
    if not user:
        raise HTTPException(status_code=400, detail="Invalid verification link or email")
    
    if user.token_expiry and user.token_expiry < datetime.utcnow():
        raise HTTPException(status_code=400, detail="Verification link has expired. Please try logging in to receive a new one.")
    
    user.is_verified = True
    user.verification_token = None
    user.token_expiry = None
    db.commit()
    return {"message": "Email verified successfully! You can now log in."}


@router.post("/change-password")
def change_password(
    payload: ChangePasswordRequest,
    background_tasks: BackgroundTasks,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # 1. Rate Limiting
    check_rate_limit(db, current_user.id, "password")

    # 2. Verify current password
    if not verify_password(payload.current_password, current_user.password_hash):
        # Log failed attempt
        attempt = SecurityAttempt(
            user_id=current_user.id,
            type="password",
            is_successful=False,
            ip_address=request.client.host
        )
        db.add(attempt)
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect current password."
        )

    # 3. New password constraints (Schema already handles complexity)
    if payload.new_password != payload.confirm_new_password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="New passwords do not match."
        )
    
    if verify_password(payload.new_password, current_user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="New password cannot be the same as the current password."
        )

    # 4. Update Security
    current_user.password_hash = hash_password(payload.new_password)
    current_user.password_changed_at = datetime.now(timezone.utc)
    
    # Log success
    attempt = SecurityAttempt(
        user_id=current_user.id,
        type="password",
        is_successful=True,
        ip_address=request.client.host
    )
    db.add(attempt)
    db.commit()

    # 5. Background Notification
    background_tasks.add_task(
        email_service.send_security_alert,
        current_user.email,
        current_user.full_name,
        "password",
        datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    )

    return {"message": "Password updated successfully. You have been logged out of all sessions."}


@router.post("/change-pin")
def change_pin(
    payload: ChangePinRequest,
    background_tasks: BackgroundTasks,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if not current_user.transaction_pin:
         raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Transaction PIN is not set. Please set it first."
        )

    # 1. Rate Limiting
    check_rate_limit(db, current_user.id, "pin")

    # 2. Verify current PIN
    if not verify_password(payload.current_pin, current_user.transaction_pin):
        # Log failed attempt
        attempt = SecurityAttempt(
            user_id=current_user.id,
            type="pin",
            is_successful=False,
            ip_address=request.client.host
        )
        db.add(attempt)
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect current PIN."
        )

    # 3. New PIN constraints
    if payload.new_pin != payload.confirm_new_pin:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="New PINs do not match."
        )
    
    if verify_password(payload.new_pin, current_user.transaction_pin):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="New PIN cannot be the same as the current PIN."
        )

    # 4. Update Security
    current_user.transaction_pin = hash_password(payload.new_pin)
    current_user.pin_changed_at = datetime.now(timezone.utc)
    
    # Log success
    attempt = SecurityAttempt(
        user_id=current_user.id,
        type="pin",
        is_successful=True,
        ip_address=request.client.host
    )
    db.add(attempt)
    db.commit()

    # 5. Background Notification
    background_tasks.add_task(
        email_service.send_security_alert,
        current_user.email,
        current_user.full_name,
        "transaction PIN",
        datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    )

    return {"message": "Transaction PIN updated successfully."}


