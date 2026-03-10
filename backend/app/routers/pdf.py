from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from sqlalchemy.orm import Session
from ..database import get_db
from ..models.user import User
from ..models.account import Account
from ..models.transaction import Transaction
from ..auth.dependencies import get_current_user
from ..services.pdf_service import generate_receipt_pdf, generate_statement_pdf

router = APIRouter(prefix="/api/pdf", tags=["pdf"])


@router.get("/receipt/{tx_id}")
def download_receipt(
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

    # Resolve names
    sender_name = "NexaBank (Deposit)"
    if tx.sender_account_id:
        sender_acc = db.query(Account).filter(Account.id == tx.sender_account_id).first()
        if sender_acc:
            sender_user = db.query(User).filter(User.id == sender_acc.user_id).first()
            sender_name = f"{sender_user.name} ({sender_acc.account_number})" if sender_user else sender_acc.account_number

    receiver_name = "N/A"
    if tx.receiver_account_id:
        receiver_acc = db.query(Account).filter(Account.id == tx.receiver_account_id).first()
        if receiver_acc:
            receiver_user = db.query(User).filter(User.id == receiver_acc.user_id).first()
            receiver_name = f"{receiver_user.name} ({receiver_acc.account_number})" if receiver_user else receiver_acc.account_number

    # Balance after: get current balance for the relevant account
    balance_after = float(account.balance)

    tx_dict = {
        "id": tx.id,
        "amount": float(tx.amount),
        "transaction_type": tx.transaction_type,
        "status": tx.status,
        "transaction_reference": tx.transaction_reference,
        "description": tx.description,
        "timestamp": tx.timestamp,
        "sender_account_id": tx.sender_account_id,
        "receiver_account_id": tx.receiver_account_id,
    }
    pdf_bytes = generate_receipt_pdf(tx_dict, sender_name, receiver_name, balance_after)

    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="receipt-{tx.transaction_reference}.pdf"'},
    )


@router.get("/statement")
def download_statement(
    date_from: str = None,
    date_to: str = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    account = db.query(Account).filter(Account.user_id == current_user.id).first()
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")

    query = db.query(Transaction).filter(
        (Transaction.sender_account_id == account.id) |
        (Transaction.receiver_account_id == account.id)
    )
    if date_from:
        from datetime import datetime
        try:
            query = query.filter(Transaction.timestamp >= datetime.fromisoformat(date_from))
        except ValueError:
            pass
    if date_to:
        from datetime import datetime
        try:
            query = query.filter(Transaction.timestamp <= datetime.fromisoformat(date_to))
        except ValueError:
            pass

    txs = query.order_by(Transaction.timestamp.asc()).all()

    tx_list = []
    for tx in txs:
        is_credit = tx.receiver_account_id == account.id
        if is_credit:
            counterpart_acc = db.query(Account).filter(Account.id == tx.sender_account_id).first() if tx.sender_account_id else None
        else:
            counterpart_acc = db.query(Account).filter(Account.id == tx.receiver_account_id).first() if tx.receiver_account_id else None

        counterpart = "NexaBank"
        if counterpart_acc:
            cp_user = db.query(User).filter(User.id == counterpart_acc.user_id).first()
            counterpart = f"{cp_user.name if cp_user else ''} ({counterpart_acc.account_number})"

        tx_list.append({
            "amount": float(tx.amount),
            "transaction_type": tx.transaction_type,
            "transaction_reference": tx.transaction_reference,
            "status": tx.status,
            "timestamp": tx.timestamp,
            "description": tx.description,
            "counterpart": counterpart,
            "is_credit": is_credit,
        })

    user_dict = {"name": current_user.name, "email": current_user.email}
    acc_dict = {"account_number": account.account_number, "balance": float(account.balance)}

    pdf_bytes = generate_statement_pdf(user_dict, acc_dict, tx_list, date_from, date_to)

    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="statement-{account.account_number}.pdf"'},
    )
