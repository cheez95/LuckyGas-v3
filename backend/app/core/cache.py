"""
Redis caching service for performance optimization
"""

import asyncio
import json
import logging
from datetime import timedelta
from functools import wraps
from typing import Any, Callable, Optional, Union

from redis import asyncio as aioredis

from app.core.config import settings

logger = logging.getLogger(__name__)


class CacheService:
    """
    Redis caching service with async support
    """

    def __init__(self):
        self.redis: Optional[aioredis.Redis] = None
        self._connected = False

    async def connect(self):
        """Connect to Redis"""
        if self._connected:
            return

        try:
            self.redis = await aioredis.from_url(
                settings.REDIS_URL,
                encoding="utf-8",
                decode_responses=True,
                socket_connect_timeout=5,
                socket_timeout=5,
                retry_on_timeout=True,
                health_check_interval=30,
            )
            await self.redis.ping()
            self._connected = True
            logger.info("Connected to Redis successfully")
        except Exception as e:
            logger.error(f"Failed to connect to Redis: {e}")
            self._connected = False

    async def disconnect(self):
        """Disconnect from Redis"""
        if self.redis:
            await self.redis.close()
            self._connected = False

    async def get(self, key: str) -> Optional[Any]:
        """Get value from cache"""
        if not self._connected:
            return None

        try:
            value = await self.redis.get(key)
            if value:
                return json.loads(value)
            return None
        except Exception as e:
            logger.error(f"Cache get error for key {key}: {e}")
            return None

    async def set(
        self, key: str, value: Any, expire: Optional[Union[int, timedelta]] = None
    ) -> bool:
        """Set value in cache with optional expiration"""
        if not self._connected:
            return False

        try:
            serialized = json.dumps(value, default=str, ensure_ascii=False)

            if expire:
                if isinstance(expire, timedelta):
                    expire = int(expire.total_seconds())
                await self.redis.setex(key, expire, serialized)
            else:
                await self.redis.set(key, serialized)
            return True
        except Exception as e:
            logger.error(f"Cache set error for key {key}: {e}")
            return False

    async def delete(self, key: str) -> bool:
        """Delete a key from cache"""
        if not self._connected:
            return False

        try:
            await self.redis.delete(key)
            return True
        except Exception as e:
            logger.error(f"Cache delete error for key {key}: {e}")
            return False

    async def invalidate(self, pattern: str) -> int:
        """Invalidate cache keys matching pattern"""
        if not self._connected:
            return 0

        try:
            keys = []
            async for key in self.redis.scan_iter(match=pattern):
                keys.append(key)

            if keys:
                deleted = await self.redis.delete(*keys)
                logger.info(
                    f"Invalidated {deleted} cache keys matching pattern: {pattern}"
                )
                return deleted
            return 0
        except Exception as e:
            logger.error(f"Cache invalidate error for pattern {pattern}: {e}")
            return 0

    async def cached(
        self, key: str, func: Callable, expire: Optional[Union[int, timedelta]] = None
    ) -> Any:
        """Get value from cache or execute function and cache result"""
        # Try to get from cache
        cached_value = await self.get(key)
        if cached_value is not None:
            logger.debug(f"Cache hit for key: {key}")
            return cached_value

        # Execute function and cache result
        logger.debug(f"Cache miss for key: {key}")
        result = await func()
        await self.set(key, result, expire)
        return result

    async def increment(self, key: str, amount: int = 1) -> Optional[int]:
        """Increment a counter in cache"""
        if not self._connected:
            return None

        try:
            return await self.redis.incr(key, amount)
        except Exception as e:
            logger.error(f"Cache increment error for key {key}: {e}")
            return None

    async def decrement(self, key: str, amount: int = 1) -> Optional[int]:
        """Decrement a counter in cache"""
        if not self._connected:
            return None

        try:
            return await self.redis.decr(key, amount)
        except Exception as e:
            logger.error(f"Cache decrement error for key {key}: {e}")
            return None

    async def exists(self, key: str) -> bool:
        """Check if key exists in cache"""
        if not self._connected:
            return False

        try:
            return await self.redis.exists(key) > 0
        except Exception as e:
            logger.error(f"Cache exists error for key {key}: {e}")
            return False

    async def ttl(self, key: str) -> Optional[int]:
        """Get time to live for a key in seconds"""
        if not self._connected:
            return None

        try:
            ttl = await self.redis.ttl(key)
            return ttl if ttl >= 0 else None
        except Exception as e:
            logger.error(f"Cache TTL error for key {key}: {e}")
            return None


# Global cache instance
cache = CacheService()


async def get_redis_client():
    """Get Redis client instance for monitoring components"""
    if not cache._connected:
        await cache.connect()
    return cache.redis


def cache_key(*args, **kwargs) -> str:
    """Generate cache key from arguments"""
    parts = [str(arg) for arg in args]
    if kwargs:
        parts.extend(f"{k}:{v}" for k, v in sorted(kwargs.items()))
    return ":".join(parts)


def cache_result(
    key_prefix: str, expire: Optional[Union[int, timedelta]] = timedelta(hours=1)
):
    """
    Decorator to cache function results

    Usage:
        @cache_result("customer", expire=timedelta(hours=2))
        async def get_customer(customer_id: int):
            # Expensive operation
            return customer_data
    """

    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Generate cache key
            key = cache_key(key_prefix, func.__name__, *args, **kwargs)

            # Try to get from cache
            cached = await cache.get(key)
            if cached is not None:
                return cached

            # Execute function and cache result
            result = await func(*args, **kwargs)
            if result is not None:
                await cache.set(key, result, expire)
            return result

        return wrapper

    return decorator


def invalidate_cache(pattern: str):
    """
    Decorator to invalidate cache after function execution

    Usage:
        @invalidate_cache("customer:*")
        async def update_customer(customer_id: int, data: dict):
            # Update operation
            return updated_customer
    """

    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            result = await func(*args, **kwargs)
            await cache.invalidate(pattern)
            return result

        return wrapper

    return decorator


# Cache key patterns for different entities
class CacheKeys:
    """Standardized cache key patterns"""

    # Customer cache keys
    CUSTOMER = "customer:{customer_id}"
    CUSTOMER_LIST = "customers:list:{skip}:{limit}"
    CUSTOMER_STATS = "customer:stats:{customer_id}"

    # Order cache keys
    ORDER = "order:{order_id}"
    ORDER_LIST = "orders:list:{skip}:{limit}:{status}"
    ORDER_DAILY_COUNT = "orders:daily_count:{date}"

    # Route cache keys
    ROUTE = "route:{route_id}"
    ROUTE_LIST = "routes:list:{date}:{area}"
    ROUTE_DRIVER = "route:driver:{driver_id}:{date}"
    ROUTE_OPTIMIZATION = "route:optimization:{date}:{area}"

    # Prediction cache keys
    PREDICTION_CUSTOMER = "prediction:customer:{customer_id}"
    PREDICTION_BATCH = "prediction:batch:{date}"
    PREDICTION_METRICS = "prediction:metrics"

    # Statistics cache keys
    STATS_DASHBOARD = "stats:dashboard:{date}"
    STATS_REVENUE = "stats:revenue:{start_date}:{end_date}"
    STATS_PERFORMANCE = "stats:performance:{driver_id}:{month}"

    @staticmethod
    def format(pattern: str, **kwargs) -> str:
        """Format cache key with parameters"""
        return pattern.format(**kwargs)
