#!/usr/bin/env python
"""
Simple customer import script for May 2025 Excel Data
Focus on just importing customers to reach 1270 count
"""

import os
import sys
import pandas as pd
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def import_customers():
    """Import customer data from Excel to SQLite database"""
    
    # Database connection
    DATABASE_URL = "sqlite:///./local_luckygas.db"
    engine = create_engine(DATABASE_URL)
    
    # File path
    excel_file = "/Users/lgee258/Desktop/LuckyGas-v3/raw/2025-05 commercial client list.xlsx"
    
    if not os.path.exists(excel_file):
        logger.error(f"Excel file not found: {excel_file}")
        return
    
    logger.info(f"Reading Excel file: {excel_file}")
    
    try:
        # Read Excel file
        df = pd.read_excel(excel_file)
        logger.info(f"Found {len(df)} rows in Excel file")
        
        # Display column names
        logger.info(f"Columns in Excel: {df.columns.tolist()}")
        
        # Create customers table if it doesn't exist
        with engine.connect() as conn:
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS customers (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    customer_code TEXT UNIQUE NOT NULL,
                    invoice_title TEXT,
                    short_name TEXT,
                    address TEXT,
                    area TEXT,
                    phone TEXT,
                    cylinders_50kg INTEGER DEFAULT 0,
                    cylinders_20kg INTEGER DEFAULT 0,
                    cylinders_16kg INTEGER DEFAULT 0,
                    cylinders_10kg INTEGER DEFAULT 0,
                    cylinders_4kg INTEGER DEFAULT 0,
                    pricing_method TEXT,
                    payment_method TEXT,
                    is_equipment_purchased BOOLEAN DEFAULT FALSE,
                    is_terminated BOOLEAN DEFAULT FALSE,
                    customer_type TEXT DEFAULT 'commercial',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """))
            conn.commit()
            
            # Clear existing data (for clean import)
            conn.execute(text("DELETE FROM customers"))
            conn.commit()
            logger.info("Cleared existing customer data")
        
        # Import customers
        imported_count = 0
        with engine.connect() as conn:
            for index, row in df.iterrows():
                try:
                    # Get customer code (required field) - using '客戶' column
                    customer_code = str(row.get('客戶', '')).strip()
                    if not customer_code or customer_code == 'nan':
                        logger.warning(f"Row {index}: Missing customer code, skipping")
                        continue
                    
                    # Prepare data - using correct column names from Excel
                    invoice_title = str(row.get('電子發票抬頭', '')).strip() if pd.notna(row.get('電子發票抬頭')) else ''
                    short_name = str(row.get('客戶簡稱', '')).strip() if pd.notna(row.get('客戶簡稱')) else customer_code
                    address = str(row.get('地址', '')).strip() if pd.notna(row.get('地址')) else '待補充'
                    area = str(row.get('區域', '')).strip() if pd.notna(row.get('區域')) else ''
                    
                    # Get cylinder counts
                    cylinders_50kg = int(row.get('50KG', 0)) if pd.notna(row.get('50KG')) else 0
                    cylinders_20kg = int(row.get('20KG', 0)) if pd.notna(row.get('20KG')) else 0
                    cylinders_16kg = int(row.get('16KG', 0)) if pd.notna(row.get('16KG')) else 0
                    cylinders_10kg = int(row.get('10KG', 0)) if pd.notna(row.get('10KG')) else 0
                    cylinders_4kg = int(row.get('4KG', 0)) if pd.notna(row.get('4KG')) else 0
                    
                    # Other fields
                    pricing_method = str(row.get('計價方式', '')).strip() if pd.notna(row.get('計價方式')) else ''
                    payment_method = str(row.get('結帳方式', '')).strip() if pd.notna(row.get('結帳方式')) else ''
                    is_equipment_purchased = bool(row.get('設備客戶買斷')) if pd.notna(row.get('設備客戶買斷')) else False
                    is_terminated = bool(row.get('已解約')) if pd.notna(row.get('已解約')) else False
                    
                    # Generate phone number (placeholder - not in Excel)
                    phone = f"09{str(index).zfill(8)}"  # Placeholder Taiwan phone
                    
                    # Insert customer
                    conn.execute(text("""
                        INSERT INTO customers (
                            customer_code, invoice_title, short_name, address, area, phone,
                            cylinders_50kg, cylinders_20kg, cylinders_16kg, cylinders_10kg, cylinders_4kg,
                            pricing_method, payment_method, is_equipment_purchased, is_terminated,
                            customer_type
                        ) VALUES (
                            :customer_code, :invoice_title, :short_name, :address, :area, :phone,
                            :cylinders_50kg, :cylinders_20kg, :cylinders_16kg, :cylinders_10kg, :cylinders_4kg,
                            :pricing_method, :payment_method, :is_equipment_purchased, :is_terminated,
                            :customer_type
                        )
                    """), {
                        'customer_code': customer_code,
                        'invoice_title': invoice_title,
                        'short_name': short_name,
                        'address': address,
                        'area': area,
                        'phone': phone,
                        'cylinders_50kg': cylinders_50kg,
                        'cylinders_20kg': cylinders_20kg,
                        'cylinders_16kg': cylinders_16kg,
                        'cylinders_10kg': cylinders_10kg,
                        'cylinders_4kg': cylinders_4kg,
                        'pricing_method': pricing_method,
                        'payment_method': payment_method,
                        'is_equipment_purchased': is_equipment_purchased,
                        'is_terminated': is_terminated,
                        'customer_type': 'commercial'
                    })
                    
                    imported_count += 1
                    
                    if imported_count % 100 == 0:
                        conn.commit()
                        logger.info(f"Imported {imported_count} customers...")
                    
                except Exception as e:
                    logger.error(f"Error importing row {index}: {str(e)}")
                    continue
            
            # Final commit
            conn.commit()
        
        logger.info(f"✅ Successfully imported {imported_count} customers")
        
        # Verify the import
        with engine.connect() as conn:
            result = conn.execute(text("SELECT COUNT(*) FROM customers"))
            count = result.scalar()
            logger.info(f"✅ Total customers in database: {count}")
            
            if count == 1270:
                logger.info("✅ PERFECT! Exactly 1270 customers imported as expected!")
            elif count < 1270:
                logger.warning(f"⚠️ Only {count} customers imported, expected 1270")
            else:
                logger.info(f"✅ {count} customers imported (more than expected 1270)")
            
            # Show sample customers
            result = conn.execute(text("SELECT customer_code, short_name, address FROM customers LIMIT 5"))
            logger.info("\nSample customers:")
            for row in result:
                logger.info(f"  - {row[0]}: {row[1]} @ {row[2]}")
    
    except Exception as e:
        logger.error(f"Import failed: {str(e)}")
        raise

if __name__ == "__main__":
    import_customers()