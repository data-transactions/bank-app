"""
Seed script — creates Super Admin, Regular Admin, and Regular User for local testing.
Updated to use new status/token_version fields.
"""
import sys
import os

sys.path.append(os.getcwd())

from app.database import SessionLocal
from app.models.user import User
from app.models.account import Account
from app.models.admin import AdminPermissions, AdminLog
from app.services.account_service import generate_account_number
from app.core.security import hash_password


def seed():
    db = SessionLocal()
    try:
        print("Clearing existing test data...")
        db.query(AdminLog).delete()
        db.query(AdminPermissions).delete()
        db.query(Account).delete()
        db.query(User).delete()
        db.commit()

        # ── Super Admin ──
        print("Seeding Super Admin...")
        super_admin = User(
            first_name="Super",
            last_name="Admin",
            email="superadmin@nexabank.com",
            password_hash=hash_password("SuperPassword123!"),
            role="super_admin",
            status="ACTIVE",
            token_version=0,
            is_verified=True,
            transaction_pin=hash_password("0000"),
        )
        db.add(super_admin)
        db.commit()
        db.refresh(super_admin)
        db.add(Account(
            user_id=super_admin.id,
            account_number=generate_account_number(),
            balance=1_000_000.0,
        ))

        # ── Regular Admin ──
        print("Seeding Regular Admin...")
        reg_admin = User(
            first_name="Regular",
            last_name="Admin",
            email="admin@nexabank.com",
            password_hash=hash_password("Password123!"),
            role="admin",
            status="ACTIVE",
            token_version=0,
            is_verified=True,
            transaction_pin=hash_password("1234"),
        )
        db.add(reg_admin)
        db.commit()
        db.refresh(reg_admin)

        db.add(AdminPermissions(
            admin_id=reg_admin.id,
            can_delete=False,
            can_manage_admins=False,
            max_deposit_limit=5000,
        ))
        db.add(Account(
            user_id=reg_admin.id,
            account_number=generate_account_number(),
            balance=50_000.0,
        ))

        # ── Regular User ──
        print("Seeding Regular User (John Doe)...")
        reg_user = User(
            first_name="John",
            last_name="Doe",
            email="john@example.com",
            password_hash=hash_password("Password123!"),
            role="user",
            status="ACTIVE",
            token_version=0,
            is_verified=True,
            transaction_pin=hash_password("5555"),
        )
        db.add(reg_user)
        db.commit()
        db.refresh(reg_user)
        db.add(Account(
            user_id=reg_user.id,
            account_number=generate_account_number(),
            balance=1_000.0,
        ))

        db.commit()
        print("─" * 40)
        print(f"Super Admin  : {super_admin.email} / SuperPassword123!")
        print(f"Regular Admin: {reg_admin.email} / Password123!")
        print(f"Regular User : {reg_user.email}   / Password123!")
        print("─" * 40)

    except Exception as e:
        print(f"Error seeding: {e}")
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    seed()
