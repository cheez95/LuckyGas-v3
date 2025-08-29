#!/usr/bin/env python3
"""
Comprehensive product seeding script for all 16 Taiwan gas product variants
Based on actual business data requirements
"""

import asyncio
from sqlalchemy import select, delete
from app.core.database_async import async_session_maker, initialize_database
from app.models.gas_product import GasProduct, DeliveryMethod, ProductAttribute


async def seed_all_products():
    """Seed database with all 16 product types from business requirements"""
    
    # Complete product catalog matching actual business data
    products_data = [
        # === REGULAR CYLINDER PRODUCTS (標準桶裝) ===
        {
            "delivery_method": DeliveryMethod.CYLINDER,
            "size_kg": 50,
            "attribute": ProductAttribute.REGULAR,
            "name_zh": "50KG",
            "name_en": "50kg Standard Cylinder",
            "unit_price": 2375,
            "deposit_amount": 3000,
            "description": "Industrial use 50kg cylinder",
            "is_available": True,
            "is_active": True
        },
        {
            "delivery_method": DeliveryMethod.CYLINDER,
            "size_kg": 20,
            "attribute": ProductAttribute.REGULAR,
            "name_zh": "20KG",
            "name_en": "20kg Standard Cylinder",
            "unit_price": 950,
            "deposit_amount": 1500,
            "is_available": True,
            "is_active": True
        },
        {
            "delivery_method": DeliveryMethod.CYLINDER,
            "size_kg": 16,
            "attribute": ProductAttribute.REGULAR,
            "name_zh": "16KG",
            "name_en": "16kg Standard Cylinder",
            "unit_price": 760,
            "deposit_amount": 1200,
            "is_available": True,
            "is_active": True
        },
        {
            "delivery_method": DeliveryMethod.CYLINDER,
            "size_kg": 10,
            "attribute": ProductAttribute.REGULAR,
            "name_zh": "10KG",
            "name_en": "10kg Standard Cylinder",
            "unit_price": 475,
            "deposit_amount": 800,
            "is_available": True,
            "is_active": True
        },
        {
            "delivery_method": DeliveryMethod.CYLINDER,
            "size_kg": 4,
            "attribute": ProductAttribute.REGULAR,
            "name_zh": "4KG",
            "name_en": "4kg Standard Cylinder",
            "unit_price": 220,
            "deposit_amount": 500,
            "is_available": True,
            "is_active": True
        },
        
        # === COMMERCIAL CYLINDER PRODUCTS (營業用) ===
        {
            "delivery_method": DeliveryMethod.CYLINDER,
            "size_kg": 20,
            "attribute": ProductAttribute.COMMERCIAL,
            "name_zh": "營20",
            "name_en": "20kg Commercial Cylinder",
            "unit_price": 980,
            "deposit_amount": 1500,
            "description": "Commercial grade 20kg cylinder",
            "is_available": True,
            "is_active": True
        },
        {
            "delivery_method": DeliveryMethod.CYLINDER,
            "size_kg": 16,
            "attribute": ProductAttribute.COMMERCIAL,
            "name_zh": "營16",
            "name_en": "16kg Commercial Cylinder",
            "unit_price": 780,
            "deposit_amount": 1200,
            "description": "Commercial grade 16kg cylinder",
            "is_available": True,
            "is_active": True
        },
        
        # === HAOYUN BRAND PRODUCTS (好運牌) ===
        {
            "delivery_method": DeliveryMethod.CYLINDER,
            "size_kg": 20,
            "attribute": ProductAttribute.HAOYUN,
            "name_zh": "好運20",
            "name_en": "20kg Haoyun Brand",
            "unit_price": 980,
            "deposit_amount": 1500,
            "description": "Premium Haoyun brand 20kg",
            "is_available": True,
            "is_active": True
        },
        {
            "delivery_method": DeliveryMethod.CYLINDER,
            "size_kg": 16,
            "attribute": ProductAttribute.HAOYUN,
            "name_zh": "好運16",
            "name_en": "16kg Haoyun Brand",
            "unit_price": 780,
            "deposit_amount": 1200,
            "description": "Premium Haoyun brand 16kg",
            "is_available": True,
            "is_active": True
        },
        
        # === PINGAN SAFETY PRODUCTS (瓶安桶) ===
        {
            "delivery_method": DeliveryMethod.CYLINDER,
            "size_kg": 10,
            "attribute": ProductAttribute.PINGAN,
            "name_zh": "瓶安桶10",
            "name_en": "10kg Pingan Safety Barrel",
            "unit_price": 500,
            "deposit_amount": 900,
            "description": "Safety-certified Pingan barrel 10kg",
            "is_available": True,
            "is_active": True
        },
        
        # === XINGFU SPECIAL PRODUCTS (幸福系列) ===
        {
            "delivery_method": DeliveryMethod.CYLINDER,
            "size_kg": 0,  # Special product without standard size
            "attribute": ProductAttribute.XINGFU,
            "name_zh": "幸福丸",
            "name_en": "Xingfu Pills",
            "unit_price": 180,
            "deposit_amount": 0,
            "description": "Special Xingfu brand product",
            "is_available": True,
            "is_active": True
        },
        
        # === FLOW METER PRODUCTS (流量計) ===
        {
            "delivery_method": DeliveryMethod.FLOW,
            "size_kg": 50,
            "attribute": ProductAttribute.REGULAR,
            "name_zh": "流量50公斤",
            "name_en": "50kg Flow Meter",
            "unit_price": 47.5,  # Per kg pricing
            "deposit_amount": 0,
            "description": "Flow-metered 50kg cylinder",
            "is_available": True,
            "is_active": True
        },
        {
            "delivery_method": DeliveryMethod.FLOW,
            "size_kg": 20,
            "attribute": ProductAttribute.REGULAR,
            "name_zh": "流量20公斤",
            "name_en": "20kg Flow Meter",
            "unit_price": 47.5,  # Per kg pricing
            "deposit_amount": 0,
            "description": "Flow-metered 20kg cylinder",
            "is_available": True,
            "is_active": True
        },
        {
            "delivery_method": DeliveryMethod.FLOW,
            "size_kg": 16,
            "attribute": ProductAttribute.REGULAR,
            "name_zh": "流量16公斤",
            "name_en": "16kg Flow Meter",
            "unit_price": 47.5,  # Per kg pricing
            "deposit_amount": 0,
            "description": "Flow-metered 16kg cylinder",
            "is_available": True,
            "is_active": True
        },
        
        # === FLOW METER HAOYUN PRODUCTS (流量好運) ===
        {
            "delivery_method": DeliveryMethod.FLOW,
            "size_kg": 20,
            "attribute": ProductAttribute.HAOYUN,
            "name_zh": "流量好運20公斤",
            "name_en": "20kg Flow Meter Haoyun",
            "unit_price": 49,  # Premium pricing
            "deposit_amount": 0,
            "description": "Premium flow-metered Haoyun 20kg",
            "is_available": True,
            "is_active": True
        },
        {
            "delivery_method": DeliveryMethod.FLOW,
            "size_kg": 16,
            "attribute": ProductAttribute.HAOYUN,
            "name_zh": "流量好運16公斤",
            "name_en": "16kg Flow Meter Haoyun",
            "unit_price": 49,  # Premium pricing
            "deposit_amount": 0,
            "description": "Premium flow-metered Haoyun 16kg",
            "is_available": True,
            "is_active": True
        },
    ]
    
    async with async_session_maker() as db:
        try:
            # Option to clear existing products first (be careful in production!)
            clear_existing = input("Clear existing products? (yes/no): ").lower() == "yes"
            
            if clear_existing:
                await db.execute(delete(GasProduct))
                await db.commit()
                print("Cleared existing products.")
            
            # Add all products
            added_count = 0
            skipped_count = 0
            
            for product_data in products_data:
                # Check if product already exists
                existing = await db.execute(
                    select(GasProduct).where(
                        (GasProduct.delivery_method == product_data["delivery_method"]) &
                        (GasProduct.size_kg == product_data["size_kg"]) &
                        (GasProduct.attribute == product_data["attribute"])
                    )
                )
                
                if existing.scalar_one_or_none():
                    print(f"⏩ Skipping existing: {product_data['name_zh']}")
                    skipped_count += 1
                    continue
                
                # Create new product
                product = GasProduct(**product_data)
                product.sku = product.generate_sku()
                
                db.add(product)
                print(f"✅ Adding: {product.name_zh} (SKU: {product.sku}, Display: {product.display_name})")
                added_count += 1
            
            await db.commit()
            
            # Summary
            print(f"\n" + "="*60)
            print(f"📊 SEEDING COMPLETE")
            print(f"✅ Added: {added_count} products")
            print(f"⏩ Skipped: {skipped_count} existing products")
            print(f"📦 Total products: {len(products_data)}")
            print("="*60)
            
            # Display all products
            print("\n📋 All Products in Database:")
            all_products = await db.execute(select(GasProduct).order_by(GasProduct.size_kg, GasProduct.attribute))
            for p in all_products.scalars():
                print(f"  - {p.display_name:20} | SKU: {p.sku:15} | ¥{p.unit_price:6.2f}")
                
        except Exception as e:
            print(f"❌ Error during seeding: {str(e)}")
            await db.rollback()
            raise


