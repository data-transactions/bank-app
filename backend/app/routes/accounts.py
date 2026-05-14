from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from ..database import get_db
from ..models.user import User
from ..models.account import Account
from ..schemas.account import AccountResponse, AccountStatsResponse
from ..core.dependencies import get_current_user
from ..services.account_service import create_account_for_user
from ..models.transaction import Transaction
from sqlalchemy import func

from ..models.ledger import LedgerEntry
from sqlalchemy import func

router = APIRouter(prefix="/api/accounts", tags=["accounts"])


@router.get("/me", response_model=AccountResponse)
def get_my_account(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    account = db.query(Account).filter(Account.user_id == current_user.id).first()
    if not account:
        account = create_account_for_user(db, current_user.id)
    return account


@router.get("/stats", response_model=AccountStatsResponse)
def get_account_stats(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    account = db.query(Account).filter(Account.user_id == current_user.id).first()
    if not account:
        account = create_account_for_user(db, current_user.id)
    
    total_volume = db.query(func.sum(LedgerEntry.amount)).filter(
        LedgerEntry.user_id == current_user.id
    ).scalar() or 0.0
    
    return {
        "transaction_limit": 500000.0,
        "total_volume": float(total_volume),
        "balance": float(account.balance)
    }
