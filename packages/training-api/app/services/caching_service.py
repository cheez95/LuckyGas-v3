import json
import hashlib
import pickle
from typing import Any, Optional, Union, Callable, List, Dict
from datetime import datetime, timedelta
from functools import wraps
import asyncio
import redis.asyncio as redis

from app.core.config import settings


class CacheService:
    """Advanced caching service with multiple strategies."""
    
    def __init__(self, redis_client: redis.Redis):
        self.redis = redis_client
        self.default_ttl = 300  # 5 minutes
        self.cache_prefix = "training_cache"
        
        # Cache statistics
        self.stats = {
            "hits": 0,
            "misses": 0,
            "sets": 0,
            "deletes": 0
        }
    
    def _make_key(self, namespace: str, key: str) -> str:
        """Generate cache key with namespace."""
        return f"{self.cache_prefix}:{namespace}:{key}"
    
    def _serialize(self, value: Any) -> bytes:
        """Serialize value for storage."""
        try:
            # Try JSON first (more portable)
            return json.dumps(value).encode('utf-8')
        except (TypeError, ValueError):
            # Fall back to pickle for complex objects
            return pickle.dumps(value)
    
    def _deserialize(self, data: bytes) -> Any:
        """Deserialize value from storage."""
        try:
            # Try JSON first
            return json.loads(data.decode('utf-8'))
        except (json.JSONDecodeError, UnicodeDecodeError):
            # Fall back to pickle
            return pickle.loads(data)
    
    async def get(
        self,
        key: str,
        namespace: str = "default",
        default: Any = None
    ) -> Any:
        """Get value from cache."""
        cache_key = self._make_key(namespace, key)
        
        try:
            data = await self.redis.get(cache_key)
            if data is None:
                self.stats["misses"] += 1
                return default
            
            self.stats["hits"] += 1
            return self._deserialize(data)
        except Exception as e:
            print(f"Cache get error: {e}")
            self.stats["misses"] += 1
            return default
    
    async def set(
        self,
        key: str,
        value: Any,
        ttl: Optional[int] = None,
        namespace: str = "default",
        tags: Optional[List[str]] = None
    ) -> bool:
        """Set value in cache with optional tags."""
        cache_key = self._make_key(namespace, key)
        ttl = ttl or self.default_ttl
        
        try:
            serialized = self._serialize(value)
            
            # Use pipeline for atomic operations
            pipe = self.redis.pipeline()
            pipe.setex(cache_key, ttl, serialized)
            
            # Add to tag sets if provided
            if tags:
                for tag in tags:
                    tag_key = f"{self.cache_prefix}:tags:{tag}"
                    pipe.sadd(tag_key, cache_key)
                    pipe.expire(tag_key, ttl + 60)  # Slightly longer TTL
            
            await pipe.execute()
            self.stats["sets"] += 1
            return True
        except Exception as e:
            print(f"Cache set error: {e}")
            return False
    
    async def delete(
        self,
        key: str,
        namespace: str = "default"
    ) -> bool:
        """Delete value from cache."""
        cache_key = self._make_key(namespace, key)
        
        try:
            result = await self.redis.delete(cache_key)
            self.stats["deletes"] += 1
            return bool(result)
        except Exception as e:
            print(f"Cache delete error: {e}")
            return False
    
    async def delete_pattern(
        self,
        pattern: str,
        namespace: str = "default"
    ) -> int:
        """Delete all keys matching pattern."""
        pattern_key = self._make_key(namespace, pattern)
        deleted_count = 0
        
        try:
            # Use SCAN to avoid blocking
            cursor = 0
            while True:
                cursor, keys = await self.redis.scan(
                    cursor,
                    match=pattern_key,
                    count=100
                )
                
                if keys:
                    deleted_count += await self.redis.delete(*keys)
                
                if cursor == 0:
                    break
            
            self.stats["deletes"] += deleted_count
            return deleted_count
        except Exception as e:
            print(f"Cache delete pattern error: {e}")
            return 0
    
    async def delete_by_tags(self, tags: Union[str, List[str]]) -> int:
        """Delete all cached items with specified tags."""
        if isinstance(tags, str):
            tags = [tags]
        
        deleted_count = 0
        
        try:
            for tag in tags:
                tag_key = f"{self.cache_prefix}:tags:{tag}"
                
                # Get all keys with this tag
                keys = await self.redis.smembers(tag_key)
                
                if keys:
                    # Delete the cached items
                    deleted_count += await self.redis.delete(*keys)
                    
                    # Delete the tag set
                    await self.redis.delete(tag_key)
            
            self.stats["deletes"] += deleted_count
            return deleted_count
        except Exception as e:
            print(f"Cache delete by tags error: {e}")
            return 0
    
    async def clear_namespace(self, namespace: str) -> int:
        """Clear all keys in a namespace."""
        return await self.delete_pattern("*", namespace)
    
    async def get_or_set(
        self,
        key: str,
        factory: Callable,
        ttl: Optional[int] = None,
        namespace: str = "default",
        tags: Optional[List[str]] = None
    ) -> Any:
        """Get from cache or compute and set."""
        # Try to get from cache first
        cached = await self.get(key, namespace)
        if cached is not None:
            return cached
        
        # Compute value
        if asyncio.iscoroutinefunction(factory):
            value = await factory()
        else:
            value = factory()
        
        # Cache the result
        await self.set(key, value, ttl, namespace, tags)
        
        return value
    
    async def increment(
        self,
        key: str,
        amount: int = 1,
        namespace: str = "counters"
    ) -> int:
        """Increment a counter."""
        cache_key = self._make_key(namespace, key)
        
        try:
            return await self.redis.incrby(cache_key, amount)
        except Exception as e:
            print(f"Cache increment error: {e}")
            return 0
    
    async def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        total_ops = sum(self.stats.values())
        hit_rate = (
            self.stats["hits"] / (self.stats["hits"] + self.stats["misses"])
            if (self.stats["hits"] + self.stats["misses"]) > 0
            else 0
        )
        
        return {
            **self.stats,
            "total_operations": total_ops,
            "hit_rate": round(hit_rate * 100, 2),
            "info": await self.redis.info()
        }


