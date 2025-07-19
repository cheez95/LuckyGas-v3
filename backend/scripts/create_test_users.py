"""Create test users for development."""
import asyncio
import sys
from pathlib import Path

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.core.database import get_async_session, async_session_maker
from app.core.security import get_password_hash
from app.models.user import User, UserRole

test_users = [
    {
        "username": "admin",
        "email": "admin@luckygas.com",
        "full_name": "系統管理員",
        "role": UserRole.SUPER_ADMIN,
        "password": "admin123",
        "is_active": True,
    },
    {
        "username": "manager1",
        "email": "manager1@luckygas.com",
        "full_name": "張經理",
        "role": UserRole.MANAGER,
        "password": "manager123",
        "is_active": True,
    },
    {
        "username": "office1",
        "email": "office1@luckygas.com",
        "full_name": "李文員",
        "role": UserRole.OFFICE_STAFF,
        "password": "office123",
        "is_active": True,
    },
    {
        "username": "driver1",
        "email": "driver1@luckygas.com",
        "full_name": "王司機",
        "role": UserRole.DRIVER,
        "password": "driver123",
        "is_active": True,
    },
    {
        "username": "customer1",
        "email": "customer1@luckygas.com",
        "full_name": "陳客戶",
        "role": UserRole.CUSTOMER,
        "password": "customer123",
        "is_active": True,
    },
]

async def create_test_users():
    """Create test users in the database."""
    # Store credentials for display
    credentials = [(u['username'], u['password']) for u in test_users]
    
    async with async_session_maker() as session:
        for user_data in test_users:
            # Check if user already exists
            stmt = select(User).where(User.username == user_data['username'])
            result = await session.execute(stmt)
            existing = result.scalar_one_or_none()
            if existing:
                print(f"User {user_data['username']} already exists, skipping...")
                continue
            
            # Create new user
            user_dict = user_data.copy()
            password = user_dict.pop("password")
            user = User(**user_dict)
            user.hashed_password = get_password_hash(password)
            
            session.add(user)
            print(f"Created user: {user.username} ({user.role.value})")
        
        await session.commit()
        print("\nTest users created successfully!")
        print("\nLogin credentials:")
        print("-" * 40)
        for username, password in credentials:
            print(f"Username: {username:<12} Password: {password}")

if __name__ == "__main__":
    asyncio.run(create_test_users())