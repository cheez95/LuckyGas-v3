#!/usr/bin/env python
"""
Fix all table schemas to match the models
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

def fix_all_tables():
    """Fix all table schemas"""
    engine = create_engine(settings.DATABASE_URL)
    
    with engine.connect() as conn:
        # Fix customers table
        logger.info("=" * 60)
        logger.info("Fixing customers table...")
        
        result = conn.execute(text("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = 'customers'
        """))
        
        customer_columns = [row[0] for row in result]
        logger.info(f"Existing customer columns: {customer_columns}")
        
        # Add missing customer columns
        customer_fields = [
            ('customer_code', 'VARCHAR(20)'),
            ('invoice_title', 'VARCHAR(200)'),
            ('short_name', 'VARCHAR(100)'),
            ('cylinders_50kg', 'INTEGER DEFAULT 0'),
            ('cylinders_20kg', 'INTEGER DEFAULT 0'),
            ('cylinders_16kg', 'INTEGER DEFAULT 0'),
            ('cylinders_10kg', 'INTEGER DEFAULT 0'),
            ('area', 'VARCHAR(50)'),
            ('is_subscription', 'BOOLEAN DEFAULT FALSE'),
            ('is_active', 'BOOLEAN DEFAULT TRUE')
        ]
        
        for col_name, col_type in customer_fields:
            if col_name not in customer_columns:
                logger.info(f"Adding column {col_name}")
                try:
                    conn.execute(text(f"ALTER TABLE customers ADD COLUMN {col_name} {col_type}"))
                    conn.commit()
                    logger.info(f"✅ Added column {col_name}")
                except Exception as e:
                    logger.error(f"Failed to add column {col_name}: {e}")
                    conn.rollback()
        
        # Fix orders table
        logger.info("=" * 60)
        logger.info("Fixing orders table...")
        
        result = conn.execute(text("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = 'orders'
        """))
        
        order_columns = [row[0] for row in result]
        logger.info(f"Existing order columns: {order_columns}")
        
        # Add missing order columns
        order_fields = [
            ('order_number', 'VARCHAR(50)'),
            ('qty_50kg', 'INTEGER DEFAULT 0'),
            ('qty_20kg', 'INTEGER DEFAULT 0'),
            ('qty_16kg', 'INTEGER DEFAULT 0'),
            ('qty_10kg', 'INTEGER DEFAULT 0'),
            ('driver_id', 'INTEGER'),
            ('route_id', 'INTEGER'),
            ('order_date', 'DATE'),
            ('delivery_date', 'TIMESTAMP')
        ]
        
        for col_name, col_type in order_fields:
            if col_name not in order_columns:
                logger.info(f"Adding column {col_name}")
                try:
                    conn.execute(text(f"ALTER TABLE orders ADD COLUMN {col_name} {col_type}"))
                    conn.commit()
                    logger.info(f"✅ Added column {col_name}")
                except Exception as e:
                    logger.error(f"Failed to add column {col_name}: {e}")
                    conn.rollback()
        
        # Generate unique customer codes for existing customers without them
        logger.info("=" * 60)
        logger.info("Generating customer codes...")
        try:
            # Get customers without codes
            result = conn.execute(text("SELECT id FROM customers WHERE customer_code IS NULL OR customer_code = ''"))
            customers_without_code = result.fetchall()
            
            for customer in customers_without_code:
                customer_id = customer[0]
                customer_code = f"C{customer_id:05d}"
                conn.execute(text("UPDATE customers SET customer_code = :code WHERE id = :id"), 
                           {"code": customer_code, "id": customer_id})
            
            conn.commit()
            logger.info(f"✅ Generated codes for {len(customers_without_code)} customers")
        except Exception as e:
            logger.error(f"Failed to generate customer codes: {e}")
            conn.rollback()
        
        # Generate order numbers for existing orders
        logger.info("Generating order numbers...")
        try:
            result = conn.execute(text("SELECT id FROM orders WHERE order_number IS NULL OR order_number = ''"))
            orders_without_number = result.fetchall()
            
            for order in orders_without_number:
                order_id = order[0]
                order_number = f"ORD{order_id:06d}"
                conn.execute(text("UPDATE orders SET order_number = :number WHERE id = :id"), 
                           {"number": order_number, "id": order_id})
            
            conn.commit()
            logger.info(f"✅ Generated numbers for {len(orders_without_number)} orders")
        except Exception as e:
            logger.error(f"Failed to generate order numbers: {e}")
            conn.rollback()
        
        # Set default values for required fields
        logger.info("Setting default values...")
        try:
            # Set default short_name for customers
            conn.execute(text("UPDATE customers SET short_name = COALESCE(name, 'Customer') WHERE short_name IS NULL"))
            
            # Set default order_date from created_at
            conn.execute(text("UPDATE orders SET order_date = DATE(created_at) WHERE order_date IS NULL"))
            
            conn.commit()
            logger.info("✅ Set default values")
        except Exception as e:
            logger.error(f"Failed to set defaults: {e}")
            conn.rollback()
        
        logger.info("=" * 60)
        logger.info("Schema fix completed!")

if __name__ == "__main__":
    fix_all_tables()