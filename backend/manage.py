#!/usr/bin/env python3
"""
Database management commands for Lucky Gas Delivery System
"""
import asyncio
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.migrations.add_performance_indexes import create_indexes, drop_indexes
from app.core.database import create_db_and_tables
from app.services.data_migration import DataMigrationService
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def init_db():
    """Initialize database with tables"""
    logger.info("Creating database tables...")
    await create_db_and_tables()
    logger.info("Database tables created successfully")


async def migrate_historical_data():
    """Migrate historical data from Excel files"""
    logger.info("Starting historical data migration...")
    migration_service = DataMigrationService()
    
    # Import customers
    customer_file = "raw/2025-05 client list.xlsx"
    if os.path.exists(customer_file):
        await migration_service.import_customers_from_excel(customer_file)
    else:
        logger.warning(f"Customer file not found: {customer_file}")
    
    # Import delivery history
    history_file = "raw/2025-05 deliver history.xlsx"
    if os.path.exists(history_file):
        await migration_service.import_delivery_history_from_excel(history_file)
    else:
        logger.warning(f"Delivery history file not found: {history_file}")
    
    logger.info("Historical data migration completed")


def show_help():
    """Show available commands"""
    print("""
Lucky Gas Database Management

Available commands:
  init-db              Initialize database with tables
  create-indexes       Create performance indexes
  drop-indexes         Drop all custom indexes
  migrate-data         Import historical data from Excel files
  full-setup          Run complete database setup (init + indexes + data)
  
Usage:
  python manage.py <command>
  
Example:
  python manage.py init-db
  python manage.py create-indexes
  python manage.py full-setup
""")


async def full_setup():
    """Run complete database setup"""
    logger.info("Running full database setup...")
    
    # 1. Initialize database
    await init_db()
    
    # 2. Create indexes
    create_indexes()
    
    # 3. Migrate historical data
    await migrate_historical_data()
    
    logger.info("Full database setup completed successfully!")


def main():
    """Main entry point"""
    if len(sys.argv) < 2:
        show_help()
        sys.exit(1)
    
    command = sys.argv[1]
    
    if command == "init-db":
        asyncio.run(init_db())
    elif command == "create-indexes":
        create_indexes()
    elif command == "drop-indexes":
        drop_indexes()
    elif command == "migrate-data":
        asyncio.run(migrate_historical_data())
    elif command == "full-setup":
        asyncio.run(full_setup())
    elif command in ["-h", "--help", "help"]:
        show_help()
    else:
        print(f"Unknown command: {command}")
        show_help()
        sys.exit(1)


if __name__ == "__main__":
    main()