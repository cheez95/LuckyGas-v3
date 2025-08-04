#!/usr/bin/env python3
"""
Create missing customers from delivery history
Ensures all customers referenced in delivery history exist in the database
Author: Devin (Data Migration Specialist)
"""

import pandas as pd
import asyncio
from datetime import datetime, timezone
from typing import Set
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

class MissingCustomerCreation:
    """Create placeholder records for customers found in delivery history but not in customer list"""
    
    def __init__(self, delivery_file: str, dry_run: bool = True):
        self.delivery_file = delivery_file
        self.dry_run = dry_run
        self.existing_customers = set()
        self.delivery_customers = set()
        self.missing_customers = set()
        self.migration_stats = {
            'total_missing': 0,
            'created': 0,
            'failed': 0
        }
    
    async def run(self):
        """Execute the missing customer creation process"""
        logger.info(f"🚀 Starting missing customer analysis from {self.delivery_file}")
        logger.info(f"Mode: {'DRY RUN' if self.dry_run else 'PRODUCTION'}")
        
        try:
            # Step 1: Load existing customers
            await self.load_existing_customers()
            
            # Step 2: Find customers in delivery history
            self.find_delivery_customers()
            
            # Step 3: Identify missing customers
            self.identify_missing_customers()
            
            # Step 4: Create missing customers
            if self.missing_customers:
                await self.create_missing_customers()
            
            # Step 5: Print summary
            self.print_summary()
            
            return self.migration_stats['failed'] == 0
            
        except Exception as e:
            logger.error(f"❌ Process failed: {str(e)}")
            return False
    
    async def load_existing_customers(self):
        """Load existing customer codes from database"""
        logger.info("📊 Loading existing customers...")
        
        engine = create_async_engine(settings.DATABASE_URL)
        async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
        
        async with async_session() as session:
            try:
                result = await session.execute(
                    text("SELECT customer_code FROM customers")
                )
                self.existing_customers = {row[0] for row in result}
                logger.info(f"✅ Found {len(self.existing_customers)} existing customers")
            finally:
                await engine.dispose()
    
    def find_delivery_customers(self):
        """Find all unique customer codes in delivery history"""
        logger.info("🔍 Analyzing delivery history...")
        
        # Read delivery history
        df = pd.read_excel(self.delivery_file)
        
        # Extract unique customer codes
        self.delivery_customers = set(df['客戶'].astype(str).str.extract(r'^(\d+)')[0].unique())
        self.delivery_customers.discard('nan')  # Remove any NaN values
        
        logger.info(f"✅ Found {len(self.delivery_customers)} unique customers in delivery history")
    
    def identify_missing_customers(self):
        """Identify customers in delivery history but not in database"""
        self.missing_customers = self.delivery_customers - self.existing_customers
        self.migration_stats['total_missing'] = len(self.missing_customers)
        
        logger.info(f"⚠️  Found {len(self.missing_customers)} missing customers")
        
        if self.missing_customers:
            # Show sample of missing customers
            sample = sorted(list(self.missing_customers))[:10]
            for code in sample:
                logger.info(f"  - {code}")
            if len(self.missing_customers) > 10:
                logger.info(f"  ... and {len(self.missing_customers) - 10} more")
    
    async def create_missing_customers(self):
        """Create placeholder records for missing customers"""
        logger.info("🚀 Creating missing customer records...")
        
        engine = create_async_engine(settings.DATABASE_URL)
        async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
        
        async with async_session() as session:
            try:
                batch_count = 0
                for i, customer_code in enumerate(sorted(self.missing_customers)):
                    try:
                        if not self.dry_run:
                            # Create placeholder customer record
                            await session.execute(
                                text("""
                                    INSERT INTO customers (
                                        customer_code, invoice_title, short_name, 
                                        address, area, created_at, updated_at
                                    ) VALUES (
                                        :customer_code, :invoice_title, :short_name,
                                        :address, :area, :created_at, :updated_at
                                    )
                                """),
                                {
                                    'customer_code': customer_code,
                                    'invoice_title': f'客戶 {customer_code}',
                                    'short_name': f'客戶{customer_code}',
                                    'address': '地址待更新',
                                    'area': '區域待更新',
                                    'created_at': datetime.now(timezone.utc),
                                    'updated_at': datetime.now(timezone.utc)
                                }
                            )
                        
                        self.migration_stats['created'] += 1
                        batch_count += 1
                        
                        # Commit every 100 records
                        if batch_count >= 100:
                            if not self.dry_run:
                                await session.commit()
                            batch_count = 0
                            logger.info(f"Progress: {i+1}/{len(self.missing_customers)}")
                        
                    except Exception as e:
                        self.migration_stats['failed'] += 1
                        logger.error(f"Failed to create customer {customer_code}: {str(e)}")
                        if not self.dry_run:
                            await session.rollback()
                
                # Final commit
                if not self.dry_run and batch_count > 0:
                    await session.commit()
                    logger.info("✅ All changes committed")
                
            finally:
                await engine.dispose()
    
    def print_summary(self):
        """Print creation summary"""
        logger.info("\n" + "="*60)
        logger.info("MISSING CUSTOMER CREATION SUMMARY")
        logger.info("="*60)
        logger.info(f"Total Missing: {self.migration_stats['total_missing']}")
        logger.info(f"✅ Created: {self.migration_stats['created']}")
        logger.info(f"❌ Failed: {self.migration_stats['failed']}")
        
        if self.dry_run:
            logger.info("\n⚠️  This was a DRY RUN. No records were actually created.")
            logger.info("To run in production mode, add --production flag")


async def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Create missing customers from delivery history')
    parser.add_argument('--file', type=str, default='raw/2025-05 commercial deliver history.xlsx',
                       help='Path to delivery history Excel file')
    parser.add_argument('--production', action='store_true',
                       help='Run in production mode (actually create records)')
    
    args = parser.parse_args()
    
    # Check if file exists
    if not os.path.exists(args.file):
        logger.error(f"❌ Error: File not found: {args.file}")
        sys.exit(1)
    
    creation = MissingCustomerCreation(
        delivery_file=args.file,
        dry_run=not args.production
    )
    
    success = await creation.run()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    asyncio.run(main())