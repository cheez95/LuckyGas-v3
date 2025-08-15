"""
Simplified SYNCHRONOUS database configuration for Lucky Gas
No async complications - perfect for 15 concurrent users
"""
import os
from sqlalchemy import create_engine, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from typing import Generator
import logging

logger = logging.getLogger(__name__)

# Get database URL from environment
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://luckygas:password@localhost/luckygas")

# Convert async URL to sync if needed
if DATABASE_URL.startswith("postgresql+asyncpg://"):
    DATABASE_URL = DATABASE_URL.replace("postgresql+asyncpg://", "postgresql://")
elif DATABASE_URL.startswith("sqlite+aiosqlite://"):
    DATABASE_URL = DATABASE_URL.replace("sqlite+aiosqlite://", "sqlite://")

# Create SYNCHRONOUS engine - no async complications!
if "sqlite" in DATABASE_URL:
    # SQLite configuration
    engine = create_engine(
        DATABASE_URL,
        connect_args={"check_same_thread": False},  # Allow multi-threading
        pool_size=1,  # SQLite doesn't support multiple connections well
        echo=False
    )
else:
    # PostgreSQL configuration - optimized for your scale
    engine = create_engine(
        DATABASE_URL,
        pool_size=10,      # Only 15 users, 10 connections is plenty
        max_overflow=5,    # Allow 5 more if needed (total 15)
        pool_pre_ping=True,  # Check connection health
        pool_recycle=3600,   # Recycle connections hourly
        echo=False,          # Don't log SQL (performance)
        connect_args={
            "connect_timeout": 10,
            "options": "-c statement_timeout=30000"  # 30 second timeout
        } if "postgresql" in DATABASE_URL else {}
    )

# Create session factory
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)

# Base class for models
Base = declarative_base()

def get_db() -> Generator[Session, None, None]:
    """
    Dependency to get DB session
    Simple, synchronous, no complications
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def init_db():
    """
    Initialize database - create all tables
    Run this once when setting up
    """
    try:
        # Import all models to register them
        from app.models import (
            User, Customer, Order,
            Driver, Delivery
        )
        
        # Create all tables
        Base.metadata.create_all(bind=engine)
        logger.info("✅ Database tables created successfully")
        
        # Create indexes if PostgreSQL
        if "postgresql" in DATABASE_URL:
            with engine.connect() as conn:
                # Critical indexes for your access patterns
                indexes = [
                    "CREATE INDEX IF NOT EXISTS idx_delivery_customer_date ON deliveries(customer_id, delivery_date DESC)",
                    "CREATE INDEX IF NOT EXISTS idx_delivery_driver_date ON deliveries(driver_id, delivery_date DESC)",
                    "CREATE INDEX IF NOT EXISTS idx_order_customer_date ON orders(customer_id, order_date DESC)",
                    "CREATE INDEX IF NOT EXISTS idx_order_status_date ON orders(status, order_date DESC)",
                    "CREATE INDEX IF NOT EXISTS idx_customer_type ON customers(customer_type)",
                    "CREATE INDEX IF NOT EXISTS idx_active_orders ON orders(status) WHERE status IN ('pending', 'processing')",
                ]
                
                for index_sql in indexes:
                    try:
                        conn.execute(text(index_sql))
                        logger.info(f"✅ Index created: {index_sql[:50]}...")
                    except Exception as e:
                        logger.warning(f"Index might already exist: {e}")
                
                conn.commit()
        
        return True
    except Exception as e:
        logger.error(f"❌ Failed to initialize database: {e}")
        raise

def test_connection():
    """Test database connection"""
    try:
        with engine.connect() as conn:
            result = conn.execute(text("SELECT 1"))
            logger.info("✅ Database connection successful")
            return True
    except Exception as e:
        logger.error(f"❌ Database connection failed: {e}")
        return False

# Performance helpers
def explain_query(query_string: str):
    """
    Get query execution plan (PostgreSQL only)
    Use this to verify indexes are being used
    """
    if "postgresql" not in DATABASE_URL:
        return "EXPLAIN only available for PostgreSQL"
    
    with engine.connect() as conn:
        result = conn.execute(text(f"EXPLAIN ANALYZE {query_string}"))
        return '\n'.join([row[0] for row in result])

def get_table_stats(table_name: str) -> dict:
    """Get table statistics"""
    try:
        with engine.connect() as conn:
            count_result = conn.execute(text(f"SELECT COUNT(*) FROM {table_name}"))
            count = count_result.scalar()
            
            stats = {'row_count': count}
            
            if "postgresql" in DATABASE_URL:
                size_result = conn.execute(text(f"""
                    SELECT 
                        pg_size_pretty(pg_total_relation_size('{table_name}')) as total_size,
                        pg_size_pretty(pg_relation_size('{table_name}')) as table_size,
                        pg_size_pretty(pg_indexes_size('{table_name}')) as indexes_size
                """)).first()
                
                if size_result:
                    stats.update({
                        'total_size': size_result[0],
                        'table_size': size_result[1],
                        'indexes_size': size_result[2]
                    })
            
            return stats
    except Exception as e:
        return {'error': str(e)}