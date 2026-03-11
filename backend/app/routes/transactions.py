from decimal import Decimal
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from ..database import get_db
from ..models.user import User
from ..models.account import Account
from ..models.transaction import Transaction, TransactionType, TransactionStatus
from ..schemas.transaction import DepositRequest, WithdrawRequest, TransferRequest
from ..core.dependencies import get_current_user
from ..services.account_service import generate_reference_code

router = APIRouter(prefix="/api/transactions", tags=["transactions"])


def _fmt(tx: Transaction, db: Session) -> dict:
    sender = db.query(Account).filter(Account.id == tx.sender_account_id).first() if tx.sender_account_id else None
    receiver = db.query(Account).filter(Account.id == tx.receiver_account_id).first() if tx.receiver_account_id else None
    return {
        "id": tx.id,
        "sender_account_id": tx.sender_account_id,
        "receiver_account_id": tx.receiver_account_id,
        "transaction_type": tx.transaction_type.value if tx.transaction_type else None,
        "amount": float(tx.amount),
        "description": tx.description,
        "status": tx.status.value if tx.status else None,
        "reference_code": tx.reference_code,
        "created_at": tx.created_at.isoformat(),
        "sender_account_number": sender.account_number if sender else None,
        "receiver_account_number": receiver.account_number if receiver else None,
    }


@router.get("/")
def get_transactions(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    account = db.query(Account).filter(Account.user_id == current_user.id).first()
    if not account:
        return []
    txs = (
        db.query(Transaction)
        .filter(
            (Transaction.sender_account_id == account.id) |
            (Transaction.receiver_account_id == account.id)
        )
        .order_by(Transaction.created_at.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )
    return [_fmt(tx, db) for tx in txs]


@router.post("/deposit")
def deposit(
    payload: DepositRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    account = db.query(Account).filter(Account.user_id == current_user.id).with_for_update().first()
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")

    tx = Transaction(
        sender_account_id=None,
        receiver_account_id=account.id,
        transaction_type=TransactionType.deposit,
        amount=Decimal(str(payload.amount)),
        description="Deposit",
        status=TransactionStatus.completed,
        reference_code=generate_reference_code(),
    )
    account.balance += Decimal(str(payload.amount))
    db.add(tx)
    db.commit()
    db.refresh(tx)
    db.refresh(account)
    return {**_fmt(tx, db), "balance_after": float(account.balance)}


@router.post("/withdraw")
def withdraw(
    payload: WithdrawRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    account = db.query(Account).filter(Account.user_id == current_user.id).with_for_update().first()
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")
    if account.balance < Decimal(str(payload.amount)):
        raise HTTPException(status_code=400, detail="Insufficient funds")

    tx = Transaction(
        sender_account_id=account.id,
        receiver_account_id=None,
        transaction_type=TransactionType.withdrawal,
        amount=Decimal(str(payload.amount)),
        description="Withdrawal",
        status=TransactionStatus.completed,
        reference_code=generate_reference_code(),
    )
    account.balance -= Decimal(str(payload.amount))
    db.add(tx)
    db.commit()
    db.refresh(tx)
    db.refresh(account)
    return {**_fmt(tx, db), "balance_after": float(account.balance)}


@router.post("/transfer")
def transfer(
    payload: TransferRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    sender_acc = db.query(Account).filter(Account.user_id == current_user.id).with_for_update().first()
    if not sender_acc:
        raise HTTPException(status_code=404, detail="Sender account not found")

    receiver_acc = db.query(Account).filter(
        Account.account_number == payload.receiver_account_number
    ).with_for_update().first()
    if not receiver_acc:
        raise HTTPException(status_code=404, detail="Receiver account not found")
    if receiver_acc.id == sender_acc.id:
        raise HTTPException(status_code=400, detail="Cannot transfer to your own account")

    amount = Decimal(str(payload.amount))
    if sender_acc.balance < amount:
        raise HTTPException(status_code=400, detail="Insufficient funds")
    if amount > Decimal("500000"):
        raise HTTPException(status_code=400, detail="Transfer exceeds the $500,000 limit")

    tx = Transaction(
        sender_account_id=sender_acc.id,
        receiver_account_id=receiver_acc.id,
        transaction_type=TransactionType.transfer,
        amount=amount,
        description=payload.description,
        status=TransactionStatus.completed,
        reference_code=generate_reference_code(),
    )
    sender_acc.balance -= amount
    receiver_acc.balance += amount
    db.add(tx)
    db.commit()
    db.refresh(tx)
    db.refresh(sender_acc)
    return {**_fmt(tx, db), "balance_after": float(sender_acc.balance)}
