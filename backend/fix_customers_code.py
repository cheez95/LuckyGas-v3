#!/usr/bin/env python
"""
Fix the 'code' column constraint in customers table
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

def fix_code_column():
    """Fix the code column constraint"""
    engine = create_engine(settings.DATABASE_URL)
    
    with engine.connect() as conn:
        logger.info("Fixing customers table 'code' column...")
        
        try:
            # Option 1: Make the 'code' column nullable
            conn.execute(text("ALTER TABLE customers ALTER COLUMN code DROP NOT NULL"))
            conn.commit()
            logger.info("✅ Made 'code' column nullable")
        except Exception as e:
            logger.error(f"Failed to alter code column: {e}")
            conn.rollback()
            
            # Option 2: Set a default value for existing rows
            try:
                conn.execute(text("UPDATE customers SET code = customer_code WHERE code IS NULL"))
                conn.commit()
                logger.info("✅ Set default values for null codes")
            except Exception as e2:
                logger.error(f"Failed to update codes: {e2}")
                conn.rollback()
        
        # Also fix the 'name' column
        try:
            conn.execute(text("ALTER TABLE customers ALTER COLUMN name DROP NOT NULL"))
            conn.commit()
            logger.info("✅ Made 'name' column nullable")
        except Exception as e:
            logger.error(f"Failed to alter name column: {e}")
            conn.rollback()
            
            # Set default values
            try:
                conn.execute(text("UPDATE customers SET name = short_name WHERE name IS NULL"))
                conn.commit()
                logger.info("✅ Set default values for null names")
            except Exception as e2:
                logger.error(f"Failed to update names: {e2}")
                conn.rollback()
        
        # Fix the address column
        try:
            conn.execute(text("ALTER TABLE customers ALTER COLUMN address DROP NOT NULL"))
            conn.commit()
            logger.info("✅ Made 'address' column nullable")
        except Exception as e:
            logger.error(f"Failed to alter address column: {e}")
            conn.rollback()
        
        logger.info("Schema fix completed!")

if __name__ == "__main__":
    fix_code_column()