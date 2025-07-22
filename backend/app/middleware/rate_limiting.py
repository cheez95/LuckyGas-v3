"""
Rate limiting middleware for API endpoints.

This module implements rate limiting using a sliding window algorithm
with Redis as the backend storage for distributed rate limiting.
"""

from fastapi import Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from datetime import datetime, timedelta
from typing import Dict, Optional, Tuple
import hashlib
import json

from app.core.config import settings
from app.core.cache import cache
from app.core.logging import get_logger

logger = get_logger(__name__)


class RateLimitExceeded(Exception):
    """Exception raised when rate limit is exceeded."""
    pass


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Rate limiting middleware using sliding window algorithm.
    
    Features:
    - Per-IP rate limiting
    - Per-user rate limiting (when authenticated)
    - Different limits for different endpoints
    - Sliding window algorithm for smooth rate limiting
    - Headers indicating rate limit status
    """
    
    def __init__(self, app, default_limit: int = 100, window_seconds: int = 60):
        super().__init__(app)
        self.default_limit = default_limit
        self.window_seconds = window_seconds
        
        # Endpoint-specific rate limits (requests per minute)
        self.endpoint_limits = {
            "/api/v1/auth/login": 5,  # Strict limit for login attempts
            "/api/v1/auth/register": 3,  # Strict limit for registration
            "/api/v1/predictions/": 10,  # ML predictions are resource-intensive
            "/api/v1/routes/optimize": 10,  # Route optimization is CPU-intensive
            "/api/v1/orders/bulk": 5,  # Bulk operations
            "/api/v1/google-api/": 30,  # Google API calls have their own limits
            "/health": 1000,  # Health checks need higher limit
            "/metrics": 1000,  # Metrics endpoint
        }
        
    async def dispatch(self, request: Request, call_next):
        """Process the request with rate limiting."""
        # Skip rate limiting if disabled
        if not settings.RATE_LIMIT_ENABLED:
            return await call_next(request)
            
        # Skip rate limiting for WebSocket connections
        if request.url.path.startswith("/socket.io"):
            return await call_next(request)
            
        try:
            # Get rate limit key and limit
            key, limit = await self._get_rate_limit_info(request)
            
            # Check rate limit
            allowed, remaining, reset_time = await self._check_rate_limit(key, limit)
            
            if not allowed:
                logger.warning(
                    "Rate limit exceeded",
                    extra={
                        "key": key,
                        "path": request.url.path,
                        "method": request.method,
                        "client": request.client.host if request.client else "unknown"
                    }
                )
                return self._rate_limit_exceeded_response(remaining, reset_time)
            
            # Process request
            response = await call_next(request)
            
            # Add rate limit headers
            response.headers["X-RateLimit-Limit"] = str(limit)
            response.headers["X-RateLimit-Remaining"] = str(remaining)
            response.headers["X-RateLimit-Reset"] = str(int(reset_time.timestamp()))
            
            return response
            
        except Exception as e:
            logger.error(f"Rate limiting error: {str(e)}", exc_info=True)
            # On error, allow the request through
            return await call_next(request)
    
    async def _get_rate_limit_info(self, request: Request) -> Tuple[str, int]:
        """Get rate limit key and limit for the request."""
        # Get client identifier
        client_id = self._get_client_id(request)
        
        # Get endpoint-specific limit
        path = request.url.path
        limit = self.default_limit
        
        # Check for specific endpoint limits
        for endpoint_pattern, endpoint_limit in self.endpoint_limits.items():
            if path.startswith(endpoint_pattern):
                limit = endpoint_limit
                break
        
        # For authenticated users, use user ID as part of the key
        user_id = getattr(request.state, "user_id", None)
        if user_id:
            key = f"rate_limit:user:{user_id}:{path}"
            # Authenticated users get 2x the limit
            limit = limit * 2
        else:
            key = f"rate_limit:ip:{client_id}:{path}"
        
        # Environment-based adjustments
        if settings.is_development():
            limit = limit * 10  # More lenient in development
        
        return key, limit
    
    def _get_client_id(self, request: Request) -> str:
        """Get client identifier from request."""
        # Try to get real IP from headers (for reverse proxy scenarios)
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            # Take the first IP in the chain
            client_ip = forwarded_for.split(",")[0].strip()
        elif request.client:
            client_ip = request.client.host
        else:
            client_ip = "unknown"
        
        # Hash the IP for privacy
        return hashlib.sha256(client_ip.encode()).hexdigest()[:16]
    
    async def _check_rate_limit(self, key: str, limit: int) -> Tuple[bool, int, datetime]:
        """
        Check if request is within rate limit using sliding window algorithm.
        
        Returns:
            - allowed: Whether the request is allowed
            - remaining: Number of remaining requests
            - reset_time: When the rate limit window resets
        """
        now = datetime.utcnow()
        window_start = now - timedelta(seconds=self.window_seconds)
        
        # Get current request count from cache
        cache_key = f"{key}:sliding_window"
        
        try:
            # Get existing requests in the window
            window_data = await cache.get(cache_key)
            if window_data:
                requests = json.loads(window_data)
            else:
                requests = []
            
            # Remove expired requests
            requests = [req for req in requests if datetime.fromisoformat(req) > window_start]
            
            # Check if limit exceeded
            if len(requests) >= limit:
                # Find when the oldest request expires
                oldest_request = min(requests, key=lambda x: datetime.fromisoformat(x))
                reset_time = datetime.fromisoformat(oldest_request) + timedelta(seconds=self.window_seconds)
                return False, 0, reset_time
            
            # Add current request
            requests.append(now.isoformat())
            
            # Update cache
            await cache.set(cache_key, json.dumps(requests), expire=self.window_seconds)
            
            remaining = limit - len(requests)
            reset_time = now + timedelta(seconds=self.window_seconds)
            
            return True, remaining, reset_time
            
        except Exception as e:
            logger.error(f"Rate limit check error: {str(e)}", exc_info=True)
            # On error, allow the request
            return True, limit, now + timedelta(seconds=self.window_seconds)
    
    def _rate_limit_exceeded_response(self, remaining: int, reset_time: datetime) -> JSONResponse:
        """Create rate limit exceeded response."""
        retry_after = int((reset_time - datetime.utcnow()).total_seconds())
        
        return JSONResponse(
            status_code=429,
            content={
                "detail": "請求次數超過限制，請稍後再試",
                "error": "rate_limit_exceeded",
                "retry_after": retry_after
            },
            headers={
                "Retry-After": str(retry_after),
                "X-RateLimit-Limit": "0",
                "X-RateLimit-Remaining": "0",
                "X-RateLimit-Reset": str(int(reset_time.timestamp()))
            }
        )


class EndpointRateLimiter:
    """
    Decorator for applying rate limits to specific endpoints.
    
    This provides more granular control than the middleware approach.
    """
    
    def __init__(self, requests_per_minute: int):
        self.requests_per_minute = requests_per_minute
        self.window_seconds = 60
    
    async def __call__(self, request: Request) -> bool:
        """Check if request is allowed."""
        # Get client identifier
        client_ip = request.client.host if request.client else "unknown"
        client_id = hashlib.sha256(client_ip.encode()).hexdigest()[:16]
        
        # Get user ID if authenticated
        user_id = getattr(request.state, "user_id", None)
        if user_id:
            key = f"rate_limit:endpoint:{user_id}:{request.url.path}"
        else:
            key = f"rate_limit:endpoint:{client_id}:{request.url.path}"
        
        # Check rate limit
        middleware = RateLimitMiddleware(None)
        allowed, _, _ = await middleware._check_rate_limit(key, self.requests_per_minute)
        
        return allowed