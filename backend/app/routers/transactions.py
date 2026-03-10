from decimal import Decimal
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from ..database import get_db
from ..models.user import User
from ..models.account import Account
from ..models.transaction import Transaction
from ..schemas.schemas import DepositRequest, TransferRequest, TransactionResponse
from ..auth.dependencies import get_current_user
from ..services.account_service import generate_transaction_reference

router = APIRouter(prefix="/api/transactions", tags=["transactions"])


def _fmt_tx(tx: Transaction, db: Session) -> dict:
    sender_acc = db.query(Account).filter(Account.id == tx.sender_account_id).first() if tx.sender_account_id else None
    receiver_acc = db.query(Account).filter(Account.id == tx.receiver_account_id).first() if tx.receiver_account_id else None
    return {
        "id": tx.id,
        "sender_account_id": tx.sender_account_id,
        "receiver_account_id": tx.receiver_account_id,
        "amount": float(tx.amount),
        "transaction_type": tx.transaction_type,
        "status": tx.status,
        "transaction_reference": tx.transaction_reference,
        "description": tx.description,
        "timestamp": tx.timestamp.isoformat(),
        "sender_account_number": sender_acc.account_number if sender_acc else None,
        "receiver_account_number": receiver_acc.account_number if receiver_acc else None,
    }


@router.post("/deposit")
def deposit(
    payload: DepositRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    account = db.query(Account).filter(Account.user_id == current_user.id).with_for_update().first()
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")

    reference = generate_transaction_reference()
    tx = Transaction(
        sender_account_id=None,
        receiver_account_id=account.id,
        amount=Decimal(str(payload.amount)),
        transaction_type="deposit",
        status="completed",
        transaction_reference=reference,
        description="Deposit",
    )
    account.balance += Decimal(str(payload.amount))
    db.add(tx)
    db.commit()
    db.refresh(tx)
    db.refresh(account)
    return {**_fmt_tx(tx, db), "balance_after": float(account.balance)}


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
        raise HTTPException(status_code=400, detail="Transfer exceeds the $500,000 transaction limit")

    reference = generate_transaction_reference()
    tx = Transaction(
        sender_account_id=sender_acc.id,
        receiver_account_id=receiver_acc.id,
        amount=amount,
        transaction_type="transfer",
        status="completed",
        transaction_reference=reference,
        description=payload.description,
    )
    sender_acc.balance -= amount
    receiver_acc.balance += amount
    db.add(tx)
    db.commit()
    db.refresh(tx)
    db.refresh(sender_acc)
    return {**_fmt_tx(tx, db), "balance_after": float(sender_acc.balance)}


@router.get("/")
def get_transactions(
    limit: int = 50,
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
        .order_by(Transaction.timestamp.desc())
        .limit(limit)
        .all()
    )
    return [_fmt_tx(tx, db) for tx in txs]


@router.get("/{tx_id}")
def get_transaction(
    tx_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    account = db.query(Account).filter(Account.user_id == current_user.id).first()
    tx = db.query(Transaction).filter(Transaction.id == tx_id).first()
    if not tx:
        raise HTTPException(status_code=404, detail="Transaction not found")
    if tx.sender_account_id != account.id and tx.receiver_account_id != account.id:
        raise HTTPException(status_code=403, detail="Access denied")
    return _fmt_tx(tx, db)
