import re
from typing import Optional
from pydantic import BaseModel, EmailStr, field_validator
from datetime import datetime


def validate_password_policy(password: str) -> str:
    if len(password) < 8:
        raise ValueError("Password must be at least 8 characters long")
    if not re.search(r"[A-Z]", password):
        raise ValueError("Password must contain at least one uppercase letter")
    if not re.search(r"[a-z]", password):
        raise ValueError("Password must contain at least one lowercase letter")
    if not re.search(r"[!@#$%^&*(),.?\":{}|<>_\-+=\[\]\\\/;']", password):
        raise ValueError("Password must contain at least one special character")
    return password


# --- Auth ---
class SignupRequest(BaseModel):
    name: str
    email: EmailStr
    password: str

    @field_validator("password")
    @classmethod
    def password_policy(cls, v):
        return validate_password_policy(v)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


# --- User ---
class UserResponse(BaseModel):
    id: int
    name: str
    email: str
    profile_image_url: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


class UpdateProfileRequest(BaseModel):
    name: Optional[str] = None


# --- Account ---
class AccountResponse(BaseModel):
    id: int
    account_number: str
    balance: float
    created_at: datetime

    class Config:
        from_attributes = True


# --- Transactions ---
class DepositRequest(BaseModel):
    amount: float

    @field_validator("amount")
    @classmethod
    def must_be_positive(cls, v):
        if v <= 0:
            raise ValueError("Amount must be positive")
        return v


class TransferRequest(BaseModel):
    receiver_account_number: str
    amount: float
    description: Optional[str] = None

    @field_validator("amount")
    @classmethod
    def must_be_positive(cls, v):
        if v <= 0:
            raise ValueError("Amount must be positive")
        return v


class TransactionResponse(BaseModel):
    id: int
    sender_account_id: Optional[int]
    receiver_account_id: Optional[int]
    amount: float
    transaction_type: str
    status: str
    transaction_reference: str
    description: Optional[str] = None
    timestamp: datetime
    sender_account_number: Optional[str] = None
    receiver_account_number: Optional[str] = None

    class Config:
        from_attributes = True
