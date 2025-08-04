"""
Enhanced rate limiting middleware using slowapi for production-grade rate limiting.

This module implements:
- Per-endpoint rate limiting with slowapi
- API key management system
- Advanced rate limiting strategies
- Redis-backed distributed rate limiting
- Configurable rate limits per endpoint and user role
"""

from typing import Callable, Optional, Dict, Any, List
from datetime import datetime, timedelta
import hashlib
import secrets
import json
from functools import wraps

from fastapi import Request, Response, HTTPException, status, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

from app.core.config import settings
from app.core.cache import cache
from app.core.logging import get_logger
from app.core.database import async_session_maker
from app.models.user import User
from sqlalchemy import select

logger = get_logger(__name__)


class APIKeyManager:
    """Manage API keys for different rate limiting tiers."""

    TIERS = {
        "basic": {
            "rate_limit": "100/hour",
            "burst_limit": "20/minute",
            "description": "Basic tier for standard API access",
        },
        "standard": {
            "rate_limit": "1000/hour",
            "burst_limit": "100/minute",
            "description": "Standard tier for regular applications",
        },
        "premium": {
            "rate_limit": "10000/hour",
            "burst_limit": "500/minute",
            "description": "Premium tier for high-volume applications",
        },
        "enterprise": {
            "rate_limit": "100000/hour",
            "burst_limit": "2000/minute",
            "description": "Enterprise tier with custom limits",
        },
    }

    @staticmethod
    async def generate_api_key(
        user_id: int, tier: str = "basic", name: str = ""
    ) -> Dict[str, Any]:
        """Generate a new API key for a user."""
        if tier not in APIKeyManager.TIERS:
            raise ValueError(f"Invalid tier: {tier}")

        # Generate secure API key
        api_key = f"lgas_{secrets.token_urlsafe(32)}"
        key_hash = hashlib.sha256(api_key.encode()).hexdigest()

        # Store API key metadata
        metadata = {
            "user_id": user_id,
            "tier": tier,
            "name": name,
            "created_at": datetime.utcnow().isoformat(),
            "last_used": None,
            "usage_count": 0,
            "active": True,
        }

        # Store in Redis with no expiration
        key = f"api_key:{key_hash}"
        await cache.set(key, json.dumps(metadata))

        # Also store user's API keys list
        user_keys_key = f"user_api_keys:{user_id}"
        user_keys = await cache.get(user_keys_key)
        if user_keys:
            keys_list = json.loads(user_keys)
        else:
            keys_list = []

        keys_list.append(
            {
                "key_hash": key_hash,
                "name": name,
                "tier": tier,
                "created_at": metadata["created_at"],
            }
        )

        await cache.set(user_keys_key, json.dumps(keys_list))

        return {
            "api_key": api_key,
            "key_hash": key_hash,
            "tier": tier,
            "rate_limits": APIKeyManager.TIERS[tier],
        }

    @staticmethod
    async def validate_api_key(api_key: str) -> Optional[Dict[str, Any]]:
        """Validate an API key and return its metadata."""
        if not api_key or not api_key.startswith("lgas_"):
            return None

        key_hash = hashlib.sha256(api_key.encode()).hexdigest()
        key = f"api_key:{key_hash}"

        metadata_str = await cache.get(key)
        if not metadata_str:
            return None

        metadata = json.loads(metadata_str)

        # Check if key is active
        if not metadata.get("active", True):
            return None

        # Update usage statistics
        metadata["last_used"] = datetime.utcnow().isoformat()
        metadata["usage_count"] = metadata.get("usage_count", 0) + 1

        await cache.set(key, json.dumps(metadata))

        return metadata

    @staticmethod
    async def revoke_api_key(key_hash: str, user_id: int) -> bool:
        """Revoke an API key."""
        key = f"api_key:{key_hash}"

        metadata_str = await cache.get(key)
        if not metadata_str:
            return False

        metadata = json.loads(metadata_str)

        # Verify ownership
        if metadata.get("user_id") != user_id:
            return False

        # Mark as inactive
        metadata["active"] = False
        metadata["revoked_at"] = datetime.utcnow().isoformat()

        await cache.set(key, json.dumps(metadata))

        return True

    @staticmethod
    async def list_user_api_keys(user_id: int) -> List[Dict[str, Any]]:
        """List all API keys for a user."""
        user_keys_key = f"user_api_keys:{user_id}"
        user_keys = await cache.get(user_keys_key)

        if not user_keys:
            return []

        keys_list = json.loads(user_keys)

        # Enrich with current status
        enriched_keys = []
        for key_info in keys_list:
            key = f"api_key:{key_info['key_hash']}"
            metadata_str = await cache.get(key)

            if metadata_str:
                metadata = json.loads(metadata_str)
                key_info["active"] = metadata.get("active", True)
                key_info["last_used"] = metadata.get("last_used")
                key_info["usage_count"] = metadata.get("usage_count", 0)
                enriched_keys.append(key_info)

        return enriched_keys


