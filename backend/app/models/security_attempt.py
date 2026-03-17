from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, func
from sqlalchemy.orm import relationship
from ..database import Base

class SecurityAttempt(Base):
    __tablename__ = "security_attempts"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    type = Column(String(20), nullable=False) # 'password', 'pin'
    is_successful = Column(Boolean, nullable=False)
    timestamp = Column(DateTime, server_default=func.now(), nullable=False)
    ip_address = Column(String(45), nullable=True)

    user = relationship("User", backref="security_attempts")
