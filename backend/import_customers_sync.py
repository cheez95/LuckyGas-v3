#!/usr/bin/env python3
"""
Synchronous Customer Data Import Script
Imports customer data from Excel to production PostgreSQL database
"""

import pandas as pd
from datetime import datetime
import logging
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
import sys
import os
import argparse

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def import_customers(excel_file: str, database_url: str, dry_run: bool = False):
    """Import customers from Excel to database"""
    
    logger.info(f"📂 Reading Excel file: {excel_file}")
    df = pd.read_excel(excel_file)
    logger.info(f"✅ Found {len(df)} records in Excel")
    
    # Clean database URL (convert async to sync if needed)
    if database_url.startswith("postgresql+asyncpg://"):
        database_url = database_url.replace("postgresql+asyncpg://", "postgresql://")
    
    logger.info(f"🔌 Connecting to database...")
    engine = create_engine(database_url)
    Session = sessionmaker(bind=engine)
    
    stats = {
        'total': len(df),
        'imported': 0,
        'skipped': 0,
        'errors': 0
    }
    
    with Session() as session:
        # Check if customers table exists
        result = session.execute(text("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_name = 'customers'
            )
        """))
        if not result.scalar():
            logger.error("❌ Customers table does not exist!")
            return False
        
        # Process each customer
        for idx, row in df.iterrows():
            try:
                # Extract customer code from the '客戶' column (format: "1234 客戶名稱")
                customer_str = str(row.get('客戶', ''))
                if ' ' in customer_str:
                    code_part = customer_str.split(' ')[0]
                    name_part = ' '.join(customer_str.split(' ')[1:])
                else:
                    code_part = customer_str
                    name_part = customer_str
                
                # Check if customer already exists
                existing = session.execute(
                    text("SELECT id FROM customers WHERE customer_code = :code"),
                    {"code": code_part}
                ).first()
                
                if existing:
                    logger.debug(f"⏭️  Customer {code_part} already exists, skipping")
                    stats['skipped'] += 1
                    continue
                
                # Prepare customer data
                customer_data = {
                    'customer_code': code_part,
                    'short_name': str(row.get('客戶簡稱', name_part))[:100] if pd.notna(row.get('客戶簡稱')) else name_part[:100],
                    'invoice_title': str(row.get('電子發票抬頭', ''))[:200] if pd.notna(row.get('電子發票抬頭')) else None,
                    'address': str(row.get('地址', ''))[:500] if pd.notna(row.get('地址')) else '',
                    'phone': str(row.get('電話', ''))[:20] if pd.notna(row.get('電話')) else None,
                    'area': str(row.get('區域', ''))[:50] if pd.notna(row.get('區域')) else None,
                    'customer_type': 'COMMERCIAL',  # All customers in this file are commercial
                    'is_active': True,
                    'created_at': datetime.utcnow(),
                    'updated_at': datetime.utcnow()
                }
                
                if not dry_run:
                    # Insert customer
                    session.execute(text("""
                        INSERT INTO customers (
                            customer_code, short_name, invoice_title, address, 
                            phone, area, customer_type, is_active, 
                            created_at, updated_at
                        ) VALUES (
                            :customer_code, :short_name, :invoice_title, :address,
                            :phone, :area, :customer_type, :is_active,
                            :created_at, :updated_at
                        )
                    """), customer_data)
                    
                logger.info(f"✅ Imported customer: {code_part} - {name_part}")
                stats['imported'] += 1
                
            except Exception as e:
                logger.error(f"❌ Error importing row {idx}: {str(e)}")
                stats['errors'] += 1
                continue
        
        if not dry_run:
            session.commit()
            logger.info("💾 Changes committed to database")
        else:
            logger.info("🔍 DRY RUN - No changes made to database")
    
    # Print summary
    logger.info("\n" + "="*50)
    logger.info("📊 IMPORT SUMMARY")
    logger.info("="*50)
    logger.info(f"Total records: {stats['total']}")
    logger.info(f"Imported: {stats['imported']} ✅")
    logger.info(f"Skipped (existing): {stats['skipped']} ⏭️")
    logger.info(f"Errors: {stats['errors']} ❌")
    logger.info("="*50)
    
    return stats['errors'] == 0

def main():
    parser = argparse.ArgumentParser(description='Import customers from Excel to PostgreSQL')
    parser.add_argument('--file', required=True, help='Path to Excel file')
    parser.add_argument('--database-url', required=True, help='PostgreSQL database URL')
    parser.add_argument('--dry-run', action='store_true', help='Run without making changes')
    
    args = parser.parse_args()
    
    success = import_customers(args.file, args.database_url, args.dry_run)
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()