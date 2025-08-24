#!/usr/bin/env python3
"""
Check the actual number of customers in the database
"""

import os
import sys
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Get database URL
DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    # Try local database
    DATABASE_URL = "sqlite:///./luckygas_local.db"
    if not os.path.exists("luckygas_local.db"):
        DATABASE_URL = "sqlite:///./local_luckygas.db"

print(f"Connecting to database: {DATABASE_URL[:50]}...")

try:
    # Create engine
    engine = create_engine(DATABASE_URL)
    
    # Count customers
    with engine.connect() as conn:
        # Total count
        result = conn.execute(text("SELECT COUNT(*) FROM customers"))
        total_count = result.scalar()
        print(f"\n✅ Total customers in database: {total_count}")
        
        # Check for any filters that might affect display
        result = conn.execute(text("SELECT COUNT(*) FROM customers WHERE is_active = true"))
        active_count = result.scalar()
        print(f"   Active customers: {active_count}")
        
        # Sample some customers to verify data
        result = conn.execute(text("SELECT id, short_name, customer_code FROM customers LIMIT 5"))
        print("\nSample customers:")
        for row in result:
            print(f"   - ID: {row[0]}, Name: {row[1]}, Code: {row[2]}")
        
        # Check if there's a specific count we're looking for
        if total_count < 1270:
            print(f"\n⚠️ WARNING: Only {total_count} customers found, expected 1270")
            print("   The data may not be fully imported from the Excel file")
        elif total_count == 1270:
            print("\n✅ Exactly 1270 customers found as expected!")
        else:
            print(f"\n✅ Found {total_count} customers (more than expected 1270)")
            
except Exception as e:
    print(f"❌ Error connecting to database: {e}")
    print("\nTrying alternative connection...")
    
    # Try SQLite directly
    import sqlite3
    
    db_paths = ["local_luckygas.db", "luckygas_local.db", "test_luckygas.db", "../database/luckygas.db"]
    
    for db_path in db_paths:
        if os.path.exists(db_path):
            print(f"Found database at: {db_path}")
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM customers")
            count = cursor.fetchone()[0]
            print(f"Customer count: {count}")
            conn.close()
            break