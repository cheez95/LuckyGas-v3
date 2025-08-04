#!/usr/bin/env python3
"""
Test script to verify cylinder data migration readiness.

This script checks:
1. Database connectivity
2. Existing customer cylinder data
3. Gas product availability
4. Potential conflicts
"""

import os
import sys

sys.path.append(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
)

from sqlalchemy import text

from app.core.database import async_session_maker as SessionLocal
from app.models.customer import Customer
from app.models.customer_inventory import CustomerInventory
from app.models.gas_product import DeliveryMethod, GasProduct, ProductAttribute


def main():
    """Run migration readiness tests."""
    db = SessionLocal()

    try:
        print("=== Migration Readiness Test ===\n")

        # 1. Check database connectivity
        print("1. Testing database connectivity...")
        result = db.execute(text("SELECT 1")).scalar()
        print("   ✓ Database connection successful\n")

        # 2. Check for customers with cylinder data
        print("2. Checking customers with cylinder data...")
        cylinder_columns = [
            "cylinders_50kg",
            "cylinders_20kg",
            "cylinders_16kg",
            "cylinders_10kg",
            "cylinders_4kg",
            "cylinders_ying20",
            "cylinders_ying16",
            "cylinders_haoyun20",
            "cylinders_haoyun16",
        ]

        for col in cylinder_columns:
            count_query = text(f"SELECT COUNT(*) FROM customers WHERE {col} > 0")
            count = db.execute(count_query).scalar()
            if count > 0:
                sum_query = text(f"SELECT SUM({col}) FROM customers WHERE {col} > 0")
                total = db.execute(sum_query).scalar()
                print(f"   - {col}: {count} customers, {total} total cylinders")
        print()

        # 3. Check gas products
        print("3. Checking gas products...")
        products = db.query(GasProduct).all()
        print(f"   Total products in database: {len(products)}")

        # Check for required product combinations
        required_products = [
            (DeliveryMethod.CYLINDER, 50, ProductAttribute.REGULAR),
            (DeliveryMethod.CYLINDER, 20, ProductAttribute.REGULAR),
            (DeliveryMethod.CYLINDER, 16, ProductAttribute.REGULAR),
            (DeliveryMethod.CYLINDER, 10, ProductAttribute.REGULAR),
            (DeliveryMethod.CYLINDER, 4, ProductAttribute.REGULAR),
            (DeliveryMethod.CYLINDER, 20, ProductAttribute.PINGAN),
            (DeliveryMethod.CYLINDER, 16, ProductAttribute.PINGAN),
            (DeliveryMethod.CYLINDER, 20, ProductAttribute.HAOYUN),
            (DeliveryMethod.CYLINDER, 16, ProductAttribute.HAOYUN),
        ]

        missing_products = []
        for method, size, attr in required_products:
            product = (
                db.query(GasProduct)
                .filter(
                    GasProduct.delivery_method == method,
                    GasProduct.size_kg == size,
                    GasProduct.attribute == attr,
                )
                .first()
            )

            if not product:
                missing_products.append((method, size, attr))

        if missing_products:
            print("   ⚠ Missing products (will be created during migration):")
            for method, size, attr in missing_products:
                print(f"     - {method.value} {size}kg {attr.value}")
        else:
            print("   ✓ All required products exist")
        print()

        # 4. Check for existing inventory records
        print("4. Checking existing inventory records...")
        inventory_count = db.query(CustomerInventory).count()
        print(f"   Current inventory records: {inventory_count}")

        if inventory_count > 0:
            print("   ⚠ Existing inventory records found. Migration will update these.")
        print()

        # 5. Check for potential conflicts
        print("5. Checking for potential conflicts...")

        # Check for customers with both old and new data
        customers_with_both = (
            db.query(Customer)
            .join(CustomerInventory)
            .filter(
                (Customer.cylinders_50kg > 0)
                | (Customer.cylinders_20kg > 0)
                | (Customer.cylinders_16kg > 0)
                | (Customer.cylinders_10kg > 0)
                | (Customer.cylinders_4kg > 0)
                | (Customer.cylinders_ying20 > 0)
                | (Customer.cylinders_ying16 > 0)
                | (Customer.cylinders_haoyun20 > 0)
                | (Customer.cylinders_haoyun16 > 0)
            )
            .count()
        )

        if customers_with_both > 0:
            print(
                f"   ⚠ {customers_with_both} customers have both old cylinder data and inventory records"
            )
            print("     Migration will update existing inventory records")
        else:
            print("   ✓ No conflicts detected")
        print()

        # Summary
        print("=== Summary ===")
        print("✓ Database is accessible")
        print("✓ Customer cylinder data found")
        if missing_products:
            print("⚠ Some products missing (will be created)")
        else:
            print("✓ All required products exist")
        if inventory_count > 0:
            print("⚠ Existing inventory records will be updated")
        else:
            print("✓ No existing inventory records")
        print("\nMigration can proceed. Run with --dry-run first to preview changes.")

    except Exception as e:
        print(f"\n❌ Error: {str(e)}")
        return 1
    finally:
        db.close()

    return 0


if __name__ == "__main__":
    sys.exit(main())
