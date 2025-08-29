#!/usr/bin/env python3
"""
Migration script to move from legacy cylinder fields in Customer table
to the normalized CustomerInventory table using GasProduct references
"""

import asyncio
from sqlalchemy import select, and_
from sqlalchemy.orm import selectinload
from app.core.database_async import async_session_maker, initialize_database
from app.models.customer import Customer
from app.models.gas_product import GasProduct, DeliveryMethod, ProductAttribute
from app.models.customer_inventory import CustomerInventory


async def migrate_customer_cylinders():
    """Migrate legacy cylinder fields to CustomerInventory"""
    
    async with async_session_maker() as db:
        try:
            print("🔄 Starting migration from legacy cylinder fields to CustomerInventory...")
            
            # First, ensure all products exist
            products_map = {}
            
            # Define the legacy field mappings
            field_mappings = [
                ("cylinders_50kg", 50, ProductAttribute.REGULAR, DeliveryMethod.CYLINDER),
                ("cylinders_20kg", 20, ProductAttribute.REGULAR, DeliveryMethod.CYLINDER),
                ("cylinders_16kg", 16, ProductAttribute.REGULAR, DeliveryMethod.CYLINDER),
                ("cylinders_10kg", 10, ProductAttribute.REGULAR, DeliveryMethod.CYLINDER),
                # Note: cylinders_4kg is not in the Customer model based on our analysis
            ]
            
            # Get all products and create a lookup map
            all_products = await db.execute(select(GasProduct))
            for product in all_products.scalars():
                key = (product.size_kg, product.attribute, product.delivery_method)
                products_map[key] = product
            
            if not products_map:
                print("❌ No products found in database. Please run seed_all_products.py first!")
                return
            
            # Get all customers with their existing inventory
            customers_result = await db.execute(
                select(Customer).options(selectinload(Customer.inventory_items))
            )
            customers = customers_result.scalars().all()
            
            if not customers:
                print("⚠️  No customers found in database.")
                return
            
            print(f"📊 Found {len(customers)} customers to migrate")
            
            # Track migration stats
            migrated_count = 0
            skipped_count = 0
            created_inventory_items = 0
            updated_inventory_items = 0
            
            for customer in customers:
                customer_migrated = False
                
                # Create a map of existing inventory for this customer
                existing_inventory = {}
                for inv_item in customer.inventory_items:
                    existing_inventory[inv_item.gas_product_id] = inv_item
                
                # Process each legacy field
                for field_name, size_kg, attribute, delivery_method in field_mappings:
                    # Get the value from the customer object
                    cylinder_count = getattr(customer, field_name, 0)
                    
                    if cylinder_count and cylinder_count > 0:
                        # Find the corresponding product
                        product_key = (size_kg, attribute, delivery_method)
                        product = products_map.get(product_key)
                        
                        if not product:
                            print(f"⚠️  Product not found for {field_name}: {size_kg}kg {attribute}")
                            continue
                        
                        # Check if inventory already exists
                        if product.id in existing_inventory:
                            # Update existing inventory
                            inv_item = existing_inventory[product.id]
                            old_qty = inv_item.quantity_total
                            
                            # Only update if different
                            if old_qty != cylinder_count:
                                inv_item.quantity_total = cylinder_count
                                inv_item.quantity_owned = cylinder_count  # Assume owned
                                inv_item.quantity_rented = 0
                                updated_inventory_items += 1
                                customer_migrated = True
                                print(f"  📝 Updated {customer.customer_code} - {product.display_name}: {old_qty} → {cylinder_count}")
                        else:
                            # Create new inventory item
                            new_inventory = CustomerInventory(
                                customer_id=customer.id,
                                gas_product_id=product.id,
                                quantity_total=cylinder_count,
                                quantity_owned=cylinder_count,  # Assume owned unless specified
                                quantity_rented=0,
                                deposit_paid=0,
                                is_active=True
                            )
                            db.add(new_inventory)
                            created_inventory_items += 1
                            customer_migrated = True
                            print(f"  ✅ Created {customer.customer_code} - {product.display_name}: {cylinder_count} cylinders")
                
                if customer_migrated:
                    migrated_count += 1
                else:
                    skipped_count += 1
            
            # Commit all changes
            await db.commit()
            
            # Print summary
            print("\n" + "="*60)
            print("📊 MIGRATION COMPLETE")
            print(f"✅ Migrated customers: {migrated_count}")
            print(f"⏩ Skipped customers: {skipped_count}")
            print(f"🆕 Created inventory items: {created_inventory_items}")
            print(f"📝 Updated inventory items: {updated_inventory_items}")
            print("="*60)
            
            # Verify migration
            print("\n🔍 Verification - Sample Customer Inventories:")
            sample_customers = await db.execute(
                select(Customer)
                .options(selectinload(Customer.inventory_items))
                .limit(5)
            )
            
            for customer in sample_customers.scalars():
                if customer.inventory_items:
                    print(f"\n📦 Customer: {customer.customer_code} ({customer.short_name})")
                    for inv in customer.inventory_items:
                        if inv.gas_product:
                            print(f"  - {inv.gas_product.display_name}: {inv.quantity_total} cylinders")
                
        except Exception as e:
            print(f"❌ Error during migration: {str(e)}")
            await db.rollback()
            raise


