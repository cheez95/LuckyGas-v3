from typing import Optional, Dict, Callable
from datetime import datetime, timedelta
import asyncio
from functools import wraps
from fastapi import HTTPException, Request, Response
from fastapi.security import HTTPBearer
import redis.asyncio as redis
import hashlib
import json

from app.core.config import settings


class RateLimiter:
    """Advanced rate limiting with multiple strategies."""
    
    def __init__(
        self,
        redis_client: redis.Redis,
        default_limit: int = 100,
        default_window: int = 60
    ):
        self.redis = redis_client
        self.default_limit = default_limit
        self.default_window = default_window
    
    async def check_rate_limit(
        self,
        key: str,
        limit: Optional[int] = None,
        window: Optional[int] = None,
        cost: int = 1
    ) -> Dict[str, int]:
        """Check if rate limit is exceeded using sliding window algorithm."""
        limit = limit or self.default_limit
        window = window or self.default_window
        
        now = datetime.utcnow()
        window_start = now - timedelta(seconds=window)
        
        # Use Redis sorted set for sliding window
        pipe = self.redis.pipeline()
        
        # Remove old entries
        pipe.zremrangebyscore(key, 0, window_start.timestamp())
        
        # Count current requests
        pipe.zcard(key)
        
        # Add current request
        pipe.zadd(key, {f"{now.timestamp()}-{id(now)}": now.timestamp()})
        
        # Set expiry
        pipe.expire(key, window + 1)
        
        results = await pipe.execute()
        current_count = results[1] + cost
        
        if current_count > limit:
            # Remove the just-added entry if limit exceeded
            await self.redis.zrem(key, f"{now.timestamp()}-{id(now)}")
            raise HTTPException(
                status_code=429,
                detail="Rate limit exceeded",
                headers={
                    "X-RateLimit-Limit": str(limit),
                    "X-RateLimit-Remaining": "0",
                    "X-RateLimit-Reset": str(int((now + timedelta(seconds=window)).timestamp()))
                }
            )
        
        return {
            "limit": limit,
            "remaining": max(0, limit - current_count),
            "reset": int((now + timedelta(seconds=window)).timestamp())
        }
    
    async def get_key_for_request(self, request: Request, strategy: str = "ip") -> str:
        """Generate rate limit key based on strategy."""
        if strategy == "ip":
            # Get real IP considering proxies
            forwarded_for = request.headers.get("X-Forwarded-For")
            if forwarded_for:
                ip = forwarded_for.split(",")[0].strip()
            else:
                ip = request.client.host
            return f"rate_limit:ip:{ip}"
        
        elif strategy == "user":
            # Requires authenticated user
            user = getattr(request.state, "user", None)
            if user:
                return f"rate_limit:user:{user.id}"
            else:
                # Fallback to IP if not authenticated
                return await self.get_key_for_request(request, "ip")
        
        elif strategy == "api_key":
            # For API key based limiting
            api_key = request.headers.get("X-API-Key")
            if api_key:
                key_hash = hashlib.sha256(api_key.encode()).hexdigest()
                return f"rate_limit:api_key:{key_hash}"
            else:
                return await self.get_key_for_request(request, "ip")
        
        elif strategy == "endpoint":
            # Per-endpoint limiting
            path = request.url.path
            method = request.method
            return f"rate_limit:endpoint:{method}:{path}"
        
        else:
            raise ValueError(f"Unknown rate limit strategy: {strategy}")
    
    def limit(
        self,
        requests: int = 100,
        window: int = 60,
        strategy: str = "user",
        cost: int = 1,
        error_message: Optional[str] = None
    ):
        """Decorator for rate limiting endpoints."""
        def decorator(func: Callable) -> Callable:
            @wraps(func)
            async def wrapper(request: Request, *args, **kwargs):
                key = await self.get_key_for_request(request, strategy)
                
                try:
                    rate_info = await self.check_rate_limit(
                        key,
                        limit=requests,
                        window=window,
                        cost=cost
                    )
                    
                    # Add rate limit headers to response
                    response = await func(request, *args, **kwargs)
                    if isinstance(response, Response):
                        response.headers["X-RateLimit-Limit"] = str(rate_info["limit"])
                        response.headers["X-RateLimit-Remaining"] = str(rate_info["remaining"])
                        response.headers["X-RateLimit-Reset"] = str(rate_info["reset"])
                    
                    return response
                
                except HTTPException as e:
                    if e.status_code == 429 and error_message:
                        e.detail = error_message
                    raise e
            
            return wrapper
        return decorator


