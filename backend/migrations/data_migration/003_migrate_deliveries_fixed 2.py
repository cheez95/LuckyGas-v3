#!/usr/bin/env python3
"""
Fixed Delivery History Migration Script
Migrates delivery records from Excel to PostgreSQL with batch processing
Author: Devin (Data Migration Specialist) - Fixed by BMad Master
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
import time
import json
from pathlib import Path

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from app.core.config import settings
from migrations.data_migration.utils.taiwan_date_converter import TaiwanDateConverter

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class DeliveryMigration:
    """Handles migration of delivery history data from Excel to PostgreSQL"""
    
    BATCH_SIZE = 5000
    CHECKPOINT_FILE = 'delivery_migration_checkpoint.json'
    
    def __init__(self, excel_file: str, dry_run: bool = True):
        self.excel_file = excel_file
        self.dry_run = dry_run
        self.date_converter = TaiwanDateConverter()
        self.customer_mapping = {}  # customer_code -> customer_id
        self.checkpoint = self.load_checkpoint()
        self.migration_stats = {
            'total_records': 0,
            'successful': 0,
            'failed': 0,
            'skipped': 0,
            'missing_customers': set(),
            'start_time': time.time()
        }
        
    def load_checkpoint(self) -> Dict:
        """Load checkpoint from file if exists"""
        if os.path.exists(self.CHECKPOINT_FILE):
            try:
                with open(self.CHECKPOINT_FILE, 'r') as f:
                    checkpoint = json.load(f)
                    logger.info(f"♻️  Resuming from checkpoint: {checkpoint['last_processed_row']} rows processed")
                    return checkpoint
            except Exception as e:
                logger.warning(f"⚠️  Could not load checkpoint: {str(e)}")
        
        return {
            'last_processed_row': 0,
            'batches_completed': 0,
            'errors': [],
            'created_at': datetime.now().isoformat()
        }
    
    def save_checkpoint(self):
        """Save current progress to checkpoint file"""
        if not self.dry_run:
            with open(self.CHECKPOINT_FILE, 'w') as f:
                json.dump(self.checkpoint, f, indent=2)
    
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
    
    async def run(self):
        """Execute the migration process"""
        logger.info(f"🚀 Starting delivery history migration from {self.excel_file}")
        logger.info(f"Mode: {'DRY RUN' if self.dry_run else 'PRODUCTION'}")
        
        try:
            # Load customer mapping first
            await self.load_customer_mapping()
            
            # Process the file in batches
            await self.process_batches()
            
            # Clean up checkpoint if successful
            if not self.dry_run and self.migration_stats['failed'] == 0:
                if os.path.exists(self.CHECKPOINT_FILE):
                    os.remove(self.CHECKPOINT_FILE)
                    logger.info("✅ Checkpoint file removed after successful migration")
            
            # Print final report
            self.print_report()
            
            return self.migration_stats['failed'] == 0
            
        except Exception as e:
            logger.error(f"❌ Migration failed: {str(e)}")
            return False
    
    async def process_batches(self):
        """Process Excel file in batches"""
        engine = create_async_engine(settings.DATABASE_URL)
        async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
        
        # First, get total rows for progress tracking
        logger.info("📊 Loading data file...")
        df = pd.read_excel(self.excel_file)
        total_rows = len(df)
        self.migration_stats['total_records'] = total_rows
        logger.info(f"📊 Total rows to process: {total_rows:,}")
        
        # Calculate batches
        total_batches = (total_rows + self.BATCH_SIZE - 1) // self.BATCH_SIZE
        
        # Resume from checkpoint
        start_row = self.checkpoint['last_processed_row']
        batch_num = self.checkpoint['batches_completed']
        
        # Process in batches
        for i in range(start_row, total_rows, self.BATCH_SIZE):
            end_row = min(i + self.BATCH_SIZE, total_rows)
            batch_df = df.iloc[i:end_row]
            batch_num += 1
            
            logger.info(f"\n🔄 Processing batch {batch_num}/{total_batches} (rows {i+1}-{end_row})...")
            batch_start_time = time.time()
            
            async with async_session() as session:
                try:
                    # Process this batch
                    batch_stats = await self.process_batch(session, batch_df, i)
                    
                    # Update stats
                    self.migration_stats['successful'] += batch_stats['successful']
                    self.migration_stats['failed'] += batch_stats['failed']
                    self.migration_stats['skipped'] += batch_stats['skipped']
                    
                    # Update checkpoint
                    self.checkpoint['last_processed_row'] = end_row
                    self.checkpoint['batches_completed'] = batch_num
                    self.save_checkpoint()
                    
                    # Calculate and display progress
                    batch_time = time.time() - batch_start_time
                    records_per_second = len(batch_df) / batch_time
                    progress = (end_row / total_rows) * 100
                    eta_seconds = (total_rows - end_row) / records_per_second if records_per_second > 0 else 0
                    
                    logger.info(f"  ✅ Batch complete: {batch_stats['successful']} successful, "
                              f"{batch_stats['failed']} failed, {batch_stats['skipped']} skipped")
                    logger.info(f"  📊 Progress: {progress:.1f}% | Speed: {records_per_second:.0f} rec/s | "
                              f"ETA: {int(eta_seconds // 60)}m {int(eta_seconds % 60)}s")
                    
                except Exception as e:
                    logger.error(f"❌ Batch {batch_num} failed: {str(e)}")
                    if not self.dry_run:
                        await session.rollback()
                finally:
                    await engine.dispose()
    
    async def process_batch(self, session: AsyncSession, batch_df: pd.DataFrame, start_row: int) -> Dict:
        """Process a single batch of records"""
        batch_stats = {
            'successful': 0,
            'failed': 0,
            'skipped': 0
        }
        
        batch_data = []
        
        for idx, row in batch_df.iterrows():
            try:
                # Transform row
                delivery_data = self.transform_row(row)
                
                if delivery_data is None:
                    batch_stats['skipped'] += 1
                    continue
                
                # Add to batch
                batch_data.append(delivery_data)
                
                # Insert when batch is full
                if len(batch_data) >= 100:
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
        
        # Insert remaining data
        if batch_data:
            if not self.dry_run:
                await self.insert_batch(session, batch_data)
            batch_stats['successful'] += len(batch_data)
        
        # Commit batch
        if not self.dry_run:
            await session.commit()
        
        return batch_stats
    
    def transform_row(self, row: pd.Series) -> Optional[Dict]:
        """Transform Excel row to database format"""
        # Skip empty rows
        if pd.isna(row.get('客戶')) or pd.isna(row.get('最後十次日期')):
            return None
        
        # Get customer ID from mapping
        customer_code = str(int(row['客戶']))
        customer_id = self.customer_mapping.get(customer_code)
        
        if not customer_id:
            self.migration_stats['missing_customers'].add(customer_code)
            # Skip deliveries for missing customers
            return None
        
        # Convert Taiwan date to Western date
        taiwan_date = str(row['最後十次日期'])
        try:
            delivery_date = self.date_converter.taiwan_to_gregorian(taiwan_date)
        except Exception as e:
            logger.debug(f"  ⚠️  Invalid date format: {taiwan_date} - {str(e)}")
            return None
        
        # Create delivery history record
        delivery_data = {
            'customer_id': customer_id,
            'customer_code': customer_code,
            'transaction_date': delivery_date,
            'transaction_time': None,  # Not available in this data
            'salesperson': None,  # Not available in this data
            'total_cylinders': 0,  # Will be calculated if we have quantity data
            'import_date': datetime.now(timezone.utc),
            'source_file': self.excel_file,
            'source_sheet': 'Sheet1',
            'created_at': datetime.now(timezone.utc),
            'updated_at': datetime.now(timezone.utc)
        }
        
        return delivery_data
    
    async def insert_batch(self, session: AsyncSession, batch_data: List[Dict]):
        """Insert batch of delivery records"""
        if not batch_data:
            return
        
        # Prepare the insert query
        columns = batch_data[0].keys()
        placeholders = ', '.join([f':{key}' for key in columns])
        column_names = ', '.join(columns)
        
        query = f"""
            INSERT INTO delivery_history ({column_names})
            VALUES ({placeholders})
        """
        
        # Execute batch insert
        for record in batch_data:
            await session.execute(text(query), record)
    
    def print_report(self):
        """Print migration report"""
        duration = time.time() - self.migration_stats['start_time']
        
        logger.info("\n" + "="*60)
        logger.info("DELIVERY MIGRATION REPORT")
        logger.info("="*60)
        logger.info(f"Total Records: {self.migration_stats['total_records']:,}")
        logger.info(f"✅ Successful: {self.migration_stats['successful']:,}")
        logger.info(f"❌ Failed: {self.migration_stats['failed']:,}")
        logger.info(f"⏭️  Skipped: {self.migration_stats['skipped']:,}")
        logger.info(f"⏱️  Duration: {int(duration // 60)}m {int(duration % 60)}s")
        
        if self.migration_stats['missing_customers']:
            logger.warning(f"\n⚠️  Missing customers: {len(self.migration_stats['missing_customers'])}")
            # Show first 10 missing customer codes
            sample = list(self.migration_stats['missing_customers'])[:10]
            for code in sample:
                logger.warning(f"  - {code}")
            if len(self.migration_stats['missing_customers']) > 10:
                logger.warning(f"  ... and {len(self.migration_stats['missing_customers']) - 10} more")
        
        if self.checkpoint['errors']:
            logger.error(f"\n❌ Errors encountered: {len(self.checkpoint['errors'])}")
            # Show first 5 errors
            for error in self.checkpoint['errors'][:5]:
                logger.error(f"  - Row {error['row']}: {error['error']}")
        
        if self.dry_run:
            logger.info("\n⚠️  This was a DRY RUN. No data was actually migrated.")
            logger.info("💡 To run in production mode, add --production flag")
        else:
            if self.migration_stats['failed'] == 0:
                logger.info("\n✅ Migration completed successfully!")
            else:
                logger.warning("\n⚠️  Migration completed with errors. Review the logs.")


async def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Migrate delivery history from Excel to PostgreSQL')
    parser.add_argument('--file', type=str, default='raw/2025-05 commercial deliver history.xlsx',
                       help='Path to Excel file')
    parser.add_argument('--production', action='store_true',
                       help='Run in production mode (actually migrate data)')
    
    args = parser.parse_args()
    
    # Check if file exists
    if not os.path.exists(args.file):
        logger.error(f"❌ Error: File not found: {args.file}")
        sys.exit(1)
    
    migration = DeliveryMigration(
        excel_file=args.file,
        dry_run=not args.production
    )
    
    success = await migration.run()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    asyncio.run(main())