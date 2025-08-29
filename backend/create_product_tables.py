#!/usr/bin/env python3
"""
Create GasProduct and CustomerInventory tables
"""

from sqlalchemy import create_engine, MetaData
from app.core.database import engine
from app.models.gas_product import GasProduct
from app.models.customer_inventory import CustomerInventory

def create_tables():
    """Create only the tables we need for product management"""
    try:
        # Create only specific tables
        GasProduct.__table__.create(engine, checkfirst=True)
        print("✅ Created gas_products table")
        
        CustomerInventory.__table__.create(engine, checkfirst=True)
        print("✅ Created customer_inventory table")
        
        print("\n📊 Tables created successfully!")
        
    except Exception as e:
        print(f"❌ Error creating tables: {str(e)}")
        # If table already exists, that's okay
        if "already exists" in str(e).lower():
            print("ℹ️  Tables may already exist, continuing...")
        else:
            raise

if __name__ == "__main__":
    create_tables()