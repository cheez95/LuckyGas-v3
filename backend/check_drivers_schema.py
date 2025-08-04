#\!/usr/bin/env python3
"""Check drivers table schema"""
import asyncio
import asyncpg

DATABASE_URL = "postgresql://luckygas:staging-password-2025@35.194.143.37/luckygas"

async def check_schema():
    conn = await asyncpg.connect(DATABASE_URL)
    try:
        # Check if table exists
        exists = await conn.fetchval("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_schema = 'public' 
                AND table_name = 'drivers'
            )
        """)
        
        if exists:
            columns = await conn.fetch("""
                SELECT column_name, data_type
                FROM information_schema.columns
                WHERE table_schema = 'public' AND table_name = 'drivers'
                ORDER BY ordinal_position
            """)
            
            print("Drivers table columns:")
            for col in columns:
                print(f"{col['column_name']}: {col['data_type']}")
        else:
            print("Drivers table does not exist")
            
            # Check if there's a users table with driver role
            users = await conn.fetch("""
                SELECT id, full_name, role 
                FROM users 
                WHERE role = 'DRIVER' OR role = 'driver'
                LIMIT 5
            """)
            
            if users:
                print("\nFound drivers in users table:")
                for user in users:
                    print(f"ID: {user['id']}, Name: {user['full_name']}, Role: {user['role']}")
    finally:
        await conn.close()

if __name__ == "__main__":
    asyncio.run(check_schema())
