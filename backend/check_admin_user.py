#!/usr/bin/env python
"""Check if admin user exists and create if needed."""
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session
from app.core.security import get_password_hash, verify_password

# Database URL
DATABASE_URL = "postgresql://luckygas:staging-password-2025@35.194.143.37/luckygas"

def check_and_create_admin():
    """Check if admin user exists and create if needed."""
    engine = create_engine(DATABASE_URL)
    
    with Session(engine) as session:
        # First check what enum values are valid
        enum_check = session.execute(
            text("SELECT enumlabel FROM pg_enum WHERE enumtypid = (SELECT oid FROM pg_type WHERE typname = 'userrole')")
        ).fetchall()
        print("Valid role enum values:")
        for row in enum_check:
            print(f"  - {row[0]}")
        
        # Check if admin exists
        result = session.execute(
            text("SELECT id, email, username, role, hashed_password FROM users WHERE email = 'admin@luckygas.com' LIMIT 5")
        ).fetchall()
        
        if result:
            print("Found existing admin users:")
            for row in result:
                print(f"  ID: {row[0]}, Email: {row[1]}, Username: {row[2]}, Role: {row[3]}")
                # Check if password matches
                if row[1] == 'admin@luckygas.com':
                    if verify_password('admin123!@#', row[4]):
                        print("  ✅ Password 'admin123!@#' is valid for this user")
                    else:
                        print("  ❌ Password 'admin123!@#' is NOT valid for this user")
                        print("  Updating password...")
                        new_hash = get_password_hash('admin123!@#')
                        session.execute(
                            text("UPDATE users SET hashed_password = :hash WHERE id = :id"),
                            {"hash": new_hash, "id": row[0]}
                        )
                        session.commit()
                        print("  ✅ Password updated to 'admin123!@#'")
        else:
            print("No admin user found. Creating one...")
            hashed_password = get_password_hash('admin123!@#')
            # Use the first valid enum value (should be like 'admin' or similar)
            admin_role = enum_check[0][0] if enum_check else 'admin'
            print(f"Using role: {admin_role}")
            session.execute(
                text("""
                    INSERT INTO users (email, username, full_name, hashed_password, is_active, role)
                    VALUES ('admin@luckygas.com', 'admin', 'System Administrator', :hash, true, :role)
                """),
                {"hash": hashed_password, "role": admin_role}
            )
            session.commit()
            print("✅ Created admin user with email 'admin@luckygas.com' and password 'admin123!@#'")
        
        # Verify the final state
        admin = session.execute(
            text("SELECT email, username, role FROM users WHERE email = 'admin@luckygas.com'")
        ).fetchone()
        
        if admin:
            print(f"\n✅ Admin user confirmed: {admin[0]} ({admin[1]}) - Role: {admin[2]}")
        else:
            print("\n❌ Failed to create admin user")

if __name__ == "__main__":
    check_and_create_admin()