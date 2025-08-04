"""
Seed script to create all gas product combinations
"""

import asyncio

from sqlalchemy import select

from app.core.database import async_session_maker
from app.models.gas_product import DeliveryMethod, GasProduct, ProductAttribute

# Product pricing configuration
PRICING = {
    # Regular cylinder prices
    (DeliveryMethod.CYLINDER, 4, ProductAttribute.REGULAR): 200,
    (DeliveryMethod.CYLINDER, 10, ProductAttribute.REGULAR): 450,
    (DeliveryMethod.CYLINDER, 16, ProductAttribute.REGULAR): 700,
    (DeliveryMethod.CYLINDER, 20, ProductAttribute.REGULAR): 850,
    (DeliveryMethod.CYLINDER, 50, ProductAttribute.REGULAR): 2100,
    # 好運 (Good Luck) cylinder prices - slightly premium
    (DeliveryMethod.CYLINDER, 4, ProductAttribute.HAOYUN): 220,
    (DeliveryMethod.CYLINDER, 10, ProductAttribute.HAOYUN): 480,
    (DeliveryMethod.CYLINDER, 16, ProductAttribute.HAOYUN): 750,
    (DeliveryMethod.CYLINDER, 20, ProductAttribute.HAOYUN): 900,
    (DeliveryMethod.CYLINDER, 50, ProductAttribute.HAOYUN): 2200,
    # 瓶安 (Bottle Safety) cylinder prices - safety premium
    (DeliveryMethod.CYLINDER, 4, ProductAttribute.PINGAN): 230,
    (DeliveryMethod.CYLINDER, 10, ProductAttribute.PINGAN): 490,
    (DeliveryMethod.CYLINDER, 16, ProductAttribute.PINGAN): 770,
    (DeliveryMethod.CYLINDER, 20, ProductAttribute.PINGAN): 920,
    (DeliveryMethod.CYLINDER, 50, ProductAttribute.PINGAN): 2250,
    # Flow meter prices (per kg) - no cylinder deposit needed
    (DeliveryMethod.FLOW, 4, ProductAttribute.REGULAR): 45,
    (DeliveryMethod.FLOW, 10, ProductAttribute.REGULAR): 43,
    (DeliveryMethod.FLOW, 16, ProductAttribute.REGULAR): 42,
    (DeliveryMethod.FLOW, 20, ProductAttribute.REGULAR): 41,
    (DeliveryMethod.FLOW, 50, ProductAttribute.REGULAR): 40,
    # 好運 flow prices
    (DeliveryMethod.FLOW, 4, ProductAttribute.HAOYUN): 48,
    (DeliveryMethod.FLOW, 10, ProductAttribute.HAOYUN): 46,
    (DeliveryMethod.FLOW, 16, ProductAttribute.HAOYUN): 45,
    (DeliveryMethod.FLOW, 20, ProductAttribute.HAOYUN): 44,
    (DeliveryMethod.FLOW, 50, ProductAttribute.HAOYUN): 43,
    # 瓶安 flow prices
    (DeliveryMethod.FLOW, 4, ProductAttribute.PINGAN): 50,
    (DeliveryMethod.FLOW, 10, ProductAttribute.PINGAN): 48,
    (DeliveryMethod.FLOW, 16, ProductAttribute.PINGAN): 47,
    (DeliveryMethod.FLOW, 20, ProductAttribute.PINGAN): 46,
    (DeliveryMethod.FLOW, 50, ProductAttribute.PINGAN): 45,
}

# Cylinder deposit amounts
DEPOSITS = {
    4: 500,
    10: 800,
    16: 1000,
    20: 1200,
    50: 2000,
}


