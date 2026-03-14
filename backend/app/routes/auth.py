import secrets
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from sqlalchemy.orm import Session
from ..database import get_db
from ..models.user import User
from ..models.account import Account
from ..schemas.auth import RegisterRequest, LoginRequest, TokenResponse
from ..core.security import hash_password, verify_password, create_access_token
from ..services.account_service import create_account_for_user
from ..services.email_service import email_service

router = APIRouter(prefix="/api/auth", tags=["auth"])


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
        is_admin=False,
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
    user = db.query(User).filter(User.email == payload.email).first()
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

    token = create_access_token({"sub": str(user.id), "is_admin": user.is_admin})
    return TokenResponse(access_token=token)


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
