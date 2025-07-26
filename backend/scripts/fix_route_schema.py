#!/usr/bin/env python3
"""
Fix route table schema by adding missing 'name' column
"""
import asyncio
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text
import os


async def fix_route_schema():
    """Add missing name column to routes table"""
    # Get database URL
    database_url = os.getenv(
        "DATABASE_URL",
        "postgresql+asyncpg://luckygas:luckygas123@localhost:5433/luckygas"
    )
    
    # Create engine
    engine = create_async_engine(database_url, echo=True)
    
    try:
        async with engine.begin() as conn:
            # Check if column exists
            check_query = text("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name = 'routes' 
                AND column_name = 'name'
            """)
            result = await conn.execute(check_query)
            exists = result.fetchone()
            
            if not exists:
                print("Adding 'name' column to routes table...")
                
                # Add column
                await conn.execute(text(
                    "ALTER TABLE routes ADD COLUMN name VARCHAR(100)"
                ))
                
                # Update existing rows
                await conn.execute(text(
                    "UPDATE routes SET name = route_name WHERE name IS NULL"
                ))
                
                print("✅ Successfully added 'name' column to routes table")
            else:
                print("ℹ️  'name' column already exists in routes table")
                
            # Add comment
            await conn.execute(text(
                "COMMENT ON COLUMN routes.name IS 'Human-readable name for the route, defaults to route_number'"
            ))
            
    except Exception as e:
        print(f"❌ Error fixing route schema: {e}")
        raise
    finally:
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(fix_route_schema())