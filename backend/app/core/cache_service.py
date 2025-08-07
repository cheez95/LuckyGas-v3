"""
Redis caching service for API optimization
"""

import json
import hashlib
from typing import Any, Optional, Union, Callable
from datetime import timedelta
import redis
from redis.exceptions import RedisError
from functools import wraps
import pickle
import logging

from app.core.config import settings

logger = logging.getLogger(__name__)


class CacheService:
    """Redis caching service with automatic serialization and TTL management"""
    
    def __init__(self):
        self.redis_client: Optional[redis.Redis] = None
        self.is_connected = False
        self._connect()
    
    def _connect(self):
        """Establish Redis connection with retry logic"""
        try:
            # Use Redis URL from environment or default to localhost
            redis_url = getattr(settings, 'REDIS_URL', 'redis://localhost:6379/0')
            
            self.redis_client = redis.from_url(
                redis_url,
                decode_responses=False,  # We'll handle encoding/decoding ourselves
                socket_connect_timeout=5,
                socket_timeout=5,
                retry_on_timeout=True,
                health_check_interval=30
            )
            
            # Test connection
            self.redis_client.ping()
            self.is_connected = True
            logger.info("Redis connection established")
            
        except (RedisError, Exception) as e:
            logger.warning(f"Redis connection failed: {e}. Cache will be disabled.")
            self.is_connected = False
    
    def _make_key(self, key: str, namespace: str = None) -> str:
        """Generate a namespaced cache key"""
        if namespace:
            return f"luckygas:{namespace}:{key}"
        return f"luckygas:{key}"
    
    def _serialize(self, value: Any) -> bytes:
        """Serialize value for Redis storage"""
        try:
            # Try JSON first (faster and more portable)
            return json.dumps(value).encode('utf-8')
        except (TypeError, ValueError):
            # Fall back to pickle for complex objects
            return pickle.dumps(value)
    
    def _deserialize(self, value: bytes) -> Any:
        """Deserialize value from Redis"""
        if not value:
            return None
        
        try:
            # Try JSON first
            return json.loads(value.decode('utf-8'))
        except (json.JSONDecodeError, UnicodeDecodeError):
            # Fall back to pickle
            try:
                return pickle.loads(value)
            except Exception as e:
                logger.error(f"Failed to deserialize cache value: {e}")
                return None
    
    def get(self, key: str, namespace: str = None) -> Optional[Any]:
        """Get value from cache"""
        if not self.is_connected:
            return None
        
        try:
            full_key = self._make_key(key, namespace)
            value = self.redis_client.get(full_key)
            
            if value:
                logger.debug(f"Cache hit: {full_key}")
                return self._deserialize(value)
            
            logger.debug(f"Cache miss: {full_key}")
            return None
            
        except RedisError as e:
            logger.error(f"Redis get error: {e}")
            return None
    
    def set(
        self, 
        key: str, 
        value: Any, 
        ttl: Union[int, timedelta] = 3600,
        namespace: str = None
    ) -> bool:
        """Set value in cache with TTL"""
        if not self.is_connected:
            return False
        
        try:
            full_key = self._make_key(key, namespace)
            serialized = self._serialize(value)
            
            # Convert timedelta to seconds
            if isinstance(ttl, timedelta):
                ttl = int(ttl.total_seconds())
            
            success = self.redis_client.setex(full_key, ttl, serialized)
            
            if success:
                logger.debug(f"Cache set: {full_key} (TTL: {ttl}s)")
            
            return bool(success)
            
        except RedisError as e:
            logger.error(f"Redis set error: {e}")
            return False
    
    def delete(self, key: str, namespace: str = None) -> bool:
        """Delete value from cache"""
        if not self.is_connected:
            return False
        
        try:
            full_key = self._make_key(key, namespace)
            deleted = self.redis_client.delete(full_key)
            
            if deleted:
                logger.debug(f"Cache deleted: {full_key}")
            
            return bool(deleted)
            
        except RedisError as e:
            logger.error(f"Redis delete error: {e}")
            return False
    
    def delete_pattern(self, pattern: str, namespace: str = None) -> int:
        """Delete all keys matching a pattern"""
        if not self.is_connected:
            return 0
        
        try:
            full_pattern = self._make_key(pattern, namespace)
            
            # Use SCAN to avoid blocking with KEYS
            deleted_count = 0
            for key in self.redis_client.scan_iter(match=full_pattern):
                if self.redis_client.delete(key):
                    deleted_count += 1
            
            logger.debug(f"Cache pattern deleted: {full_pattern} ({deleted_count} keys)")
            return deleted_count
            
        except RedisError as e:
            logger.error(f"Redis delete pattern error: {e}")
            return 0
    
    def exists(self, key: str, namespace: str = None) -> bool:
        """Check if key exists in cache"""
        if not self.is_connected:
            return False
        
        try:
            full_key = self._make_key(key, namespace)
            return bool(self.redis_client.exists(full_key))
            
        except RedisError as e:
            logger.error(f"Redis exists error: {e}")
            return False
    
    def increment(self, key: str, amount: int = 1, namespace: str = None) -> Optional[int]:
        """Increment a counter in cache"""
        if not self.is_connected:
            return None
        
        try:
            full_key = self._make_key(key, namespace)
            return self.redis_client.incr(full_key, amount)
            
        except RedisError as e:
            logger.error(f"Redis increment error: {e}")
            return None
    
    def get_ttl(self, key: str, namespace: str = None) -> Optional[int]:
        """Get remaining TTL for a key"""
        if not self.is_connected:
            return None
        
        try:
            full_key = self._make_key(key, namespace)
            ttl = self.redis_client.ttl(full_key)
            
            # Redis returns -2 if key doesn't exist, -1 if no TTL
            if ttl >= 0:
                return ttl
            return None
            
        except RedisError as e:
            logger.error(f"Redis TTL error: {e}")
            return None
    
    def flush_all(self) -> bool:
        """Flush all cache entries (use with caution!)"""
        if not self.is_connected:
            return False
        
        try:
            # Only flush keys with our namespace
            deleted = self.delete_pattern("*", "")
            logger.warning(f"Cache flushed: {deleted} keys deleted")
            return True
            
        except RedisError as e:
            logger.error(f"Redis flush error: {e}")
            return False


