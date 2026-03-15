import sys
import os
from sqlalchemy.orm import Session
from passlib.hash import bcrypt

# Add app to path
sys.path.append(os.getcwd())

from app.database import SessionLocal, engine
from app.models.user import User
from app.models.account import Account
from app.models.admin import AdminPermissions, AdminLog
from app.services.account_service import generate_account_number

def seed():
    db = SessionLocal()
    try:
        # Clear existing users and accounts (test data)
        print("Clearing existing test data...")
        db.query(AdminLog).delete()
        db.query(AdminPermissions).delete()
        db.query(Account).delete()
        db.query(User).delete()
        db.commit()

        # Seed Super Admin
        print("Seeding Super Admin...")
        super_admin = User(
            first_name="Super",
            last_name="Admin",
            email="superadmin@nexabank.com",
            password_hash=bcrypt.hash("SuperPassword123!"),
            role="super_admin",
            is_verified=True,
            transaction_pin=bcrypt.hash("0000")
        )
        db.add(super_admin)
        db.commit()
        db.refresh(super_admin)

        # Create account for super admin
        account = Account(
            user_id=super_admin.id,
            account_number=generate_account_number(),
            balance=1000000.0
        )
        db.add(account)

        # Seed Regular Admin
        print("Seeding Regular Admin...")
        reg_admin = User(
            first_name="Regular",
            last_name="Admin",
            email="admin@nexabank.com",
            password_hash=bcrypt.hash("Password123!"),
            role="admin",
            is_verified=True,
            transaction_pin=bcrypt.hash("1234")
        )
        db.add(reg_admin)
        db.commit()
        db.refresh(reg_admin)
        
        # Admin Permissions for reg_admin
        perms = AdminPermissions(
            admin_id=reg_admin.id,
            can_deposit=True,
            can_delete=False,
            can_suspend=True,
            can_manage_admins=False,
            max_deposit_limit=5000
        )
        db.add(perms)
        
        db.add(Account(user_id=reg_admin.id, account_number=generate_account_number(), balance=50000.0))

        # Seed Regular User
        print("Seeding Regular User...")
        reg_user = User(
            first_name="John",
            last_name="Doe",
            email="john@example.com",
            password_hash=bcrypt.hash("Password123!"),
            role="user",
            is_verified=True,
            transaction_pin=bcrypt.hash("5555")
        )
        db.add(reg_user)
        db.commit()
        db.refresh(reg_user)
        db.add(Account(user_id=reg_user.id, account_number=generate_account_number(), balance=1000.0))

        db.commit()
        print(f"Super Admin seeded: {super_admin.email} / SuperPassword123!")
        print(f"Regular Admin seeded: {reg_admin.email} / Password123!")
        print(f"Regular User seeded: {reg_user.email} / Password123!")
        
    except Exception as e:
        print(f"Error seeding: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    seed()
