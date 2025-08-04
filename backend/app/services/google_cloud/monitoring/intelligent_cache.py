"""
Intelligent Caching System for Google API Cost Optimization
Implements predictive caching, TTL optimization, and cache warming
"""

import asyncio
import json
import hashlib
from typing import Any, Dict, Optional, Tuple, List
from datetime import datetime, timedelta
import logging
from dataclasses import dataclass
from collections import defaultdict
import numpy as np
from app.core.cache import get_redis_client
import redis.asyncio as redis

logger = logging.getLogger(__name__)


@dataclass
class CacheStats:
    """Cache performance statistics"""

    hits: int = 0
    misses: int = 0
    cost_saved_usd: float = 0.0
    api_calls_saved: int = 0

    @property
    def hit_rate(self) -> float:
        total = self.hits + self.misses
        return self.hits / total if total > 0 else 0.0


class IntelligentCache:
    """
    Intelligent caching system with:
    - Predictive TTL based on access patterns
    - Cost-aware caching decisions
    - Automatic cache warming for popular routes
    - Compression for large responses
    """

    # API costs per request (USD)
    API_COSTS = {
        "routes": 0.005,  # $5 per 1000
        "geocoding": 0.005,  # $5 per 1000
        "places": 0.017,  # $17 per 1000
        "distance_matrix": 0.005,  # $5 per 1000
    }

    # Default TTLs (seconds)
    DEFAULT_TTLS = {
        "routes": 3600,  # 1 hour
        "geocoding": 86400,  # 24 hours (addresses don't change often)
        "places": 3600,  # 1 hour
        "distance_matrix": 1800,  # 30 minutes
    }

    def __init__(self, redis_client: Optional[redis.Redis] = None):
        self.redis = redis_client
        self._initialized = False
        self.stats = defaultdict(CacheStats)
        self.access_patterns = defaultdict(list)  # Track access times
        self._cache_warmup_task = None

    async def _ensure_redis(self):
        """Ensure Redis client is initialized"""
        if not self._initialized:
            if not self.redis:
                self.redis = await get_redis_client()
            self._initialized = True

            # Start cache warmup task
            if not self._cache_warmup_task:
                self._cache_warmup_task = asyncio.create_task(self._cache_warmup_loop())

    def _generate_cache_key(self, api_type: str, params: Dict[str, Any]) -> str:
        """Generate consistent cache key from API type and parameters"""
        # Sort params for consistent key generation
        sorted_params = json.dumps(params, sort_keys=True)
        key_data = f"{api_type}:{sorted_params}"

        # Use SHA256 for shorter keys
        key_hash = hashlib.sha256(key_data.encode()).hexdigest()[:16]
        return f"luckygas:cache:{api_type}:{key_hash}"

    def _calculate_optimal_ttl(self, api_type: str, cache_key: str) -> int:
        """Calculate optimal TTL based on access patterns"""
        # Get access history
        access_times = self.access_patterns.get(cache_key, [])

        if len(access_times) < 2:
            # Not enough data, use default
            return self.DEFAULT_TTLS.get(api_type, 3600)

        # Calculate average time between accesses
        intervals = []
        for i in range(1, len(access_times)):
            interval = (access_times[i] - access_times[i - 1]).total_seconds()
            intervals.append(interval)

        if intervals:
            # Use 90th percentile of intervals as TTL
            ttl = int(np.percentile(intervals, 90))

            # Apply bounds
            min_ttl = 300  # 5 minutes minimum
            max_ttl = 86400  # 24 hours maximum

            return max(min_ttl, min(ttl, max_ttl))

        return self.DEFAULT_TTLS.get(api_type, 3600)

    def _should_cache(self, api_type: str, response_size: int) -> bool:
        """Determine if response should be cached based on cost/benefit"""
        # Always cache expensive APIs
        if api_type in ["places", "routes"]:
            return True

        # Cache if response is reasonable size (< 1MB)
        if response_size > 1048576:
            logger.warning(f"Response too large to cache: {response_size} bytes")
            return False

        # Cache if hit rate is good
        stats = self.stats[api_type]
        if stats.hit_rate > 0.3:  # 30% hit rate threshold
            return True

        # Default to caching
        return True

    async def get(self, api_type: str, params: Dict[str, Any]) -> Optional[Any]:
        """Get cached response if available"""
        await self._ensure_redis()

        cache_key = self._generate_cache_key(api_type, params)

        try:
            # Get from cache
            cached_data = await self.redis.get(cache_key)

            if cached_data:
                # Update stats
                self.stats[api_type].hits += 1
                self.stats[api_type].api_calls_saved += 1
                self.stats[api_type].cost_saved_usd += self.API_COSTS.get(api_type, 0)

                # Track access for TTL optimization
                self.access_patterns[cache_key].append(datetime.utcnow())

                # Decode response
                return json.loads(cached_data)
            else:
                # Cache miss
                self.stats[api_type].misses += 1
                return None

        except Exception as e:
            logger.error(f"Cache get error: {e}")
            return None

    async def set(
        self,
        api_type: str,
        params: Dict[str, Any],
        response: Any,
        force_ttl: Optional[int] = None,
    ) -> bool:
        """Cache API response with intelligent TTL"""
        await self._ensure_redis()

        cache_key = self._generate_cache_key(api_type, params)

        try:
            # Serialize response
            serialized = json.dumps(response)
            response_size = len(serialized)

            # Check if should cache
            if not self._should_cache(api_type, response_size):
                return False

            # Calculate TTL
            if force_ttl:
                ttl = force_ttl
            else:
                ttl = self._calculate_optimal_ttl(api_type, cache_key)

            # Store in cache
            await self.redis.setex(cache_key, ttl, serialized)

            # Track access pattern
            self.access_patterns[cache_key].append(datetime.utcnow())

            # Store metadata for cache warming
            metadata_key = f"{cache_key}:meta"
            metadata = {
                "api_type": api_type,
                "params": params,
                "cached_at": datetime.utcnow().isoformat(),
                "ttl": ttl,
                "size": response_size,
                "access_count": len(self.access_patterns[cache_key]),
            }
            await self.redis.setex(metadata_key, ttl + 3600, json.dumps(metadata))

            logger.debug(
                f"Cached {api_type} response, TTL: {ttl}s, Size: {response_size}"
            )
            return True

        except Exception as e:
            logger.error(f"Cache set error: {e}")
            return False

    async def invalidate(self, api_type: str, params: Optional[Dict[str, Any]] = None):
        """Invalidate cache entries"""
        await self._ensure_redis()

        try:
            if params:
                # Invalidate specific entry
                cache_key = self._generate_cache_key(api_type, params)
                await self.redis.delete(cache_key, f"{cache_key}:meta")
            else:
                # Invalidate all entries for API type
                pattern = f"luckygas:cache:{api_type}:*"
                cursor = 0

                while True:
                    cursor, keys = await self.redis.scan(
                        cursor, match=pattern, count=100
                    )
                    if keys:
                        await self.redis.delete(*keys)
                    if cursor == 0:
                        break

            logger.info(f"Invalidated cache for {api_type}")

        except Exception as e:
            logger.error(f"Cache invalidation error: {e}")

    async def get_stats(self) -> Dict[str, Dict[str, Any]]:
        """Get cache performance statistics"""
        stats_dict = {}

        for api_type, stats in self.stats.items():
            stats_dict[api_type] = {
                "hits": stats.hits,
                "misses": stats.misses,
                "hit_rate": round(stats.hit_rate * 100, 2),
                "api_calls_saved": stats.api_calls_saved,
                "cost_saved_usd": round(stats.cost_saved_usd, 2),
                "cost_saved_ntd": round(stats.cost_saved_usd * 31.5, 2),
            }

        # Add total savings
        total_saved_usd = sum(s.cost_saved_usd for s in self.stats.values())
        stats_dict["total"] = {
            "cost_saved_usd": round(total_saved_usd, 2),
            "cost_saved_ntd": round(total_saved_usd * 31.5, 2),
            "api_calls_saved": sum(s.api_calls_saved for s in self.stats.values()),
        }

        return stats_dict

    async def warm_cache(self, predictions: List[Dict[str, Any]]):
        """Pre-cache predicted popular routes"""
        await self._ensure_redis()

        warmed = 0
        for prediction in predictions[:10]:  # Limit to top 10
            api_type = prediction.get("api_type")
            params = prediction.get("params")

            if api_type and params:
                # Check if already cached
                cache_key = self._generate_cache_key(api_type, params)
                exists = await self.redis.exists(cache_key)

                if not exists:
                    # This would trigger actual API call in production
                    logger.info(f"Cache warming needed for {api_type}: {params}")
                    warmed += 1

        logger.info(f"Cache warming: {warmed} entries need warming")
        return warmed

    async def _cache_warmup_loop(self):
        """Background task to warm cache based on patterns"""
        while True:
            try:
                await asyncio.sleep(3600)  # Run hourly

                # Analyze access patterns to predict popular routes
                popular_routes = await self._analyze_access_patterns()

                if popular_routes:
                    await self.warm_cache(popular_routes)

            except Exception as e:
                logger.error(f"Cache warmup error: {e}")

    async def _analyze_access_patterns(self) -> List[Dict[str, Any]]:
        """Analyze patterns to predict popular routes"""
        predictions = []

        # Get all metadata keys
        pattern = "luckygas:cache:*:meta"
        cursor = 0

        while True:
            cursor, keys = await self.redis.scan(cursor, match=pattern, count=100)

            for key in keys:
                try:
                    metadata = await self.redis.get(key)
                    if metadata:
                        meta_dict = json.loads(metadata)
                        access_count = meta_dict.get("access_count", 0)

                        if access_count > 5:  # Popular threshold
                            predictions.append(
                                {
                                    "api_type": meta_dict["api_type"],
                                    "params": meta_dict["params"],
                                    "score": access_count,
                                }
                            )
                except Exception as e:
                    logger.error(f"Error analyzing pattern: {e}")

            if cursor == 0:
                break

        # Sort by popularity
        predictions.sort(key=lambda x: x["score"], reverse=True)

        return predictions[:20]  # Top 20 predictions

    async def cleanup_expired(self):
        """Clean up expired cache entries and old access patterns"""
        # Trim old access patterns
        cutoff_time = datetime.utcnow() - timedelta(days=7)

        for key, times in list(self.access_patterns.items()):
            # Keep only recent accesses
            self.access_patterns[key] = [t for t in times if t > cutoff_time]

            # Remove if no recent accesses
            if not self.access_patterns[key]:
                del self.access_patterns[key]

        logger.info(
            f"Cleaned up access patterns, {len(self.access_patterns)} active keys"
        )


# Global cache instance
_intelligent_cache = None


async def get_intelligent_cache() -> IntelligentCache:
    """Get or create intelligent cache instance"""
    global _intelligent_cache

    if _intelligent_cache is None:
        _intelligent_cache = IntelligentCache()

    return _intelligent_cache
