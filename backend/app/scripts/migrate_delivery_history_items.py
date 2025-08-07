#!/usr / bin / env python3
"""
Migrate existing delivery history records to use the new DeliveryHistoryItem structure
This script creates DeliveryHistoryItem records from the existing column data
"""
import asyncio
import logging
import sys
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

# Add project root to Python path
project_root = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(project_root))

from app.core.database import async_session_maker
from app.models.delivery_history import DeliveryHistory
from app.models.delivery_history_item import DeliveryHistoryItem
from app.models.gas_product import DeliveryMethod, GasProduct, ProductAttribute

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Mapping of legacy columns to gas product attributes
COLUMN_TO_PRODUCT = {
    # Cylinder products
    "qty_50kg": {
        "delivery_method": DeliveryMethod.CYLINDER,
        "size_kg": 50,
        "attribute": ProductAttribute.REGULAR,
    },
    "qty_ying20": {
        "delivery_method": DeliveryMethod.CYLINDER,
        "size_kg": 20,
        "attribute": ProductAttribute.REGULAR,
    },
    "qty_ying16": {
        "delivery_method": DeliveryMethod.CYLINDER,
        "size_kg": 16,
        "attribute": ProductAttribute.REGULAR,
    },
    "qty_20kg": {
        "delivery_method": DeliveryMethod.CYLINDER,
        "size_kg": 20,
        "attribute": ProductAttribute.REGULAR,
    },
    "qty_16kg": {
        "delivery_method": DeliveryMethod.CYLINDER,
        "size_kg": 16,
        "attribute": ProductAttribute.REGULAR,
    },
    "qty_10kg": {
        "delivery_method": DeliveryMethod.CYLINDER,
        "size_kg": 10,
        "attribute": ProductAttribute.REGULAR,
    },
    "qty_4kg": {
        "delivery_method": DeliveryMethod.CYLINDER,
        "size_kg": 4,
        "attribute": ProductAttribute.REGULAR,
    },
    "qty_haoyun16": {
        "delivery_method": DeliveryMethod.CYLINDER,
        "size_kg": 16,
        "attribute": ProductAttribute.HAOYUN,
    },
    "qty_pingantong10": {
        "delivery_method": DeliveryMethod.CYLINDER,
        "size_kg": 10,
        "attribute": ProductAttribute.PINGAN,
    },
    "qty_xingfuwan4": {
        "delivery_method": DeliveryMethod.CYLINDER,
        "size_kg": 4,
        "attribute": ProductAttribute.REGULAR,
    },
    "qty_haoyun20": {
        "delivery_method": DeliveryMethod.CYLINDER,
        "size_kg": 20,
        "attribute": ProductAttribute.HAOYUN,
    },
    # Flow products
    "flow_50kg": {
        "delivery_method": DeliveryMethod.FLOW,
        "size_kg": 50,
        "attribute": ProductAttribute.REGULAR,
    },
    "flow_20kg": {
        "delivery_method": DeliveryMethod.FLOW,
        "size_kg": 20,
        "attribute": ProductAttribute.REGULAR,
    },
    "flow_16kg": {
        "delivery_method": DeliveryMethod.FLOW,
        "size_kg": 16,
        "attribute": ProductAttribute.REGULAR,
    },
    "flow_haoyun20kg": {
        "delivery_method": DeliveryMethod.FLOW,
        "size_kg": 20,
        "attribute": ProductAttribute.HAOYUN,
    },
    "flow_haoyun16kg": {
        "delivery_method": DeliveryMethod.FLOW,
        "size_kg": 16,
        "attribute": ProductAttribute.HAOYUN,
    },
}


async def get_gas_products(session: AsyncSession):
    """Get all gas products and create a lookup map"""
    products_map = {}

    # Get all products
    stmt = select(GasProduct)
    result = await session.execute(stmt)
    products = result.scalars().all()

    # Create lookup map
    for product in products:
        key = (product.delivery_method, product.size_kg, product.attribute)
        products_map[key] = product

    return products_map


async def migrate_delivery_history(session: AsyncSession):
    """Migrate delivery history records to use items"""
    logger.info("Starting delivery history migration...")

    # Get gas products map
    products_map = await get_gas_products(session)
    logger.info(f"Found {len(products_map)} gas products")

    # Get all delivery history records
    stmt = select(DeliveryHistory)
    result = await session.execute(stmt)
    histories = result.scalars().all()
    logger.info(f"Found {len(histories)} delivery history records to migrate")

    migrated_count = 0
    skipped_count = 0

    for history in histories:
        try:
            # Check if already has items
            if history.delivery_items:
                logger.debug(
                    f"Delivery history {history.id} already has items, skipping"
                )
                skipped_count += 1
                continue

            items_created = 0

            # Process each column
            for column_name, product_attrs in COLUMN_TO_PRODUCT.items():
                value = getattr(history, column_name, 0)
                if value and value > 0:
                    # Find the gas product
                    product_key = (
                        product_attrs["delivery_method"],
                        product_attrs["size_kg"],
                        product_attrs["attribute"],
                    )
                    product = products_map.get(product_key)

                    if not product:
                        logger.warning(
                            f"Product not found for {column_name}: {product_key}"
                        )
                        continue

                    # Create delivery item
                    item = DeliveryHistoryItem(
                        delivery_history_id=history.id,
                        gas_product_id=product.id,
                        quantity=(
                            int(value)
                            if product.delivery_method == DeliveryMethod.CYLINDER
                            else 1
                        ),
                        unit_price=100.0,  # Default price since we don't have historical prices
                        is_flow_delivery=(
                            product.delivery_method == DeliveryMethod.FLOW
                        ),
                        flow_quantity=(
                            float(value)
                            if product.delivery_method == DeliveryMethod.FLOW
                            else None
                        ),
                        legacy_product_code=column_name,
                    )
                    item.calculate_subtotal()
                    session.add(item)
                    items_created += 1

            if items_created > 0:
                migrated_count += 1
                if migrated_count % 100 == 0:
                    await session.commit()
                    logger.info(f"Progress: {migrated_count} records migrated")

        except Exception as e:
            logger.error(f"Error migrating delivery history {history.id}: {e}")
            await session.rollback()
            continue

    # Final commit
    await session.commit()
    logger.info(
        f"Migration complete: {migrated_count} records migrated, {skipped_count} skipped"
    )
    return migrated_count, skipped_count


async def main():
    """Main migration function"""
    logger.info("Starting delivery history items migration...")

    async with async_session_maker() as session:
        try:
            migrated, skipped = await migrate_delivery_history(session)

            logger.info("\n" + "=" * 60)
            logger.info("MIGRATION SUMMARY")
            logger.info("=" * 60)
            logger.info(f"Records migrated: {migrated}")
            logger.info(f"Records skipped: {skipped}")
            logger.info("=" * 60)

        except Exception as e:
            logger.error(f"Migration failed: {e}")
            raise


if __name__ == "__main__":
    asyncio.run(main())
