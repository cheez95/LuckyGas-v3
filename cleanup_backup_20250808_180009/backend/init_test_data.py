"""Initialize test data for UAT"""
import asyncio
import sys
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import text
import bcrypt

# Use asyncpg for database connection
DATABASE_URL = "postgresql+asyncpg://luckygas:staging-password-2025@35.194.143.37/luckygas"

async def init_test_data():
    # Create async engine
    engine = create_async_engine(DATABASE_URL, echo=True)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    async with async_session() as session:
        try:
            # Create tables if they don't exist
            await session.execute(text("""
                CREATE TABLE IF NOT EXISTS users (
                    id SERIAL PRIMARY KEY,
                    email VARCHAR(255) UNIQUE NOT NULL,
                    hashed_password VARCHAR(255) NOT NULL,
                    is_active BOOLEAN DEFAULT true,
                    is_superuser BOOLEAN DEFAULT false,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """))
            
            # Hash passwords
            admin_password = bcrypt.hashpw("Test123!".encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
            user_password = bcrypt.hashpw("Test123!".encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
            
            # Check table structure
            result = await session.execute(text("""
                SELECT column_name FROM information_schema.columns 
                WHERE table_name = 'users'
            """))
            columns = [row[0] for row in result]
            print(f"Existing columns: {columns}")
            
            # Check role values
            if 'role' in columns:
                result = await session.execute(text("""
                    SELECT enum_range(NULL::userrole)
                """))
                role_values = result.scalar()
                print(f"Valid role values: {role_values}")
                
                # Use role-based schema with correct enum values
                await session.execute(text("""
                    INSERT INTO users (email, username, hashed_password, is_active, role, full_name)
                    VALUES 
                        (:admin_email, :admin_email, :admin_password, true, 'SUPER_ADMIN', 'System Admin'),
                        (:user_email, :user_email, :user_password, true, 'CUSTOMER', 'Test User')
                    ON CONFLICT (email) DO UPDATE 
                    SET hashed_password = EXCLUDED.hashed_password, role = EXCLUDED.role
                """), {
                "admin_email": "admin@luckygas.com",
                "admin_password": admin_password,
                "user_email": "test@luckygas.com", 
                "user_password": user_password
                })
            else:
                # Use is_superuser schema
                await session.execute(text("""
                    INSERT INTO users (email, hashed_password, is_active)
                    VALUES 
                        (:admin_email, :admin_password, true),
                        (:user_email, :user_password, true)
                    ON CONFLICT (email) DO UPDATE 
                    SET hashed_password = EXCLUDED.hashed_password
                """), {
                    "admin_email": "admin@luckygas.com",
                    "admin_password": admin_password,
                    "user_email": "test@luckygas.com", 
                    "user_password": user_password
                })
            
            await session.commit()
            print("✅ Test data initialized successfully!")
            print("Admin: admin@luckygas.com / Test123!")
            print("User: test@luckygas.com / Test123!")
            
        except Exception as e:
            print(f"❌ Error: {e}")
            await session.rollback()
            raise
        finally:
            await engine.dispose()

if __name__ == "__main__":
    asyncio.run(init_test_data())