import re
import datetime
from typing import Optional
from pydantic import BaseModel, EmailStr, field_validator


import phonenumbers
from phonenumbers import NumberParseException

def _validate_password(v: str) -> str:
    if len(v) < 8:
        raise ValueError("Password must be at least 8 characters long")
    if not re.search(r"[A-Z]", v):
        raise ValueError("Password must contain at least one uppercase letter")
    if not re.search(r"[a-z]", v):
        raise ValueError("Password must contain at least one lowercase letter")
    if not re.search(r"[0-9]", v):
        raise ValueError("Password must contain at least one number")
    if not re.search(r'[!@#$%^&*(),.?":{}|<>_\-+=\[\]\\/;\'`~]', v):
        raise ValueError("Password must contain at least one special character")
    return v

def _validate_phone(v: str) -> str:
    if v is None: return v
    # Remove any non-numeric/non-plus chars (cleanup)
    v = re.sub(r'[^0-9+]', '', v)
    try:
        # Check if it starts with + or try to parse as international
        # Default to NG (+234) if no leading +? The user said "accept formats like +234... or 080..." 
        # so we should handle local prefix too.
        if v.startswith('0') and len(v) >= 10:
            # Assume Nigeria for now as a fallback if it looks like a local number
            parsed = phonenumbers.parse(v, "NG")
        else:
            parsed = phonenumbers.parse(v, None)
            
        if not phonenumbers.is_valid_number(parsed):
            raise ValueError("Invalid phone number format")
        
        # Format as E.164
        formatted = phonenumbers.format_number(parsed, phonenumbers.PhoneNumberFormat.E164)
        
        # Check digit count (user said 7-15) - E164 includes + and CC
        digit_count = sum(c.isdigit() for c in formatted)
        if not (7 <= digit_count <= 15):
             raise ValueError("Phone number must be between 7 and 15 digits")
        
        return formatted
    except NumberParseException:
        raise ValueError("Invalid phone number")

class UserUpdateRequest(BaseModel):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    email: Optional[EmailStr] = None
    phone_number: Optional[str] = None
    home_address: Optional[str] = None
    date_of_birth: Optional[str] = None

    @field_validator("phone_number")
    @classmethod
    def validate_phone(cls, v):
        return _validate_phone(v)

    @field_validator("home_address")
    @classmethod
    def validate_address(cls, v):
        if v is None: return v
        if not (10 <= len(v) <= 255):
            raise ValueError("Address must be between 10 and 255 characters")
        return v

    @field_validator("first_name", "last_name")
    @classmethod
    def validate_names(cls, v: str, info):
        if v is None: return v
        if len(v) < 3:
            raise ValueError(f"{info.field_name.replace('_', ' ').capitalize()} must be at least 3 characters long")
        if any(char.isdigit() for char in v):
            raise ValueError(f"{info.field_name.replace('_', ' ').capitalize()} cannot contain numbers")
        return v

class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str
    confirm_new_password: str

    @field_validator("new_password")
    @classmethod
    def password_policy(cls, v):
        return _validate_password(v)

class ChangePinRequest(BaseModel):
    current_pin: str
    new_pin: str
    confirm_new_pin: str

    @field_validator("new_pin")
    @classmethod
    def validate_pin(cls, v):
        if not v.isdigit() or len(v) != 4:
            raise ValueError("PIN must be exactly 4 digits")
        return v

class RegisterRequest(BaseModel):
    first_name: str
    last_name: str
    email: EmailStr
    password: str

    @field_validator("first_name", "last_name")
    @classmethod
    def validate_names(cls, v: str, info):
        if len(v) < 3:
            raise ValueError(f"{info.field_name.replace('_', ' ').capitalize()} must be at least 3 characters long")
        if any(char.isdigit() for char in v):
            raise ValueError(f"{info.field_name.replace('_', ' ').capitalize()} cannot contain numbers")
        return v

    @field_validator("password")
    @classmethod
    def password_policy(cls, v):
        return _validate_password(v)

class LoginRequest(BaseModel):
    email: EmailStr
    password: str

class SetPinRequest(BaseModel):
    pin: str

    @field_validator("pin")
    @classmethod
    def validate_pin(cls, v):
        if not v.isdigit() or not (4 <= len(v) <= 6):
            raise ValueError("PIN must be 4-6 digits long")
        return v

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserResponse(BaseModel):
    id: int
    first_name: str
    last_name: str
    full_name: str
    email: EmailStr
    phone_number: Optional[str] = None
    home_address: Optional[str] = None
    role: str
    is_suspended: bool
    is_verified: bool
    is_pin_set: bool
    profile_image_url: Optional[str] = None
    login_count: int
    created_at: datetime.datetime

    class Config:
        from_attributes = True
