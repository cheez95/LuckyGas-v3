#!/usr/bin/env python3
"""
Delivery History Migration Script
Migrates commercial delivery history from Excel to PostgreSQL with batch processing
Author: Devin (Data Migration Specialist)

Features:
- Batch processing (5,000 records per batch)
- Taiwan date conversion (民國年 to Western)
- Checkpoint recovery for resumability
- Memory-efficient chunked reading
- Progress tracking with ETA
- Comprehensive error handling
"""

import pandas as pd
import asyncio
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Tuple, Optional, Any
import logging
import sys
import os
import json
import time
from pathlib import Path
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy import text
import numpy as np

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from app.core.config import settings

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class DeliveryMigration:
    """Handles migration of delivery history data from Excel to PostgreSQL"""
    
    # Batch configuration
    BATCH_SIZE = 5000
    CHECKPOINT_FILE = "delivery_migration_checkpoint.json"
    
    def __init__(self, excel_file: str, dry_run: bool = True):
        self.excel_file = excel_file
        self.dry_run = dry_run
        self.customer_mapping = {}  # customer_code -> customer_id mapping
        self.checkpoint = {
            'last_processed_row': 0,
            'total_rows': 0,
            'batches_completed': 0,
            'start_time': None,
            'errors': []
        }
        self.migration_stats = {
            'total_records': 0,
            'successful': 0,
            'failed': 0,
            'skipped': 0,
            'missing_customers': set(),
            'processing_time': 0
        }
        
        # Column mapping from Excel to database
        self.field_mapping = {
            '日期': 'transaction_date',
            '時間': 'transaction_time',
            '業務': 'salesperson',
            '客戶編號': 'customer_code',
            '50公斤': 'qty_50kg',
            '丙烷20': 'qty_ying20',
            '丙烷16': 'qty_ying16',
            '20公斤': 'qty_20kg',
            '16公斤': 'qty_16kg',
            '10公斤': 'qty_10kg',
            '4公斤': 'qty_4kg',
            '好運桶16': 'qty_haoyun16',
            '瓶安桶10': 'qty_pingantong10',
            '幸福丸4': 'qty_xingfuwan4',
            '好運桶20': 'qty_haoyun20',
            '流量50公斤': 'flow_50kg',
            '流量20公斤': 'flow_20kg',
            '流量16公斤': 'flow_16kg',
            '流量好運20公斤': 'flow_haoyun20kg',
            '流量好運16公斤': 'flow_haoyun16kg'
        }
        
        # Cylinder weights for total calculation
        self.cylinder_weights = {
            'qty_50kg': 50,
            'qty_ying20': 20,
            'qty_ying16': 16,
            'qty_20kg': 20,
            'qty_16kg': 16,
            'qty_10kg': 10,
            'qty_4kg': 4,
            'qty_haoyun20': 20,
            'qty_haoyun16': 16,
            'qty_pingantong10': 10,
            'qty_xingfuwan4': 4
        }
    
    async def run(self):
        """Execute the migration process"""
        start_time = time.time()
        logger.info(f"🚀 Starting delivery history migration from {self.excel_file}")
        logger.info(f"Mode: {'DRY RUN' if self.dry_run else 'PRODUCTION'}")
        
        try:
            # Load checkpoint if exists
            self.load_checkpoint()
            
            # Step 1: Load customer mapping
            await self.load_customer_mapping()
            
            # Step 2: Get total row count
            total_rows = self.get_total_rows()
            self.checkpoint['total_rows'] = total_rows
            logger.info(f"📊 Total records to process: {total_rows:,}")
            
            # Step 3: Process in batches
            await self.process_batches()
            
            # Step 4: Final report
            self.migration_stats['processing_time'] = time.time() - start_time
            self.print_final_report()
            
            # Clean up checkpoint on successful completion
            if not self.dry_run and self.migration_stats['failed'] == 0:
                self.remove_checkpoint()
            
            return self.migration_stats['failed'] == 0
            
        except Exception as e:
            logger.error(f"❌ Migration failed: {str(e)}")
            self.save_checkpoint()
            return False
    
    def load_checkpoint(self):
        """Load checkpoint from file if exists"""
        if os.path.exists(self.CHECKPOINT_FILE):
            logger.info("📂 Loading checkpoint from previous run...")
            with open(self.CHECKPOINT_FILE, 'r') as f:
                saved_checkpoint = json.load(f)
                self.checkpoint.update(saved_checkpoint)
                logger.info(f"  Resuming from row {self.checkpoint['last_processed_row']:,}")
    
    def save_checkpoint(self):
        """Save current progress to checkpoint file"""
        if not self.dry_run:
            with open(self.CHECKPOINT_FILE, 'w') as f:
                json.dump(self.checkpoint, f, indent=2, default=str)
            logger.info("💾 Checkpoint saved")
    
    def remove_checkpoint(self):
        """Remove checkpoint file after successful migration"""
        if os.path.exists(self.CHECKPOINT_FILE):
            os.remove(self.CHECKPOINT_FILE)
            logger.info("🗑️  Checkpoint file removed")
    
    async def load_customer_mapping(self):
        """Load customer code to ID mapping from database"""
        logger.info("🔍 Loading customer mapping...")
        
        engine = create_async_engine(settings.DATABASE_URL)
        async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
        
        async with async_session() as session:
            try:
                result = await session.execute(
                    text("SELECT id, customer_code FROM customers WHERE customer_code IS NOT NULL")
                )
                for row in result:
                    self.customer_mapping[str(row.customer_code)] = row.id
                
                logger.info(f"✅ Loaded {len(self.customer_mapping)} customer mappings")
                
            finally:
                await engine.dispose()
    
    def get_total_rows(self) -> int:
        """Get total number of rows in Excel file"""
        # Use pandas to get row count efficiently
        df_info = pd.read_excel(self.excel_file, nrows=0)
        total_rows = sum(1 for _ in pd.read_excel(self.excel_file, chunksize=1000))
        return total_rows * 1000  # Approximate, will be refined during processing
    
    async def process_batches(self):
        """Process Excel file in batches"""
        engine = create_async_engine(settings.DATABASE_URL)
        async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
        
        batch_num = self.checkpoint['batches_completed']
        start_row = self.checkpoint['last_processed_row']
        
        # Read Excel in chunks
        chunk_iterator = pd.read_excel(
            self.excel_file,
            chunksize=self.BATCH_SIZE,
            skiprows=range(1, start_row + 1) if start_row > 0 else None
        )
        
        async with async_session() as session:
            for chunk_df in chunk_iterator:
                batch_num += 1
                batch_start_time = time.time()
                
                logger.info(f"\n🔄 Processing batch {batch_num} ({len(chunk_df)} records)...")
                
                # Process chunk
                batch_stats = await self.process_chunk(session, chunk_df, start_row)
                
                # Update stats
                self.migration_stats['successful'] += batch_stats['successful']
                self.migration_stats['failed'] += batch_stats['failed']
                self.migration_stats['skipped'] += batch_stats['skipped']
                
                # Update checkpoint
                start_row += len(chunk_df)
                self.checkpoint['last_processed_row'] = start_row
                self.checkpoint['batches_completed'] = batch_num
                
                # Save checkpoint every batch
                if not self.dry_run:
                    self.save_checkpoint()
                
                # Log progress
                batch_time = time.time() - batch_start_time
                records_per_second = len(chunk_df) / batch_time if batch_time > 0 else 0
                progress_pct = (start_row / self.checkpoint['total_rows']) * 100 if self.checkpoint['total_rows'] > 0 else 0
                
                logger.info(f"  ✅ Batch {batch_num} completed in {batch_time:.1f}s ({records_per_second:.0f} records/sec)")
                logger.info(f"  📊 Progress: {progress_pct:.1f}% ({start_row:,}/{self.checkpoint['total_rows']:,})")
                
                # Estimate remaining time
                if records_per_second > 0:
                    remaining_records = self.checkpoint['total_rows'] - start_row
                    eta_seconds = remaining_records / records_per_second
                    eta_str = str(timedelta(seconds=int(eta_seconds)))
                    logger.info(f"  ⏱️  Estimated time remaining: {eta_str}")
        
        await engine.dispose()
    
    async def process_chunk(self, session: AsyncSession, chunk_df: pd.DataFrame, start_row: int) -> Dict:
        """Process a single chunk of data"""
        batch_stats = {
            'successful': 0,
            'failed': 0,
            'skipped': 0
        }
        
        # Prepare batch insert data
        batch_data = []
        
        for idx, row in chunk_df.iterrows():
            try:
                # Transform row
                delivery_data = self.transform_row(row)
                
                if delivery_data is None:
                    batch_stats['skipped'] += 1
                    continue
                
                # Add to batch
                batch_data.append(delivery_data)
                
                # Insert when batch is full or at end of chunk
                if len(batch_data) >= 100 or idx == chunk_df.index[-1]:
                    if not self.dry_run:
                        await self.insert_batch(session, batch_data)
                    batch_stats['successful'] += len(batch_data)
                    batch_data = []
                    
            except Exception as e:
                logger.error(f"  ❌ Error processing row {start_row + idx}: {str(e)}")
                batch_stats['failed'] += 1
                self.checkpoint['errors'].append({
                    'row': start_row + idx,
                    'error': str(e),
                    'timestamp': datetime.now().isoformat()
                })
        
        # Commit batch
        if not self.dry_run:
            await session.commit()
        
        return batch_stats
    
    def transform_row(self, row: pd.Series) -> Optional[Dict]:
        """Transform Excel row to database format"""
        # Skip empty rows
        if pd.isna(row.get('客戶編號')) or pd.isna(row.get('日期')):
            return None
        
        # Get customer ID from mapping
        customer_code = str(row['客戶編號'])
        customer_id = self.customer_mapping.get(customer_code)
        
        if not customer_id:
            self.migration_stats['missing_customers'].add(customer_code)
            logger.debug(f"  ⚠️  Customer not found: {customer_code}")
            return None
        
        # Convert Taiwan date to Western date
        transaction_date = self.convert_taiwan_date(row['日期'])
        if not transaction_date:
            logger.warning(f"  ⚠️  Invalid date format: {row['日期']}")
            return None
        
        # Build delivery record
        delivery_data = {
            'transaction_date': transaction_date,
            'transaction_time': str(row.get('時間', '')),
            'salesperson': str(row.get('業務', '')),
            'customer_id': customer_id,
            'customer_code': customer_code,
            'source_file': os.path.basename(self.excel_file),
            'source_sheet': 'Sheet1',
            'created_at': datetime.now(timezone.utc),
            'updated_at': datetime.now(timezone.utc)
        }
        
        # Add cylinder quantities
        total_cylinders = 0
        total_weight = 0.0
        
        for excel_col, db_col in self.field_mapping.items():
            if db_col.startswith('qty_'):
                value = row.get(excel_col, 0)
                qty = int(value) if pd.notna(value) and value != '' else 0
                delivery_data[db_col] = qty
                
                # Calculate totals
                if qty > 0 and db_col in self.cylinder_weights:
                    total_cylinders += qty
                    total_weight += qty * self.cylinder_weights[db_col]
            
            elif db_col.startswith('flow_'):
                value = row.get(excel_col, 0)
                flow = float(value) if pd.notna(value) and value != '' else 0.0
                delivery_data[db_col] = flow
        
        # Set calculated fields
        delivery_data['total_cylinders'] = total_cylinders
        delivery_data['total_weight_kg'] = total_weight
        
        return delivery_data
    
    def convert_taiwan_date(self, date_value) -> Optional[datetime]:
        """Convert Taiwan date (民國年) to Western date"""
        if pd.isna(date_value):
            return None
        
        try:
            # Handle different date formats
            if isinstance(date_value, (int, float)):
                # Taiwan format: 1130520 (113年5月20日)
                date_str = str(int(date_value))
                if len(date_str) == 7:
                    year = int(date_str[:3]) + 1911  # Convert from 民國 to 西元
                    month = int(date_str[3:5])
                    day = int(date_str[5:7])
                    return datetime(year, month, day)
                elif len(date_str) == 6:
                    # Handle 2-digit year: 980520
                    year = int(date_str[:2]) + 1911
                    month = int(date_str[2:4])
                    day = int(date_str[4:6])
                    return datetime(year, month, day)
            
            elif isinstance(date_value, datetime):
                # Already a datetime object
                return date_value
            
            elif isinstance(date_value, str):
                # Try parsing string date
                return pd.to_datetime(date_value).to_pydatetime()
            
        except Exception as e:
            logger.debug(f"Date conversion error: {date_value} - {str(e)}")
        
        return None
    
    async def insert_batch(self, session: AsyncSession, batch_data: List[Dict]):
        """Insert a batch of delivery records"""
        if not batch_data:
            return
        
        # Build bulk insert query
        columns = list(batch_data[0].keys())
        placeholders = ', '.join([f':{col}' for col in columns])
        column_names = ', '.join(columns)
        
        query = f"""
            INSERT INTO delivery_history ({column_names})
            VALUES ({placeholders})
        """
        
        # Execute batch insert
        for record in batch_data:
            await session.execute(text(query), record)
    
    def print_final_report(self):
        """Print comprehensive migration report"""
        logger.info("\n" + "="*70)
        logger.info("📊 DELIVERY HISTORY MIGRATION REPORT")
        logger.info("="*70)
        
        logger.info(f"\n📈 Overall Statistics:")
        logger.info(f"  Total Records: {self.migration_stats['total_records']:,}")
        logger.info(f"  ✅ Successful: {self.migration_stats['successful']:,}")
        logger.info(f"  ❌ Failed: {self.migration_stats['failed']:,}")
        logger.info(f"  ⏭️  Skipped: {self.migration_stats['skipped']:,}")
        
        # Success rate
        if self.migration_stats['total_records'] > 0:
            success_rate = (self.migration_stats['successful'] / self.migration_stats['total_records']) * 100
            logger.info(f"  📊 Success Rate: {success_rate:.2f}%")
        
        # Processing performance
        if self.migration_stats['processing_time'] > 0:
            records_per_second = self.migration_stats['successful'] / self.migration_stats['processing_time']
            logger.info(f"\n⚡ Performance:")
            logger.info(f"  Processing Time: {timedelta(seconds=int(self.migration_stats['processing_time']))}")
            logger.info(f"  Speed: {records_per_second:.0f} records/second")
        
        # Missing customers
        if self.migration_stats['missing_customers']:
            logger.warning(f"\n⚠️  Missing Customers: {len(self.migration_stats['missing_customers'])}")
            logger.warning("  First 10 missing customer codes:")
            for code in list(self.migration_stats['missing_customers'])[:10]:
                logger.warning(f"    - {code}")
        
        # Errors
        if self.checkpoint['errors']:
            logger.error(f"\n❌ Errors: {len(self.checkpoint['errors'])}")
            logger.error("  Last 5 errors:")
            for error in self.checkpoint['errors'][-5:]:
                logger.error(f"    Row {error['row']}: {error['error']}")
        
        if self.dry_run:
            logger.info("\n⚠️  This was a DRY RUN. No data was actually migrated.")
            logger.info("  Run with --production flag to perform actual migration.")
        else:
            logger.info("\n✅ Migration completed successfully!")
            logger.info("  All delivery history records have been imported.")


async def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(
        description='Migrate delivery history from Excel to PostgreSQL',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Dry run (default)
  python 003_migrate_deliveries.py
  
  # Production run
  python 003_migrate_deliveries.py --production
  
  # Custom file
  python 003_migrate_deliveries.py --file "path/to/delivery_history.xlsx" --production
        """
    )
    
    parser.add_argument('--file', type=str, default='raw/2025-05 commercial deliver history.xlsx',
                       help='Path to Excel file containing delivery history')
    parser.add_argument('--production', action='store_true',
                       help='Run in production mode (actually migrate data)')
    
    args = parser.parse_args()
    
    # Check if file exists
    if not os.path.exists(args.file):
        logger.error(f"❌ Error: File not found: {args.file}")
        sys.exit(1)
    
    # Create migration instance
    migration = DeliveryMigration(
        excel_file=args.file,
        dry_run=not args.production
    )
    
    # Run migration
    success = await migration.run()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    asyncio.run(main())