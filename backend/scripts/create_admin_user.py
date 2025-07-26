#!/usr/bin/env python
"""Create a simple admin user for testing"""
import asyncio
import sys
from pathlib import Path

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

from sqlalchemy import select
from app.core.database import async_session_maker
from app.models.user import User, UserRole
from app.core.security import get_password_hash

async def create_admin():
    async with async_session_maker() as session:
        # Check if test admin exists
        result = await session.execute(
            select(User).where(User.email == "testadmin@luckygas.tw")
        )
        existing = result.scalar_one_or_none()
        
        if existing:
            print("Test admin already exists")
            return
            
        # Create test admin
        admin = User(
            email="testadmin@luckygas.tw",
            username="testadmin",
            full_name="Test Administrator",
            hashed_password=get_password_hash("test123"),
            role=UserRole.SUPER_ADMIN,
            is_active=True
        )
        
        session.add(admin)
        await session.commit()
        print("Created test admin user: testadmin@luckygas.tw / test123")

if __name__ == "__main__":
    asyncio.run(create_admin())