# Singleton instance
cache_service = CacheService()


def cache_key_wrapper(
    ttl: Union[int, timedelta] = 3600,
    namespace: str = None,
    key_prefix: str = None,
    include_args: bool = True
):
    """
    Decorator for caching function results
    
    Args:
        ttl: Time to live in seconds or timedelta
        namespace: Cache namespace
        key_prefix: Custom key prefix
        include_args: Include function arguments in cache key
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            # Generate cache key
            if key_prefix:
                cache_key = key_prefix
            else:
                cache_key = f"{func.__module__}.{func.__name__}"
            
            # Include arguments in key if requested
            if include_args:
                # Create a hash of arguments for the key
                args_str = str(args) + str(sorted(kwargs.items()))
                args_hash = hashlib.md5(args_str.encode()).hexdigest()[:8]
                cache_key = f"{cache_key}:{args_hash}"
            
            # Try to get from cache
            cached = cache_service.get(cache_key, namespace)
            if cached is not None:
                return cached
            
            # Execute function
            result = await func(*args, **kwargs)
            
            # Store in cache
            cache_service.set(cache_key, result, ttl, namespace)
            
            return result
        
        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            # Generate cache key
            if key_prefix:
                cache_key = key_prefix
            else:
                cache_key = f"{func.__module__}.{func.__name__}"
            
            # Include arguments in key if requested
            if include_args:
                # Create a hash of arguments for the key
                args_str = str(args) + str(sorted(kwargs.items()))
                args_hash = hashlib.md5(args_str.encode()).hexdigest()[:8]
                cache_key = f"{cache_key}:{args_hash}"
            
            # Try to get from cache
            cached = cache_service.get(cache_key, namespace)
            if cached is not None:
                return cached
            
            # Execute function
            result = func(*args, **kwargs)
            
            # Store in cache
            cache_service.set(cache_key, result, ttl, namespace)
            
            return result
        
        # Return appropriate wrapper based on function type
        import asyncio
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper
    
    return decorator


# Cache invalidation helpers
def invalidate_customer_cache(customer_id: int):
    """Invalidate all cache entries for a customer"""
    cache_service.delete_pattern(f"customer:{customer_id}:*", "api")
    cache_service.delete_pattern(f"*:customer_{customer_id}:*", "api")


def invalidate_order_cache(order_id: int = None, customer_id: int = None):
    """Invalidate order-related cache entries"""
    if order_id:
        cache_service.delete_pattern(f"order:{order_id}:*", "api")
    if customer_id:
        cache_service.delete_pattern(f"orders:customer_{customer_id}:*", "api")
    # Invalidate order lists
    cache_service.delete_pattern("orders:list:*", "api")


def invalidate_route_cache(route_id: int = None):
    """Invalidate route-related cache entries"""
    if route_id:
        cache_service.delete_pattern(f"route:{route_id}:*", "api")
    # Invalidate route lists and optimizations
    cache_service.delete_pattern("routes:*", "api")
    cache_service.delete_pattern("optimization:*", "api")


# Export all
__all__ = [
    'cache_service',
    'cache_key_wrapper',
    'invalidate_customer_cache',
    'invalidate_order_cache',
    'invalidate_route_cache',
]