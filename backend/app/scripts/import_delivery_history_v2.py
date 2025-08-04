#!/usr/bin/env python3
"""
Import delivery history from Excel files using the new flexible gas product system
This version creates DeliveryHistoryItem records for each product delivered
"""
import asyncio
import logging

# Add project root to Python path
import sys
from datetime import date, datetime
from pathlib import Path

import numpy as np
import pandas as pd
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

project_root = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(project_root))

from app.core.database import async_session_maker, engine
from app.models.customer import Customer
from app.models.delivery_history import DeliveryHistory
from app.models.delivery_history_item import DeliveryHistoryItem
from app.models.gas_product import DeliveryMethod, GasProduct, ProductAttribute

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# File paths
RAW_DIR = project_root.parent / "raw"
DELIVERY_FILE = RAW_DIR / "2025-05 deliver history.xlsx"

# Mapping of Excel columns to gas product attributes
PRODUCT_MAPPING = {
    # Cylinder products
    "50公斤": {
        "delivery_method": DeliveryMethod.CYLINDER,
        "size_kg": 50,
        "attribute": ProductAttribute.REGULAR,
        "legacy_code": "qty_50kg",
    },
    "丙烷20": {
        "delivery_method": DeliveryMethod.CYLINDER,
        "size_kg": 20,
        "attribute": ProductAttribute.REGULAR,
        "legacy_code": "qty_ying20",
    },
    "丙烷16": {
        "delivery_method": DeliveryMethod.CYLINDER,
        "size_kg": 16,
        "attribute": ProductAttribute.REGULAR,
        "legacy_code": "qty_ying16",
    },
    "20公斤": {
        "delivery_method": DeliveryMethod.CYLINDER,
        "size_kg": 20,
        "attribute": ProductAttribute.REGULAR,
        "legacy_code": "qty_20kg",
    },
    "16公斤": {
        "delivery_method": DeliveryMethod.CYLINDER,
        "size_kg": 16,
        "attribute": ProductAttribute.REGULAR,
        "legacy_code": "qty_16kg",
    },
    "10公斤": {
        "delivery_method": DeliveryMethod.CYLINDER,
        "size_kg": 10,
        "attribute": ProductAttribute.REGULAR,
        "legacy_code": "qty_10kg",
    },
    "4公斤": {
        "delivery_method": DeliveryMethod.CYLINDER,
        "size_kg": 4,
        "attribute": ProductAttribute.REGULAR,
        "legacy_code": "qty_4kg",
    },
    "好運桶16": {
        "delivery_method": DeliveryMethod.CYLINDER,
        "size_kg": 16,
        "attribute": ProductAttribute.HAOYUN,
        "legacy_code": "qty_haoyun16",
    },
    "瓶安桶10": {
        "delivery_method": DeliveryMethod.CYLINDER,
        "size_kg": 10,
        "attribute": ProductAttribute.PINGAN,
        "legacy_code": "qty_pingantong10",
    },
    "幸福丸4": {
        "delivery_method": DeliveryMethod.CYLINDER,
        "size_kg": 4,
        "attribute": ProductAttribute.REGULAR,
        "legacy_code": "qty_xingfuwan4",
    },
    "好運桶20": {
        "delivery_method": DeliveryMethod.CYLINDER,
        "size_kg": 20,
        "attribute": ProductAttribute.HAOYUN,
        "legacy_code": "qty_haoyun20",
    },
    # Flow products
    "流量50公斤": {
        "delivery_method": DeliveryMethod.FLOW,
        "size_kg": 50,
        "attribute": ProductAttribute.REGULAR,
        "legacy_code": "flow_50kg",
    },
    "流量20公斤": {
        "delivery_method": DeliveryMethod.FLOW,
        "size_kg": 20,
        "attribute": ProductAttribute.REGULAR,
        "legacy_code": "flow_20kg",
    },
    "流量16公斤": {
        "delivery_method": DeliveryMethod.FLOW,
        "size_kg": 16,
        "attribute": ProductAttribute.REGULAR,
        "legacy_code": "flow_16kg",
    },
    "流量好運20公斤": {
        "delivery_method": DeliveryMethod.FLOW,
        "size_kg": 20,
        "attribute": ProductAttribute.HAOYUN,
        "legacy_code": "flow_haoyun20kg",
    },
    "流量好運16公斤": {
        "delivery_method": DeliveryMethod.FLOW,
        "size_kg": 16,
        "attribute": ProductAttribute.HAOYUN,
        "legacy_code": "flow_haoyun16kg",
    },
}


