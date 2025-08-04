#!/usr/bin/env python3
import asyncio
import sys
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text
from app.core.security import get_password_hash
import os

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql+asyncpg://luckygas_test:test_password_secure_123@localhost:5433/luckygas_test")

async def init_db():
    engine = create_async_engine(DATABASE_URL)
    
    async with engine.begin() as conn:
        # Create tables if they don't exist
        await conn.execute(text("""
            CREATE TABLE IF NOT EXISTS users (
                id SERIAL PRIMARY KEY,
                username VARCHAR(255) UNIQUE NOT NULL,
                email VARCHAR(255) UNIQUE NOT NULL,
                hashed_password VARCHAR(255) NOT NULL,
                full_name VARCHAR(255),
                is_active BOOLEAN DEFAULT TRUE,
                is_superuser BOOLEAN DEFAULT FALSE,
                role VARCHAR(50) DEFAULT 'customer',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """))
        
        # Check if admin user exists
        result = await conn.execute(text("SELECT COUNT(*) FROM users WHERE username = 'administrator'"))
        count = result.scalar()
        
        if count == 0:
            # Create test users
            admin_password = get_password_hash("SuperSecure#9876")
            superuser_password = get_password_hash("admin123")
            
            await conn.execute(text("""
                INSERT INTO users (username, email, hashed_password, full_name, is_active, is_superuser, role)
                VALUES 
                    ('administrator', 'admin@luckygas.com', :admin_pwd, 'System Admin', TRUE, TRUE, 'super_admin'),
                    ('admin@luckygas.com', 'admin@luckygas.com', :super_pwd, 'Super Admin', TRUE, TRUE, 'super_admin'),
                    ('test_user', 'test@luckygas.com', :admin_pwd, 'Test User', TRUE, FALSE, 'customer')
            """), {"admin_pwd": admin_password, "super_pwd": superuser_password})
            
            print("✅ Test users created successfully!")
        else:
            print("ℹ️ Users already exist in database")
    
    await engine.dispose()

if __name__ == "__main__":
    asyncio.run(init_db())