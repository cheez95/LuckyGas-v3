#!/usr/bin/env python3
"""
Fixed Client Data Migration Script
Migrates commercial clients from Excel to PostgreSQL with corrected column mapping
Author: Sam (QA) - Fixing issues found during testing
"""

import pandas as pd
import asyncio
from datetime import datetime, timezone
from typing import Dict, List, Tuple, Optional
import logging
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy import text
import sys
import os

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from app.models.customer import Customer
from app.core.config import settings

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ClientMigration:
    """Handles migration of client data from Excel to PostgreSQL"""
    
    def __init__(self, excel_file: str, dry_run: bool = True):
        self.excel_file = excel_file
        self.dry_run = dry_run
        self.excel_data = None
        self.validation_errors = []
        self.migration_stats = {
            'total_records': 0,
            'successful': 0,
            'failed': 0,
            'skipped': 0
        }
        
        # CORRECTED Field mapping from Excel to Database (based on actual model)
        self.field_mapping = {
            '客戶': 'customer_code',
            '電子發票抬頭': 'invoice_title',
            '客戶簡稱': 'short_name',
            '地址': 'address',
            '50KG': 'cylinders_50kg',
            '20KG': 'cylinders_20kg', 
            '16KG': 'cylinders_16kg',
            '10KG': 'cylinders_10kg',
            '4KG': 'cylinders_4kg',
            '營20': 'cylinders_ying20',
            '營16': 'cylinders_ying16',
            '好運20': 'cylinders_haoyun20',
            '好運16': 'cylinders_haoyun16',
            '計價方式': 'pricing_method',
            '結帳方式': 'payment_method',
            '訂閱式會員': 'is_subscription',
            '需要當天配送': 'needs_same_day_delivery',
            '公休日': 'closed_days',
            '區域': 'area',
            '類型': 'customer_type',
            '已解約': 'is_terminated',
            '月配送量': 'monthly_delivery_volume',
            '平均日使用': 'avg_daily_usage',
            '最大週期': 'max_cycle_days',
            '可延後天數': 'can_delay_days',
            '切替器型號': 'regulator_model',
            '流量表': 'has_flow_meter',
            '帶線流量錶': 'has_wired_flow_meter',
            '切替器': 'has_regulator',
            '接點式壓力錶': 'has_pressure_gauge',
            '壓差開關': 'has_pressure_switch',
            '微動開關': 'has_micro_switch',
            '智慧秤': 'has_smart_scale',
            '發報': 'needs_report',
            '排巡': 'needs_patrol',
            '設備客戶買斷': 'is_equipment_purchased'
        }
        
        # Time slot mapping to delivery preferences
        self.time_slots = {
            '8~9': '08:00-09:00',
            '9~10': '09:00-10:00',
            '10~11': '10:00-11:00',
            '11~12': '11:00-12:00',
            '12~13': '12:00-13:00',
            '13~14': '13:00-14:00',
            '14~15': '14:00-15:00',
            '15~16': '15:00-16:00',
            '16~17': '16:00-17:00',
            '17~18': '17:00-18:00',
            '18~19': '18:00-19:00',
            '19~20': '19:00-20:00'
        }
        
    async def run(self):
        """Execute the migration process"""
        logger.info(f"Starting client migration from {self.excel_file}")
        logger.info(f"Mode: {'DRY RUN' if self.dry_run else 'PRODUCTION'}")
        
        try:
            # Step 1: Extract
            self.extract()
            
            # Step 2: Validate
            if not self.validate_data():
                logger.error("Validation failed. Aborting migration.")
                return False
            
            # Step 3: Transform and Load
            await self.transform_and_load()
            
            # Step 4: Report
            self.print_report()
            
            return self.migration_stats['failed'] == 0
            
        except Exception as e:
            logger.error(f"Migration failed: {str(e)}")
            return False
    
    def extract(self):
        """Extract data from Excel file"""
        logger.info("Extracting data from Excel...")
        self.excel_data = pd.read_excel(self.excel_file)
        self.migration_stats['total_records'] = len(self.excel_data)
        logger.info(f"Extracted {len(self.excel_data)} records")
        
    def validate_data(self) -> bool:
        """Validate extracted data"""
        logger.info("Validating data...")
        
        # Check required columns
        required_columns = ['客戶', '地址']
        missing_columns = [col for col in required_columns if col not in self.excel_data.columns]
        
        if missing_columns:
            self.validation_errors.append(f"Missing required columns: {missing_columns}")
            return False
        
        # Check for duplicate client codes
        duplicates = self.excel_data[self.excel_data.duplicated(subset=['客戶'], keep=False)]
        if len(duplicates) > 0:
            logger.warning(f"Found {len(duplicates)} duplicate client codes")
            
        # Validate client codes format
        invalid_codes = self.excel_data[~self.excel_data['客戶'].astype(str).str.match(r'^\d{7}$')]
        if len(invalid_codes) > 0:
            logger.warning(f"Found {len(invalid_codes)} invalid client codes")
            
        return len(self.validation_errors) == 0
    
    async def transform_and_load(self):
        """Transform and load data into database"""
        engine = create_async_engine(settings.DATABASE_URL)
        async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
        
        async with async_session() as session:
            try:
                if not self.dry_run:
                    await session.execute(text("BEGIN"))
                
                for index, row in self.excel_data.iterrows():
                    try:
                        customer_data = self.transform_row(row)
                        
                        if self.dry_run:
                            logger.debug(f"Would insert: {customer_data['short_name']} ({customer_data['customer_code']})")
                        else:
                            # Check if customer exists
                            existing = await session.execute(
                                text("SELECT id FROM customers WHERE customer_code = :code"),
                                {"code": customer_data['customer_code']}
                            )
                            if existing.scalar():
                                logger.info(f"Skipping existing customer: {customer_data['customer_code']}")
                                self.migration_stats['skipped'] += 1
                                continue
                            
                            # Insert new customer
                            await self.insert_customer(session, customer_data)
                            
                        self.migration_stats['successful'] += 1
                        
                        # Commit in batches
                        if not self.dry_run and (index + 1) % 100 == 0:
                            await session.commit()
                            logger.info(f"Processed {index + 1} records...")
                            
                    except Exception as e:
                        logger.error(f"Failed to process row {index}: {str(e)}")
                        self.migration_stats['failed'] += 1
                        if not self.dry_run:
                            await session.rollback()
                
                if not self.dry_run:
                    await session.commit()
                    
            finally:
                await engine.dispose()
    
    def transform_row(self, row: pd.Series) -> Dict:
        """Transform Excel row to database format"""
        # Basic customer data
        customer_data = {
            'customer_code': str(row['客戶']),
            'invoice_title': row.get('電子發票抬頭', ''),
            'short_name': row.get('客戶簡稱', row.get('電子發票抬頭', '')),
            'address': row.get('地址', ''),
            'created_at': datetime.now(timezone.utc),
            'updated_at': datetime.now(timezone.utc)
        }
        
        # Add cylinder quantities
        cylinder_fields = {
            '50KG': 'cylinders_50kg',
            '20KG': 'cylinders_20kg',
            '16KG': 'cylinders_16kg',
            '10KG': 'cylinders_10kg',
            '4KG': 'cylinders_4kg',
            '營20': 'cylinders_ying20',
            '營16': 'cylinders_ying16',
            '好運20': 'cylinders_haoyun20',
            '好運16': 'cylinders_haoyun16'
        }
        
        for excel_field, db_field in cylinder_fields.items():
            value = row.get(excel_field, 0)
            customer_data[db_field] = int(value) if pd.notna(value) else 0
        
        # Add string fields
        string_fields = {
            '計價方式': 'pricing_method',
            '結帳方式': 'payment_method',
            '類型': 'customer_type',
            '區域': 'area',
            '公休日': 'closed_days',
            '切替器型號': 'regulator_model'
        }
        
        for excel_field, db_field in string_fields.items():
            value = row.get(excel_field)
            if pd.notna(value):
                customer_data[db_field] = str(value)
        
        # Add boolean fields
        bool_fields = {
            '訂閱式會員': 'is_subscription',
            '需要當天配送': 'needs_same_day_delivery',
            '已解約': 'is_terminated',
            '流量表': 'has_flow_meter',
            '帶線流量錶': 'has_wired_flow_meter',
            '切替器': 'has_regulator',
            '接點式壓力錶': 'has_pressure_gauge',
            '壓差開關': 'has_pressure_switch',
            '微動開關': 'has_micro_switch',
            '智慧秤': 'has_smart_scale',
            '發報': 'needs_report',
            '排巡': 'needs_patrol',
            '設備客戶買斷': 'is_equipment_purchased'
        }
        
        for excel_field, db_field in bool_fields.items():
            value = row.get(excel_field, 0)
            customer_data[db_field] = bool(value) if pd.notna(value) else False
        
        # Add numeric fields
        numeric_fields = {
            '月配送量': 'monthly_delivery_volume',
            '平均日使用': 'avg_daily_usage',
            '最大週期': 'max_cycle_days',
            '可延後天數': 'can_delay_days'
        }
        
        for excel_field, db_field in numeric_fields.items():
            value = row.get(excel_field)
            if pd.notna(value):
                try:
                    if db_field in ['max_cycle_days', 'can_delay_days']:
                        customer_data[db_field] = int(float(value))
                    else:
                        customer_data[db_field] = float(value)
                except Exception:
                    pass
        
        # Process delivery time preferences
        time_preferences = []
        time_slot_value = row.get('時段早1午2晚3全天0')
        if pd.notna(time_slot_value):
            customer_data['delivery_time_slot'] = int(time_slot_value)
        
        # Find the preferred time slot
        for time_slot in self.time_slots.keys():
            if row.get(time_slot, 0):
                time_range = self.time_slots[time_slot]
                customer_data['delivery_time_start'] = time_range.split('-')[0]
                customer_data['delivery_time_end'] = time_range.split('-')[1]
                break
        
        # Delivery type
        delivery_type_value = row.get('1汽車/2機車/0全部')
        if pd.notna(delivery_type_value):
            customer_data['delivery_type'] = int(delivery_type_value)
        
        return customer_data
    
    async def insert_customer(self, session: AsyncSession, customer_data: Dict):
        """Insert customer into database"""
        columns = ', '.join(customer_data.keys())
        placeholders = ', '.join([f':{key}' for key in customer_data.keys()])
        
        query = f"""
            INSERT INTO customers ({columns})
            VALUES ({placeholders})
        """
        
        await session.execute(text(query), customer_data)
    
    def print_report(self):
        """Print migration report"""
        logger.info("\n" + "="*50)
        logger.info("MIGRATION REPORT")
        logger.info("="*50)
        logger.info(f"Total Records: {self.migration_stats['total_records']}")
        logger.info(f"Successful: {self.migration_stats['successful']}")
        logger.info(f"Failed: {self.migration_stats['failed']}")
        logger.info(f"Skipped: {self.migration_stats['skipped']}")
        
        if self.validation_errors:
            logger.warning("\nValidation Errors:")
            for error in self.validation_errors:
                logger.warning(f"  - {error}")
        
        if self.dry_run:
            logger.info("\n⚠️  This was a DRY RUN. No data was actually migrated.")
        else:
            logger.info("\n✅ Migration completed successfully!")


async def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Migrate client data from Excel to PostgreSQL')
    parser.add_argument('--file', type=str, default='raw/2025-05 commercial client list.xlsx',
                       help='Path to Excel file')
    parser.add_argument('--production', action='store_true',
                       help='Run in production mode (actually migrate data)')
    
    args = parser.parse_args()
    
    migration = ClientMigration(
        excel_file=args.file,
        dry_run=not args.production
    )
    
    success = await migration.run()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    asyncio.run(main())