# Product mapping for import operations
PRODUCT_MAPPING = {
    "50KG": {"size": 50, "attr": ProductAttribute.REGULAR, "method": DeliveryMethod.CYLINDER},
    "營20": {"size": 20, "attr": ProductAttribute.COMMERCIAL, "method": DeliveryMethod.CYLINDER},
    "營16": {"size": 16, "attr": ProductAttribute.COMMERCIAL, "method": DeliveryMethod.CYLINDER},
    "20KG": {"size": 20, "attr": ProductAttribute.REGULAR, "method": DeliveryMethod.CYLINDER},
    "16KG": {"size": 16, "attr": ProductAttribute.REGULAR, "method": DeliveryMethod.CYLINDER},
    "10KG": {"size": 10, "attr": ProductAttribute.REGULAR, "method": DeliveryMethod.CYLINDER},
    "4KG": {"size": 4, "attr": ProductAttribute.REGULAR, "method": DeliveryMethod.CYLINDER},
    "好運16": {"size": 16, "attr": ProductAttribute.HAOYUN, "method": DeliveryMethod.CYLINDER},
    "好運20": {"size": 20, "attr": ProductAttribute.HAOYUN, "method": DeliveryMethod.CYLINDER},
    "瓶安桶10": {"size": 10, "attr": ProductAttribute.PINGAN, "method": DeliveryMethod.CYLINDER},
    "幸福丸": {"size": 0, "attr": ProductAttribute.XINGFU, "method": DeliveryMethod.CYLINDER},
    "流量50公斤": {"size": 50, "attr": ProductAttribute.REGULAR, "method": DeliveryMethod.FLOW},
    "流量20公斤": {"size": 20, "attr": ProductAttribute.REGULAR, "method": DeliveryMethod.FLOW},
    "流量16公斤": {"size": 16, "attr": ProductAttribute.REGULAR, "method": DeliveryMethod.FLOW},
    "流量好運20公斤": {"size": 20, "attr": ProductAttribute.HAOYUN, "method": DeliveryMethod.FLOW},
    "流量好運16公斤": {"size": 16, "attr": ProductAttribute.HAOYUN, "method": DeliveryMethod.FLOW},
}


async def find_or_create_product(name_zh: str, db):
    """Find existing product or create new one based on mapping"""
    if name_zh not in PRODUCT_MAPPING:
        print(f"⚠️  Unknown product: {name_zh}")
        return None
    
    mapping = PRODUCT_MAPPING[name_zh]
    
    # Try to find existing product
    result = await db.execute(
        select(GasProduct).where(
            (GasProduct.delivery_method == mapping["method"]) &
            (GasProduct.size_kg == mapping["size"]) &
            (GasProduct.attribute == mapping["attr"])
        )
    )
    
    product = result.scalar_one_or_none()
    
    if not product:
        print(f"⚠️  Product not found in DB: {name_zh} - Please run seed_all_products.py first")
    
    return product


async def main():
    """Main entry point"""
    print("🚀 Starting comprehensive product seeding...")
    # Initialize database connection
    await initialize_database()
    # Run seeding
    await seed_all_products()


if __name__ == "__main__":
    asyncio.run(main())