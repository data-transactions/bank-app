"""
Admin Routes — Full Rewrite
Implements:
- POST /api/admin/users/create          — admin creates user directly
- POST /api/admin/users/{id}/block      — hard block + increment token_version
- POST /api/admin/users/{id}/unblock    — unblock + increment token_version
- POST /api/admin/users/{id}/credit     — ledger-based credit (atomic)
- POST /api/admin/users/{id}/debit      — ledger-based debit (atomic)

Legacy read-only and permission endpoints are retained.
Old suspend/deposit/non-ledger endpoints are REMOVED.
"""
import secrets
import datetime
from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from sqlalchemy.orm import Session
from sqlalchemy import func
from ..database import get_db
from ..models.user import User
from ..models.account import Account
from ..models.transaction import Transaction, TransactionType, TransactionStatus
from ..models.admin import AdminPermissions, AdminLog
from ..models.ledger import LedgerEntry
from ..core.dependencies import get_current_admin, get_current_super_admin, get_current_user
from ..core.security import hash_password
from ..schemas.admin import (
    AdminPermissionUpdate, AdminRoleUpdate, AdminLogResponse, AdminPermissionsResponse,
    AdminUserActionsResponse, AdminCreateUserRequest, AdminBlockRequest,
    AdminLedgerRequest, LedgerEntryResponse, AdminEditProfileRequest, AdminResetPasswordRequest,
)
from ..services.ledger_service import credit_user, debit_user, InsufficientFundsError, UserHasNoAccountError
from ..services.account_service import generate_account_number, generate_reference_code
from ..services.email_service import email_service

router = APIRouter(prefix="/api/admin", tags=["admin"])


# ─────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────

def _log_action(db: Session, admin_id: int, action: str, target_id: int = None, details: str = None):
    log = AdminLog(
        admin_id=admin_id,
        action=action,
        target_user_id=target_id,
        details=details,
    )
    db.add(log)
    db.commit()


def _check_permission(admin: User, db: Session, permission_name: str) -> bool:
    if admin.role == "super_admin":
        return True
    perms = db.query(AdminPermissions).filter(AdminPermissions.admin_id == admin.id).first()
    if not perms:
        return False
    return getattr(perms, permission_name, False)


def _get_target_user(db: Session, user_id: int) -> User:
    user = db.query(User).filter(User.id == user_id, User.is_deleted == False).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return user


