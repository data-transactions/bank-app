import secrets
import datetime
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import func
from ..database import get_db
from ..models.user import User
from ..models.account import Account
from ..models.transaction import Transaction, TransactionType, TransactionStatus
from ..models.admin import AdminPermissions, AdminLog
from ..core.dependencies import get_current_admin, get_current_super_admin
from ..schemas.admin import AdminDepositRequest, AdminPermissionUpdate, AdminRoleUpdate, AdminLogResponse, AdminPermissionsResponse, AdminUserActionsResponse

router = APIRouter(prefix="/api/admin", tags=["admin"])


def _log_action(db: Session, admin_id: int, action: str, target_id: int = None, details: str = None):
    log = AdminLog(
        admin_id=admin_id,
        action=action,
        target_user_id=target_id,
        details=details
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


def _user_row(user: User, db: Session) -> dict:
    account = db.query(Account).filter(Account.user_id == user.id).first()
    return {
        "id": user.id,
        "first_name": user.first_name,
        "last_name": user.last_name,
        "full_name": f"{user.first_name} {user.last_name}",
        "email": user.email,
        "role": user.role,
        "is_suspended": user.is_suspended,
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
    db: Session = Depends(get_db)
):
    users = db.query(User).filter(User.is_deleted == False).order_by(User.created_at.desc()).all()
    return [_user_row(u, db) for u in users]


@router.delete("/users/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_user(
    user_id: int,
    admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    if not _check_permission(admin, db, "can_delete"):
        raise HTTPException(status_code=403, detail="You do not have permission to delete users")
    
    if admin.id == user_id:
        raise HTTPException(status_code=400, detail="You cannot delete yourself")
        
    user = db.query(User).filter(User.id == user_id, User.is_deleted == False).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
        
    # Regular admins cannot delete other admins or super admins
    if admin.role == "admin" and user.role != "user":
        raise HTTPException(status_code=403, detail="Admins can only delete regular users")

    if user.role == "super_admin":
        raise HTTPException(status_code=400, detail="Cannot delete a Super Admin")
        
    _log_action(db, admin.id, "delete", user.id, f"Deactivated account: {user.email}")
    
    # Soft delete
    user.is_deleted = True
    user.deleted_at = datetime.datetime.utcnow()
    db.commit()


@router.post("/users/{user_id}/deposit")
def admin_deposit(
    user_id: int,
    payload: AdminDepositRequest,
    admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    if not _check_permission(admin, db, "can_deposit"):
        raise HTTPException(status_code=403, detail="You do not have permission to perform deposits")
    
    # Check limit for regular admins
    if admin.role != "super_admin":
        perms = db.query(AdminPermissions).filter(AdminPermissions.admin_id == admin.id).first()
        if perms and payload.amount > perms.max_deposit_limit:
            raise HTTPException(status_code=403, detail=f"Deposit exceeds your limit of ${perms.max_deposit_limit}")

    user = db.query(User).filter(User.id == user_id, User.is_deleted == False).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    account = db.query(Account).filter(Account.user_id == user.id).first()
    if not account:
        raise HTTPException(status_code=404, detail="User account not found")
    
    account.balance += payload.amount
    
    tx = Transaction(
        sender_account_id=None,
        receiver_account_id=account.id,
        amount=payload.amount,
        transaction_type=TransactionType.deposit,
        status=TransactionStatus.completed,
        description=f"Admin Deposit by {admin.email}",
        reference_code=f"ADM-{secrets.token_hex(4).upper()}"
    )
    db.add(tx)
    _log_action(db, admin.id, "deposit", user.id, f"Deposited ${payload.amount} to {user.email}")
    db.commit()
    return {"message": "Deposit successful"}


@router.post("/users/{user_id}/suspend")
def suspend_user(
    user_id: int,
    admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    if not _check_permission(admin, db, "can_suspend"):
        raise HTTPException(status_code=403, detail="You do not have permission to suspend users")
    
    if admin.id == user_id:
        raise HTTPException(status_code=400, detail="You cannot suspend yourself")
    
    user = db.query(User).filter(User.id == user_id, User.is_deleted == False).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Regular admins cannot suspend other admins or super admins
    if admin.role == "admin" and user.role != "user":
        raise HTTPException(status_code=403, detail="Admins can only suspend regular users")

    if user.role == "super_admin":
        raise HTTPException(status_code=400, detail="Cannot suspend a Super Admin")
        
    user.is_suspended = True
    _log_action(db, admin.id, "suspend", user.id, f"Suspended account: {user.email}")
    db.commit()
    return {"message": "User suspended"}


@router.post("/users/{user_id}/unsuspend")
def unsuspend_user(
    user_id: int,
    admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    if not _check_permission(admin, db, "can_suspend"):
        raise HTTPException(status_code=403, detail="You do not have permission to unsuspend users")
    
    user = db.query(User).filter(User.id == user_id, User.is_deleted == False).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Regular admins cannot unsuspend other admins (consistent with suspension)
    if admin.role == "admin" and user.role != "user":
        raise HTTPException(status_code=403, detail="Admins can only manage regular users")
        
    user.is_suspended = False
    _log_action(db, admin.id, "unsuspend", user.id, f"Unsuspended account: {user.email}")
    db.commit()
    return {"message": "User unsuspended"}


@router.post("/users/{user_id}/role")
def update_user_role(
    user_id: int,
    payload: AdminRoleUpdate,
    admin: User = Depends(get_current_super_admin),
    db: Session = Depends(get_db)
):
    user = db.query(User).filter(User.id == user_id, User.is_deleted == False).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    if user.id == admin.id:
        raise HTTPException(status_code=400, detail="Cannot change your own role")
        
    old_role = user.role
    user.role = payload.role
    
    # If demoted from admin, clear permissions
    if old_role in ["admin", "super_admin"] and payload.role == "user":
        db.query(AdminPermissions).filter(AdminPermissions.admin_id == user.id).delete()
    
    _log_action(db, admin.id, f"role_change", user.id, f"Changed role from {old_role} to {payload.role}")
    db.commit()
    return {"message": f"User role updated to {payload.role}"}


@router.get("/users/{user_id}/permissions", response_model=AdminPermissionsResponse)
def get_admin_permissions(
    user_id: int,
    admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    user = db.query(User).filter(User.id == user_id, User.is_deleted == False).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
        
    perms = db.query(AdminPermissions).filter(AdminPermissions.admin_id == user_id).first()
    if not perms:
        return AdminPermissions(
            admin_id=user_id,
            can_deposit=False,
            can_delete=False,
            can_suspend=False,
            can_manage_admins=False,
            max_deposit_limit=0
        )
    return perms


@router.get("/permissions/me", response_model=AdminPermissionsResponse)
def get_my_permissions(
    admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    perms = db.query(AdminPermissions).filter(AdminPermissions.admin_id == admin.id).first()
    if not perms:
        return AdminPermissions(
            admin_id=admin.id,
            can_deposit=(admin.role == "super_admin"),
            can_delete=(admin.role == "super_admin"),
            can_suspend=(admin.role == "super_admin"),
            can_manage_admins=(admin.role == "super_admin"),
            max_deposit_limit=1000000000 if admin.role == "super_admin" else 0
        )
    return perms


@router.get("/users/{user_id}/actions", response_model=AdminUserActionsResponse)
def get_user_actions(
    user_id: int,
    admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    target_user = db.query(User).filter(User.id == user_id, User.is_deleted == False).first()
    if not target_user:
        raise HTTPException(status_code=404, detail="User not found")
        
    perms = db.query(AdminPermissions).filter(AdminPermissions.admin_id == admin.id).first()
    
    res = {
        "show_deposit": False,
        "show_suspend": False,
        "show_delete": False,
        "show_role_toggle": None,
        "show_permissions_panel": False,
        "is_self": (admin.id == target_user.id),
        "message": None
    }
    
    is_super = (admin.role == "super_admin")
    is_admin = (admin.role == "admin")
    is_target_self = (admin.id == target_user.id)
    is_target_user = (target_user.role == "user")
    is_target_admin = (target_user.role in ["admin", "super_admin"])

    # Rule 1 & 4: Viewing self
    if is_target_self:
        return res

    # Rule 2: Super admin viewing regular user
    if is_super and is_target_user:
        res["show_deposit"] = True
        res["show_suspend"] = True
        res["show_delete"] = True
        res["show_role_toggle"] = "promote"

    # Rule 3: Super admin viewing another admin
    elif is_super and is_target_admin:
        res["show_deposit"] = True
        res["show_suspend"] = True
        res["show_delete"] = True
        res["show_role_toggle"] = "demote"
        res["show_permissions_panel"] = True

    # Rule 5: Regular admin viewing regular user
    elif is_admin and is_target_user:
        if perms:
            res["show_deposit"] = perms.can_deposit
            res["show_suspend"] = perms.can_suspend
            res["show_delete"] = perms.can_delete

    # Rule 6: Regular admin viewing another admin
    elif is_admin and is_target_admin:
        if perms and perms.can_manage_admins:
            res["show_deposit"] = perms.can_deposit
            res["show_suspend"] = perms.can_suspend
            res["show_delete"] = perms.can_delete
        else:
            res["message"] = "Insufficient permissions"

    return res


@router.patch("/users/{user_id}/permissions")
def update_admin_permissions(
    user_id: int,
    payload: AdminPermissionUpdate,
    admin: User = Depends(get_current_super_admin),
    db: Session = Depends(get_db)
):
    user = db.query(User).filter(User.id == user_id, User.is_deleted == False).first()
    if not user or user.role not in ["admin", "super_admin"]:
        raise HTTPException(status_code=400, detail="Target user is not an admin")
        
    perms = db.query(AdminPermissions).filter(AdminPermissions.admin_id == user_id).first()
    if not perms:
        perms = AdminPermissions(admin_id=user_id)
        db.add(perms)
    
    perms.can_deposit = payload.can_deposit
    perms.can_delete = payload.can_delete
    perms.can_suspend = payload.can_suspend
    perms.can_manage_admins = payload.can_manage_admins
    perms.max_deposit_limit = payload.max_deposit_limit
    
    _log_action(db, admin.id, "permission_change", user.id, "Updated granular permissions")
    db.commit()
    return {"message": "Permissions updated"}


@router.get("/logs")
def get_admin_logs(
    admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    logs = db.query(AdminLog).order_by(AdminLog.timestamp.desc()).limit(100).all()
    res = []
    for l in logs:
        res.append({
            "id": l.id,
            "admin_id": l.admin_id,
            "admin_name": f"{l.admin.first_name} {l.admin.last_name}" if l.admin else "Unknown",
            "action": l.action,
            "target_user_id": l.target_user_id,
            "target_user_name": f"{l.target_user.first_name} {l.target_user.last_name}" if l.target_user else None,
            "details": l.details,
            "timestamp": l.timestamp.isoformat()
        })
    return res


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
    total_users = db.query(func.count(User.id)).filter(User.is_deleted == False).scalar() or 0
    total_volume = db.query(func.sum(Transaction.amount)).scalar() or 0
    total_transactions = db.query(func.count(Transaction.id)).scalar() or 0
    return {
        "total_users": total_users,
        "total_volume": float(total_volume),
        "total_transactions": total_transactions,
    }
