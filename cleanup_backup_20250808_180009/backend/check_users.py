#!/usr/bin/env python3
"""Check users in database"""
import asyncio
import asyncpg

DATABASE_URL = "postgresql://luckygas:staging-password-2025@35.194.143.37/luckygas"

async def check_users():
    conn = await asyncpg.connect(DATABASE_URL)
    try:
        users = await conn.fetch("""
            SELECT id, username, email, full_name, role, is_active, created_at
            FROM users
            ORDER BY id
        """)
        
        print("Users in database:")
        print("=" * 80)
        for user in users:
            print(f"ID: {user['id']}")
            print(f"Username: {user['username']}")
            print(f"Email: {user['email']}")
            print(f"Full Name: {user['full_name']}")
            print(f"Role: {user['role']}")
            print(f"Active: {user['is_active']}")
            print(f"Created: {user['created_at']}")
            print("-" * 40)
    finally:
        await conn.close()

if __name__ == "__main__":
    asyncio.run(check_users())