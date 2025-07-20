import asyncio
from app.core.database import async_session_maker
from app.models.gas_product import GasProduct, DeliveryMethod, ProductAttribute
from sqlalchemy import select

async def seed_products():
    """Seed the database with typical Taiwan gas products"""
    
    # Define typical Taiwan gas products
    products_data = [
        # Regular cylinder products (一般桶裝)
        {
            "delivery_method": DeliveryMethod.CYLINDER,
            "size_kg": 20,
            "attribute": ProductAttribute.REGULAR,
            "name_zh": "20公斤桶裝瓦斯 - 一般",
            "name_en": "20kg Cylinder LPG - Regular",
            "unit_price": 950,
            "deposit_amount": 1500,
            "is_available": True,
            "is_active": True
        },
        {
            "delivery_method": DeliveryMethod.CYLINDER,
            "size_kg": 16,
            "attribute": ProductAttribute.REGULAR,
            "name_zh": "16公斤桶裝瓦斯 - 一般",
            "name_en": "16kg Cylinder LPG - Regular",
            "unit_price": 760,
            "deposit_amount": 1200,
            "is_available": True,
            "is_active": True
        },
        {
            "delivery_method": DeliveryMethod.CYLINDER,
            "size_kg": 10,
            "attribute": ProductAttribute.REGULAR,
            "name_zh": "10公斤桶裝瓦斯 - 一般",
            "name_en": "10kg Cylinder LPG - Regular",
            "unit_price": 475,
            "deposit_amount": 800,
            "is_available": True,
            "is_active": True
        },
        {
            "delivery_method": DeliveryMethod.CYLINDER,
            "size_kg": 4,
            "attribute": ProductAttribute.REGULAR,
            "name_zh": "4公斤桶裝瓦斯 - 一般",
            "name_en": "4kg Cylinder LPG - Regular",
            "unit_price": 220,
            "deposit_amount": 500,
            "is_available": True,
            "is_active": True
        },
        # Haoyun (好運) products
        {
            "delivery_method": DeliveryMethod.CYLINDER,
            "size_kg": 20,
            "attribute": ProductAttribute.HAOYUN,
            "name_zh": "20公斤桶裝瓦斯 - 好運",
            "name_en": "20kg Cylinder LPG - Haoyun",
            "unit_price": 980,
            "deposit_amount": 1500,
            "is_available": True,
            "is_active": True
        },
        {
            "delivery_method": DeliveryMethod.CYLINDER,
            "size_kg": 16,
            "attribute": ProductAttribute.HAOYUN,
            "name_zh": "16公斤桶裝瓦斯 - 好運",
            "name_en": "16kg Cylinder LPG - Haoyun",
            "unit_price": 780,
            "deposit_amount": 1200,
            "is_available": True,
            "is_active": True
        },
        # Pingan (瓶安) products
        {
            "delivery_method": DeliveryMethod.CYLINDER,
            "size_kg": 20,
            "attribute": ProductAttribute.PINGAN,
            "name_zh": "20公斤桶裝瓦斯 - 瓶安",
            "name_en": "20kg Cylinder LPG - Pingan",
            "unit_price": 1000,
            "deposit_amount": 1500,
            "is_available": True,
            "is_active": True
        },
        {
            "delivery_method": DeliveryMethod.CYLINDER,
            "size_kg": 16,
            "attribute": ProductAttribute.PINGAN,
            "name_zh": "16公斤桶裝瓦斯 - 瓶安",
            "name_en": "16kg Cylinder LPG - Pingan",
            "unit_price": 800,
            "deposit_amount": 1200,
            "is_available": True,
            "is_active": True
        },
        # Special sizes
        {
            "delivery_method": DeliveryMethod.CYLINDER,
            "size_kg": 50,
            "attribute": ProductAttribute.REGULAR,
            "name_zh": "50公斤桶裝瓦斯 - 一般 (工業用)",
            "name_en": "50kg Cylinder LPG - Regular (Industrial)",
            "unit_price": 2375,
            "deposit_amount": 3000,
            "is_available": True,
            "is_active": True
        },
        # Flow meter products (流量計)
        {
            "delivery_method": DeliveryMethod.FLOW,
            "size_kg": 0,  # Flow products don't have fixed size
            "attribute": ProductAttribute.REGULAR,
            "name_zh": "流量計瓦斯 - 一般",
            "name_en": "Flow Meter LPG - Regular",
            "unit_price": 25.5,  # Per cubic meter
            "deposit_amount": 0,
            "is_available": True,
            "is_active": True
        }
    ]
    
    async with async_session_maker() as db:
        # Check if products already exist
        existing_count = await db.execute(select(GasProduct))
        if existing_count.scalars().first():
            print("Products already exist in database. Skipping seed.")
            return
        
        # Add products
        for product_data in products_data:
            product = GasProduct(**product_data)
            # Generate SKU
            product.sku = product.generate_sku()
            db.add(product)
            print(f"Adding product: {product.name_zh} (SKU: {product.sku})")
        
        await db.commit()
        print(f"\nSuccessfully seeded {len(products_data)} products.")

if __name__ == "__main__":
    asyncio.run(seed_products())