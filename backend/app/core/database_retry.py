"""Database Connection with Retry Logic

This module provides resilient database connection with exponential backoff retry logic.
"""

import asyncio
import logging
import time
from contextlib import asynccontextmanager

from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import text
from sqlalchemy.exc import OperationalError, DatabaseError

logger = logging.getLogger(__name__)


class DatabaseConnectionManager:
    """Manages database connections with retry logic and health checks."""
    
    def __init__(
        self,
        database_url: str,
        pool_size: int = 20,
        max_overflow: int = 10,
        pool_timeout: int = 30,
        pool_recycle: int = 1800,
        echo: bool = False,
    ):
        """
        Initialize database connection manager.
        
        Args:
            database_url: Database connection URL
            pool_size: Number of connections to maintain in pool
            max_overflow: Maximum overflow connections allowed
            pool_timeout: Timeout for getting connection from pool
            pool_recycle: Time to recycle connections (seconds)
            echo: Whether to echo SQL statements
        """
        self.database_url = database_url
        self.pool_size = pool_size
        self.max_overflow = max_overflow
        self.pool_timeout = pool_timeout
        self.pool_recycle = pool_recycle
        self.echo = echo
        self.engine: Optional[AsyncEngine] = None
        self.SessionLocal: Optional[sessionmaker] = None
        
    async def connect_with_retry(
        self,
        max_retries: int = 5,
        initial_delay: float = 1.0,
        max_delay: float = 60.0,
        exponential_base: float = 2.0,
    ) -> AsyncEngine:
        """
        Connect to database with exponential backoff retry logic.
        
        Args:
            max_retries: Maximum number of retry attempts
            initial_delay: Initial delay between retries (seconds)
            max_delay: Maximum delay between retries (seconds)
            exponential_base: Base for exponential backoff
        
        Returns:
            Connected AsyncEngine
        
        Raises:
            Exception: If connection fails after all retries
        """
        delay = initial_delay
        last_exception = None
        
        for attempt in range(max_retries):
            try:
                logger.info(f"Attempting database connection (attempt {attempt + 1}/{max_retries})")
                
                # Create engine
                self.engine = create_async_engine(
                    self.database_url,
                    pool_size=self.pool_size,
                    max_overflow=self.max_overflow,
                    pool_timeout=self.pool_timeout,
                    pool_recycle=self.pool_recycle,
                    echo=self.echo,
                    # Cloud SQL specific settings
                    connect_args={
                        "server_settings": {
                            "application_name": "luckygas-backend",
                            "jit": "off",
                        },
                        "command_timeout": 60,
                        "timeout": 60,
                    }
                )
                
                # Test connection
                async with self.engine.begin() as conn:
                    result = await conn.execute(text("SELECT 1"))
                    await conn.commit()
                
                # Create session factory
                self.SessionLocal = sessionmaker(
                    self.engine,
                    class_=AsyncSession,
                    expire_on_commit=False,
                )
                
                logger.info("✅ Database connection established successfully")
                return self.engine
                
            except (OperationalError, DatabaseError) as e:
                last_exception = e
                logger.warning(
                    f"Database connection attempt {attempt + 1} failed: {str(e)}. "
                    f"Retrying in {delay:.1f} seconds..."
                )
                
                if attempt < max_retries - 1:
                    await asyncio.sleep(delay)
                    # Exponential backoff with jitter
                    delay = min(delay * exponential_base, max_delay)
                    # Add jitter to prevent thundering herd
                    delay = delay * (0.5 + 0.5 * time.time() % 1)
            
            except Exception as e:
                logger.error(f"Unexpected error during database connection: {str(e)}")
                raise
        
        # All retries exhausted
        error_msg = f"Failed to connect to database after {max_retries} attempts"
        logger.error(f"{error_msg}. Last error: {last_exception}")
        raise Exception(error_msg) from last_exception
    
    async def health_check(self) -> bool:
        """
        Perform database health check.
        
        Returns:
            True if database is healthy, False otherwise
        """
        if not self.engine:
            logger.warning("Database engine not initialized")
            return False
        
        try:
            async with self.engine.begin() as conn:
                result = await conn.execute(text("SELECT 1"))
                return True
        except Exception as e:
            logger.error(f"Database health check failed: {str(e)}")
            return False
    
    async def close(self):
        """Close database connection."""
        if self.engine:
            await self.engine.dispose()
            logger.info("Database connection closed")
    
    @asynccontextmanager
    async def get_session(self):
        """
        Get database session with automatic cleanup.
        
        Yields:
            AsyncSession: Database session
        """
        if not self.SessionLocal:
            raise Exception("Database not connected. Call connect_with_retry() first.")
        
        async with self.SessionLocal() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise
            finally:
                await session.close()


# Global database manager instance
db_manager: Optional[DatabaseConnectionManager] = None


async def initialize_database(database_url: str, **kwargs) -> DatabaseConnectionManager:
    """
    Initialize global database manager.
    
    Args:
        database_url: Database connection URL
        **kwargs: Additional arguments for DatabaseConnectionManager
    
    Returns:
        Initialized DatabaseConnectionManager
    """
    global db_manager
    
    db_manager = DatabaseConnectionManager(database_url, **kwargs)
    await db_manager.connect_with_retry()
    
    return db_manager


async def get_db_manager() -> DatabaseConnectionManager:
    """
    Get global database manager.
    
    Returns:
        DatabaseConnectionManager instance
    
    Raises:
        Exception: If database not initialized
    """
    if not db_manager:
        raise Exception("Database not initialized. Call initialize_database() first.")
    
    return db_manager