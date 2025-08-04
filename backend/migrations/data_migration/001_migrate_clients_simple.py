#!/usr/bin/env python3
"""
Simplified Client Data Migration Script
Migrates commercial clients from Excel to PostgreSQL without rollback complexity
Author: Devin (Data Migration Specialist) - Simplified version
"""

import pandas as pd
import asyncio
from datetime import datetime, timezone
from typing import Dict, List
import logging
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy import text
import sys
import os

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from app.core.config import settings

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class SimpleClientMigration:
    """Simplified client data migration without rollback complexity"""
    
    def __init__(self, excel_file: str, dry_run: bool = True):
        self.excel_file = excel_file
        self.dry_run = dry_run
        self.excel_data = None
        self.validation_errors = []
        self.migration_stats = {
            'total_records': 0,
            'successful': 0,
            'failed': 0,
            'skipped': 0,
            'duplicates': 0
        }
        
        # Field mapping from Excel to Database
        self.field_mapping = {
            '客戶': 'customer_code_and_name',  # Contains both code and name
            '地址': 'address',
            '電子發票抬頭': 'invoice_title',
            '客戶簡稱': 'short_name',
            '區域': 'district',
            '類型': 'customer_category'
        }
    
    async def run(self):
        """Execute the migration process"""
        logger.info(f"🚀 Starting client migration from {self.excel_file}")
        logger.info(f"Mode: {'DRY RUN' if self.dry_run else 'PRODUCTION'}")
        
        try:
            # Step 1: Extract data
            self.extract_data()
            
            # Step 2: Validate data
            self.validate_data()
            
            # Step 3: Migrate to database
            await self.migrate_to_database()
            
            # Step 4: Print summary
            self.print_summary()
            
            return self.migration_stats['failed'] == 0
            
        except Exception as e:
            logger.error(f"❌ Migration failed: {str(e)}")
            return False
    
    def extract_data(self):
        """Extract data from Excel file"""
        logger.info("📊 Extracting data from Excel...")
        self.excel_data = pd.read_excel(self.excel_file)
        self.migration_stats['total_records'] = len(self.excel_data)
        logger.info(f"✅ Extracted {len(self.excel_data)} records")
    
    def validate_data(self):
        """Validate extracted data"""
        logger.info("🔍 Validating data...")
        
        # Check for required columns
        required_columns = ['客戶', '地址']
        missing_columns = [col for col in required_columns if col not in self.excel_data.columns]
        
        if missing_columns:
            raise ValueError(f"Missing required columns: {missing_columns}")
        
        # Extract customer codes from the '客戶' column
        self.excel_data['customer_code'] = self.excel_data['客戶'].astype(str).str.extract(r'^(\d+)')
        
        # Check for duplicate customer codes
        duplicates = self.excel_data[self.excel_data.duplicated(subset=['customer_code'], keep=False)]
        if not duplicates.empty:
            self.migration_stats['duplicates'] = len(duplicates)
            logger.warning(f"⚠️  Found {len(duplicates)} duplicate customer codes")
    
    async def migrate_to_database(self):
        """Migrate validated data to PostgreSQL"""
        logger.info("🚀 Starting database migration...")
        
        engine = create_async_engine(settings.DATABASE_URL)
        async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
        
        async with async_session() as session:
            try:
                # Get existing customer codes to avoid duplicates
                result = await session.execute(
                    text("SELECT customer_code FROM customers")
                )
                existing_codes = {row[0] for row in result}
                logger.info(f"Found {len(existing_codes)} existing customers")
                
                # Process each record
                for idx, row in self.excel_data.iterrows():
                    try:
                        customer_code = str(row['customer_code'])
                        
                        # Skip if already exists
                        if customer_code in existing_codes:
                            self.migration_stats['skipped'] += 1
                            logger.debug(f"Skipping existing customer: {customer_code}")
                            continue
                        
                        # Transform data
                        customer_data = self.transform_row(row)
                        
                        if not self.dry_run:
                            # Insert into database - using the actual table schema
                            await session.execute(
                                text("""
                                    INSERT INTO customers (
                                        customer_code, invoice_title, short_name, address,
                                        area, created_at, updated_at
                                    ) VALUES (
                                        :customer_code, :invoice_title, :short_name, :address,
                                        :area, :created_at, :updated_at
                                    )
                                """),
                                {
                                    'customer_code': customer_data['customer_code'],
                                    'invoice_title': customer_data['invoice_title'],
                                    'short_name': customer_data['short_name'],
                                    'address': customer_data['address'],
                                    'area': customer_data['district'],
                                    'created_at': customer_data['created_at'],
                                    'updated_at': customer_data['updated_at']
                                }
                            )
                        
                        self.migration_stats['successful'] += 1
                        
                        # Log progress every 100 records
                        if (idx + 1) % 100 == 0:
                            logger.info(f"Progress: {idx + 1}/{len(self.excel_data)}")
                            if not self.dry_run:
                                await session.commit()
                        
                    except Exception as e:
                        self.migration_stats['failed'] += 1
                        logger.error(f"Failed to migrate row {idx}: {str(e)}")
                        if not self.dry_run:
                            await session.rollback()
                
                # Final commit
                if not self.dry_run:
                    await session.commit()
                    logger.info("✅ All changes committed")
                
            finally:
                await engine.dispose()
    
    def transform_row(self, row: pd.Series) -> Dict:
        """Transform Excel row to database format"""
        # Extract customer name from the '客戶' column (remove the code part)
        full_customer = str(row['客戶'])
        # The customer name is after the code
        customer_name = full_customer.replace(str(row['customer_code']), '').strip()
        if not customer_name:
            customer_name = str(row.get('客戶簡稱', full_customer))
        
        # Determine city from address
        address = str(row.get('地址', ''))
        city = '臺東市'  # Default
        if '臺東縣' in address:
            city = '臺東縣'
        
        # Determine customer type based on '類型' column
        customer_type = 'commercial'  # Default
        if pd.notna(row.get('類型')):
            type_str = str(row.get('類型')).lower()
            if '學校' in type_str:
                customer_type = 'commercial'  # Schools are still commercial
            elif '住宅' in type_str or '家庭' in type_str:
                customer_type = 'residential'
        
        # Clean and transform data
        customer_data = {
            'customer_code': str(row['customer_code']),
            'short_name': customer_name,  # Using short_name field
            'customer_type': customer_type,
            'phone': '',  # Not in this Excel file
            'email': None,  # Not in Excel
            'address': address,
            'district': str(row.get('區域', '')) if pd.notna(row.get('區域')) else '',
            'city': city,
            'postal_code': None,  # Not in Excel
            'tax_id': None,  # Not in this Excel file
            'invoice_title': str(row.get('電子發票抬頭', '')) if pd.notna(row.get('電子發票抬頭')) else None,
            'contact_person': None,  # Not in Excel
            'is_active': True,
            'credit_limit': 50000.00,  # Default credit limit
            'balance': 0.00,
            'created_at': datetime.now(timezone.utc),
            'updated_at': datetime.now(timezone.utc)
        }
        
        return customer_data
    
    def clean_phone(self, phone: str) -> str:
        """Clean phone number format"""
        if not phone or phone == 'nan':
            return ''
        
        # Remove common separators
        phone = phone.replace('-', '').replace(' ', '').replace('(', '').replace(')', '')
        
        # Ensure it starts with 0
        if phone and not phone.startswith('0'):
            phone = '0' + phone
        
        return phone
    
    def print_summary(self):
        """Print migration summary"""
        logger.info("\n" + "="*60)
        logger.info("MIGRATION SUMMARY")
        logger.info("="*60)
        logger.info(f"Total Records: {self.migration_stats['total_records']}")
        logger.info(f"✅ Successful: {self.migration_stats['successful']}")
        logger.info(f"❌ Failed: {self.migration_stats['failed']}")
        logger.info(f"⏭️  Skipped (existing): {self.migration_stats['skipped']}")
        logger.info(f"⚠️  Duplicates in source: {self.migration_stats['duplicates']}")
        
        if self.dry_run:
            logger.info("\n⚠️  This was a DRY RUN. No data was actually migrated.")
            logger.info("To run in production mode, add --production flag")


async def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Migrate client data from Excel to PostgreSQL')
    parser.add_argument('--file', type=str, default='raw/2025-05 commercial client list.xlsx',
                       help='Path to Excel file')
    parser.add_argument('--production', action='store_true',
                       help='Run in production mode (actually migrate data)')
    
    args = parser.parse_args()
    
    # Check if file exists
    if not os.path.exists(args.file):
        logger.error(f"❌ Error: File not found: {args.file}")
        sys.exit(1)
    
    migration = SimpleClientMigration(
        excel_file=args.file,
        dry_run=not args.production
    )
    
    success = await migration.run()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    asyncio.run(main())