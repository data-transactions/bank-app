from datetime import datetime
from pydantic import BaseModel


class AccountResponse(BaseModel):
    id: int
    account_number: str
    balance: float
    created_at: datetime

    model_config = {"from_attributes": True}


class AccountStatsResponse(BaseModel):
    transaction_limit: float = 500000.0
    total_volume: float
    balance: float
