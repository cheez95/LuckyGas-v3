"""
Simple in-memory caching for Lucky Gas
Perfect for 15 concurrent users - no Redis needed!
"""
import time
import hashlib
import json
from functools import wraps, lru_cache
from typing import Any, Optional, Dict
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)


class SimpleCache:
    """
    Simple TTL-based in-memory cache
    Perfect for your scale - 15 users don't need Redis!
    """
    
    def __init__(self, ttl_seconds: int = 300, max_size: int = 1000):
        """
        Initialize cache
        
        Args:
            ttl_seconds: Time to live in seconds (default 5 minutes)
            max_size: Maximum number of items in cache
        """
        self._cache: Dict[str, tuple[Any, float]] = {}
        self.ttl_seconds = ttl_seconds
        self.max_size = max_size
        self.hits = 0
        self.misses = 0
    
    def _make_key(self, *args, **kwargs) -> str:
        """Create cache key from arguments"""
        key_str = f"{str(args)}:{str(sorted(kwargs.items()))}"
        return hashlib.md5(key_str.encode()).hexdigest()
    
    def get(self, key: str) -> Optional[Any]:
        """Get value from cache if not expired"""
        if key in self._cache:
            value, timestamp = self._cache[key]
            if time.time() - timestamp < self.ttl_seconds:
                self.hits += 1
                logger.debug(f"Cache HIT: {key[:8]}...")
                return value
            else:
                # Expired, remove it
                del self._cache[key]
                logger.debug(f"Cache EXPIRED: {key[:8]}...")
        
        self.misses += 1
        logger.debug(f"Cache MISS: {key[:8]}...")
        return None
    
    def set(self, key: str, value: Any):
        """Set value in cache with current timestamp"""
        # Check size limit
        if len(self._cache) >= self.max_size:
            # Remove oldest entry (simple FIFO)
            oldest_key = next(iter(self._cache))
            del self._cache[oldest_key]
            logger.debug(f"Cache EVICT: {oldest_key[:8]}... (size limit)")
        
        self._cache[key] = (value, time.time())
        logger.debug(f"Cache SET: {key[:8]}...")
    
    def clear(self):
        """Clear all cache entries"""
        self._cache.clear()
        self.hits = 0
        self.misses = 0
        logger.info("Cache cleared")
    
    def get_stats(self) -> dict:
        """Get cache statistics"""
        total = self.hits + self.misses
        hit_rate = (self.hits / total * 100) if total > 0 else 0
        
        return {
            'entries': len(self._cache),
            'hits': self.hits,
            'misses': self.misses,
            'hit_rate': f"{hit_rate:.1f}%",
            'memory_kb': len(str(self._cache)) / 1024  # Rough estimate
        }


# Global cache instances for different data types
customer_cache = SimpleCache(ttl_seconds=600, max_size=500)    # 10 minutes - customer data
delivery_cache = SimpleCache(ttl_seconds=300, max_size=1000)   # 5 minutes - delivery data
stats_cache = SimpleCache(ttl_seconds=900, max_size=100)       # 15 minutes - statistics
auth_cache = SimpleCache(ttl_seconds=1800, max_size=50)        # 30 minutes - auth tokens


def cache_result(cache_instance: SimpleCache = None, ttl_seconds: int = 300):
    """
    Decorator to cache function results
    
    Usage:
        @cache_result(ttl_seconds=600)
        def get_customer(customer_id: int):
            # Expensive database query
            return customer
    """
    if cache_instance is None:
        cache_instance = SimpleCache(ttl_seconds=ttl_seconds)
    
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Create cache key
            cache_key = cache_instance._make_key(func.__name__, *args, **kwargs)
            
            # Check cache
            cached_value = cache_instance.get(cache_key)
            if cached_value is not None:
                return cached_value
            
            # Execute function
            result = func(*args, **kwargs)
            
            # Cache result
            cache_instance.set(cache_key, result)
            
            return result
        
        # Add cache control methods
        wrapper.cache_clear = cache_instance.clear
        wrapper.cache_stats = cache_instance.get_stats
        
        return wrapper
    
    return decorator


