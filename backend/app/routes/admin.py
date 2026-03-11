from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import func
from ..database import get_db
from ..models.user import User
from ..models.account import Account
from ..models.transaction import Transaction
from ..core.dependencies import get_current_admin

router = APIRouter(prefix="/api/admin", tags=["admin"])


def _user_row(user: User, db: Session) -> dict:
    account = db.query(Account).filter(Account.user_id == user.id).first()
    return {
        "id": user.id,
        "full_name": user.full_name,
        "email": user.email,
        "is_admin": user.is_admin,
        "created_at": user.created_at.isoformat(),
        "account_number": account.account_number if account else None,
        "balance": float(account.balance) if account else 0.0,
    }


def _tx_row(tx: Transaction, db: Session) -> dict:
    sender = db.query(Account).filter(Account.id == tx.sender_account_id).first() if tx.sender_account_id else None
    receiver = db.query(Account).filter(Account.id == tx.receiver_account_id).first() if tx.receiver_account_id else None
    return {
        "id": tx.id,
        "transaction_type": tx.transaction_type.value if tx.transaction_type else None,
        "amount": float(tx.amount),
        "description": tx.description,
        "status": tx.status.value if tx.status else None,
        "reference_code": tx.reference_code,
        "created_at": tx.created_at.isoformat(),
        "sender_account_number": sender.account_number if sender else None,
        "receiver_account_number": receiver.account_number if receiver else None,
    }


@router.get("/users")
def list_users(
    admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    users = db.query(User).order_by(User.created_at.desc()).all()
    return [_user_row(u, db) for u in users]


@router.delete("/users/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_user(
    user_id: int,
    admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if user.id == admin.id:
        raise HTTPException(status_code=400, detail="Cannot delete your own admin account")
    db.delete(user)
    db.commit()


@router.get("/transactions")
def list_transactions(
    admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    txs = db.query(Transaction).order_by(Transaction.created_at.desc()).all()
    return [_tx_row(tx, db) for tx in txs]


@router.get("/stats")
def get_stats(
    admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    total_users = db.query(func.count(User.id)).scalar() or 0
    total_volume = db.query(func.sum(Transaction.amount)).scalar() or 0
    total_transactions = db.query(func.count(Transaction.id)).scalar() or 0
    return {
        "total_users": total_users,
        "total_volume": float(total_volume),
        "total_transactions": total_transactions,
    }
