"""
Database metrics tracking utilities
"""
import time
import asyncio
import functools
from typing import Any, Callable, TypeVar, Optional
from contextlib import asynccontextmanager
import logging

from app.core.metrics import (
    db_query_counter,
    db_query_duration_histogram,
    db_connection_pool_gauge
)

logger = logging.getLogger(__name__)

T = TypeVar('T')


def track_db_query(operation: str, table: str):
    """
    Decorator to track database query metrics
    
    Args:
        operation: Type of operation (select, insert, update, delete)
        table: Table name being queried
    """
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @functools.wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> T:
            # Start timer
            start_time = time.time()
            
            try:
                # Execute query
                result = await func(*args, **kwargs)
                
                # Track successful query
                db_query_counter.labels(
                    operation=operation,
                    table=table
                ).inc()
                
                # Track query duration
                duration = time.time() - start_time
                db_query_duration_histogram.labels(
                    operation=operation,
                    table=table
                ).observe(duration)
                
                return result
                
            except Exception as e:
                # Track failed query
                db_query_counter.labels(
                    operation=f"{operation}_error",
                    table=table
                ).inc()
                
                logger.error(f"Database query error: {operation} on {table} - {str(e)}")
                raise
        
        return wrapper
    return decorator


@asynccontextmanager
async def track_query_context(operation: str, table: str):
    """
    Context manager to track database query metrics
    
    Usage:
        async with track_query_context("select", "customers"):
            result = await db.execute(query)
    """
    start_time = time.time()
    
    try:
        yield
        
        # Track successful query
        db_query_counter.labels(
            operation=operation,
            table=table
        ).inc()
        
        # Track query duration
        duration = time.time() - start_time
        db_query_duration_histogram.labels(
            operation=operation,
            table=table
        ).observe(duration)
        
    except Exception as e:
        # Track failed query
        db_query_counter.labels(
            operation=f"{operation}_error",
            table=table
        ).inc()
        
        logger.error(f"Database query error: {operation} on {table} - {str(e)}")
        raise


def update_connection_pool_metrics(engine):
    """
    Update connection pool metrics from SQLAlchemy engine
    
    Args:
        engine: SQLAlchemy engine instance
    """
    try:
        pool = engine.pool
        
        # Update pool metrics
        db_connection_pool_gauge.labels(status="active").set(pool.checkedout())
        db_connection_pool_gauge.labels(status="idle").set(pool.size() - pool.checkedout())
        db_connection_pool_gauge.labels(status="overflow").set(pool.overflow())
        
    except Exception as e:
        logger.error(f"Error updating connection pool metrics: {str(e)}")


class DatabaseMetricsCollector:
    """
    Background task to collect database metrics periodically
    """
    
    def __init__(self, engine):
        self.engine = engine
        self.running = False
    
    async def start(self):
        """Start collecting metrics"""
        self.running = True
        
        while self.running:
            try:
                update_connection_pool_metrics(self.engine)
                await asyncio.sleep(10)  # Update every 10 seconds
            except Exception as e:
                logger.error(f"Error in metrics collector: {str(e)}")
                await asyncio.sleep(60)  # Wait longer on error
    
    def stop(self):
        """Stop collecting metrics"""
        self.running = False