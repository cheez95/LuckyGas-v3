#!/usr/bin/env python
"""
Fix orders table schema to match the model
"""

import os
import sys
from sqlalchemy import create_engine, text
import logging

# Add the parent directory to the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.core.config import settings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def fix_orders_table():
    """Add missing columns to orders table"""
    engine = create_engine(settings.DATABASE_URL)
    
    with engine.connect() as conn:
        # First check what columns exist
        result = conn.execute(text("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = 'orders'
        """))
        
        existing_columns = [row[0] for row in result]
        logger.info(f"Existing columns: {existing_columns}")
        
        # Add missing qty columns if they don't exist
        qty_columns = [
            ('qty_50kg', 'INTEGER DEFAULT 0'),
            ('qty_20kg', 'INTEGER DEFAULT 0'),
            ('qty_16kg', 'INTEGER DEFAULT 0'),
            ('qty_10kg', 'INTEGER DEFAULT 0')
        ]
        
        for col_name, col_type in qty_columns:
            if col_name not in existing_columns:
                logger.info(f"Adding column {col_name}")
                try:
                    conn.execute(text(f"ALTER TABLE orders ADD COLUMN {col_name} {col_type}"))
                    conn.commit()
                    logger.info(f"✅ Added column {col_name}")
                except Exception as e:
                    logger.error(f"Failed to add column {col_name}: {e}")
                    conn.rollback()
        
        # Check if order_date column exists, if not add it
        if 'order_date' not in existing_columns:
            logger.info("Adding order_date column")
            try:
                conn.execute(text("ALTER TABLE orders ADD COLUMN order_date DATE"))
                # Set default value from created_at
                conn.execute(text("UPDATE orders SET order_date = DATE(created_at) WHERE order_date IS NULL"))
                conn.commit()
                logger.info("✅ Added order_date column")
            except Exception as e:
                logger.error(f"Failed to add order_date: {e}")
                conn.rollback()
        
        # Check if delivery_date column exists
        if 'delivery_date' not in existing_columns:
            logger.info("Adding delivery_date column")
            try:
                conn.execute(text("ALTER TABLE orders ADD COLUMN delivery_date TIMESTAMP"))
                conn.commit()
                logger.info("✅ Added delivery_date column")
            except Exception as e:
                logger.error(f"Failed to add delivery_date: {e}")
                conn.rollback()
        
        # Check if driver_id column exists
        if 'driver_id' not in existing_columns:
            logger.info("Adding driver_id column")
            try:
                conn.execute(text("ALTER TABLE orders ADD COLUMN driver_id INTEGER"))
                conn.commit()
                logger.info("✅ Added driver_id column")
            except Exception as e:
                logger.error(f"Failed to add driver_id: {e}")
                conn.rollback()
        
        # Check if route_id column exists
        if 'route_id' not in existing_columns:
            logger.info("Adding route_id column")
            try:
                conn.execute(text("ALTER TABLE orders ADD COLUMN route_id INTEGER"))
                conn.commit()
                logger.info("✅ Added route_id column")
            except Exception as e:
                logger.error(f"Failed to add route_id: {e}")
                conn.rollback()
        
        logger.info("Schema fix completed!")

if __name__ == "__main__":
    fix_orders_table()