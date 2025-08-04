#!/usr/bin/env python3
"""Create test user with known password"""
import asyncio
import asyncpg
import bcrypt

DATABASE_URL = "postgresql://luckygas:staging-password-2025@35.194.143.37/luckygas"

async def create_test_user():
    conn = await asyncpg.connect(DATABASE_URL)
    try:
        # Create password hash
        password = "test123"
        hashed = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
        
        # Insert test user
        await conn.execute("""
            INSERT INTO users (username, email, hashed_password, full_name, role, is_active)
            VALUES ($1, $2, $3, $4, $5, $6)
            ON CONFLICT (email) DO UPDATE
            SET hashed_password = $3, is_active = true
        """, "test@example.com", "test@example.com", hashed, "Test User", "MANAGER", True)
        
        print(f"Created/updated test user:")
        print(f"Email: test@example.com")
        print(f"Password: test123")
        print(f"Role: MANAGER")
        
    finally:
        await conn.close()

if __name__ == "__main__":
    asyncio.run(create_test_user())