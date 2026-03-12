import re
from pydantic import BaseModel, EmailStr, field_validator


def _validate_password(v: str) -> str:
    if len(v) < 8:
        raise ValueError("Password must be at least 8 characters long")
    if not re.search(r"[A-Z]", v):
        raise ValueError("Password must contain at least one uppercase letter")
    if not re.search(r"[a-z]", v):
        raise ValueError("Password must contain at least one lowercase letter")
    if not re.search(r'[!@#$%^&*(),.?":{}|<>_\-+=\[\]\\/;\'`~]', v):
        raise ValueError("Password must contain at least one special character")
    return v


class RegisterRequest(BaseModel):
    first_name: str
    last_name: str
    email: EmailStr
    password: str

    @field_validator("password")
    @classmethod
    def password_policy(cls, v):
        return _validate_password(v)

class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserResponse(BaseModel):
    id: int
    first_name: str
    last_name: str
    full_name: str
    email: EmailStr
    is_admin: bool
    created_at: datetime.datetime

    class Config:
        from_attributes = True
