#!/usr/bin/env python3
"""
Script to create an admin user
"""
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from api.database.connection import SessionLocal
from api.schemas.db_models import PlatformUser
from api.utils.security import get_password_hash


def create_admin_user(
    username: str = "admin",
    email: str = "admin@training-platform.com",
    password: str = "Admin123!Change",
    full_name: str = "Administrator"
):
    """Create an admin user"""
    db = SessionLocal()
    
    try:
        # Check if admin already exists
        existing_admin = db.query(PlatformUser).filter(
            PlatformUser.username == username
        ).first()
        
        if existing_admin:
            print(f"❌ Admin user '{username}' already exists!")
            print(f"   ID: {existing_admin.id}")
            print(f"   Email: {existing_admin.email}")
            print(f"   Role: {existing_admin.role}")
            print(f"   Active: {existing_admin.is_active}")
            return False
        
        # Create admin user
        hashed_password = get_password_hash(password)
        
        admin_user = PlatformUser(
            username=username,
            email=email,
            password_hash=hashed_password,
            role="admin",
            full_name=full_name,
            is_active=True
        )
        
        db.add(admin_user)
        db.commit()
        db.refresh(admin_user)
        
        print("✅ Admin user created successfully!")
        print(f"   ID: {admin_user.id}")
        print(f"   Username: {admin_user.username}")
        print(f"   Email: {admin_user.email}")
        print(f"   Role: {admin_user.role}")
        print(f"\n🔐 Login credentials:")
        print(f"   Username: {username}")
        print(f"   Password: {password}")
        print(f"\n⚠️  IMPORTANT: Change the password after first login!")
        
        return True
        
    except Exception as e:
        db.rollback()
        print(f"❌ Error creating admin user: {e}")
        return False
        
    finally:
        db.close()


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Create admin user for Training Platform")
    parser.add_argument("--username", default="admin", help="Admin username")
    parser.add_argument("--email", default="admin@training-platform.com", help="Admin email")
    parser.add_argument("--password", default="Admin123!Change", help="Admin password")
    parser.add_argument("--full-name", default="Administrator", help="Admin full name")
    
    args = parser.parse_args()
    
    print("🔧 Creating admin user for RASA Training Platform...")
    print()
    
    success = create_admin_user(
        username=args.username,
        email=args.email,
        password=args.password,
        full_name=args.full_name
    )
    
    sys.exit(0 if success else 1)
