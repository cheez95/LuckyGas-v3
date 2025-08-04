#!/usr/bin/env python3
"""
Client Data Migration Script
Migrates commercial clients from Excel to PostgreSQL
Author: Devin (Data Migration Specialist)
Updated: Added comprehensive rollback support
"""

import pandas as pd
import asyncio
from datetime import datetime
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
from rollback_manager import RollbackManager, MigrationTransaction, RollbackType

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ClientMigration:
    """Handles migration of client data from Excel to PostgreSQL"""
    
    def __init__(self, excel_file: str, dry_run: bool = True, enable_rollback: bool = True):
        self.excel_file = excel_file
        self.dry_run = dry_run
        self.enable_rollback = enable_rollback
        self.excel_data = None
        self.validation_errors = []
        self.rollback_manager = RollbackManager(settings.DATABASE_URL) if enable_rollback else None
        self.migration_id = f"client_migration_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"
        self.failed_records = []
        self.migration_stats = {
            'total_records': 0,
            'successful': 0,
            'failed': 0,
            'skipped': 0
        }
        
        # Field mapping from Excel to Database
        self.field_mapping = {
            '客戶': 'client_code',
            '電子發票抬頭': 'invoice_title',
            '客戶簡稱': 'name',  # Using short name as display name
            '地址': 'address',
            '系統上鋼瓶數量': 'total_cylinders',
            '50KG': 'cylinder_qty_50kg',
            '20KG': 'cylinder_qty_20kg', 
            '16KG': 'cylinder_qty_16kg',
            '10KG': 'cylinder_qty_10kg',
            '4KG': 'cylinder_qty_4kg',
            '計價方式': 'pricing_method',
            '結帳方式': 'payment_terms',
            '訂閱式會員': 'is_subscription_member',
            '需要當天配送': 'requires_same_day_delivery',
            '公休日': 'closed_days',
            '區域': 'delivery_area',
            '類型': 'business_type',
            '已解約': 'is_terminated',
            '月配送量': 'monthly_volume',
            '平均日使用': 'avg_daily_usage',
            '最大週期': 'max_delivery_cycle_days',
            '可延後天數': 'delivery_delay_tolerance'
        }
        
        # Time slot mapping
        self.time_slots = {
            '8~9': 'slot_08_09',
            '9~10': 'slot_09_10',
            '10~11': 'slot_10_11',
            '11~12': 'slot_11_12',
            '12~13': 'slot_12_13',
            '13~14': 'slot_13_14',
            '14~15': 'slot_14_15',
            '15~16': 'slot_15_16',
            '16~17': 'slot_16_17',
            '17~18': 'slot_17_18',
            '18~19': 'slot_18_19',
            '19~20': 'slot_19_20'
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
        if self.enable_rollback and not self.dry_run:
            # Use rollback-enabled transaction
            await self._transform_and_load_with_rollback()
        else:
            # Original implementation without rollback
            await self._transform_and_load_basic()
    
    async def _transform_and_load_with_rollback(self):
        """Transform and load with rollback support"""
        try:
            async with MigrationTransaction(
                self.rollback_manager,
                migration_id=self.migration_id,
                table_name="customers",
                description=f"Commercial client migration from {os.path.basename(self.excel_file)}"
            ) as session:
                await self._process_records(session)
                
                # If we had failures, decide whether to rollback
                if self.migration_stats['failed'] > 0:
                    failure_rate = self.migration_stats['failed'] / self.migration_stats['total_records']
                    if failure_rate > 0.1:  # More than 10% failure
                        raise Exception(f"High failure rate: {failure_rate:.1%}. Triggering rollback.")
                
        except Exception as e:
            logger.error(f"Migration failed with rollback: {str(e)}")
            # Rollback is automatic with MigrationTransaction
            raise
    
    async def _transform_and_load_basic(self):
        """Original transform and load implementation"""
        engine = create_async_engine(settings.DATABASE_URL)
        async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
        
        async with async_session() as session:
            try:
                if not self.dry_run:
                    await session.execute(text("BEGIN"))
                
                await self._process_records(session)
                
                if not self.dry_run:
                    await session.commit()
                    
            except Exception as e:
                if not self.dry_run:
                    await session.rollback()
                raise
            finally:
                await engine.dispose()
    
    async def _process_records(self, session: AsyncSession):
        """Process individual records"""
        for index, row in self.excel_data.iterrows():
            try:
                customer_data = self.transform_row(row)
                
                if self.dry_run:
                    logger.debug(f"Would insert: {customer_data['name']} ({customer_data['client_code']})")
                else:
                    # Check if customer exists
                    existing = await session.execute(
                        text("SELECT id FROM customers WHERE client_code = :code"),
                        {"code": customer_data['client_code']}
                    )
                    if existing.scalar():
                        logger.info(f"Skipping existing customer: {customer_data['client_code']}")
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
                self.failed_records.append({
                    'index': index,
                    'client_code': row.get('客戶', 'Unknown'),
                    'error': str(e)
                })
                # Don't rollback individual failures, continue processing
    
    def transform_row(self, row: pd.Series) -> Dict:
        """Transform Excel row to database format"""
        customer_data = {
            'client_code': str(row['客戶']),
            'invoice_title': row.get('電子發票抬頭', ''),
            'name': row.get('客戶簡稱', row.get('電子發票抬頭', '')),
            'address': row.get('地址', ''),
            'is_corporate': True,  # All commercial clients
            'is_active': not bool(row.get('已解約', 0)),
            'created_at': datetime.utcnow(),
            'updated_at': datetime.utcnow()
        }
        
        # Add cylinder quantities
        cylinder_fields = {
            '50KG': 'cylinder_qty_50kg',
            '20KG': 'cylinder_qty_20kg',
            '16KG': 'cylinder_qty_16kg',
            '10KG': 'cylinder_qty_10kg',
            '4KG': 'cylinder_qty_4kg'
        }
        
        for excel_field, db_field in cylinder_fields.items():
            value = row.get(excel_field, 0)
            customer_data[db_field] = int(value) if pd.notna(value) else 0
        
        # Add business fields
        business_fields = {
            '計價方式': 'pricing_type',
            '結帳方式': 'payment_terms',
            '類型': 'business_type',
            '區域': 'delivery_area'
        }
        
        for excel_field, db_field in business_fields.items():
            value = row.get(excel_field)
            if pd.notna(value):
                customer_data[db_field] = str(value)
        
        # Add boolean fields
        bool_fields = {
            '訂閱式會員': 'is_subscription',
            '需要當天配送': 'requires_same_day_delivery'
        }
        
        for excel_field, db_field in bool_fields.items():
            value = row.get(excel_field, 0)
            customer_data[db_field] = bool(value) if pd.notna(value) else False
        
        # Add numeric fields
        numeric_fields = {
            '月配送量': 'monthly_volume',
            '平均日使用': 'avg_daily_usage',
            '最大週期': 'max_delivery_cycle_days',
            '可延後天數': 'delivery_delay_tolerance'
        }
        
        for excel_field, db_field in numeric_fields.items():
            value = row.get(excel_field)
            if pd.notna(value):
                try:
                    customer_data[db_field] = float(value)
                except:
                    pass
        
        # Process delivery time preferences
        time_preferences = []
        for time_slot, db_field in self.time_slots.items():
            if row.get(time_slot, 0):
                time_preferences.append(time_slot.replace('~', '-'))
        
        if time_preferences:
            customer_data['preferred_delivery_times'] = ','.join(time_preferences)
        
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
        logger.info(f"Migration ID: {self.migration_id}")
        logger.info(f"Total Records: {self.migration_stats['total_records']}")
        logger.info(f"Successful: {self.migration_stats['successful']}")
        logger.info(f"Failed: {self.migration_stats['failed']}")
        logger.info(f"Skipped: {self.migration_stats['skipped']}")
        
        if self.validation_errors:
            logger.warning("\nValidation Errors:")
            for error in self.validation_errors:
                logger.warning(f"  - {error}")
        
        if self.failed_records:
            logger.warning("\nFailed Records:")
            for record in self.failed_records[:10]:  # Show first 10
                logger.warning(f"  - Row {record['index']}: {record['client_code']} - {record['error']}")
            if len(self.failed_records) > 10:
                logger.warning(f"  ... and {len(self.failed_records) - 10} more")
        
        if self.rollback_manager and not self.dry_run:
            logger.info("\nRollback Information:")
            history = self.rollback_manager.get_rollback_history()
            for item in history:
                logger.info(f"  - Rollback Point: {item['rollback_id']}")
                logger.info(f"    Status: {item['status']}")
        
        if self.dry_run:
            logger.info("\n⚠️  This was a DRY RUN. No data was actually migrated.")
        else:
            logger.info("\n✅ Migration completed successfully!")
    
    async def rollback_migration(self, rollback_id: Optional[str] = None):
        """Manually trigger rollback of migration"""
        if not self.rollback_manager:
            logger.error("Rollback manager not enabled for this migration")
            return False
        
        # Get latest rollback point if not specified
        if not rollback_id:
            history = self.rollback_manager.get_rollback_history()
            if not history:
                logger.error("No rollback points available")
                return False
            rollback_id = history[0]['rollback_id']
        
        try:
            logger.info(f"Executing rollback for: {rollback_id}")
            result = await self.rollback_manager.execute_rollback(
                rollback_id, RollbackType.FULL
            )
            
            # Verify rollback
            verification = await self.rollback_manager.verify_rollback(rollback_id)
            
            logger.info(f"Rollback completed: {result}")
            logger.info(f"Verification: {verification}")
            
            return verification['status'] == 'verified'
            
        except Exception as e:
            logger.error(f"Rollback failed: {str(e)}")
            return False


async def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Migrate client data from Excel to PostgreSQL')
    parser.add_argument('--file', type=str, default='raw/2025-05 commercial client list.xlsx',
                       help='Path to Excel file')
    parser.add_argument('--production', action='store_true',
                       help='Run in production mode (actually migrate data)')
    parser.add_argument('--no-rollback', action='store_true',
                       help='Disable rollback functionality')
    parser.add_argument('--rollback', type=str, metavar='ROLLBACK_ID',
                       help='Execute rollback for specified rollback ID')
    
    args = parser.parse_args()
    
    migration = ClientMigration(
        excel_file=args.file,
        dry_run=not args.production,
        enable_rollback=not args.no_rollback
    )
    
    # If rollback requested, execute rollback instead of migration
    if args.rollback:
        success = await migration.rollback_migration(args.rollback)
    else:
        success = await migration.run()
    
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    asyncio.run(main())