from datetime import datetime
from typing import Optional
from pydantic import BaseModel, field_validator


class DepositRequest(BaseModel):
    amount: float

    @field_validator("amount")
    @classmethod
    def must_be_positive(cls, v):
        if v <= 0:
            raise ValueError("Amount must be positive")
        return v


class WithdrawRequest(BaseModel):
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
    transaction_type: str
    amount: float
    description: Optional[str] = None
    status: str
    reference_code: str
    created_at: datetime
    sender_account_number: Optional[str] = None
    receiver_account_number: Optional[str] = None

    model_config = {"from_attributes": True}
