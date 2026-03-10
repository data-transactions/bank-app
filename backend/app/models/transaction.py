from sqlalchemy import Column, Integer, String, Numeric, ForeignKey, DateTime, func
from sqlalchemy.orm import relationship
from ..database import Base


class Transaction(Base):
    __tablename__ = "transactions"

    id = Column(Integer, primary_key=True, index=True)
    sender_account_id = Column(Integer, ForeignKey("accounts.id", ondelete="SET NULL"), nullable=True)
    receiver_account_id = Column(Integer, ForeignKey("accounts.id", ondelete="SET NULL"), nullable=True)
    amount = Column(Numeric(15, 2), nullable=False)
    transaction_type = Column(String(20), nullable=False)  # 'transfer' or 'deposit'
    status = Column(String(20), default="completed", nullable=False)
    transaction_reference = Column(String(50), unique=True, nullable=False, index=True)
    description = Column(String(255), nullable=True)
    timestamp = Column(DateTime, server_default=func.now(), nullable=False)

    sender = relationship("Account", foreign_keys=[sender_account_id], backref="sent_transactions")
    receiver = relationship("Account", foreign_keys=[receiver_account_id], backref="received_transactions")
