import os
from typing import AsyncGenerator, Optional

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine, AsyncEngine
from sqlalchemy.orm import DeclarativeBase
import logging

from app.core.config import settings
from app.core.cloud_sql import get_database_urls
from app.core.database_retry import DatabaseConnectionManager

logger = logging.getLogger(__name__)

# Get database URLs based on environment
async_url, sync_url = get_database_urls()

# Create database connection manager with retry logic
db_manager = DatabaseConnectionManager(
    database_url=async_url or settings.DATABASE_URL.replace(
        "postgresql + psycopg2://", "postgresql + asyncpg://"
    ),
    pool_size=settings.database.pool_size,
    max_overflow=settings.database.max_overflow,
    pool_timeout=settings.database.pool_timeout,
    pool_recycle=settings.database.pool_recycle,
    echo=False,
)

# Initialize as None, will be set during startup
engine: Optional[AsyncEngine] = None
async_session_maker: Optional[async_sessionmaker] = None


class Base(DeclarativeBase):
    pass


async def initialize_database():
    """Initialize database connection with retry logic."""
    global engine, async_session_maker
    
    try:
        logger.info("Starting database initialization...")
        logger.info(f"Database URL (masked): {async_url[:30]}..." if async_url else "No URL configured")
        
        # Connect with retry
        engine = await db_manager.connect_with_retry()
        
        # Create async session factory
        async_session_maker = async_sessionmaker(
            engine, class_=AsyncSession, expire_on_commit=False
        )
        
        logger.info("✅ Database initialized successfully")
        return engine
    except Exception as e:
        logger.error(f"❌ Failed to initialize database: {str(e)}")
        logger.error(f"Database URL configured: {bool(async_url)}")
        raise


async def create_db_and_tables():
    """Create database tables."""
    global engine
    
    try:
        logger.info("Starting create_db_and_tables...")
        
        # Initialize database if not already done
        if engine is None:
            logger.info("Engine is None, initializing database...")
            await initialize_database()
        else:
            logger.info("Engine already initialized")
        
        logger.info("Creating database tables...")
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        
        logger.info("✅ Database tables created successfully")
    except Exception as e:
        logger.error(f"❌ Failed to create database tables: {str(e)}")
        raise


async def get_async_session() -> AsyncGenerator[AsyncSession, None]:
    async with async_session_maker() as session:
        yield session
