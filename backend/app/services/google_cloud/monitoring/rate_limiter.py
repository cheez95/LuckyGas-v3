"""
Google API Rate Limiter
"""
import asyncio
from datetime import datetime, timedelta
from collections import deque
from typing import Dict, Optional, Tuple
import redis.asyncio as redis
import logging
from app.core.cache import get_redis_client
from app.core.metrics import google_api_calls_counter

logger = logging.getLogger(__name__)


class GoogleAPIRateLimiter:
    """Rate limiter for Google API calls with Redis backend"""
    
    # Google API rate limits
    LIMITS = {
        "routes": {
            "per_second": 10,
            "per_minute": 300,
            "per_day": 25000,
            "burst": 20  # Allow burst up to 20 requests
        },
        "geocoding": {
            "per_second": 50,
            "per_minute": 3000,
            "per_day": 2500,
            "burst": 100
        },
        "places": {
            "per_second": 10,
            "per_minute": 600,
            "per_day": 150000,
            "burst": 20
        },
        "vertex_ai": {
            "per_second": 5,
            "per_minute": 300,
            "per_day": 50000,
            "burst": 10
        }
    }
    
    def __init__(self, redis_client: Optional[redis.Redis] = None):
        self.redis = redis_client
        self.local_queues: Dict[str, deque] = {}
        self._initialized = False
    
    async def _ensure_redis(self):
        """Ensure Redis client is initialized"""
        if not self._initialized:
            if not self.redis:
                self.redis = await get_redis_client()
            self._initialized = True
    
    async def check_rate_limit(self, api_type: str) -> Tuple[bool, Optional[float]]:
        """
        Check if API call is within rate limits
        Returns: (allowed, wait_time_seconds)
        """
        await self._ensure_redis()
        
        if api_type not in self.LIMITS:
            logger.warning(f"Unknown API type: {api_type}, allowing request")
            return True, None
        
        limits = self.LIMITS[api_type]
        now = datetime.now()
        
        # Check all rate limit windows
        checks = [
            ("second", limits["per_second"], 1),
            ("minute", limits["per_minute"], 60),
            ("day", limits["per_day"], 86400)
        ]
        
        for window_name, limit, window_seconds in checks:
            allowed, wait_time = await self._check_window(
                api_type, window_name, limit, window_seconds
            )
            if not allowed:
                logger.warning(
                    f"Rate limit exceeded for {api_type} ({window_name}): "
                    f"wait {wait_time:.2f}s"
                )
                return False, wait_time
        
        return True, None
    
    async def _check_window(
        self, 
        api_type: str, 
        window: str, 
        limit: int, 
        window_seconds: int
    ) -> Tuple[bool, Optional[float]]:
        """Check rate limit for a specific time window"""
        key = f"rate_limit:{api_type}:{window}"
        
        try:
            # Use Redis INCR with expiry for atomic rate limiting
            current = await self.redis.incr(key)
            
            if current == 1:
                # First request in this window, set expiry
                await self.redis.expire(key, window_seconds)
            
            if current <= limit:
                return True, None
            else:
                # Calculate wait time
                ttl = await self.redis.ttl(key)
                wait_time = max(0.1, ttl) if ttl > 0 else 0.1
                return False, wait_time
                
        except Exception as e:
            logger.error(f"Rate limit check failed: {e}, failing open")
            # Fail open - allow request if Redis is down
            return True, None
    
    async def wait_if_needed(self, api_type: str, max_wait: float = 60.0) -> bool:
        """
        Wait if rate limit is exceeded
        Returns: True if request can proceed, False if max_wait exceeded
        """
        start_time = asyncio.get_event_loop().time()
        
        while True:
            allowed, wait_time = await self.check_rate_limit(api_type)
            
            if allowed:
                # Record successful acquisition
                google_api_calls_counter.labels(
                    api=api_type,
                    status="allowed"
                ).inc()
                return True
            
            if wait_time is None:
                wait_time = 0.1
            
            # Check if we've waited too long
            elapsed = asyncio.get_event_loop().time() - start_time
            if elapsed + wait_time > max_wait:
                google_api_calls_counter.labels(
                    api=api_type,
                    status="timeout"
                ).inc()
                logger.error(f"Rate limit wait timeout for {api_type}")
                return False
            
            # Wait before retrying
            logger.info(f"Rate limited on {api_type}, waiting {wait_time:.2f}s")
            await asyncio.sleep(wait_time)
    
    async def get_usage_stats(self, api_type: str) -> Dict[str, any]:
        """Get current usage statistics for an API"""
        await self._ensure_redis()
        
        if api_type not in self.LIMITS:
            return {"error": f"Unknown API type: {api_type}"}
        
        limits = self.LIMITS[api_type]
        now = datetime.now()
        stats = {
            "api_type": api_type,
            "timestamp": now.isoformat(),
            "limits": limits,
            "usage": {}
        }
        
        try:
            # Get usage for each window
            windows = [
                ("second", limits["per_second"], "Current second"),
                ("minute", limits["per_minute"], "Current minute"),
                ("day", limits["per_day"], f"Today ({now.date()})")
            ]
            
            for window_name, limit, description in windows:
                key = f"rate_limit:{api_type}:{window_name}"
                current = await self.redis.get(key)
                current_value = int(current) if current else 0
                
                stats["usage"][window_name] = {
                    "current": current_value,
                    "limit": limit,
                    "remaining": max(0, limit - current_value),
                    "percentage": round((current_value / limit) * 100, 2) if limit > 0 else 0,
                    "description": description
                }
        
        except Exception as e:
            logger.error(f"Failed to get usage stats: {e}")
            stats["error"] = str(e)
        
        return stats
    
    async def reset_limits(self, api_type: str, window: Optional[str] = None) -> bool:
        """
        Reset rate limits for an API (admin function)
        window: 'second', 'minute', 'day', or None for all
        """
        await self._ensure_redis()
        
        try:
            if window:
                key = f"rate_limit:{api_type}:{window}"
                await self.redis.delete(key)
                logger.info(f"Reset {window} rate limit for {api_type}")
            else:
                # Reset all windows
                for w in ["second", "minute", "day"]:
                    key = f"rate_limit:{api_type}:{w}"
                    await self.redis.delete(key)
                logger.info(f"Reset all rate limits for {api_type}")
            
            return True
        except Exception as e:
            logger.error(f"Failed to reset limits: {e}")
            return False
    
    async def get_all_usage_stats(self) -> Dict[str, Dict]:
        """Get usage statistics for all APIs"""
        stats = {}
        for api_type in self.LIMITS.keys():
            stats[api_type] = await self.get_usage_stats(api_type)
        return stats
    
    def get_recommended_wait(self, api_type: str, current_usage: Dict) -> float:
        """Get recommended wait time based on current usage"""
        if api_type not in self.LIMITS:
            return 0.0
        
        limits = self.LIMITS[api_type]
        
        # Check if we're close to limits
        second_usage = current_usage.get("usage", {}).get("second", {})
        if second_usage.get("percentage", 0) > 80:
            # Near per-second limit, wait a bit
            return 1.0 / limits["per_second"]
        
        minute_usage = current_usage.get("usage", {}).get("minute", {})
        if minute_usage.get("percentage", 0) > 90:
            # Near per-minute limit, wait longer
            return 60.0 / limits["per_minute"]
        
        return 0.0


# Singleton instance (will be initialized on first use)
_rate_limiter_instance: Optional[GoogleAPIRateLimiter] = None


async def get_rate_limiter() -> GoogleAPIRateLimiter:
    """Get or create the singleton rate limiter instance"""
    global _rate_limiter_instance
    if _rate_limiter_instance is None:
        _rate_limiter_instance = GoogleAPIRateLimiter()
    return _rate_limiter_instance