def clean_numeric(value):
    """Clean numeric values, handling NaN and converting to appropriate type"""
    if pd.isna(value):
        return None
    if isinstance(value, str):
        # Remove any non-numeric characters
        value = "".join(filter(lambda x: x.isdigit() or x == ".", value))
        if not value:
            return None
    try:
        if "." in str(value):
            return float(value)
        return int(value)
    except:
        return None


async def get_or_create_gas_products(session: AsyncSession):
    """Ensure all gas products exist in the database"""
    logger.info("Checking/creating gas products...")

    products_cache = {}

    for col_name, attrs in PRODUCT_MAPPING.items():
        # Check if product exists
        stmt = select(GasProduct).where(
            (GasProduct.delivery_method == attrs["delivery_method"])
            & (GasProduct.size_kg == attrs["size_kg"])
            & (GasProduct.attribute == attrs["attribute"])
        )
        result = await session.execute(stmt)
        product = result.scalar_one_or_none()

        if not product:
            # Create the product
            product = GasProduct(
                delivery_method=attrs["delivery_method"],
                size_kg=attrs["size_kg"],
                attribute=attrs["attribute"],
                sku=f"GAS-{'C' if attrs['delivery_method'] == DeliveryMethod.CYLINDER else 'F'}{attrs['size_kg']:02d}-{attrs['attribute'][0]}",
                name_zh=col_name,
                unit_price=100.0,  # Default price, should be updated later
                is_active=True,
                is_available=True,
            )
            session.add(product)
            await session.flush()
            logger.info(f"Created gas product: {col_name}")

        products_cache[col_name] = product

    await session.commit()
    return products_cache


