import asyncio
from app.core.database import async_session_maker
from sqlalchemy import text

async def check():
    async with async_session_maker() as db:
        result = await db.execute(text('SELECT username, email, is_active, role FROM users'))
        users = result.fetchall()
        print('All users in database:')
        for u in users:
            print(f'  - username: {u[0]}, email: {u[1]}, active: {u[2]}, role: {u[3]}')

asyncio.run(check())