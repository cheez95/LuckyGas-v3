#!/usr/bin/env python3
import asyncio
import os
from sqlalchemy import create_engine, text
from sqlalchemy.ext.asyncio import create_async_engine
from app.core.security import get_password_hash

# First, create the database using sync connection
sync_url = "postgresql://postgres:postgres@localhost:5432/postgres"
engine = create_engine(sync_url)

try:
    with engine.connect() as conn:
        conn.execute(text("COMMIT"))  # Close any existing transaction
        try:
            conn.execute(text("CREATE DATABASE luckygas_local"))
            print("✅ Database luckygas_local created successfully!")
        except Exception as e:
            print(f"Database might already exist: {e}")
finally:
    engine.dispose()

# Now set up the tables and admin user
async_url = "postgresql+asyncpg://postgres:postgres@localhost:5432/luckygas_local"

async def setup_db():
    engine = create_async_engine(async_url)
    
    async with engine.begin() as conn:
        # Create users table if it doesn't exist
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
                two_factor_enabled BOOLEAN DEFAULT FALSE,
                two_factor_secret VARCHAR(255),
                last_login TIMESTAMP WITH TIME ZONE,
                password_changed_at TIMESTAMP WITH TIME ZONE,
                failed_login_attempts INTEGER DEFAULT 0,
                locked_until TIMESTAMP WITH TIME ZONE,
                created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
            );
        """))
        
        # Check if admin user exists
        result = await conn.execute(text("SELECT COUNT(*) FROM users WHERE username = 'admin@luckygas.com'"))
        count = result.scalar()
        
        if count == 0:
            # Create admin user
            admin_password = get_password_hash('admin-password-2025')
            
            await conn.execute(text("""
                INSERT INTO users (username, email, hashed_password, full_name, is_active, is_superuser, role)
                VALUES ('admin@luckygas.com', 'admin@luckygas.com', :pwd, 'System Admin', TRUE, TRUE, 'super_admin')
            """), {"pwd": admin_password})
            
            print('✅ Admin user created successfully!')
            print('   Username: admin@luckygas.com')
            print('   Password: admin-password-2025')
        else:
            # Update password
            admin_password = get_password_hash('admin-password-2025')
            await conn.execute(text("UPDATE users SET hashed_password = :pwd WHERE username = 'admin@luckygas.com'"), {"pwd": admin_password})
            print('✅ Admin password updated successfully!')
    
    await engine.dispose()

# Run the setup
asyncio.run(setup_db())