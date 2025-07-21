"""
Script to set up test users for E2E testing
"""
import asyncio
import sys
from pathlib import Path

# Add the parent directory to the Python path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from sqlalchemy import select
from app.core.database import async_session_maker
from app.models.user import User
from app.core.security import get_password_hash


async def create_test_users():
    """Create test users for E2E testing"""
    test_users = [
        {
            "username": "admin",
            "email": "admin@luckygas.tw",
            "full_name": "系統管理員",
            "password": "admin123",
            "role": "super_admin",
            "is_active": True,
            "display_name": "系統管理員"
        },
        {
            "username": "driver1", 
            "email": "driver1@luckygas.tw",
            "full_name": "司機一號",
            "password": "driver123",
            "role": "driver",
            "is_active": True,
            "display_name": "司機一號"
        },
        {
            "username": "office1",
            "email": "office1@luckygas.tw", 
            "full_name": "辦公室人員",
            "password": "office123",
            "role": "office_staff",
            "is_active": True,
            "display_name": "辦公室人員"
        },
        {
            "username": "manager1",
            "email": "manager1@luckygas.tw",
            "full_name": "經理",
            "password": "manager123",
            "role": "manager",
            "is_active": True,
            "display_name": "經理"
        }
    ]
    
    async with async_session_maker() as session:
        for user_data in test_users:
            # Check if user already exists
            result = await session.execute(
                select(User).where(User.username == user_data["username"])
            )
            existing_user = result.scalar_one_or_none()
            
            if existing_user:
                print(f"User {user_data['username']} already exists, skipping...")
                continue
                
            # Create new user
            password = user_data.pop("password")
            display_name = user_data.pop("display_name", user_data["full_name"])
            
            user = User(
                **user_data,
                hashed_password=get_password_hash(password)
            )
            session.add(user)
            print(f"Created user: {user_data['username']} ({display_name})")
        
        await session.commit()
        print("Test users setup completed!")


if __name__ == "__main__":
    asyncio.run(create_test_users())