async def import_delivery_history_v2(session: AsyncSession):
    """Import delivery history with flexible product items"""
    logger.info(f"Reading delivery history from {DELIVERY_FILE}")

    # Get or create gas products
    products_cache = await get_or_create_gas_products(session)

    # Get all sheets
    xl_file = pd.ExcelFile(DELIVERY_FILE)
    total_imported = 0

    for sheet_name in xl_file.sheet_names:
        logger.info(f"Processing sheet: {sheet_name}")
        df = pd.read_excel(DELIVERY_FILE, sheet_name=sheet_name)

        # Skip empty sheets
        if len(df) == 0:
            continue

        imported_count = 0

        for idx, row in df.iterrows():
            try:
                # Skip rows without essential data
                customer_code = row.get("客戶編號") or row.get("編號")
                if pd.isna(customer_code):
                    continue

                customer_code = (
                    str(int(customer_code)) if not pd.isna(customer_code) else None
                )
                if not customer_code:
                    continue

                # Find customer in database
                stmt = select(Customer).where(Customer.customer_code == customer_code)
                result = await session.execute(stmt)
                customer = result.scalar_one_or_none()

                if not customer:
                    logger.warning(f"Customer {customer_code} not found in database")
                    continue

                # Parse transaction date
                trans_date = None
                if "交易日期" in row:
                    date_val = row["交易日期"]
                    if pd.notna(date_val):
                        try:
                            # Handle different date formats
                            if isinstance(date_val, (int, float)):
                                # Assuming format like 1140520 (year 114 = 2025, month 05, day 20)
                                date_str = str(int(date_val))
                                if len(date_str) >= 6:
                                    year = (
                                        int(date_str[:3]) + 1911
                                    )  # Convert from ROC year
                                    month = int(date_str[3:5])
                                    day = int(date_str[5:7])
                                    trans_date = date(year, month, day)
                            elif isinstance(date_val, datetime):
                                trans_date = date_val.date()
                            else:
                                trans_date = pd.to_datetime(date_val).date()
                        except:
                            logger.warning(f"Could not parse date: {date_val}")
                            continue

                if not trans_date:
                    # Try to infer from sheet name
                    if "Sheet" in sheet_name and sheet_name[-1].isdigit():
                        # Assume May 2025 data
                        day = 20 - int(sheet_name[-1]) + 1
                        trans_date = date(2025, 5, day)
                    else:
                        continue

                # Check if record already exists
                stmt = select(DeliveryHistory).where(
                    (DeliveryHistory.customer_code == customer_code)
                    & (DeliveryHistory.transaction_date == trans_date)
                )
                result = await session.execute(stmt)
                if result.scalar_one_or_none():
                    logger.debug(
                        f"Delivery history already exists for {customer_code} on {trans_date}"
                    )
                    continue

                # Create delivery history record (keeping old columns for backward compatibility)
                history_data = {
                    "transaction_date": trans_date,
                    "transaction_time": (
                        str(row.get("交易時間", ""))
                        if pd.notna(row.get("交易時間"))
                        else None
                    ),
                    "salesperson": (
                        str(row.get("業務員", ""))
                        if pd.notna(row.get("業務員"))
                        else None
                    ),
                    "customer_id": customer.id,
                    "customer_code": customer_code,
                    "source_file": DELIVERY_FILE.name,
                    "source_sheet": sheet_name,
                }

                # Add old column values for backward compatibility
                for col_name, attrs in PRODUCT_MAPPING.items():
                    legacy_code = attrs["legacy_code"]
                    value = clean_numeric(row.get(col_name, 0)) or 0
                    if legacy_code.startswith("qty_"):
                        history_data[legacy_code] = int(value)
                    else:  # flow_
                        history_data[legacy_code] = float(value)

                # Calculate totals
                total_weight = 0
                total_cylinders = 0

                # Create the delivery history record
                new_history = DeliveryHistory(**history_data)
                session.add(new_history)
                await session.flush()  # Get the ID

                # Create delivery items for each product
                has_items = False
                for col_name, attrs in PRODUCT_MAPPING.items():
                    value = clean_numeric(row.get(col_name, 0))
                    if value and value > 0:
                        product = products_cache[col_name]

                        # Create delivery item
                        item = DeliveryHistoryItem(
                            delivery_history_id=new_history.id,
                            gas_product_id=product.id,
                            quantity=(
                                int(value)
                                if attrs["delivery_method"] == DeliveryMethod.CYLINDER
                                else 1
                            ),
                            unit_price=product.unit_price,  # Use current price, could be improved
                            is_flow_delivery=(
                                attrs["delivery_method"] == DeliveryMethod.FLOW
                            ),
                            flow_quantity=(
                                float(value)
                                if attrs["delivery_method"] == DeliveryMethod.FLOW
                                else None
                            ),
                            legacy_product_code=attrs["legacy_code"],
                        )
                        item.calculate_subtotal()
                        session.add(item)
                        has_items = True

                        # Update totals
                        if attrs["delivery_method"] == DeliveryMethod.CYLINDER:
                            total_cylinders += int(value)
                            total_weight += int(value) * attrs["size_kg"]
                        else:  # Flow
                            total_weight += float(value)

                # Update totals in delivery history
                new_history.total_weight_kg = total_weight
                new_history.total_cylinders = total_cylinders

                # Skip if no items
                if not has_items:
                    await session.rollback()
                    continue

                imported_count += 1

                # Commit every 100 records
                if imported_count % 100 == 0:
                    await session.commit()
                    logger.info(
                        f"Progress: {imported_count} delivery records imported from {sheet_name}"
                    )

            except Exception as e:
                logger.error(
                    f"Error processing delivery history at row {idx} in {sheet_name}: {e}"
                )
                await session.rollback()
                continue

        # Commit remaining records
        await session.commit()
        logger.info(f"Imported {imported_count} delivery records from {sheet_name}")
        total_imported += imported_count

    logger.info(f"Delivery history import complete: {total_imported} total records")
    return total_imported


async def main():
    """Main import function"""
    logger.info("Starting delivery history import with flexible product system...")

    # Create tables if they don't exist
    async with engine.begin() as conn:
        from app.core.database import Base

        await conn.run_sync(Base.metadata.create_all)

    # Import data
    async with async_session_maker() as session:
        try:
            # Import delivery history
            delivery_count = await import_delivery_history_v2(session)

            logger.info("\n" + "=" * 60)
            logger.info("IMPORT SUMMARY")
            logger.info("=" * 60)
            logger.info(f"Delivery History: {delivery_count} records imported")
            logger.info("=" * 60)

        except Exception as e:
            logger.error(f"Import failed: {e}")
            raise


if __name__ == "__main__":
    asyncio.run(main())
