#!/usr/bin/env python3
"""
Add all missing columns to customers table based on Customer model
"""
import asyncio
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text
import os


async def fix_customer_schema():
    """Add all missing columns to customers table"""
    database_url = os.getenv(
        "DATABASE_URL",
        "postgresql+asyncpg://luckygas:luckygas123@localhost:5433/luckygas"
    )
    
    engine = create_async_engine(database_url, echo=True)
    
    async with engine.begin() as conn:
        # Add all missing columns with defaults
        columns_to_add = [
            # Credit management columns
            ("credit_limit", "FLOAT DEFAULT 0.0"),
            ("current_balance", "FLOAT DEFAULT 0.0"),
            ("is_credit_blocked", "BOOLEAN DEFAULT FALSE"),
            
            # Contact columns
            ("phone", "VARCHAR(15)"),
            ("tax_id", "VARCHAR(8)"),
            
            # Location columns
            ("latitude", "FLOAT"),
            ("longitude", "FLOAT"),
            
            # Business/equipment columns
            ("closed_days", "VARCHAR(100)"),
            ("regulator_model", "VARCHAR(100)"),
            ("has_flow_meter", "BOOLEAN DEFAULT FALSE"),
            ("has_wired_flow_meter", "BOOLEAN DEFAULT FALSE"),
            ("has_regulator", "BOOLEAN DEFAULT FALSE"),
            ("has_pressure_gauge", "BOOLEAN DEFAULT FALSE"),
            ("has_pressure_switch", "BOOLEAN DEFAULT FALSE"),
            ("has_micro_switch", "BOOLEAN DEFAULT FALSE"),
            ("has_smart_scale", "BOOLEAN DEFAULT FALSE"),
            
            # Status flags
            ("is_subscription", "BOOLEAN DEFAULT FALSE"),
            ("needs_report", "BOOLEAN DEFAULT FALSE"),
            ("needs_patrol", "BOOLEAN DEFAULT FALSE"),
            ("is_equipment_purchased", "BOOLEAN DEFAULT FALSE"),
            ("is_terminated", "BOOLEAN DEFAULT FALSE"),
            ("needs_same_day_delivery", "BOOLEAN DEFAULT FALSE"),
            
            # Duplicate customer_type - will check if exists
            ("customer_type", "VARCHAR(50) DEFAULT 'household'"),
            
            # Timestamps
            ("created_at", "TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP"),
            ("updated_at", "TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP")
        ]
        
        try:
            for column_name, column_def in columns_to_add:
                try:
                    print(f"Adding {column_name} column...")
                    await conn.execute(text(
                        f"ALTER TABLE customers ADD COLUMN IF NOT EXISTS {column_name} {column_def}"
                    ))
                except Exception as e:
                    # Some columns might already exist, that's okay
                    print(f"  Note: {column_name} might already exist: {e}")
            
            print("✅ Customer schema updated successfully!")
            
        except Exception as e:
            print(f"❌ Error updating customer schema: {e}")
            raise
        finally:
            await engine.dispose()


if __name__ == "__main__":
    asyncio.run(fix_customer_schema())