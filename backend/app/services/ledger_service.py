"""
Ledger Service — all balance mutations go through here.
Operations are atomic: ledger entry + account balance update inside a single DB transaction.
"""
from decimal import Decimal
from sqlalchemy.orm import Session
from ..models.account import Account
from ..models.ledger import LedgerEntry, LedgerType


class InsufficientFundsError(Exception):
    pass


class UserHasNoAccountError(Exception):
    pass


def _get_account(db: Session, user_id: int) -> Account:
    account = db.query(Account).filter(Account.user_id == user_id).with_for_update().first()
    if not account:
        raise UserHasNoAccountError(f"No account found for user_id={user_id}")
    return account


def credit_user(
    db: Session,
    user_id: int,
    amount: Decimal,
    admin_id: int,
    description: str = None,
    commit: bool = True
) -> LedgerEntry:
    """
    Atomically credit a user's account and append a CREDIT ledger entry.
    Raises UserHasNoAccountError if the user has no account.
    """
    if amount <= 0:
        raise ValueError("Credit amount must be positive")

    account = _get_account(db, user_id)
    prev = account.balance
    new = prev + amount

    account.balance = new

    entry = LedgerEntry(
        user_id=user_id,
        type=LedgerType.CREDIT,
        amount=amount,
        previous_balance=prev,
        new_balance=new,
        description=description,
        created_by=admin_id,
    )
    db.add(entry)
    if commit:
        db.commit()
        db.refresh(entry)
    else:
        db.flush()
    return entry


def debit_user(
    db: Session,
    user_id: int,
    amount: Decimal,
    admin_id: int,
    description: str = None,
    commit: bool = True
) -> LedgerEntry:
    """
    Atomically debit a user's account and append a DEBIT ledger entry.
    Raises InsufficientFundsError if balance would go negative.
    Raises UserHasNoAccountError if the user has no account.
    """
    if amount <= 0:
        raise ValueError("Debit amount must be positive")

    account = _get_account(db, user_id)
    prev = account.balance
    new = prev - amount

    if new < 0:
        raise InsufficientFundsError(
            f"Insufficient balance. Current: {prev}, Requested debit: {amount}"
        )

    account.balance = new

    entry = LedgerEntry(
        user_id=user_id,
        type=LedgerType.DEBIT,
        amount=amount,
        previous_balance=prev,
        new_balance=new,
        description=description,
        created_by=admin_id,
    )
    db.add(entry)
    if commit:
        db.commit()
        db.refresh(entry)
    else:
        db.flush()
    return entry
