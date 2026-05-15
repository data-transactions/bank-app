from decimal import Decimal
from pydantic import BaseModel, EmailStr, field_validator
from typing import Optional
from datetime import datetime


# ── Existing compatibility schemas (kept for other routes) ──
class AdminDepositRequest(BaseModel):
    amount: Decimal

class AdminPermissionUpdate(BaseModel):
    can_delete: bool
    can_manage_admins: bool
    max_deposit_limit: int

class AdminRoleUpdate(BaseModel):
    role: str  # user, admin, super_admin

class AdminLogResponse(BaseModel):
    id: int
    admin_id: int
    admin_name: str
    action: str
    target_user_id: Optional[int]
    target_user_name: Optional[str]
    details: Optional[str]
    timestamp: datetime

    class Config:
        from_attributes = True

class AdminPermissionsResponse(BaseModel):
    can_delete: bool
    can_manage_admins: bool
    max_deposit_limit: int

    class Config:
        from_attributes = True

class AdminUserActionsResponse(BaseModel):
    show_delete: bool
    show_role_toggle: Optional[str]  # "promote", "demote", or None
    show_permissions_panel: bool
    is_self: bool
    message: Optional[str]


# ── New Schemas (Rewrite) ──

class AdminCreateUserRequest(BaseModel):
    """Admin creates a user directly — no email verification flow."""
    full_name: str
    email: EmailStr
    password: str
    pin: str
    role: str = "user"

    @field_validator("password")
    @classmethod
    def password_min_length(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters")
        return v

    @field_validator("pin")
    @classmethod
    def pin_digits(cls, v: str) -> str:
        if not v.isdigit() or not (4 <= len(v) <= 6):
            raise ValueError("PIN must be 4–6 digits")
        return v

    @field_validator("role")
    @classmethod
    def role_allowed(cls, v: str) -> str:
        if v not in ("user", "admin"):
            raise ValueError("Role must be 'user' or 'admin'")
        return v


class AdminBlockRequest(BaseModel):
    """Optional reason when blocking a user."""
    reason: Optional[str] = None


class AdminLedgerRequest(BaseModel):
    """Payload for credit or debit operations."""
    amount: Decimal
    description: Optional[str] = None

    @field_validator("amount")
    @classmethod
    def must_be_positive(cls, v: Decimal) -> Decimal:
        if v <= 0:
            raise ValueError("Amount must be positive")
        return v


class LedgerEntryResponse(BaseModel):
    id: int
    user_id: int
    type: str
    amount: float
    previous_balance: float
    new_balance: float
    description: Optional[str]
    created_by: Optional[int]
    created_at: datetime

    class Config:
        from_attributes = True


# ── Edit Profile ──
class AdminEditProfileRequest(BaseModel):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    email: Optional[EmailStr] = None
    phone_number: Optional[str] = None
    home_address: Optional[str] = None
    date_of_birth: Optional[str] = None  # ISO format string
    new_password: Optional[str] = None
    new_pin: Optional[str] = None



# ── Reset Password ──
class AdminResetPasswordRequest(BaseModel):
    new_password: str

    @field_validator("new_password")
    @classmethod
    def min_length(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters")
        return v
