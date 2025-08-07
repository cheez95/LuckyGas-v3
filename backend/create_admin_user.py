#!/usr/bin/env python3
"""Create admin user for testing"""

import asyncio
import sys
from pathlib import Path

# Add parent directory to path
sys.path.append(str(Path(__file__).parent))

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from app.core.config import settings
from app.core.database import Base
from app.core.security import get_password_hash
from app.models.user import User, UserRole

async def create_admin():
    """Create admin user in the database"""
    # Create engine
    engine = create_async_engine(settings.DATABASE_URL)

    # Create all tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # Create session
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with async_session() as session:
        # Check if user already exists
        result = await session.execute(
            select(User).where(User.email == "admin@luckygas.com")
        )
        existing_user = result.scalar_one_or_none()

        if not existing_user:
            # Create new user
            user = User(
                email="admin@luckygas.com",
                username="admin@luckygas.com",
                full_name="System Admin",
                hashed_password=get_password_hash("admin-password-2025"),
                role=UserRole.SUPER_ADMIN,
                is_active=True,
                is_superuser=True
            )
            session.add(user)
            await session.commit()
            print("✅ Created admin user: admin@luckygas.com with password: admin-password-2025")
        else:
            # Update password
            existing_user.hashed_password = get_password_hash("admin-password-2025")
            existing_user.is_active = True
            existing_user.role = UserRole.SUPER_ADMIN
            await session.commit()
            print("✅ Updated admin user password")

    await engine.dispose()
    print("\nAdmin user setup completed!")

if __name__ == "__main__":
    asyncio.run(create_admin())