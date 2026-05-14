import enum
from sqlalchemy import Column, Integer, String, Numeric, ForeignKey, DateTime, Enum, func
from sqlalchemy.orm import relationship
from ..database import Base


class LedgerType(str, enum.Enum):
    CREDIT = "CREDIT"
    DEBIT = "DEBIT"


class LedgerEntry(Base):
    """Immutable ledger – rows are never updated or deleted."""
    __tablename__ = "ledger_entries"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="RESTRICT"), nullable=False, index=True)
    type = Column(Enum(LedgerType), nullable=False)
    amount = Column(Numeric(15, 2), nullable=False)
    previous_balance = Column(Numeric(15, 2), nullable=False)
    new_balance = Column(Numeric(15, 2), nullable=False)
    description = Column(String(255), nullable=True)
    created_by = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)

    user = relationship("User", foreign_keys=[user_id], backref="ledger_entries")
    admin = relationship("User", foreign_keys=[created_by])