class CacheWarmer:
    """Proactively warm cache with frequently accessed data."""
    
    def __init__(self, cache: CacheService):
        self.cache = cache
        self.warming_tasks = []
    
    async def warm_user_data(self, user_id: str):
        """Warm cache with user-specific data."""
        # This would typically fetch and cache:
        # - User profile
        # - Active enrollments
        # - Recent progress
        # - Achievements
        pass
    
    async def warm_course_data(self, course_id: str):
        """Warm cache with course data."""
        # This would typically fetch and cache:
        # - Course details
        # - Module list
        # - Video URLs
        # - Materials
        pass
    
    async def warm_popular_content(self):
        """Warm cache with popular content."""
        # This would typically:
        # - Query for most accessed courses
        # - Cache their data
        # - Pre-compute expensive aggregations
        pass


class CacheKeyBuilder:
    """Utility for building consistent cache keys."""
    
    @staticmethod
    def user_profile(user_id: str) -> str:
        return f"user:{user_id}:profile"
    
    @staticmethod
    def user_enrollments(user_id: str) -> str:
        return f"user:{user_id}:enrollments"
    
    @staticmethod
    def course_details(course_id: str) -> str:
        return f"course:{course_id}:details"
    
    @staticmethod
    def course_modules(course_id: str) -> str:
        return f"course:{course_id}:modules"
    
    @staticmethod
    def module_content(module_id: str) -> str:
        return f"module:{module_id}:content"
    
    @staticmethod
    def analytics_dashboard(department: Optional[str] = None) -> str:
        dept = department or "all"
        return f"analytics:dashboard:{dept}"
    
    @staticmethod
    def leaderboard(timeframe: str = "all", department: Optional[str] = None) -> str:
        dept = department or "all"
        return f"leaderboard:{timeframe}:{dept}"
    
    @staticmethod
    def user_progress(user_id: str, course_id: str) -> str:
        return f"progress:{user_id}:{course_id}"


# Cache decorator
def cache_result(
    ttl: int = 300,
    namespace: str = "default",
    key_builder: Optional[Callable] = None,
    tags: Optional[List[str]] = None
):
    """Decorator to cache function results."""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Get cache service from somewhere (e.g., dependency injection)
            cache_service = getattr(args[0], 'cache', None) if args else None
            if not cache_service:
                # No cache available, just execute function
                return await func(*args, **kwargs)
            
            # Build cache key
            if key_builder:
                cache_key = key_builder(*args, **kwargs)
            else:
                # Default key builder using function name and arguments
                key_parts = [func.__name__]
                key_parts.extend(str(arg) for arg in args[1:])  # Skip self
                key_parts.extend(f"{k}={v}" for k, v in sorted(kwargs.items()))
                cache_key = ":".join(key_parts)
            
            # Try to get from cache
            cached = await cache_service.get(cache_key, namespace)
            if cached is not None:
                return cached
            
            # Execute function
            result = await func(*args, **kwargs)
            
            # Cache the result
            await cache_service.set(cache_key, result, ttl, namespace, tags)
            
            return result
        
        return wrapper
    return decorator


# Global cache instance (initialized in app startup)
cache_service: Optional[CacheService] = None


async def init_cache_service(redis_client: redis.Redis):
    """Initialize global cache service."""
    global cache_service
    cache_service = CacheService(redis_client)