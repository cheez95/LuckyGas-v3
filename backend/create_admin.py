#!/usr/bin/env python
"""Create initial admin user for Lucky Gas system."""

import sys
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from passlib.context import CryptContext

# Import models directly
from app.models import User, UserRole

# Database URL
DATABASE_URL = "postgresql://luckygas:staging-password-2025@35.194.143.37/luckygas"

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def get_password_hash(password: str) -> str:
    """Hash a password."""
    return pwd_context.hash(password)

def main():
    """Create admin user."""
    # Create engine and session
    engine = create_engine(DATABASE_URL)
    SessionLocal = sessionmaker(bind=engine)
    db = SessionLocal()
    
    try:
        # Check if admin already exists
        existing = db.query(User).filter(User.email == "admin@luckygas.com").first()
        if existing:
            print(f"ℹ️ Admin user already exists: {existing.email}")
            return
        
        # Create admin user
        admin_user = User(
            email="admin@luckygas.com",
            username="admin",
            hashed_password=get_password_hash("admin123"),
            full_name="System Administrator",
            role=UserRole.SUPER_ADMIN,
            is_active=True
        )
        
        db.add(admin_user)
        db.commit()
        
        print("✅ Admin user created successfully")
        print(f"   Email: {admin_user.email}")
        print(f"   Username: {admin_user.username}")
        print(f"   Password: admin123")
        print(f"   Role: {admin_user.role}")
        
    except Exception as e:
        print(f"❌ Error creating admin user: {e}")
        db.rollback()
        sys.exit(1)
    finally:
        db.close()

if __name__ == "__main__":
    main()
