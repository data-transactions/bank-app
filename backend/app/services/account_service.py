import random
import string
import uuid
from sqlalchemy.orm import Session
from ..models.account import Account


def generate_account_number() -> str:
    """Generate a unique 10-digit account number."""
    return "NX" + "".join(random.choices(string.digits, k=10))


def generate_transaction_reference() -> str:
    """Generate a unique transaction reference."""
    return "TXN-" + uuid.uuid4().hex[:12].upper()


def create_account_for_user(db: Session, user_id: int) -> Account:
    """Create a new bank account for a user."""
    account_number = generate_account_number()
    # Ensure uniqueness
    while db.query(Account).filter(Account.account_number == account_number).first():
        account_number = generate_account_number()

    account = Account(user_id=user_id, account_number=account_number, balance=0.00)
    db.add(account)
    db.commit()
    db.refresh(account)
    return account