# Specific cache decorators for common use cases
def cache_customer(ttl_seconds: int = 600):
    """Cache customer data for 10 minutes"""
    return cache_result(customer_cache, ttl_seconds)


def cache_delivery(ttl_seconds: int = 300):
    """Cache delivery data for 5 minutes"""
    return cache_result(delivery_cache, ttl_seconds)


def cache_stats(ttl_seconds: int = 900):
    """Cache statistics for 15 minutes"""
    return cache_result(stats_cache, ttl_seconds)


# LRU cache for frequently called functions
@lru_cache(maxsize=128)
def get_active_customers_cached(date_str: str):
    """
    Get active customers for a specific date
    Uses built-in LRU cache - perfect for your scale!
    
    Args:
        date_str: Date string (used for cache key)
    
    Note: In real implementation, this would query the database
    """
    # This is just a placeholder
    # Real implementation would query database
    return []


@lru_cache(maxsize=64)
def get_driver_schedule_cached(driver_id: int, date_str: str):
    """
    Get driver schedule for a specific date
    Cached because schedules don't change often during the day
    """
    # Placeholder for real implementation
    return []


# Cache management functions
def clear_all_caches():
    """Clear all cache instances"""
    customer_cache.clear()
    delivery_cache.clear()
    stats_cache.clear()
    auth_cache.clear()
    
    # Clear LRU caches
    get_active_customers_cached.cache_clear()
    get_driver_schedule_cached.cache_clear()
    
    logger.info("All caches cleared")


def get_all_cache_stats() -> dict:
    """Get statistics for all caches"""
    return {
        'customer_cache': customer_cache.get_stats(),
        'delivery_cache': delivery_cache.get_stats(),
        'stats_cache': stats_cache.get_stats(),
        'auth_cache': auth_cache.get_stats(),
        'lru_caches': {
            'active_customers': {
                'size': get_active_customers_cached.cache_info().currsize,
                'hits': get_active_customers_cached.cache_info().hits,
                'misses': get_active_customers_cached.cache_info().misses
            },
            'driver_schedule': {
                'size': get_driver_schedule_cached.cache_info().currsize,
                'hits': get_driver_schedule_cached.cache_info().hits,
                'misses': get_driver_schedule_cached.cache_info().misses
            }
        }
    }


# Scheduled cache clearing (call this periodically)
def scheduled_cache_maintenance():
    """
    Run this every hour to clear old cache entries
    Can be called from a cron job or scheduler
    """
    stats_before = get_all_cache_stats()
    
    # Clear caches that are too large
    for cache_name, cache in [
        ('customer', customer_cache),
        ('delivery', delivery_cache),
        ('stats', stats_cache),
        ('auth', auth_cache)
    ]:
        if cache.get_stats()['entries'] > cache.max_size * 0.8:
            logger.info(f"Cache {cache_name} is 80% full, clearing...")
            cache.clear()
    
    stats_after = get_all_cache_stats()
    logger.info(f"Cache maintenance complete. Before: {stats_before}, After: {stats_after}")


# Example usage in API endpoint
def example_cached_endpoint():
    """
    Example of how to use caching in endpoints
    """
    
    @cache_customer(ttl_seconds=600)
    def get_customer_summary(customer_id: int, date: str):
        """This expensive query will be cached for 10 minutes"""
        # Simulate expensive database query
        time.sleep(0.1)  # Pretend this takes 100ms
        return {
            'customer_id': customer_id,
            'date': date,
            'total_orders': 42,
            'total_amount': 1234.56
        }
    
    # First call - will be slow (100ms)
    result1 = get_customer_summary(1, "2024-01-20")
    
    # Second call - will be instant (from cache)
    result2 = get_customer_summary(1, "2024-01-20")
    
    # Check cache stats
    stats = get_customer_summary.cache_stats()
    print(f"Cache stats: {stats}")