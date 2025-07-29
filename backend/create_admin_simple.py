#!/usr/bin/env python
"""Create admin user directly in database"""
import asyncio
import sys
from pathlib import Path

# Add parent directory to path
sys.path.append(str(Path(__file__).parent))

from sqlalchemy import select
from app.core.database import async_session_maker
from app.models.user import User, UserRole
from app.core.security import get_password_hash

async def create_admin():
    async with async_session_maker() as session:
        # Check if admin exists
        result = await session.execute(
            select(User).where(User.email == "admin@luckygas.tw")
        )
        existing = result.scalar_one_or_none()
        
        if existing:
            print("Admin user already exists")
            return
            
        # Create admin
        admin = User(
            email="admin@luckygas.tw",
            username="admin",
            full_name="系統管理員",
            hashed_password=get_password_hash("admin123"),
            role=UserRole.SUPER_ADMIN,
            is_active=True
        )
        
        session.add(admin)
        await session.commit()
        print("✅ Created admin user: admin@luckygas.tw / admin123")

if __name__ == "__main__":
    asyncio.run(create_admin())