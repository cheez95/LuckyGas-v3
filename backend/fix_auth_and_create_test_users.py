#!/usr/bin/env python3
"""Fix authentication issues and create test users for Playwright testing"""

import asyncio
import sys
from pathlib import Path

# Add parent directory to path
sys.path.append(str(Path(__file__).parent))

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from app.core.config import settings
from app.core.database import Base
from app.core.security import get_password_hash
from app.models.user import User, UserRole

# Test users for Playwright tests
TEST_USERS = [
    {
        "email": "office1@luckygas.com",
        "username": "office1",
        "full_name": "辦公室員工一",
        "password": "office123",
        "role": UserRole.OFFICE_STAFF,
        "is_active": True,
        "is_superuser": False,
        "two_factor_enabled": False
    },
    {
        "email": "admin@luckygas.com",
        "username": "admin@luckygas.com",
        "full_name": "系統管理員",
        "password": "admin-password-2025",
        "role": UserRole.SUPER_ADMIN,
        "is_active": True,
        "is_superuser": True,
        "two_factor_enabled": False
    },
    {
        "email": "manager@luckygas.com",
        "username": "manager1",
        "full_name": "經理",
        "password": "manager123",
        "role": UserRole.MANAGER,
        "is_active": True,
        "is_superuser": False,
        "two_factor_enabled": False
    },
    {
        "email": "driver1@luckygas.com",
        "username": "driver1",
        "full_name": "司機一號",
        "password": "driver123",
        "role": UserRole.DRIVER,
        "is_active": True,
        "is_superuser": False,
        "two_factor_enabled": False
    }
]

async def fix_and_create_users():
    """Fix existing users and create test users"""
    # Create engine
    engine = create_async_engine(settings.DATABASE_URL)

    # Create all tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # Create session
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with async_session() as session:
        # First, fix all existing users to have two_factor_enabled = False
        print("🔧 Fixing existing users...")
        await session.execute(
            update(User).values(two_factor_enabled=False).where(User.two_factor_enabled.is_(None))
        )
        await session.commit()
        
        # Create test users
        for user_data in TEST_USERS:
            # Check if user already exists
            result = await session.execute(
                select(User).where(
                    (User.email == user_data["email"]) | 
                    (User.username == user_data["username"])
                )
            )
            existing_user = result.scalar_one_or_none()

            if not existing_user:
                # Create new user
                user = User(
                    email=user_data["email"],
                    username=user_data["username"],
                    full_name=user_data["full_name"],
                    hashed_password=get_password_hash(user_data["password"]),
                    role=user_data["role"],
                    is_active=user_data["is_active"],
                    is_superuser=user_data.get("is_superuser", False),
                    two_factor_enabled=user_data.get("two_factor_enabled", False)
                )
                session.add(user)
                print(f"✅ Created user: {user_data['username']} ({user_data['email']}) - Role: {user_data['role']}")
            else:
                # Update existing user
                existing_user.hashed_password = get_password_hash(user_data["password"])
                existing_user.is_active = True
                existing_user.role = user_data["role"]
                existing_user.two_factor_enabled = user_data.get("two_factor_enabled", False)
                print(f"✅ Updated user: {user_data['username']} ({user_data['email']}) - Role: {user_data['role']}")

        await session.commit()

    await engine.dispose()
    print("\n✅ User setup completed!")
    print("\n📋 Test Credentials:")
    for user in TEST_USERS:
        print(f"   - {user['username']} / {user['password']} ({user['role']})")

if __name__ == "__main__":
    asyncio.run(fix_and_create_users())