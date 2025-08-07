"""
Google API Response Caching
"""

import hashlib
import json
import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

import redis.asyncio as redis

from app.core.cache import get_redis_client
from app.core.metrics import cache_operations_counter

logger = logging.getLogger(__name__)


class GoogleAPICache:
    """Intelligent caching for Google API responses"""

    # Cache TTLs by API type
    CACHE_TTLS = {
        "routes": timedelta(minutes=30),  # Route optimizations valid for 30 min
        "routes_matrix": timedelta(hours=1),  # Distance matrix valid for 1 hour
        "geocoding": timedelta(days=30),  # Addresses don't change often
        "reverse_geocoding": timedelta(days=7),  # Reverse geocoding updates weekly
        "places": timedelta(hours=24),  # Place data updates daily
        "place_details": timedelta(hours=12),  # Detailed place info
        "vertex_ai": timedelta(hours=1),  # Predictions expire hourly
        "static_maps": timedelta(days=7),  # Static map images
    }

    # Cache key prefixes
    CACHE_PREFIX = "google_api"

    def __init__(self, redis_client: Optional[redis.Redis] = None):
        self.redis = redis_client
        self._initialized = False

    async def _ensure_redis(self):
        """Ensure Redis client is initialized"""
        if not self._initialized:
            if not self.redis:
                self.redis = await get_redis_client()
            self._initialized = True

    def _generate_cache_key(self, api_type: str, params: Dict[str, Any]) -> str:
        """
        Generate consistent cache key from parameters

        Args:
            api_type: Type of API (routes, geocoding, etc.)
            params: API request parameters

        Returns:
            Cache key string
        """
        # Remove non - deterministic parameters
        filtered_params = {
            k: v
            for k, v in params.items()
            if k not in ["timestamp", "request_id", "session_id"]
        }

        # Sort parameters for consistent hashing
        sorted_params = json.dumps(filtered_params, sort_keys=True, ensure_ascii=True)

        # Generate hash
        param_hash = hashlib.sha256(sorted_params.encode()).hexdigest()[:16]

        return f"{self.CACHE_PREFIX}:{api_type}:{param_hash}"

    async def get(
        self, api_type: str, params: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """
        Get cached API response

        Args:
            api_type: Type of API
            params: Request parameters

        Returns:
            Cached response or None if not found
        """
        await self._ensure_redis()

        cache_key = self._generate_cache_key(api_type, params)

        try:
            cached = await self.redis.get(cache_key)

            if cached:
                # Parse cached data
                data = json.loads(cached)

                # Update metrics
                cache_operations_counter.labels(
                    operation="get", status="hit", api_type=api_type
                ).inc()

                logger.debug(f"Cache hit for {api_type}: {cache_key}")

                # Add cache metadata
                data["_cache_hit"] = True
                data["_cache_key"] = cache_key

                return data
            else:
                # Cache miss
                cache_operations_counter.labels(
                    operation="get", status="miss", api_type=api_type
                ).inc()

                logger.debug(f"Cache miss for {api_type}: {cache_key}")
                return None

        except json.JSONDecodeError as e:
            logger.error(f"Cache corruption detected for {cache_key}: {e}")
            # Delete corrupted cache entry
            await self.redis.delete(cache_key)
            return None

        except Exception as e:
            logger.error(f"Cache get error: {e}")
            cache_operations_counter.labels(
                operation="get", status="error", api_type=api_type
            ).inc()
            return None

    async def set(
        self,
        api_type: str,
        params: Dict[str, Any],
        response: Dict[str, Any],
        ttl_override: Optional[timedelta] = None,
    ) -> bool:
        """
        Cache API response

        Args:
            api_type: Type of API
            params: Request parameters
            response: API response to cache
            ttl_override: Override default TTL

        Returns:
            True if cached successfully
        """
        await self._ensure_redis()

        # Don't cache error responses
        if response.get("error") or response.get("status") == "error":
            logger.debug(f"Not caching error response for {api_type}")
            return False

        cache_key = self._generate_cache_key(api_type, params)
        ttl = ttl_override or self.CACHE_TTLS.get(api_type, timedelta(minutes=5))

        try:
            # Add cache metadata
            cache_data = response.copy()
            cache_data["_cached_at"] = datetime.now().isoformat()
            cache_data["_ttl_seconds"] = int(ttl.total_seconds())

            # Serialize and store
            serialized = json.dumps(cache_data, ensure_ascii=True)

            await self.redis.setex(cache_key, int(ttl.total_seconds()), serialized)

            # Update metrics
            cache_operations_counter.labels(
                operation="set", status="success", api_type=api_type
            ).inc()

            logger.debug(f"Cached {api_type} response for {ttl}: {cache_key}")
            return True

        except Exception as e:
            logger.error(f"Cache set error: {e}")
            cache_operations_counter.labels(
                operation="set", status="error", api_type=api_type
            ).inc()
            return False

    async def invalidate(self, api_type: str, params: Dict[str, Any]) -> bool:
        """
        Invalidate specific cache entry

        Args:
            api_type: Type of API
            params: Request parameters

        Returns:
            True if invalidated successfully
        """
        await self._ensure_redis()

        cache_key = self._generate_cache_key(api_type, params)

        try:
            result = await self.redis.delete(cache_key)

            if result > 0:
                cache_operations_counter.labels(
                    operation="invalidate", status="success", api_type=api_type
                ).inc()
                logger.info(f"Invalidated cache: {cache_key}")
                return True
            else:
                logger.debug(f"Cache key not found: {cache_key}")
                return False

        except Exception as e:
            logger.error(f"Cache invalidation error: {e}")
            cache_operations_counter.labels(
                operation="invalidate", status="error", api_type=api_type
            ).inc()
            return False

    async def invalidate_pattern(self, pattern: str) -> int:
        """
        Invalidate all cache entries matching pattern

        Args:
            pattern: Redis pattern (e.g., "routes*" for all route caches)

        Returns:
            Number of entries invalidated
        """
        await self._ensure_redis()

        try:
            full_pattern = f"{self.CACHE_PREFIX}:{pattern}"
            keys = []

            # Scan for matching keys
            async for key in self.redis.scan_iter(match=full_pattern):
                keys.append(key)

            if keys:
                deleted = await self.redis.delete(*keys)

                cache_operations_counter.labels(
                    operation="invalidate_pattern",
                    status="success",
                    api_type=pattern.split("*")[0] if "*" in pattern else pattern,
                ).inc()

                logger.info(
                    f"Invalidated {deleted} cache entries for pattern: {pattern}"
                )
                return deleted
            else:
                logger.debug(f"No cache entries found for pattern: {pattern}")
                return 0

        except Exception as e:
            logger.error(f"Cache pattern invalidation error: {e}")
            cache_operations_counter.labels(
                operation="invalidate_pattern", status="error", api_type="unknown"
            ).inc()
            return 0

    async def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        await self._ensure_redis()

        stats = {"cache_types": {}}

        try:
            # Get counts for each API type
            for api_type in self.CACHE_TTLS.keys():
                pattern = f"{self.CACHE_PREFIX}:{api_type}:*"
                count = 0

                async for _ in self.redis.scan_iter(match=pattern, count=100):
                    count += 1

                stats["cache_types"][api_type] = {
                    "count": count,
                    "ttl_seconds": int(self.CACHE_TTLS[api_type].total_seconds()),
                }

            # Get total cache size
            total_count = sum(
                type_stats["count"] for type_stats in stats["cache_types"].values()
            )
            stats["total_entries"] = total_count

            # Get Redis info for memory usage
            info = await self.redis.info("memory")
            stats["memory_used_mb"] = round(info.get("used_memory", 0) / 1024 / 1024, 2)

        except Exception as e:
            logger.error(f"Failed to get cache stats: {e}")
            stats["error"] = str(e)

        return stats

    async def warm_cache(
        self, api_type: str, common_requests: List[Dict[str, Any]]
    ) -> int:
        """
        Pre - populate cache with common requests

        Args:
            api_type: Type of API
            common_requests: List of common request parameters

        Returns:
            Number of entries warmed
        """
        warmed = 0

        for params in common_requests:
            # Check if already cached
            existing = await self.get(api_type, params)
            if not existing:
                # Would need to make actual API call here
                # For now, just count
                logger.debug(f"Would warm cache for {api_type} with params: {params}")
                warmed += 1

        return warmed

    async def clear_all(self) -> int:
        """Clear all API cache entries (admin function)"""
        await self._ensure_redis()

        try:
            pattern = f"{self.CACHE_PREFIX}:*"
            keys = []

            async for key in self.redis.scan_iter(match=pattern):
                keys.append(key)

            if keys:
                deleted = await self.redis.delete(*keys)
                logger.warning(f"Cleared {deleted} API cache entries")
                return deleted

            return 0

        except Exception as e:
            logger.error(f"Failed to clear cache: {e}")
            return 0


# Singleton instance
_api_cache_instance: Optional[GoogleAPICache] = None


async def get_api_cache() -> GoogleAPICache:
    """Get or create the singleton API cache instance"""
    global _api_cache_instance
    if _api_cache_instance is None:
        _api_cache_instance = GoogleAPICache()
    return _api_cache_instance