def _user_row(user: User, db: Session) -> dict:
    account = db.query(Account).filter(Account.user_id == user.id).first()
    return {
        "id": user.id,
        "first_name": user.first_name,
        "last_name": user.last_name,
        "full_name": f"{user.first_name} {user.last_name}",
        "email": user.email,
        "role": user.role,
        "status": user.status,
        "phone_number": getattr(user, "phone_number", None),
        "home_address": getattr(user, "home_address", None),
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


# ─────────────────────────────────────────────
# READ endpoints (unchanged, required by dashboard)
# ─────────────────────────────────────────────

@router.get("/users")
def list_users(admin: User = Depends(get_current_admin), db: Session = Depends(get_db)):
    users = db.query(User).filter(User.is_deleted == False).order_by(User.created_at.desc()).all()
    return [_user_row(u, db) for u in users]


@router.get("/stats")
def get_stats(admin: User = Depends(get_current_admin), db: Session = Depends(get_db)):
    total_users = db.query(User).filter(User.is_deleted == False).count()
    # Include both regular transactions AND admin ledger operations in totals
    txn_volume = db.query(func.sum(Transaction.amount)).scalar() or 0
    ledger_volume = db.query(func.sum(LedgerEntry.amount)).scalar() or 0
    total_volume = float(txn_volume) + float(ledger_volume)
    total_transactions = db.query(Transaction).count() + db.query(LedgerEntry).count()
    return {
        "total_users": total_users,
        "total_volume": total_volume,
        "total_transactions": total_transactions,
    }


@router.get("/transactions")
def list_transactions(admin: User = Depends(get_current_admin), db: Session = Depends(get_db)):
    rows = []
    # Regular user transactions
    txns = db.query(Transaction).order_by(Transaction.created_at.desc()).all()
    rows.extend([_tx_row(t, db) for t in txns])
    # Admin ledger operations (credit/debit)
    ledger_entries = db.query(LedgerEntry).order_by(LedgerEntry.created_at.desc()).all()
    for entry in ledger_entries:
        acct = db.query(Account).filter(Account.user_id == entry.user_id).first()
        rows.append({
            "id": f"ledger-{entry.id}",
            "transaction_type": entry.type.value.lower() if entry.type else "credit",
            "amount": float(entry.amount),
            "description": entry.description or "Admin ledger adjustment",
            "status": "completed",
            "reference_code": None,
            "transaction_reference": None,
            "created_at": entry.created_at.isoformat(),
            "sender_account_number": "ADMIN",
            "receiver_account_number": acct.account_number if acct else "—",
        })
    # Sort all by date descending
    rows.sort(key=lambda r: r["created_at"], reverse=True)
    return rows


@router.get("/logs")
def list_logs(admin: User = Depends(get_current_admin), db: Session = Depends(get_db)):
    logs = db.query(AdminLog).order_by(AdminLog.timestamp.desc()).all()
    result = []
    for log in logs:
        admin_user = db.query(User).filter(User.id == log.admin_id).first()
        target_user = db.query(User).filter(User.id == log.target_user_id).first() if log.target_user_id else None
        result.append({
            "id": log.id,
            "admin_id": log.admin_id,
            "admin_name": f"{admin_user.first_name} {admin_user.last_name}" if admin_user else "Unknown",
            "action": log.action,
            "target_user_id": log.target_user_id,
            "target_user_name": f"{target_user.first_name} {target_user.last_name}" if target_user else None,
            "details": log.details,
            "timestamp": log.timestamp.isoformat(),
        })
    return result


@router.get("/permissions/me")
def get_my_permissions(admin: User = Depends(get_current_admin), db: Session = Depends(get_db)):
    if admin.role == "super_admin":
        return {
            "can_delete": True,
            "can_manage_admins": True, "max_deposit_limit": 0,
        }
    perms = db.query(AdminPermissions).filter(AdminPermissions.admin_id == admin.id).first()
    if not perms:
        return {
            "can_delete": False,
            "can_manage_admins": False, "max_deposit_limit": 0,
        }
    return {
        "can_delete": perms.can_delete,
        "can_manage_admins": perms.can_manage_admins,
        "max_deposit_limit": perms.max_deposit_limit,
    }


@router.get("/users/{user_id}/actions")
def get_user_actions(
    user_id: int,
    admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    target = _get_target_user(db, user_id)
    is_self = admin.id == user_id
    is_super = admin.role == "super_admin"
    can_delete = _check_permission(admin, db, "can_delete")
    can_manage = _check_permission(admin, db, "can_manage_admins")

    show_role_toggle = None
    if is_super and not is_self:
        if target.role == "user":
            show_role_toggle = "promote"
        elif target.role == "admin":
            show_role_toggle = "demote"

    return {
        "show_delete": can_delete and not is_self,
        "show_role_toggle": show_role_toggle,
        "show_permissions_panel": can_manage and not is_self and target.role in ("admin",),
        "is_self": is_self,
        "message": None,
    }


# ─────────────────────────────────────────────
# NEW: User Creation (Admin only, no email flow)
# ─────────────────────────────────────────────

@router.post("/users/create", status_code=status.HTTP_201_CREATED)
def admin_create_user(
    payload: AdminCreateUserRequest,
    admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    """
    Admin directly creates a verified user with hashed password and PIN.
    No email verification required.
    """
    existing = db.query(User).filter(User.email == payload.email).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A user with this email already exists.",
        )

    # Split full_name into first/last
    parts = payload.full_name.strip().split(" ", 1)
    first_name = parts[0]
    last_name = parts[1] if len(parts) > 1 else "."

    new_user = User(
        first_name=first_name,
        last_name=last_name,
        email=payload.email,
        password_hash=hash_password(payload.password),
        transaction_pin=hash_password(payload.pin),
        role=payload.role,
        status="ACTIVE",
        token_version=0,
        is_verified=True,  # admin-created users are auto-verified
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    # Create bank account
    account = Account(
        user_id=new_user.id,
        account_number=generate_account_number(),
        balance=0.00,
    )
    db.add(account)
    db.commit()

    _log_action(db, admin.id, "create_user", new_user.id, f"Created user {new_user.email} with role {new_user.role}")

    return {
        "message": "User created successfully.",
        "user_id": new_user.id,
        "email": new_user.email,
        "account_number": account.account_number,
    }


# ─────────────────────────────────────────────
# NEW: Hard Block / Unblock (token_version++, immediate session invalidation)
# ─────────────────────────────────────────────

@router.post("/users/{user_id}/block")
def block_user(
    user_id: int,
    payload: AdminBlockRequest,
    admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    target = _get_target_user(db, user_id)
    if admin.id == user_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="You cannot block your own account.")
    if target.role == "super_admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Super Admin accounts cannot be blocked.")

    target.status = "BLOCKED"
    target.token_version = (target.token_version or 0) + 1  # invalidate all existing JWTs
    target.blocked_at = datetime.datetime.utcnow()
    target.blocked_by = admin.id
    target.block_reason = payload.reason
    db.commit()

    _log_action(db, admin.id, "block_user", user_id, f"Reason: {payload.reason or 'No reason given'}")
    return {"message": f"User {target.email} has been blocked. All sessions invalidated."}


@router.post("/users/{user_id}/unblock")
def unblock_user(
    user_id: int,
    admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    target = _get_target_user(db, user_id)
    target.status = "ACTIVE"
    target.token_version = (target.token_version or 0) + 1  # force fresh login after unblock too
    target.blocked_at = None
    target.blocked_by = None
    target.block_reason = None
    db.commit()

    _log_action(db, admin.id, "unblock_user", user_id, "User unblocked")
    return {"message": f"User {target.email} has been unblocked. They must log in again."}


# ─────────────────────────────────────────────
# NEW: Ledger-based Credit / Debit
# ─────────────────────────────────────────────

@router.post("/users/{user_id}/credit")
def admin_credit(
    user_id: int,
    payload: AdminLedgerRequest,
    admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    """Atomically credit a user's account and record an immutable ledger entry."""

    _get_target_user(db, user_id)  # existence check

    try:
        entry = credit_user(db, user_id, payload.amount, admin.id, payload.description, commit=False)
        target_account = db.query(Account).filter(Account.user_id == user_id).first()
        
        # Create Transaction record for visibility in history
        tx = Transaction(
            sender_account_id=None,
            receiver_account_id=target_account.id,
            transaction_type=TransactionType.deposit,
            amount=payload.amount,
            description=payload.description or "Administrative Credit",
            scope="System adjustment",
            status=TransactionStatus.completed,
            reference_code=generate_reference_code(),
        )
        db.add(tx)
        db.commit()
        db.refresh(entry)
    except UserHasNoAccountError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Target user has no bank account.")

    _log_action(
        db, admin.id, "credit_user", user_id,
        f"Credited ${payload.amount} | New balance: ${entry.new_balance} | {payload.description or ''}"
    )
    return {
        "message": f"Successfully credited ${payload.amount}.",
        "ledger_entry_id": entry.id,
        "new_balance": float(entry.new_balance),
    }


@router.post("/users/{user_id}/debit")
def admin_debit(
    user_id: int,
    payload: AdminLedgerRequest,
    admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    """Atomically debit a user's account and record an immutable ledger entry."""

    _get_target_user(db, user_id)

    try:
        entry = debit_user(db, user_id, payload.amount, admin.id, payload.description, commit=False)
        target_account = db.query(Account).filter(Account.user_id == user_id).first()

        # Create Transaction record for visibility in history
        tx = Transaction(
            sender_account_id=target_account.id,
            receiver_account_id=None,
            transaction_type=TransactionType.withdrawal,
            amount=payload.amount,
            description=payload.description or "Administrative Debit",
            scope="System adjustment",
            status=TransactionStatus.completed,
            reference_code=generate_reference_code(),
        )
        db.add(tx)
        db.commit()
        db.refresh(entry)
    except InsufficientFundsError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except UserHasNoAccountError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Target user has no bank account.")

    _log_action(
        db, admin.id, "debit_user", user_id,
        f"Debited ${payload.amount} | New balance: ${entry.new_balance} | {payload.description or ''}"
    )
    return {
        "message": f"Successfully debited ${payload.amount}.",
        "ledger_entry_id": entry.id,
        "new_balance": float(entry.new_balance),
    }


# ─────────────────────────────────────────────
# Ledger History (read)
# ─────────────────────────────────────────────

@router.get("/users/{user_id}/ledger")
def get_user_ledger(
    user_id: int,
    admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    _get_target_user(db, user_id)
    entries = (
        db.query(LedgerEntry)
        .filter(LedgerEntry.user_id == user_id)
        .order_by(LedgerEntry.created_at.desc())
        .all()
    )
    return [
        {
            "id": e.id,
            "type": e.type.value,
            "amount": float(e.amount),
            "previous_balance": float(e.previous_balance),
            "new_balance": float(e.new_balance),
            "description": e.description,
            "created_by": e.created_by,
            "created_at": e.created_at.isoformat(),
        }
        for e in entries
    ]


# ─────────────────────────────────────────────
# Profile Edit (retained)
# ─────────────────────────────────────────────

@router.patch("/users/{user_id}/profile")
def edit_user_profile(
    user_id: int,
    payload: AdminEditProfileRequest,
    admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    target = _get_target_user(db, user_id)
    update_data = payload.model_dump(exclude_unset=True)
    protected = {"password_hash", "transaction_pin", "token_version", "status"}
    for field, value in update_data.items():
        if field not in protected and hasattr(target, field):
            setattr(target, field, value)
    db.commit()
    _log_action(db, admin.id, "edit_profile", user_id, str(update_data))
    return {"message": "Profile updated successfully."}


# ─────────────────────────────────────────────
# Reset Password (retained)
# ─────────────────────────────────────────────

@router.post("/users/{user_id}/reset-password")
def reset_user_password(
    user_id: int,
    payload: AdminResetPasswordRequest,
    admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    target = _get_target_user(db, user_id)
    target.password_hash = hash_password(payload.new_password)
    target.password_changed_at = datetime.datetime.utcnow()
    # Bump token_version so all existing sessions are invalidated
    target.token_version = (target.token_version or 0) + 1
    db.commit()
    _log_action(db, admin.id, "reset_password", user_id, "Admin forced password reset")
    return {"message": "Password reset successfully. User must log in again."}


# ─────────────────────────────────────────────
# Role toggle (super_admin only)
# ─────────────────────────────────────────────

@router.post("/users/{user_id}/role")
def update_role(
    user_id: int,
    payload: AdminRoleUpdate,
    admin: User = Depends(get_current_super_admin),
    db: Session = Depends(get_db),
):
    target = _get_target_user(db, user_id)
    if admin.id == user_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot change your own role.")
    if target.role == "super_admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Cannot change Super Admin role.")
    old_role = target.role
    target.role = payload.role
    db.commit()
    _log_action(db, admin.id, "role_change", user_id, f"{old_role} → {payload.role}")
    return {"message": f"Role updated to {payload.role}."}


# ─────────────────────────────────────────────
# Permissions (super_admin only)
# ─────────────────────────────────────────────

@router.patch("/users/{user_id}/permissions")
def update_permissions(
    user_id: int,
    payload: AdminPermissionUpdate,
    admin: User = Depends(get_current_super_admin),
    db: Session = Depends(get_db),
):
    target = _get_target_user(db, user_id)
    if target.role not in ("admin",):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Permissions only apply to admins.")

    perms = db.query(AdminPermissions).filter(AdminPermissions.admin_id == user_id).first()
    if not perms:
        perms = AdminPermissions(admin_id=user_id)
        db.add(perms)

    perms.can_delete = payload.can_delete
    perms.can_manage_admins = payload.can_manage_admins
    perms.max_deposit_limit = payload.max_deposit_limit
    db.commit()
    _log_action(db, admin.id, "permission_change", user_id, str(payload.model_dump()))
    return {"message": "Permissions updated."}


# ─────────────────────────────────────────────
# Delete user (soft-delete)
# ─────────────────────────────────────────────

@router.delete("/users/{user_id}")
def delete_user(
    user_id: int,
    admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    if not _check_permission(admin, db, "can_delete"):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You do not have delete permission.")

    target = _get_target_user(db, user_id)
    if admin.id == user_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot delete your own account.")
    if target.role == "super_admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Super Admin accounts cannot be deleted.")

    target.is_deleted = True
    target.deleted_at = datetime.datetime.utcnow()
    target.status = "BLOCKED"
    target.token_version = (target.token_version or 0) + 1
    db.commit()
    _log_action(db, admin.id, "delete_user", user_id, f"Soft-deleted {target.email}")
    return {"message": "User deleted successfully."}
