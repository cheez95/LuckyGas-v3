"""
Drop and recreate all tables with correct schema from models
"""
import os
import psycopg2
from sqlalchemy import create_engine, text
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Database connection
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://luckygas:staging-password-2025@35.194.143.37/luckygas")

def drop_all_tables():
    """Drop all existing tables"""
    conn = None
    cursor = None
    
    try:
        logger.info("Connecting to database...")
        conn = psycopg2.connect(DATABASE_URL)
        cursor = conn.cursor()
        
        # Get all table names
        cursor.execute("""
            SELECT tablename FROM pg_tables 
            WHERE schemaname = 'public'
        """)
        tables = cursor.fetchall()
        
        # Drop each table
        for table in tables:
            table_name = table[0]
            logger.info(f"Dropping table: {table_name}")
            cursor.execute(f"DROP TABLE IF EXISTS {table_name} CASCADE")
        
        conn.commit()
        logger.info("✅ All tables dropped successfully")
        return True
        
    except Exception as e:
        logger.error(f"Failed to drop tables: {e}")
        if conn:
            conn.rollback()
        return False
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

def create_tables_from_models():
    """Create tables from SQLAlchemy models"""
    from app.core.database import Base, engine, init_db
    
    # Import all models to register them
    from app.models import (
        User, Customer, Order, Driver, Route, 
        Delivery, OrderTemplate, Notification, FeatureFlag
    )
    
    try:
        logger.info("Creating tables from models...")
        Base.metadata.create_all(bind=engine)
        logger.info("✅ Tables created successfully")
        
        # Initialize with indexes
        init_db()
        
        return True
    except Exception as e:
        logger.error(f"Failed to create tables: {e}")
        return False

if __name__ == "__main__":
    # Drop all existing tables
    if drop_all_tables():
        # Create new tables from models
        if create_tables_from_models():
            logger.info("\n✅ Database recreated successfully!")
        else:
            logger.error("\n❌ Failed to create new tables")
    else:
        logger.error("\n❌ Failed to drop existing tables")