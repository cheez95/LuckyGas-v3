#!/usr/bin/env python3
"""Check customer table schema"""
import asyncio
import asyncpg

DATABASE_URL = "postgresql://luckygas:staging-password-2025@35.194.143.37/luckygas"

async def check_schema():
    conn = await asyncpg.connect(DATABASE_URL)
    try:
        columns = await conn.fetch("""
            SELECT column_name, data_type, is_nullable
            FROM information_schema.columns
            WHERE table_schema = 'public' AND table_name = 'customers'
            ORDER BY ordinal_position
        """)
        
        print("Customer table columns:")
        print("=" * 50)
        for col in columns:
            print(f"{col['column_name']}: {col['data_type']} ({col['is_nullable']})")
    finally:
        await conn.close()

if __name__ == "__main__":
    asyncio.run(check_schema())