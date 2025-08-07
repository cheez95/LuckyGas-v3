#!/usr/bin/env python3
"""
Migration to preserve payment and invoice data while features are disabled.

This migration creates backup tables for payment/invoice data to ensure
no data is lost while these features are disabled. When the features are
re-enabled, the data can be restored from these backup tables.

Usage:
    python migrations/preserve_payment_data.py

The migration will:
1. Create backup tables for all payment/invoice related data
2. Copy existing data to backup tables
3. Create indexes on backup tables for efficient restoration
4. Log all operations for audit trail
"""

import asyncio
import json
import logging
from datetime import datetime
from typing import List, Dict, Any

from sqlalchemy import text, inspect, MetaData
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db_session, engine

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Tables to backup
PAYMENT_TABLES = [
    'invoices',
    'invoice_items',
    'credit_notes',
    'payments',
    'payment_batches',
    'payment_transactions',
    'reconciliation_logs',
    'invoice_sequences'
]


async def create_backup_table(session: AsyncSession, table_name: str) -> bool:
    """Create a backup table for the given table."""
    backup_table_name = f"{table_name}_backup_20250806"
    
    try:
        # Check if backup table already exists
        result = await session.execute(
            text("""
                SELECT EXISTS (
                    SELECT 1 FROM information_schema.tables 
                    WHERE table_schema = 'public' 
                    AND table_name = :backup_table
                )
            """),
            {"backup_table": backup_table_name}
        )
        exists = result.scalar()
        
        if exists:
            logger.warning(f"Backup table {backup_table_name} already exists, skipping creation")
            return False
        
        # Create backup table with same structure
        await session.execute(
            text(f"""
                CREATE TABLE {backup_table_name} AS 
                TABLE {table_name}
            """)
        )
        
        logger.info(f"Created backup table: {backup_table_name}")
        
        # Copy indexes
        await session.execute(
            text(f"""
                DO $$
                DECLARE
                    index_record RECORD;
                    new_index_name TEXT;
                BEGIN
                    FOR index_record IN 
                        SELECT indexname, indexdef 
                        FROM pg_indexes 
                        WHERE tablename = '{table_name}'
                        AND indexname NOT LIKE '%_pkey'
                    LOOP
                        new_index_name := REPLACE(index_record.indexname, '{table_name}', '{backup_table_name}');
                        EXECUTE REPLACE(
                            REPLACE(index_record.indexdef, index_record.indexname, new_index_name),
                            '{table_name}',
                            '{backup_table_name}'
                        );
                    END LOOP;
                END $$;
            """)
        )
        
        logger.info(f"Copied indexes for table: {backup_table_name}")
        
        # Add backup metadata
        await session.execute(
            text(f"""
                ALTER TABLE {backup_table_name} 
                ADD COLUMN IF NOT EXISTS _backup_created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                ADD COLUMN IF NOT EXISTS _backup_reason TEXT DEFAULT 'Payment/Invoice features disabled'
            """)
        )
        
        return True
        
    except Exception as e:
        logger.error(f"Error creating backup table {backup_table_name}: {str(e)}")
        raise


async def get_table_row_count(session: AsyncSession, table_name: str) -> int:
    """Get the row count for a table."""
    try:
        result = await session.execute(
            text(f"SELECT COUNT(*) FROM {table_name}")
        )
        return result.scalar() or 0
    except Exception:
        return 0


async def create_restoration_script() -> str:
    """Create a script to restore data from backup tables."""
    script = """#!/usr/bin/env python3
'''
Script to restore payment/invoice data from backup tables.

Usage:
    python migrations/restore_payment_data.py

This will restore all payment/invoice data from the backup tables
created when the features were disabled.
'''

import asyncio
from sqlalchemy import text
from app.core.database import get_db_session

PAYMENT_TABLES = {tables}

async def restore_data():
    async with get_db_session() as session:
        for table in PAYMENT_TABLES:
            backup_table = f"{{table}}_backup_20250806"
            
            # Check if backup exists
            result = await session.execute(
                text(f"SELECT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = :table)"),
                {{"table": backup_table}}
            )
            if not result.scalar():
                print(f"Backup table {{backup_table}} not found, skipping")
                continue
            
            # Clear current table
            await session.execute(text(f"TRUNCATE TABLE {{table}} CASCADE"))
            
            # Restore from backup
            await session.execute(
                text(f'''
                    INSERT INTO {{table}} 
                    SELECT * FROM {{backup_table}}
                    WHERE _backup_created_at IS NOT NULL
                ''')
            )
            
            await session.commit()
            print(f"Restored {{table}} from {{backup_table}}")

if __name__ == "__main__":
    asyncio.run(restore_data())
""".format(tables=json.dumps(PAYMENT_TABLES))
    
    with open('migrations/restore_payment_data.py', 'w') as f:
        f.write(script)
    
    return 'migrations/restore_payment_data.py'


async def main():
    """Main migration function."""
    logger.info("Starting payment/invoice data preservation migration")
    
    backup_summary = {
        "migration_date": datetime.now().isoformat(),
        "tables_backed_up": [],
        "total_rows_backed_up": 0,
        "errors": []
    }
    
    async with get_db_session() as session:
        try:
            # Check which tables exist
            inspector = inspect(engine.sync_engine)
            existing_tables = inspector.get_table_names()
            
            for table_name in PAYMENT_TABLES:
                if table_name not in existing_tables:
                    logger.warning(f"Table {table_name} does not exist, skipping")
                    backup_summary["errors"].append(f"Table {table_name} not found")
                    continue
                
                try:
                    # Get row count before backup
                    row_count = await get_table_row_count(session, table_name)
                    
                    # Create backup
                    created = await create_backup_table(session, table_name)
                    
                    if created:
                        backup_summary["tables_backed_up"].append({
                            "table": table_name,
                            "backup_table": f"{table_name}_backup_20250806",
                            "rows": row_count
                        })
                        backup_summary["total_rows_backed_up"] += row_count
                    
                except Exception as e:
                    error_msg = f"Error backing up {table_name}: {str(e)}"
                    logger.error(error_msg)
                    backup_summary["errors"].append(error_msg)
            
            await session.commit()
            
            # Create restoration script
            restore_script_path = await create_restoration_script()
            backup_summary["restore_script"] = restore_script_path
            
            # Save backup summary
            summary_path = 'migrations/backup_summary_20250806.json'
            with open(summary_path, 'w') as f:
                json.dump(backup_summary, f, indent=2)
            
            logger.info(f"Backup summary saved to: {summary_path}")
            
            # Print summary
            print("\n" + "="*50)
            print("PAYMENT/INVOICE DATA BACKUP SUMMARY")
            print("="*50)
            print(f"Date: {backup_summary['migration_date']}")
            print(f"Tables backed up: {len(backup_summary['tables_backed_up'])}")
            print(f"Total rows preserved: {backup_summary['total_rows_backed_up']:,}")
            
            if backup_summary['tables_backed_up']:
                print("\nBackup Details:")
                for table_info in backup_summary['tables_backed_up']:
                    print(f"  - {table_info['table']}: {table_info['rows']:,} rows → {table_info['backup_table']}")
            
            if backup_summary['errors']:
                print("\nErrors:")
                for error in backup_summary['errors']:
                    print(f"  - {error}")
            
            print(f"\nRestore script created: {restore_script_path}")
            print("\nTo restore data later, run:")
            print(f"  python {restore_script_path}")
            print("="*50 + "\n")
            
    except Exception as e:
        logger.error(f"Migration failed: {str(e)}")
        raise


if __name__ == "__main__":
    asyncio.run(main())