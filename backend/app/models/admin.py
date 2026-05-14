from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Text, func
from sqlalchemy.orm import relationship
from ..database import Base


class AdminPermissions(Base):
    __tablename__ = "admin_permissions"

    id = Column(Integer, primary_key=True, index=True)
    admin_id = Column(Integer, ForeignKey("users.id"), unique=True, nullable=False)
    can_delete = Column(Boolean, default=False, nullable=False)
    can_manage_admins = Column(Boolean, default=False, nullable=False)
    max_deposit_limit = Column(Integer, default=0, nullable=False)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)

    admin = relationship("User", foreign_keys=[admin_id], back_populates="permissions")


class AdminLog(Base):
    __tablename__ = "admin_logs"

    id = Column(Integer, primary_key=True, index=True)
    admin_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    action = Column(String(100), nullable=False) # deposit, delete, suspend, unsuspend, promote, demote, permission_change, limit_change
    target_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    details = Column(Text, nullable=True)
    timestamp = Column(DateTime, server_default=func.now(), nullable=False)

    admin = relationship("User", foreign_keys=[admin_id], back_populates="actions_performed")
    target_user = relationship("User", foreign_keys=[target_user_id], back_populates="actions_received")