# Custom key function that considers API keys and user authentication
async def get_rate_limit_key(request: Request) -> str:
    """Get rate limit key based on API key, user ID, or IP address."""
    # Check for API key in header
    api_key = request.headers.get("X-API-Key")
    if api_key:
        metadata = await APIKeyManager.validate_api_key(api_key)
        if metadata:
            return f"api_key:{metadata['user_id']}:{metadata['tier']}"

    # Check for authenticated user
    if hasattr(request.state, "user_id") and request.state.user_id:
        return f"user:{request.state.user_id}"

    # Fall back to IP address
    return get_remote_address(request)


# Create limiter instance with Redis backend
limiter = Limiter(
    key_func=get_rate_limit_key,
    storage_uri=settings.REDIS_URL if settings.REDIS_URL else "memory://",
    strategy="fixed-window",
    default_limits=["100/hour", "20/minute"],  # Default limits
)


class EnhancedRateLimitMiddleware:
    """Enhanced rate limiting middleware with per-endpoint configuration."""

    # Endpoint-specific rate limits
    ENDPOINT_LIMITS = {
        # Authentication endpoints - strict limits
        "/api/v1/auth/login": ["5/minute", "20/hour"],
        "/api/v1/auth/register": ["3/minute", "10/hour"],
        "/api/v1/auth/forgot-password": ["3/minute", "10/hour"],
        # Resource-intensive endpoints
        "/api/v1/predictions/generate": ["10/minute", "100/hour"],
        "/api/v1/routes/optimize": ["10/minute", "100/hour"],
        "/api/v1/financial-reports/generate": ["5/minute", "50/hour"],
        # Bulk operations
        "/api/v1/orders/bulk-create": ["5/minute", "50/hour"],
        "/api/v1/customers/bulk-import": ["5/minute", "30/hour"],
        # Google API proxy endpoints
        "/api/v1/google-api/geocode": ["30/minute", "300/hour"],
        "/api/v1/google-api/directions": ["20/minute", "200/hour"],
        # WebSocket endpoints
        "/api/v1/websocket/connect": ["10/minute", "100/hour"],
        # SMS/Communication endpoints
        "/api/v1/sms/send": ["20/minute", "200/hour"],
        "/api/v1/communications/send-notification": ["30/minute", "300/hour"],
        # Financial operations
        "/api/v1/payments/process": ["20/minute", "200/hour"],
        "/api/v1/invoices/generate": ["20/minute", "200/hour"],
        # Admin endpoints - more lenient
        "/api/v1/admin/*": ["100/minute", "1000/hour"],
        # Health checks - very lenient
        "/health": ["1000/minute"],
        "/api/v1/health": ["1000/minute"],
        "/metrics": ["1000/minute"],
    }

    # Role-based rate limit multipliers
    ROLE_MULTIPLIERS = {
        "super_admin": 10.0,
        "admin": 5.0,
        "manager": 3.0,
        "office_staff": 2.0,
        "driver": 1.5,
        "customer": 1.0,
    }

    @classmethod
    def get_endpoint_limits(
        cls, path: str, user_role: Optional[str] = None
    ) -> List[str]:
        """Get rate limits for a specific endpoint and user role."""
        # Find matching endpoint pattern
        limits = None
        for pattern, endpoint_limits in cls.ENDPOINT_LIMITS.items():
            if pattern.endswith("*"):
                if path.startswith(pattern[:-1]):
                    limits = endpoint_limits
                    break
            elif path == pattern or path.startswith(pattern + "/"):
                limits = endpoint_limits
                break

        # Use default limits if no specific limits found
        if not limits:
            limits = ["100/hour", "20/minute"]

        # Apply role-based multiplier if user is authenticated
        if user_role and user_role in cls.ROLE_MULTIPLIERS:
            multiplier = cls.ROLE_MULTIPLIERS[user_role]
            adjusted_limits = []

            for limit in limits:
                count, period = limit.split("/")
                adjusted_count = int(int(count) * multiplier)
                adjusted_limits.append(f"{adjusted_count}/{period}")

            return adjusted_limits

        return limits


