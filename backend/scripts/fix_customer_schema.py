#!/usr/bin/env python3
"""
Add missing columns to customers table
"""
import asyncio
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text
import os


async def fix_customer_schema():
    """Add missing columns to customers table"""
    database_url = os.getenv(
        "DATABASE_URL",
        "postgresql+asyncpg://luckygas:luckygas123@localhost:5433/luckygas"
    )
    
    engine = create_async_engine(database_url, echo=True)
    
    async with engine.begin() as conn:
        # Add missing columns with defaults
        try:
            print("Adding credit_limit column...")
            await conn.execute(text(
                "ALTER TABLE customers ADD COLUMN IF NOT EXISTS credit_limit FLOAT DEFAULT 0.0"
            ))
            
            print("Adding current_balance column...")
            await conn.execute(text(
                "ALTER TABLE customers ADD COLUMN IF NOT EXISTS current_balance FLOAT DEFAULT 0.0"
            ))
            
            print("Adding is_credit_blocked column...")
            await conn.execute(text(
                "ALTER TABLE customers ADD COLUMN IF NOT EXISTS is_credit_blocked BOOLEAN DEFAULT FALSE"
            ))
            
            print("✅ Customer schema updated successfully!")
            
        except Exception as e:
            print(f"❌ Error updating customer schema: {e}")
            raise
        finally:
            await engine.dispose()


if __name__ == "__main__":
    asyncio.run(fix_customer_schema())