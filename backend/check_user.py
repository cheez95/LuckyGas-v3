import asyncio
from sqlalchemy import select
from app.core.database import async_session_maker
from app.models.user import User

async def check_user():
    async with async_session_maker() as db:
        result = await db.execute(select(User).where(User.username == 'administrator'))
        user = result.scalar_one_or_none()
        if user:
            print(f'✅ User found: username={user.username}, email={user.email}, is_active={user.is_active}, role={user.role}')
        else:
            print('❌ User not found')
            
        # List all users
        all_users = await db.execute(select(User))
        users = all_users.scalars().all()
        print(f'\nAll users in database:')
        for u in users:
            print(f'  - username: {u.username}, email: {u.email}, role: {u.role}, active: {u.is_active}')

asyncio.run(check_user())