async def create_gas_products():
    """Create all gas product combinations"""
    async with async_session_maker() as session:
        created_count = 0
        updated_count = 0

        for method in DeliveryMethod:
            for size in [4, 10, 16, 20, 50]:
                for attribute in ProductAttribute:
                    # Check if product already exists
                    result = await session.execute(
                        select(GasProduct).where(
                            GasProduct.delivery_method == method,
                            GasProduct.size_kg == size,
                            GasProduct.attribute == attribute,
                        )
                    )
                    existing_product = result.scalar_one_or_none()

                    # Generate product details
                    product = GasProduct(
                        delivery_method=method, size_kg=size, attribute=attribute
                    )

                    # Generate SKU
                    product.sku = product.generate_sku()

                    # Set Chinese name
                    method_name = (
                        "桶裝" if method == DeliveryMethod.CYLINDER else "流量"
                    )
                    attr_prefix = {
                        ProductAttribute.REGULAR: "",
                        ProductAttribute.HAOYUN: "好運",
                        ProductAttribute.PINGAN: "瓶安",
                    }.get(attribute, "")

                    if attr_prefix:
                        product.name_zh = f"{attr_prefix}{size}公斤{method_name}瓦斯"
                    else:
                        product.name_zh = f"{size}公斤{method_name}瓦斯"

                    # Set English name
                    attr_eng = {
                        ProductAttribute.REGULAR: "Regular",
                        ProductAttribute.HAOYUN: "Good Luck",
                        ProductAttribute.PINGAN: "Safety",
                    }.get(attribute, "Regular")

                    method_eng = (
                        "Cylinder" if method == DeliveryMethod.CYLINDER else "Flow"
                    )
                    product.name_en = f"{size}kg {attr_eng} {method_eng} Gas"

                    # Set description
                    if method == DeliveryMethod.CYLINDER:
                        product.description = (
                            f"{product.name_zh} - 桶裝瓦斯，需要瓦斯桶"
                        )
                    else:
                        product.description = (
                            f"{product.name_zh} - 流量計費，按實際使用量收費"
                        )

                    # Set pricing
                    price_key = (method, size, attribute)
                    product.unit_price = PRICING.get(price_key, 0)

                    # Set deposit for cylinders
                    if method == DeliveryMethod.CYLINDER:
                        product.deposit_amount = DEPOSITS.get(size, 0)
                    else:
                        product.deposit_amount = 0

                    # Set inventory thresholds based on size
                    if size <= 10:
                        product.low_stock_threshold = 20
                    elif size <= 20:
                        product.low_stock_threshold = 15
                    else:
                        product.low_stock_threshold = 10

                    if existing_product:
                        # Update existing product
                        existing_product.name_zh = product.name_zh
                        existing_product.name_en = product.name_en
                        existing_product.description = product.description
                        existing_product.unit_price = product.unit_price
                        existing_product.deposit_amount = product.deposit_amount
                        existing_product.low_stock_threshold = (
                            product.low_stock_threshold
                        )
                        updated_count += 1
                        print(f"Updated: {product.sku} - {product.name_zh}")
                    else:
                        # Create new product
                        session.add(product)
                        created_count += 1
                        print(f"Created: {product.sku} - {product.name_zh}")

        await session.commit()
        print(f"\nSummary:")
        print(f"Created {created_count} new products")
        print(f"Updated {updated_count} existing products")
        print(f"Total products: {created_count + updated_count}")


async def list_products():
    """List all gas products for verification"""
    async with async_session_maker() as session:
        result = await session.execute(
            select(GasProduct).order_by(
                GasProduct.delivery_method, GasProduct.size_kg, GasProduct.attribute
            )
        )
        products = result.scalars().all()

        print("\n=== Gas Products Catalog ===")
        print(f"Total products: {len(products)}\n")

        current_method = None
        for product in products:
            if product.delivery_method != current_method:
                current_method = product.delivery_method
                print(f"\n--- {current_method.value} Products ---")
                print(f"{'SKU':<15} {'Name':<30} {'Price':<10} {'Deposit':<10}")
                print("-" * 70)

            print(
                f"{product.sku:<15} {product.name_zh:<30} "
                f"${product.unit_price:<9.2f} ${product.deposit_amount:<9.2f}"
            )


async def main():
    """Main function to seed gas products"""
    print("Starting gas product seeding...")
    await create_gas_products()
    await list_products()


if __name__ == "__main__":
    asyncio.run(main())
