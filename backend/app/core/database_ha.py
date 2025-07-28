"""High Availability Database Configuration.

This module provides database connection management with support for:
- Primary/replica routing
- Connection pooling
- Automatic failover
- Health checking
- Performance monitoring
"""

import asyncio
import logging
from typing import Optional, Dict, List, Any
from contextlib import asynccontextmanager
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, AsyncEngine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import NullPool, AsyncAdaptedQueuePool
from sqlalchemy import event, text
import asyncpg
from datetime import datetime, timedelta

from .config import settings

logger = logging.getLogger(__name__)


class DatabaseManager:
    """Manages database connections with high availability support."""
    
    def __init__(self):
        self.primary_engine: Optional[AsyncEngine] = None
        self.read_engines: List[AsyncEngine] = []
        self.pgbouncer_engine: Optional[AsyncEngine] = None
        self.current_read_index = 0
        self._health_check_task: Optional[asyncio.Task] = None
        self._metrics: Dict[str, Any] = {
            "connections": {"primary": 0, "replicas": []},
            "queries": {"read": 0, "write": 0},
            "errors": {"primary": 0, "replicas": []},
            "latency": {"primary": [], "replicas": []},
            "last_health_check": None
        }
    
    async def initialize(self):
        """Initialize database connections."""
        logger.info("Initializing database connections...")
        
        # Create primary connection
        await self._create_primary_connection()
        
        # Create read replica connections
        await self._create_replica_connections()
        
        # Create pgBouncer connection if available
        await self._create_pgbouncer_connection()
        
        # Start health check task
        self._health_check_task = asyncio.create_task(self._health_check_loop())
        
        logger.info("Database initialization complete")
    
    async def _create_primary_connection(self):
        """Create connection to primary database."""
        try:
            primary_url = self._get_primary_url()
            self.primary_engine = create_async_engine(
                primary_url,
                pool_size=settings.database.pool_size,
                max_overflow=settings.database.max_overflow,
                pool_timeout=settings.database.pool_timeout,
                pool_recycle=settings.database.pool_recycle,
                pool_pre_ping=settings.database.pool_pre_ping,
                echo=settings.LOG_LEVEL == "DEBUG",
                connect_args={
                    "server_settings": {
                        "application_name": "luckygas_backend",
                        "jit": "off"
                    },
                    "command_timeout": settings.database.command_timeout,
                    "timeout": settings.database.pool_timeout,
                }
            )
            
            # Test connection
            async with self.primary_engine.connect() as conn:
                await conn.execute(text("SELECT 1"))
            
            logger.info("Primary database connection established")
            
        except Exception as e:
            logger.error(f"Failed to connect to primary database: {e}")
            raise
    
    async def _create_replica_connections(self):
        """Create connections to read replicas."""
        replica_hosts = self._get_replica_hosts()
        
        for i, host in enumerate(replica_hosts):
            try:
                replica_url = self._get_replica_url(host)
                engine = create_async_engine(
                    replica_url,
                    pool_size=settings.database.pool_size // len(replica_hosts),
                    max_overflow=settings.database.max_overflow // len(replica_hosts),
                    pool_timeout=settings.database.pool_timeout,
                    pool_recycle=settings.database.pool_recycle,
                    pool_pre_ping=settings.database.pool_pre_ping,
                    echo=False,  # Less verbose for replicas
                    connect_args={
                        "server_settings": {
                            "application_name": f"luckygas_backend_read_{i}",
                            "jit": "off"
                        },
                        "command_timeout": settings.database.command_timeout,
                        "timeout": settings.database.pool_timeout,
                    }
                )
                
                # Test connection
                async with engine.connect() as conn:
                    await conn.execute(text("SELECT 1"))
                
                self.read_engines.append(engine)
                logger.info(f"Read replica {i} connection established: {host}")
                
            except Exception as e:
                logger.warning(f"Failed to connect to replica {host}: {e}")
                # Continue with other replicas
    
    async def _create_pgbouncer_connection(self):
        """Create connection through pgBouncer if configured."""
        pgbouncer_host = settings.get("PGBOUNCER_HOST", None)
        if not pgbouncer_host:
            return
        
        try:
            pgbouncer_url = self._get_pgbouncer_url()
            self.pgbouncer_engine = create_async_engine(
                pgbouncer_url,
                poolclass=NullPool,  # pgBouncer handles pooling
                echo=False,
                connect_args={
                    "server_settings": {
                        "application_name": "luckygas_backend_pgbouncer",
                    }
                }
            )
            
            # Test connection
            async with self.pgbouncer_engine.connect() as conn:
                await conn.execute(text("SELECT 1"))
            
            logger.info("pgBouncer connection established")
            
        except Exception as e:
            logger.warning(f"Failed to connect through pgBouncer: {e}")
            # Fall back to direct connections
    
    def _get_primary_url(self) -> str:
        """Get primary database URL."""
        return settings.get_database_url(async_mode=True)
    
    def _get_replica_url(self, host: str) -> str:
        """Get replica database URL."""
        return (
            f"postgresql+asyncpg://{settings.POSTGRES_USER}:"
            f"{settings.POSTGRES_PASSWORD}@{host}:{settings.POSTGRES_PORT}/"
            f"{settings.POSTGRES_DB}"
        )
    
    def _get_pgbouncer_url(self) -> str:
        """Get pgBouncer URL."""
        pgbouncer_host = settings.get("PGBOUNCER_HOST", "pgbouncer")
        pgbouncer_port = settings.get("PGBOUNCER_PORT", 6432)
        return (
            f"postgresql+asyncpg://{settings.POSTGRES_USER}:"
            f"{settings.POSTGRES_PASSWORD}@{pgbouncer_host}:{pgbouncer_port}/"
            f"{settings.POSTGRES_DB}"
        )
    
    def _get_replica_hosts(self) -> List[str]:
        """Get list of replica hosts from configuration."""
        # Get from environment or use defaults
        replica_hosts = settings.get("POSTGRES_REPLICAS", "").split(",")
        if not replica_hosts or replica_hosts == ['']:
            # Default replicas for docker-compose setup
            return ["postgres-replica-1", "postgres-replica-2"]
        return [host.strip() for host in replica_hosts]
    
    async def get_primary_session(self) -> AsyncSession:
        """Get session for write operations."""
        if not self.primary_engine:
            raise RuntimeError("Primary database not initialized")
        
        self._metrics["queries"]["write"] += 1
        
        AsyncSessionLocal = sessionmaker(
            self.primary_engine,
            class_=AsyncSession,
            expire_on_commit=False
        )
        
        return AsyncSessionLocal()
    
    async def get_read_session(self) -> AsyncSession:
        """Get session for read operations with load balancing."""
        # Use pgBouncer if available for better connection pooling
        if self.pgbouncer_engine:
            engine = self.pgbouncer_engine
        elif self.read_engines:
            # Round-robin load balancing
            engine = self._get_next_read_engine()
        else:
            # Fall back to primary if no replicas available
            logger.warning("No read replicas available, using primary")
            engine = self.primary_engine
        
        if not engine:
            raise RuntimeError("No database engines available")
        
        self._metrics["queries"]["read"] += 1
        
        AsyncSessionLocal = sessionmaker(
            engine,
            class_=AsyncSession,
            expire_on_commit=False
        )
        
        return AsyncSessionLocal()
    
    def _get_next_read_engine(self) -> AsyncEngine:
        """Get next read engine using round-robin."""
        if not self.read_engines:
            return self.primary_engine
        
        engine = self.read_engines[self.current_read_index]
        self.current_read_index = (self.current_read_index + 1) % len(self.read_engines)
        return engine
    
    async def _health_check_loop(self):
        """Periodically check database health."""
        while True:
            try:
                await asyncio.sleep(30)  # Check every 30 seconds
                await self._check_all_connections()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Health check error: {e}")
    
    async def _check_all_connections(self):
        """Check health of all database connections."""
        self._metrics["last_health_check"] = datetime.utcnow()
        
        # Check primary
        if self.primary_engine:
            try:
                start_time = datetime.utcnow()
                async with self.primary_engine.connect() as conn:
                    await conn.execute(text("SELECT 1"))
                latency = (datetime.utcnow() - start_time).total_seconds() * 1000
                self._metrics["latency"]["primary"].append(latency)
                # Keep only last 100 measurements
                self._metrics["latency"]["primary"] = self._metrics["latency"]["primary"][-100:]
            except Exception as e:
                logger.error(f"Primary health check failed: {e}")
                self._metrics["errors"]["primary"] += 1
        
        # Check replicas
        for i, engine in enumerate(self.read_engines):
            try:
                start_time = datetime.utcnow()
                async with engine.connect() as conn:
                    result = await conn.execute(text(
                        "SELECT pg_is_in_recovery(), "
                        "pg_last_wal_receive_lsn(), "
                        "EXTRACT(EPOCH FROM now() - pg_last_xact_replay_timestamp()) as lag"
                    ))
                    row = result.fetchone()
                    if row:
                        is_replica, lsn, lag = row
                        logger.debug(f"Replica {i} - In recovery: {is_replica}, Lag: {lag}s")
                
                latency = (datetime.utcnow() - start_time).total_seconds() * 1000
                if i < len(self._metrics["latency"]["replicas"]):
                    self._metrics["latency"]["replicas"][i].append(latency)
                else:
                    self._metrics["latency"]["replicas"].append([latency])
                
            except Exception as e:
                logger.error(f"Replica {i} health check failed: {e}")
                if i < len(self._metrics["errors"]["replicas"]):
                    self._metrics["errors"]["replicas"][i] += 1
                else:
                    self._metrics["errors"]["replicas"].append(1)
                
                # Remove unhealthy replica from rotation
                if engine in self.read_engines:
                    self.read_engines.remove(engine)
                    logger.warning(f"Removed unhealthy replica {i} from rotation")
    
    async def close(self):
        """Close all database connections."""
        logger.info("Closing database connections...")
        
        # Cancel health check
        if self._health_check_task:
            self._health_check_task.cancel()
            try:
                await self._health_check_task
            except asyncio.CancelledError:
                pass
        
        # Close all engines
        if self.primary_engine:
            await self.primary_engine.dispose()
        
        for engine in self.read_engines:
            await engine.dispose()
        
        if self.pgbouncer_engine:
            await self.pgbouncer_engine.dispose()
        
        logger.info("Database connections closed")
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get database metrics."""
        return {
            **self._metrics,
            "connection_pools": {
                "primary": self.primary_engine.pool.status() if self.primary_engine else None,
                "replicas": [
                    engine.pool.status() for engine in self.read_engines
                ] if self.read_engines else [],
                "pgbouncer": self.pgbouncer_engine.pool.status() if self.pgbouncer_engine else None
            }
        }


# Global database manager instance
db_manager = DatabaseManager()


@asynccontextmanager
async def get_primary_db():
    """Get primary database session for writes."""
    async with await db_manager.get_primary_session() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


@asynccontextmanager
async def get_read_db():
    """Get read database session with load balancing."""
    async with await db_manager.get_read_session() as session:
        try:
            yield session
        finally:
            await session.close()


# Dependency for FastAPI
async def get_db():
    """FastAPI dependency for database session."""
    async with await db_manager.get_primary_session() as session:
        try:
            yield session
        finally:
            await session.close()


async def get_read_only_db():
    """FastAPI dependency for read-only database session."""
    async with await db_manager.get_read_session() as session:
        try:
            yield session
        finally:
            await session.close()