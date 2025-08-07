#\!/usr/bin/env python3
"""Create a simple test user for login testing."""

import asyncio
from sqlalchemy import select
from app.core.database import async_session_maker
from app.models.user import User
from app.core.security import get_password_hash

async def create_test_user():
    """Create a test staff user."""
    async with async_session_maker() as session:
        # Check if user already exists
        result = await session.execute(
            select(User).where(User.email == "staff@luckygas.com")
        )
        existing_user = result.scalar_one_or_none()
        
        if existing_user:
            print("Test user already exists")
            return
        
        # Create new test user
        test_user = User(
            email="staff@luckygas.com",
            hashed_password=get_password_hash("staff123"),
            full_name="Test Staff User",
            is_active=True,
            is_superuser=False,
            role="office_staff"
        )
        
        session.add(test_user)
        await session.commit()
        print("Test user created successfully")

if __name__ == "__main__":
    asyncio.run(create_test_user())