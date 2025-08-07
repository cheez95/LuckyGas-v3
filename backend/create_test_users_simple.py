#!/usr/bin/env python3
"""Create test users using direct SQL to bypass ORM issues"""

import asyncio
import os
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text
from app.core.security import get_password_hash

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql+asyncpg://luckygas:staging-password-2025@35.194.143.37/luckygas")

# Test users for Playwright tests
TEST_USERS = [
    {
        "email": "office1@luckygas.com",
        "username": "office1",
        "full_name": "辦公室員工一",
        "password": "office123",
        "role": "OFFICE_STAFF",
        "is_active": True,
        "is_superuser": False,
        "two_factor_enabled": False
    },
    {
        "email": "admin@luckygas.com",
        "username": "admin@luckygas.com",
        "full_name": "系統管理員",
        "password": "admin-password-2025",
        "role": "SUPER_ADMIN",
        "is_active": True,
        "is_superuser": True,
        "two_factor_enabled": False
    },
    {
        "email": "manager@luckygas.com",
        "username": "manager1",
        "full_name": "經理",
        "password": "manager123",
        "role": "MANAGER",
        "is_active": True,
        "is_superuser": False,
        "two_factor_enabled": False
    },
    {
        "email": "driver1@luckygas.com",
        "username": "driver1",
        "full_name": "司機一號",
        "password": "driver123",
        "role": "DRIVER",
        "is_active": True,
        "is_superuser": False,
        "two_factor_enabled": False
    }
]

async def create_users():
    """Create test users using direct SQL"""
    engine = create_async_engine(DATABASE_URL)
    
    async with engine.begin() as conn:
        # First, ensure two_factor_enabled column exists and fix existing users
        try:
            await conn.execute(text("""
                ALTER TABLE users ADD COLUMN IF NOT EXISTS two_factor_enabled BOOLEAN DEFAULT FALSE
            """))
            
            await conn.execute(text("""
                UPDATE users SET two_factor_enabled = FALSE WHERE two_factor_enabled IS NULL
            """))
        except Exception as e:
            print(f"Column might already exist: {e}")
        
        # Create test users
        for user_data in TEST_USERS:
            # Check if user exists
            result = await conn.execute(text("""
                SELECT id FROM users WHERE username = :username OR email = :email
            """), {"username": user_data["username"], "email": user_data["email"]})
            
            existing = result.fetchone()
            
            if not existing:
                # Create new user
                hashed_pwd = get_password_hash(user_data["password"])
                await conn.execute(text("""
                    INSERT INTO users (username, email, hashed_password, full_name, is_active, role, two_factor_enabled)
                    VALUES (:username, :email, :hashed_password, :full_name, :is_active, :role, :two_factor_enabled)
                """), {
                    "username": user_data["username"],
                    "email": user_data["email"],
                    "hashed_password": hashed_pwd,
                    "full_name": user_data["full_name"],
                    "is_active": user_data["is_active"],
                    "role": user_data["role"],
                    "two_factor_enabled": user_data.get("two_factor_enabled", False)
                })
                print(f"✅ Created user: {user_data['username']} ({user_data['email']}) - Role: {user_data['role']}")
            else:
                # Update existing user
                hashed_pwd = get_password_hash(user_data["password"])
                await conn.execute(text("""
                    UPDATE users 
                    SET hashed_password = :hashed_password, 
                        is_active = :is_active,
                        role = :role,
                        two_factor_enabled = :two_factor_enabled
                    WHERE username = :username OR email = :email
                """), {
                    "username": user_data["username"],
                    "email": user_data["email"],
                    "hashed_password": hashed_pwd,
                    "is_active": user_data["is_active"],
                    "role": user_data["role"],
                    "two_factor_enabled": user_data.get("two_factor_enabled", False)
                })
                print(f"✅ Updated user: {user_data['username']} ({user_data['email']}) - Role: {user_data['role']}")
    
    await engine.dispose()
    print("\n✅ User setup completed!")
    print("\n📋 Test Credentials:")
    for user in TEST_USERS:
        print(f"   - {user['username']} / {user['password']} ({user['role']})")

if __name__ == "__main__":
    asyncio.run(create_users())