class DynamicRateLimiter(RateLimiter):
    """Dynamic rate limiting based on user behavior and system load."""
    
    def __init__(self, redis_client: redis.Redis):
        super().__init__(redis_client)
        self.behavior_scores = {}
        self.load_multiplier = 1.0
    
    async def calculate_user_limit(self, user_id: str) -> int:
        """Calculate dynamic limit based on user behavior."""
        # Get user behavior score from Redis
        score_key = f"user_behavior:{user_id}"
        score = await self.redis.get(score_key)
        
        if score is None:
            # New user gets default limit
            return self.default_limit
        
        score = float(score)
        
        # Adjust limit based on behavior score
        # Good behavior (score > 0.8) gets bonus
        # Bad behavior (score < 0.5) gets penalty
        if score > 0.8:
            multiplier = 1.5
        elif score > 0.6:
            multiplier = 1.0
        elif score > 0.4:
            multiplier = 0.7
        else:
            multiplier = 0.5
        
        # Apply system load multiplier
        return int(self.default_limit * multiplier * self.load_multiplier)
    
    async def update_user_behavior(self, user_id: str, event: str, weight: float = 1.0):
        """Update user behavior score based on events."""
        score_key = f"user_behavior:{user_id}"
        
        # Events and their impact on score
        event_impacts = {
            "successful_request": 0.01,
            "rate_limit_hit": -0.05,
            "error_4xx": -0.02,
            "error_5xx": 0,  # Not user's fault
            "suspicious_activity": -0.1,
            "good_citizen": 0.05,  # E.g., using caching headers
        }
        
        impact = event_impacts.get(event, 0) * weight
        
        # Get current score
        current_score = await self.redis.get(score_key)
        if current_score is None:
            current_score = 0.7  # Default neutral score
        else:
            current_score = float(current_score)
        
        # Update score (keep between 0 and 1)
        new_score = max(0, min(1, current_score + impact))
        
        # Store with 7-day expiry
        await self.redis.setex(score_key, 7 * 24 * 60 * 60, str(new_score))
    
    async def adjust_for_system_load(self, cpu_usage: float, memory_usage: float):
        """Adjust rate limits based on system load."""
        # Reduce limits when system is under stress
        if cpu_usage > 80 or memory_usage > 85:
            self.load_multiplier = 0.5
        elif cpu_usage > 60 or memory_usage > 70:
            self.load_multiplier = 0.8
        else:
            self.load_multiplier = 1.0


class TokenBucketRateLimiter:
    """Token bucket algorithm for burst-allowing rate limiting."""
    
    def __init__(self, redis_client: redis.Redis):
        self.redis = redis_client
    
    async def check_token_bucket(
        self,
        key: str,
        capacity: int,
        refill_rate: float,
        tokens_required: int = 1
    ) -> bool:
        """Check if tokens are available in the bucket."""
        now = datetime.utcnow().timestamp()
        
        # Lua script for atomic token bucket operation
        lua_script = """
        local key = KEYS[1]
        local capacity = tonumber(ARGV[1])
        local refill_rate = tonumber(ARGV[2])
        local tokens_required = tonumber(ARGV[3])
        local now = tonumber(ARGV[4])
        
        local bucket = redis.call('HMGET', key, 'tokens', 'last_refill')
        local tokens = tonumber(bucket[1]) or capacity
        local last_refill = tonumber(bucket[2]) or now
        
        -- Calculate tokens to add based on time passed
        local time_passed = now - last_refill
        local tokens_to_add = time_passed * refill_rate
        tokens = math.min(capacity, tokens + tokens_to_add)
        
        if tokens >= tokens_required then
            tokens = tokens - tokens_required
            redis.call('HMSET', key, 'tokens', tokens, 'last_refill', now)
            redis.call('EXPIRE', key, 3600)
            return 1
        else
            redis.call('HMSET', key, 'tokens', tokens, 'last_refill', now)
            redis.call('EXPIRE', key, 3600)
            return 0
        end
        """
        
        result = await self.redis.eval(
            lua_script,
            1,
            key,
            capacity,
            refill_rate,
            tokens_required,
            now
        )
        
        return bool(result)


class GeoRateLimiter:
    """Geographic-based rate limiting."""
    
    def __init__(self, redis_client: redis.Redis):
        self.redis = redis_client
        self.country_limits = {
            "default": 100,
            "TW": 200,  # Higher limit for Taiwan
            "CN": 50,   # Lower limit for certain regions
            "US": 150,
        }
    
    async def get_country_from_ip(self, ip: str) -> str:
        """Get country code from IP address."""
        # In production, use a GeoIP service
        # For now, return default
        return "TW"
    
    async def get_limit_for_request(self, request: Request) -> int:
        """Get rate limit based on geographic location."""
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            ip = forwarded_for.split(",")[0].strip()
        else:
            ip = request.client.host
        
        country = await self.get_country_from_ip(ip)
        return self.country_limits.get(country, self.country_limits["default"])


# Global rate limiter instance
rate_limiter: Optional[RateLimiter] = None
dynamic_limiter: Optional[DynamicRateLimiter] = None
token_bucket: Optional[TokenBucketRateLimiter] = None
geo_limiter: Optional[GeoRateLimiter] = None


async def init_rate_limiters(redis_client: redis.Redis):
    """Initialize rate limiter instances."""
    global rate_limiter, dynamic_limiter, token_bucket, geo_limiter
    
    rate_limiter = RateLimiter(redis_client)
    dynamic_limiter = DynamicRateLimiter(redis_client)
    token_bucket = TokenBucketRateLimiter(redis_client)
    geo_limiter = GeoRateLimiter(redis_client)


# Convenience decorators
def rate_limit(requests: int = 100, window: int = 60, **kwargs):
    """Basic rate limiting decorator."""
    def decorator(func):
        @wraps(func)
        async def wrapper(request: Request, *args, **kwargs_inner):
            if not rate_limiter:
                # Rate limiter not initialized, skip
                return await func(request, *args, **kwargs_inner)
            
            return await rate_limiter.limit(requests, window, **kwargs)(func)(request, *args, **kwargs_inner)
        return wrapper
    return decorator


def burst_limit(capacity: int = 10, refill_rate: float = 0.1):
    """Token bucket rate limiting for burst traffic."""
    def decorator(func):
        @wraps(func)
        async def wrapper(request: Request, *args, **kwargs):
            if not token_bucket:
                return await func(request, *args, **kwargs)
            
            key = f"token_bucket:{request.client.host}:{request.url.path}"
            allowed = await token_bucket.check_token_bucket(key, capacity, refill_rate)
            
            if not allowed:
                raise HTTPException(
                    status_code=429,
                    detail="Rate limit exceeded (burst)"
                )
            
            return await func(request, *args, **kwargs)
        return wrapper
    return decorator