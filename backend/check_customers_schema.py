#!/usr/bin/env python
"""
Check the actual customers table schema
"""

import os
import sys
from sqlalchemy import create_engine, text

# Add the parent directory to the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.core.config import settings

def check_schema():
    """Check customers table schema"""
    engine = create_engine(settings.DATABASE_URL)
    
    with engine.connect() as conn:
        # Get all columns and their properties
        result = conn.execute(text("""
            SELECT 
                column_name,
                data_type,
                is_nullable,
                column_default
            FROM information_schema.columns 
            WHERE table_name = 'customers'
            ORDER BY ordinal_position
        """))
        
        print("=" * 80)
        print("CUSTOMERS TABLE SCHEMA:")
        print("=" * 80)
        print(f"{'Column':<25} {'Type':<20} {'Nullable':<10} {'Default':<20}")
        print("-" * 80)
        
        for row in result:
            col_name, data_type, is_nullable, default = row
            print(f"{col_name:<25} {data_type:<20} {is_nullable:<10} {str(default or ''):<20}")
        
        print("=" * 80)
        
        # Check constraints
        result = conn.execute(text("""
            SELECT conname, pg_get_constraintdef(oid) 
            FROM pg_constraint 
            WHERE conrelid = 'customers'::regclass
        """))
        
        print("\nCONSTRAINTS:")
        print("-" * 80)
        for row in result:
            print(f"{row[0]}: {row[1]}")

if __name__ == "__main__":
    check_schema()