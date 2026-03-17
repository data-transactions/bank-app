import datetime
from sqlalchemy import Column, Integer, String, Boolean, DateTime, func
from sqlalchemy.orm import relationship
from ..database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    first_name = Column(String(50), nullable=False)
    last_name = Column(String(50), nullable=False)
    email = Column(String(150), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    role = Column(String(20), default="user", nullable=False) # user, admin, super_admin
    is_suspended = Column(Boolean, default=False, nullable=False)
    is_deleted = Column(Boolean, default=False, nullable=False)
    deleted_at = Column(DateTime, nullable=True)
    is_verified = Column(Boolean, default=False, nullable=False)
    verification_token = Column(String(255), nullable=True, index=True)
    token_expiry = Column(DateTime, nullable=True)
    transaction_pin = Column(String(255), nullable=True)  # Hashed 4-6 digit PIN
    profile_image_url = Column(String(255), nullable=True)
    phone_number = Column(String(20), unique=True, nullable=True)
    home_address = Column(String(255), nullable=True)
    password_changed_at = Column(DateTime, nullable=True)
    pin_changed_at = Column(DateTime, nullable=True)
    login_count = Column(Integer, default=0, nullable=False)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)

    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}"

    @property
    def is_pin_set(self):
        return self.transaction_pin is not None

    # Deletion is now soft (is_deleted=True), so we don't need cascades.
    # We keep relationships for easy access to history.
    accounts = relationship("Account", back_populates="user")
    notifications = relationship("Notification", back_populates="user")
    permissions = relationship("AdminPermissions", back_populates="admin", uselist=False)
    
    actions_performed = relationship("AdminLog", foreign_keys="[AdminLog.admin_id]", back_populates="admin")
    actions_received = relationship("AdminLog", foreign_keys="[AdminLog.target_user_id]", back_populates="target_user")

