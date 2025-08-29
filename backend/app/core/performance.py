"""
Performance optimizations for high-data, low-concurrency pattern
Designed for: 350,000+ records, 15 concurrent users
"""
import time
import logging
from functools import wraps, lru_cache
from datetime import datetime, timedelta
import hashlib
import json

from sqlalchemy.orm import Session
from sqlalchemy import text

logger = logging.getLogger(__name__)


# ============================================================================
# QUERY PERFORMANCE MONITORING
# ============================================================================

def log_slow_query(threshold_ms: float = 100):
    """
    Decorator to log slow database queries
    
    Args:
        threshold_ms: Log queries slower than this (default 100ms)
    """
    def decorator(func):
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            start = time.time()
            try:
                result = await func(*args, **kwargs)
                duration_ms = (time.time() - start) * 1000
                
                if duration_ms > threshold_ms:
                    logger.warning(
                        f"Slow query in {func.__name__}: {duration_ms:.2f}ms"
                    )
                
                return result
            except Exception as e:
                duration_ms = (time.time() - start) * 1000
                logger.error(
                    f"Query failed in {func.__name__} after {duration_ms:.2f}ms: {e}"
                )
                raise
        
        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            start = time.time()
            try:
                result = func(*args, **kwargs)
                duration_ms = (time.time() - start) * 1000
                
                if duration_ms > threshold_ms:
                    logger.warning(
                        f"Slow query in {func.__name__}: {duration_ms:.2f}ms"
                    )
                
                return result
            except Exception as e:
                duration_ms = (time.time() - start) * 1000
                logger.error(
                    f"Query failed in {func.__name__} after {duration_ms:.2f}ms: {e}"
                )
                raise
        
        # Return appropriate wrapper based on function type
        import asyncio
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper
    
    return decorator


# ============================================================================
# IN-MEMORY CACHING (Perfect for 15 users)
# ============================================================================

class SimpleCache:
    """Simple TTL-based cache for frequently accessed data"""
    
    def __init__(self, ttl_seconds: int = 300):
        """
        Initialize cache with TTL
        
        Args:
            ttl_seconds: Time to live in seconds (default 5 minutes)
        """
        self._cache: Dict[str, tuple[Any, float]] = {}
        self.ttl_seconds = ttl_seconds
        self.hits = 0
        self.misses = 0
    
    def get(self, key: str) -> Optional[Any]:
        """Get value from cache if not expired"""
        if key in self._cache:
            value, timestamp = self._cache[key]
            if time.time() - timestamp < self.ttl_seconds:
                self.hits += 1
                return value
            else:
                # Expired, remove it
                del self._cache[key]
        
        self.misses += 1
        return None
    
    def set(self, key: str, value: Any):
        """Set value in cache with current timestamp"""
        self._cache[key] = (value, time.time())
    
    def clear(self):
        """Clear all cache entries"""
        self._cache.clear()
        self.hits = 0
        self.misses = 0
    
    def get_stats(self) -> dict:
        """Get cache statistics"""
        total = self.hits + self.misses
        hit_rate = (self.hits / total * 100) if total > 0 else 0
        
        return {
            'entries': len(self._cache),
            'hits': self.hits,
            'misses': self.misses,
            'hit_rate': f"{hit_rate:.1f}%"
        }


# Global cache instances for different data types
customer_cache = SimpleCache(ttl_seconds=600)  # 10 minutes
delivery_cache = SimpleCache(ttl_seconds=300)  # 5 minutes
route_cache = SimpleCache(ttl_seconds=60)      # 1 minute (changes frequently)


