#!/usr/bin/env python3
"""Initialize test users for E2E testing"""

import asyncio
import sys
from pathlib import Path

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent.parent))

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from app.core.config import settings
from app.core.database import Base
from app.core.security import get_password_hash
from app.models.user import User

# Test users matching E2E test data
TEST_USERS = [
    {
        "email": "admin@luckygas.com.tw",
        "username": "admin@luckygas.com.tw",
        "full_name": "系統管理員",
        "password": "Admin123!@#",
        "role": "super_admin",
        "is_active": True,
    },
    {
        "email": "manager@luckygas.com.tw",
        "username": "manager@luckygas.com.tw",
        "full_name": "經理",
        "password": "Manager123!",
        "role": "manager",
        "is_active": True,
    },
    {
        "email": "staff@luckygas.com.tw",
        "username": "staff@luckygas.com.tw",
        "full_name": "辦公室員工",
        "password": "Staff123!",
        "role": "office_staff",
        "is_active": True,
    },
    {
        "email": "driver@luckygas.com.tw",
        "username": "driver@luckygas.com.tw",
        "full_name": "司機",
        "password": "Driver123!",
        "role": "driver",
        "is_active": True,
    },
    {
        "email": "customer@example.com",
        "username": "customer@example.com",
        "full_name": "測試客戶",
        "password": "Customer123!",
        "role": "customer",
        "is_active": True,
    },
]


async def init_test_users():
    """Create test users in the database"""
    # Create engine
    engine = create_async_engine(settings.DATABASE_URL)

    # Create all tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # Create session
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with async_session() as session:
        for user_data in TEST_USERS:
            # Check if user already exists
            result = await session.execute(
                select(User).where(User.email == user_data["email"])
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
                )
                session.add(user)
                print(
                    f"Created user: {user_data['email']} with role {user_data['role']}"
                )
            else:
                print(f"User already exists: {user_data['email']}")

        await session.commit()

    await engine.dispose()
    print("\nTest users initialization completed!")


if __name__ == "__main__":
    asyncio.run(init_test_users())
