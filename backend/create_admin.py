#!/usr/bin/env python3
"""Create admin user for testing"""

import asyncio
import sys
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from app.models.user import User
from app.core.security import get_password_hash
from app.core.config import settings
import os

# Set test database URL
DATABASE_URL = os.getenv('DATABASE_URL', 'postgresql+asyncpg://luckygas_test:test_password_secure_123@localhost:5433/luckygas_test')

async def create_admin_user():
    """Create an admin user for testing"""
    
    # Create async engine
    engine = create_async_engine(DATABASE_URL, echo=True)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    async with async_session() as session:
        try:
            # Check if admin already exists
            from sqlalchemy import select
            stmt = select(User).where(User.email == "admin@luckygas.com")
            result = await session.execute(stmt)
            existing = result.scalar_one_or_none()
            if existing:
                print("Admin user already exists!")
                return
            
            # Create admin user
            admin_user = User(
                email="admin@luckygas.com",
                username="admin",
                full_name="系統管理員",
                hashed_password=get_password_hash("admin123"),
                is_active=True,
                is_superuser=True,
                role="admin"
            )
            
            session.add(admin_user)
            await session.commit()
            
            print("✅ Admin user created successfully!")
            print("📧 Email: admin@luckygas.com")
            print("🔑 Password: admin123")
            print("👤 Role: Admin (Superuser)")
            
        except Exception as e:
            print(f"❌ Error creating admin user: {e}")
            await session.rollback()
        finally:
            await engine.dispose()

if __name__ == "__main__":
    asyncio.run(create_admin_user())