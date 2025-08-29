"""
Simplified database configuration for Lucky Gas backend.
Supports both PostgreSQL and SQLite for development flexibility.
"""
import os
from typing import Optional, AsyncGenerator
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine, AsyncEngine
from sqlalchemy.orm import DeclarativeBase, sessionmaker
from sqlalchemy import create_engine
import logging

logger = logging.getLogger(__name__)

# Get database URL from environment
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./local_luckygas.db")

# Convert URL for async if needed
if DATABASE_URL.startswith("postgresql://"):
    DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://")
elif DATABASE_URL.startswith("sqlite:///"):
    DATABASE_URL = DATABASE_URL.replace("sqlite:///", "sqlite+aiosqlite:///")

# Initialize as None, will be set during startup
engine: Optional[AsyncEngine] = None
async_session_maker: Optional[async_sessionmaker] = None


class Base(DeclarativeBase):
    pass


async def initialize_database():
    """Initialize database connection."""
    global engine, async_session_maker
    
    try:
        logger.info(f"Initializing database with URL: {DATABASE_URL[:30]}...")
        
        # Create async engine with appropriate settings
        if "sqlite" in DATABASE_URL:
            # SQLite settings
            engine = create_async_engine(
                DATABASE_URL,
                connect_args={"check_same_thread": False},
                echo=False
            )
        else:
            # PostgreSQL settings
            engine = create_async_engine(
                DATABASE_URL,
                pool_size=10,
                max_overflow=20,
                echo=False
            )
        
        # Create async session factory
        async_session_maker = async_sessionmaker(
            engine, class_=AsyncSession, expire_on_commit=False
        )
        
        logger.info("✅ Database initialized successfully")
        return engine
    except Exception as e:
        logger.error(f"❌ Failed to initialize database: {str(e)}")
        raise


async def create_db_and_tables():
    """Create database tables."""
    global engine
    
    try:
        # Initialize database if not already done
        if engine is None:
            await initialize_database()
        
        logger.info("Creating database tables...")
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        
        logger.info("✅ Database tables created successfully")
    except Exception as e:
        logger.error(f"❌ Failed to create database tables: {str(e)}")
        raise


async def get_async_session() -> AsyncGenerator[AsyncSession, None]:
    """Get async database session."""
    if async_session_maker is None:
        await initialize_database()
    
    async with async_session_maker() as session:
        yield session