def cached_result(cache_instance: SimpleCache, key_prefix: str = ""):
    """
    Decorator to cache function results
    
    Args:
        cache_instance: Cache instance to use
        key_prefix: Prefix for cache keys
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Create cache key from function name and arguments
            cache_key = f"{key_prefix}:{func.__name__}:{str(args)}:{str(kwargs)}"
            cache_key = hashlib.md5(cache_key.encode()).hexdigest()
            
            # Check cache
            cached = cache_instance.get(cache_key)
            if cached is not None:
                return cached
            
            # Execute function and cache result
            result = func(*args, **kwargs)
            cache_instance.set(cache_key, result)
            
            return result
        
        return wrapper
    return decorator


# ============================================================================
# EFFICIENT PAGINATION
# ============================================================================

class CursorPagination:
    """Cursor-based pagination for large datasets"""
    
    @staticmethod
    def paginate_query(
        query,
        cursor_field: str,
        cursor_value: Optional[Any] = None,
        limit: int = 50,
        descending: bool = True
    ):
        """
        Apply cursor-based pagination to a query
        
        Args:
            query: SQLAlchemy query object
            cursor_field: Field to use for cursor (must be unique and ordered)
            cursor_value: Current cursor value
            limit: Number of records per page
            descending: Whether to order descending
            
        Returns:
            Tuple of (results, next_cursor, has_more)
        """
        # Apply cursor filter
        if cursor_value is not None:
            if descending:
                query = query.filter(text(f"{cursor_field} < :cursor")).params(cursor=cursor_value)
            else:
                query = query.filter(text(f"{cursor_field} > :cursor")).params(cursor=cursor_value)
        
        # Apply ordering
        if descending:
            query = query.order_by(text(f"{cursor_field} DESC"))
        else:
            query = query.order_by(text(f"{cursor_field} ASC"))
        
        # Fetch one extra to check if there are more
        results = query.limit(limit + 1).all()
        
        has_more = len(results) > limit
        results = results[:limit]
        
        # Get next cursor from last result
        next_cursor = None
        if results and has_more:
            last_item = results[-1]
            next_cursor = getattr(last_item, cursor_field.split('.')[-1])
        
        return results, next_cursor, has_more


# ============================================================================
# BATCH OPERATIONS
# ============================================================================

def batch_insert(session: Session, model_class, records: List[dict], batch_size: int = 1000):
    """
    Efficiently insert large number of records in batches
    
    Args:
        session: Database session
        model_class: SQLAlchemy model class
        records: List of dictionaries with record data
        batch_size: Number of records per batch
    """
    total = len(records)
    inserted = 0
    
    for i in range(0, total, batch_size):
        batch = records[i:i + batch_size]
        
        # Use bulk_insert_mappings for efficiency
        session.bulk_insert_mappings(model_class, batch)
        session.commit()
        
        inserted += len(batch)
        logger.info(f"Inserted {inserted}/{total} records")
    
    return inserted


def batch_update(session: Session, model_class, updates: List[dict], batch_size: int = 500):
    """
    Efficiently update large number of records in batches
    
    Args:
        session: Database session
        model_class: SQLAlchemy model class
        updates: List of dictionaries with 'id' and update data
        batch_size: Number of records per batch
    """
    total = len(updates)
    updated = 0
    
    for i in range(0, total, batch_size):
        batch = updates[i:i + batch_size]
        
        # Use bulk_update_mappings for efficiency
        session.bulk_update_mappings(model_class, batch)
        session.commit()
        
        updated += len(batch)
        logger.info(f"Updated {updated}/{total} records")
    
    return updated


# ============================================================================
# QUERY OPTIMIZATION HELPERS
# ============================================================================

class QueryOptimizer:
    """Helper class for query optimization"""
    
    @staticmethod
    def explain_query(session: Session, query_string: str) -> str:
        """
        Get query execution plan (PostgreSQL)
        
        Args:
            session: Database session
            query_string: SQL query to explain
            
        Returns:
            Execution plan as string
        """
        if 'postgresql' not in str(session.bind.url):
            return "EXPLAIN only available for PostgreSQL"
        
        result = session.execute(text(f"EXPLAIN ANALYZE {query_string}"))
        return '\n'.join([row[0] for row in result])
    
    @staticmethod
    def get_table_stats(session: Session, table_name: str) -> dict:
        """
        Get table statistics
        
        Args:
            session: Database session
            table_name: Name of the table
            
        Returns:
            Dictionary with table statistics
        """
        stats = {}
        
        # Get row count
        count = session.execute(
            text(f"SELECT COUNT(*) FROM {table_name}")
        ).scalar()
        stats['row_count'] = count
        
        if 'postgresql' in str(session.bind.url):
            # Get table size
            size_result = session.execute(
                text(f"""
                SELECT 
                    pg_size_pretty(pg_total_relation_size('{table_name}')) as total_size,
                    pg_size_pretty(pg_relation_size('{table_name}')) as table_size,
                    pg_size_pretty(pg_indexes_size('{table_name}')) as indexes_size
                """)
            ).first()
            
            if size_result:
                stats['total_size'] = size_result[0]
                stats['table_size'] = size_result[1]
                stats['indexes_size'] = size_result[2]
        
        return stats
    
    @staticmethod
    def find_missing_indexes(session: Session) -> List[str]:
        """
        Suggest missing indexes based on query patterns (PostgreSQL)
        
        Returns:
            List of suggested CREATE INDEX statements
        """
        if 'postgresql' not in str(session.bind.url):
            return []
        
        # Query to find tables with sequential scans
        result = session.execute(text("""
            SELECT 
                schemaname,
                tablename,
                seq_scan,
                seq_tup_read,
                idx_scan,
                idx_tup_fetch
            FROM pg_stat_user_tables
            WHERE seq_scan > idx_scan * 2
            AND seq_tup_read > 100000
            ORDER BY seq_tup_read DESC
        """))
        
        suggestions = []
        for row in result:
            table = row[1]
            suggestions.append(
                f"-- Consider adding index to {table} (high sequential scans)"
            )
        
        return suggestions


# ============================================================================
# SMART QUERY BUILDER
# ============================================================================

class SmartQueryBuilder:
    """Build optimized queries for common patterns"""
    
    @staticmethod
    def customer_delivery_history(
        session: Session,
        customer_id: int,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        limit: int = 100
    ):
        """
        Get customer delivery history with optimal query
        
        Uses index: idx_delivery_customer_date
        """
        query = """
        SELECT 
            d.id,
            d.delivery_date,
            d.delivered_50kg,
            d.delivered_20kg,
            d.delivered_16kg,
            d.delivered_10kg,
            d.amount_collected,
            d.is_successful,
            d.notes
        FROM deliveries d
        WHERE d.customer_id = :customer_id
        """
        
        params = {'customer_id': customer_id}
        
        if start_date:
            query += " AND d.delivery_date >= :start_date"
            params['start_date'] = start_date
        
        if end_date:
            query += " AND d.delivery_date <= :end_date"
            params['end_date'] = end_date
        
        query += " ORDER BY d.delivery_date DESC LIMIT :limit"
        params['limit'] = limit
        
        return session.execute(text(query), params).fetchall()
    
    @staticmethod
    def daily_summary(session: Session, date: datetime):
        """
        Get daily delivery summary
        
        Uses materialized view if available, otherwise calculates
        """
        # Try materialized view first
        try:
            result = session.execute(
                text("""
                SELECT * FROM daily_delivery_summary
                WHERE delivery_date = :date
                """),
                {'date': date}
            ).first()
            
            if result:
                return result._asdict()
        except:
            pass
        
        # Fallback to direct calculation
        result = session.execute(
            text("""
            SELECT 
                COUNT(*) as total_deliveries,
                COUNT(DISTINCT customer_id) as unique_customers,
                COUNT(DISTINCT route_id) as total_routes,
                SUM(CASE WHEN is_successful THEN 1 ELSE 0 END) as successful,
                SUM(amount_collected) as total_collected
            FROM deliveries
            WHERE delivery_date = :date
            """),
            {'date': date}
        ).first()
        
        return result._asdict() if result else {}


# ============================================================================
# DATABASE CONNECTION OPTIMIZATION
# ============================================================================

def get_optimized_engine_config() -> dict:
    """
    Get optimized database engine configuration for your pattern
    
    Returns:
        Dictionary of engine configuration options
    """
    return {
        # Connection pool settings (small for 15 users)
        'pool_size': 5,           # Base pool size
        'max_overflow': 5,        # Additional connections when needed
        'pool_timeout': 30,       # Timeout waiting for connection
        'pool_recycle': 3600,     # Recycle connections after 1 hour
        'pool_pre_ping': True,    # Test connections before using
        
        # Statement execution settings
        'echo': False,            # Don't log SQL (performance)
        'echo_pool': False,       # Don't log pool events
        
        # PostgreSQL specific
        'connect_args': {
            'connect_timeout': 10,
            'application_name': 'luckygas_backend',
            'options': '-c statement_timeout=30000'  # 30 second timeout
        }
    }


# ============================================================================
# PERFORMANCE MONITORING
# ============================================================================

class PerformanceMonitor:
    """Monitor and report on application performance"""
    
    def __init__(self):
        self.query_times: List[float] = []
        self.slow_queries: List[dict] = []
        self.start_time = time.time()
    
    def record_query(self, query_name: str, duration_ms: float):
        """Record query execution time"""
        self.query_times.append(duration_ms)
        
        if duration_ms > 100:  # Slow query threshold
            self.slow_queries.append({
                'query': query_name,
                'duration_ms': duration_ms,
                'timestamp': datetime.now()
            })
    
    def get_stats(self) -> dict:
        """Get performance statistics"""
        if not self.query_times:
            return {'status': 'No queries recorded'}
        
        uptime = time.time() - self.start_time
        
        return {
            'uptime_seconds': uptime,
            'total_queries': len(self.query_times),
            'avg_query_time_ms': sum(self.query_times) / len(self.query_times),
            'max_query_time_ms': max(self.query_times),
            'min_query_time_ms': min(self.query_times),
            'slow_queries_count': len(self.slow_queries),
            'cache_stats': {
                'customer': customer_cache.get_stats(),
                'delivery': delivery_cache.get_stats(),
                'route': route_cache.get_stats()
            }
        }
    
    def reset(self):
        """Reset performance statistics"""
        self.query_times.clear()
        self.slow_queries.clear()
        self.start_time = time.time()


# Global performance monitor instance
performance_monitor = PerformanceMonitor()