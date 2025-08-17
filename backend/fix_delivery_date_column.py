#!/usr/bin/env python3
"""
Quick fix to add missing delivery_date column to orders table
"""
import psycopg2
from psycopg2 import sql

# Database connection parameters
DB_PARAMS = {
    'host': '35.194.143.37',
    'database': 'luckygas',
    'user': 'luckygas',
    'password': 'staging-password-2025'
}

def add_delivery_date_column():
    """Add delivery_date column to orders table if it doesn't exist"""
    conn = None
    cursor = None
    
    try:
        # Connect to database
        print("Connecting to database...")
        conn = psycopg2.connect(**DB_PARAMS)
        cursor = conn.cursor()
        
        # Check if column exists
        cursor.execute("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = 'orders' 
            AND column_name = 'delivery_date'
        """)
        
        if cursor.fetchone():
            print("✅ delivery_date column already exists")
        else:
            print("Adding delivery_date column...")
            cursor.execute("""
                ALTER TABLE orders 
                ADD COLUMN delivery_date TIMESTAMP WITH TIME ZONE
            """)
            conn.commit()
            print("✅ delivery_date column added successfully")
        
        # List all columns in orders table
        cursor.execute("""
            SELECT column_name, data_type 
            FROM information_schema.columns 
            WHERE table_name = 'orders'
            ORDER BY ordinal_position
        """)
        
        print("\nCurrent columns in orders table:")
        for column in cursor.fetchall():
            print(f"  - {column[0]}: {column[1]}")
            
    except Exception as e:
        print(f"❌ Error: {e}")
        if conn:
            conn.rollback()
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

if __name__ == "__main__":
    add_delivery_date_column()