# Rate limit decorators for specific endpoints
def ratelimit_endpoint(limits: Optional[List[str]] = None):
    """Decorator to apply rate limiting to specific endpoints."""

    def decorator(func: Callable) -> Callable:
        # If no limits specified, use defaults
        actual_limits = limits or ["100/hour", "20/minute"]

        # Apply each limit
        for limit in actual_limits:
            func = limiter.limit(limit)(func)

        return func

    return decorator


# API key dependency
security = HTTPBearer(auto_error=False)


async def get_api_key_tier(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
) -> Optional[str]:
    """Get API key tier from request."""
    if not credentials:
        return None

    metadata = await APIKeyManager.validate_api_key(credentials.credentials)
    if metadata:
        return metadata.get("tier")

    return None


# Circuit breaker for external service calls
class CircuitBreaker:
    """Circuit breaker pattern for external service protection."""

    def __init__(
        self,
        failure_threshold: int = 5,
        recovery_timeout: int = 60,
        expected_exception: type = Exception,
    ):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.expected_exception = expected_exception
        self.failure_count = 0
        self.last_failure_time = None
        self.state = "closed"  # closed, open, half-open

    async def call(self, func: Callable, *args, **kwargs):
        """Execute function with circuit breaker protection."""
        if self.state == "open":
            if datetime.utcnow() - self.last_failure_time > timedelta(
                seconds=self.recovery_timeout
            ):
                self.state = "half-open"
            else:
                raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail="Service temporarily unavailable",
                )

        try:
            result = await func(*args, **kwargs)
            if self.state == "half-open":
                self.state = "closed"
                self.failure_count = 0
            return result

        except self.expected_exception as e:
            self.failure_count += 1
            self.last_failure_time = datetime.utcnow()

            if self.failure_count >= self.failure_threshold:
                self.state = "open"
                logger.error(f"Circuit breaker opened for {func.__name__}")

            raise e


# Create circuit breakers for external services
google_api_circuit_breaker = CircuitBreaker(failure_threshold=5, recovery_timeout=60)
sms_api_circuit_breaker = CircuitBreaker(failure_threshold=3, recovery_timeout=120)
banking_api_circuit_breaker = CircuitBreaker(failure_threshold=3, recovery_timeout=180)
einvoice_api_circuit_breaker = CircuitBreaker(failure_threshold=5, recovery_timeout=120)


# Export components
__all__ = [
    "limiter",
    "ratelimit_endpoint",
    "APIKeyManager",
    "EnhancedRateLimitMiddleware",
    "get_api_key_tier",
    "CircuitBreaker",
    "google_api_circuit_breaker",
    "sms_api_circuit_breaker",
    "banking_api_circuit_breaker",
    "einvoice_api_circuit_breaker",
    "RateLimitExceeded",
    "_rate_limit_exceeded_handler",
]
