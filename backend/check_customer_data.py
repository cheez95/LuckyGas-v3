#!/usr/bin/env python3
"""
Check current customer cylinder data state before migration
"""

from sqlalchemy import select, func
from sqlalchemy.orm import Session
from app.core.database import SessionLocal
from app.models.customer import Customer
from app.models.customer_inventory import CustomerInventory
from app.models.gas_product import GasProduct

def check_customer_data():
    """Check if there's customer cylinder data to migrate"""
    
    db: Session = SessionLocal()
    
    try:
        print("="*60)
        print("📊 CUSTOMER DATA ANALYSIS")
        print("="*60)
        
        # Count customers
        customer_count = db.query(func.count(Customer.id)).scalar()
        print(f"\n📦 Total Customers: {customer_count}")
        
        if customer_count == 0:
            print("⚠️  No customers found in database")
            print("ℹ️  Migration not needed - no data to migrate")
            return False
        
        # Check legacy cylinder fields
        customers_with_cylinders = db.query(Customer).filter(
            (Customer.cylinders_50kg > 0) |
            (Customer.cylinders_20kg > 0) |
            (Customer.cylinders_16kg > 0) |
            (Customer.cylinders_10kg > 0)
        ).all()
        
        print(f"\n🔍 Customers with legacy cylinder data: {len(customers_with_cylinders)}")
        
        if len(customers_with_cylinders) > 0:
            print("\n📋 Sample customers with cylinder data:")
            for customer in customers_with_cylinders[:5]:  # Show first 5
                cylinders = []
                if customer.cylinders_50kg > 0:
                    cylinders.append(f"50kg:{customer.cylinders_50kg}")
                if customer.cylinders_20kg > 0:
                    cylinders.append(f"20kg:{customer.cylinders_20kg}")
                if customer.cylinders_16kg > 0:
                    cylinders.append(f"16kg:{customer.cylinders_16kg}")
                if customer.cylinders_10kg > 0:
                    cylinders.append(f"10kg:{customer.cylinders_10kg}")
                    
                print(f"  - {customer.customer_code}: {customer.short_name}")
                print(f"    Cylinders: {', '.join(cylinders)}")
        
        # Check existing inventory records
        inventory_count = db.query(func.count(CustomerInventory.id)).scalar()
        print(f"\n📦 Existing CustomerInventory records: {inventory_count}")
        
        # Check product count
        product_count = db.query(func.count(GasProduct.id)).scalar()
        print(f"\n🏷️  Available GasProducts: {product_count}")
        
        # Summary
        print("\n" + "="*60)
        print("📊 MIGRATION ASSESSMENT")
        print("="*60)
        
        if len(customers_with_cylinders) > 0:
            print(f"✅ Found {len(customers_with_cylinders)} customers with cylinder data")
            print("🔄 Migration recommended to move data to CustomerInventory")
            print(f"📦 {product_count} products available for mapping")
            return True
        else:
            print("ℹ️  No legacy cylinder data found")
            print("✅ Can skip migration - no data to migrate")
            return False
            
    except Exception as e:
        print(f"❌ Error checking data: {str(e)}")
        return False
    finally:
        db.close()


if __name__ == "__main__":
    needs_migration = check_customer_data()
    
    if needs_migration:
        print("\n💡 Next Step: Run migration script")
        print("   Command: python3 migrate_to_customer_inventory.py")
    else:
        print("\n💡 Next Step: Proceed with frontend integration")
        print("   No migration needed")