async def verify_migration():
    """Verify that migration was successful by comparing legacy fields with inventory"""
    
    async with async_session_maker() as db:
        print("\n🔍 Verifying migration integrity...")
        
        customers_result = await db.execute(
            select(Customer).options(selectinload(Customer.inventory_items))
        )
        customers = customers_result.scalars().all()
        
        mismatches = []
        
        for customer in customers:
            # Check each legacy field against inventory
            legacy_fields = [
                ("cylinders_50kg", 50, ProductAttribute.REGULAR),
                ("cylinders_20kg", 20, ProductAttribute.REGULAR),
                ("cylinders_16kg", 16, ProductAttribute.REGULAR),
                ("cylinders_10kg", 10, ProductAttribute.REGULAR),
            ]
            
            for field_name, size_kg, attribute in legacy_fields:
                legacy_count = getattr(customer, field_name, 0)
                
                if legacy_count > 0:
                    # Find corresponding inventory
                    inventory_count = 0
                    for inv in customer.inventory_items:
                        if (inv.gas_product and 
                            inv.gas_product.size_kg == size_kg and 
                            inv.gas_product.attribute == attribute and
                            inv.gas_product.delivery_method == DeliveryMethod.CYLINDER):
                            inventory_count = inv.quantity_total
                            break
                    
                    if legacy_count != inventory_count:
                        mismatches.append({
                            "customer": customer.customer_code,
                            "field": field_name,
                            "legacy": legacy_count,
                            "inventory": inventory_count
                        })
        
        if mismatches:
            print(f"⚠️  Found {len(mismatches)} mismatches:")
            for m in mismatches[:10]:  # Show first 10
                print(f"  - {m['customer']}: {m['field']} legacy={m['legacy']} vs inventory={m['inventory']}")
        else:
            print("✅ All legacy fields match inventory records perfectly!")


async def cleanup_legacy_fields():
    """Optional: Set legacy cylinder fields to 0 after successful migration"""
    
    confirm = input("\n⚠️  Set all legacy cylinder fields to 0? This is irreversible! (yes/no): ")
    if confirm.lower() != "yes":
        print("Skipping cleanup.")
        return
    
    async with async_session_maker() as db:
        customers = await db.execute(select(Customer))
        
        updated_count = 0
        for customer in customers.scalars():
            if any([
                getattr(customer, "cylinders_50kg", 0) > 0,
                getattr(customer, "cylinders_20kg", 0) > 0,
                getattr(customer, "cylinders_16kg", 0) > 0,
                getattr(customer, "cylinders_10kg", 0) > 0,
            ]):
                customer.cylinders_50kg = 0
                customer.cylinders_20kg = 0
                customer.cylinders_16kg = 0
                customer.cylinders_10kg = 0
                updated_count += 1
        
        await db.commit()
        print(f"✅ Cleared legacy fields for {updated_count} customers")


async def main():
    """Main migration workflow"""
    print("="*60)
    print("🚀 CUSTOMER INVENTORY MIGRATION TOOL")
    print("="*60)
    
    # Initialize database connection
    await initialize_database()
    
    # Step 1: Ensure products exist
    print("\n📦 Step 1: Checking products...")
    from seed_all_products import seed_all_products
    await seed_all_products()
    
    # Step 2: Migrate data
    print("\n🔄 Step 2: Migrating customer cylinder data...")
    await migrate_customer_cylinders()
    
    # Step 3: Verify
    print("\n✅ Step 3: Verifying migration...")
    await verify_migration()
    
    # Step 4: Optional cleanup
    print("\n🧹 Step 4: Cleanup (optional)...")
    await cleanup_legacy_fields()
    
    print("\n✨ Migration process complete!")


if __name__ == "__main__":
    asyncio.run(main())