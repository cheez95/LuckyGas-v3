"""
API Key Security Module

Provides comprehensive security features for API key management:
- Key validation and restrictions enforcement
- Rate limiting with adaptive thresholds
- Usage monitoring and anomaly detection
- Webhook signature validation
- Emergency response capabilities
"""

import hashlib
import hmac
import time
import json
import logging
from typing import Dict, Optional, List, Any, Tuple, Callable
from datetime import datetime, timedelta
from functools import wraps
from collections import defaultdict
import asyncio
import ipaddress

from fastapi import HTTPException, Request, Response
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from starlette.middleware.base import BaseHTTPMiddleware
from prometheus_client import Counter, Histogram, Gauge
import redis
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.enhanced_secrets_manager import get_secret_secure
from app.models.api_usage import APIUsageLog, APIKey, RateLimitViolation
from app.core.notifications import send_security_alert

logger = logging.getLogger(__name__)

# Security metrics
api_requests_counter = Counter(
    'api_requests_total',
    'Total API requests',
    ['api_key', 'endpoint', 'status']
)
rate_limit_violations_counter = Counter(
    'rate_limit_violations_total',
    'Rate limit violations',
    ['api_key', 'endpoint']
)
api_response_time_histogram = Histogram(
    'api_response_time_seconds',
    'API response time',
    ['endpoint']
)
suspicious_activity_gauge = Gauge(
    'suspicious_api_activity',
    'Current suspicious activity score',
    ['api_key']
)


class APIKeyValidator:
    """Validates API keys and enforces restrictions."""
    
    def __init__(self):
        self._redis_client = None
        self._init_redis()
        self._key_cache = {}
        self._cache_ttl = 300  # 5 minutes
    
    def _init_redis(self):
        """Initialize Redis connection."""
        try:
            self._redis_client = redis.Redis(
                host=settings.REDIS_HOST,
                port=settings.REDIS_PORT,
                password=settings.REDIS_PASSWORD,
                decode_responses=True
            )
            self._redis_client.ping()
        except Exception as e:
            logger.warning(f"Redis not available for API security: {e}")
            self._redis_client = None
    
    def validate_api_key(
        self,
        api_key: str,
        request: Request,
        required_scopes: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Validate API key and check restrictions.
        
        Args:
            api_key: The API key to validate
            request: FastAPI request object
            required_scopes: Required scopes for this endpoint
            
        Returns:
            Dict with validation result and key metadata
            
        Raises:
            HTTPException: If validation fails
        """
        # Check cache first
        cached = self._get_cached_key_info(api_key)
        if cached:
            key_info = cached
        else:
            # Validate against database
            key_info = self._validate_key_db(api_key)
            if key_info:
                self._cache_key_info(api_key, key_info)
        
        if not key_info:
            logger.warning(f"Invalid API key attempted: {api_key[:8]}...")
            raise HTTPException(status_code=401, detail="Invalid API key")
        
        # Check if key is active
        if not key_info.get("is_active"):
            raise HTTPException(status_code=401, detail="API key is inactive")
        
        # Check expiration
        if key_info.get("expires_at"):
            expires_at = datetime.fromisoformat(key_info["expires_at"])
            if datetime.utcnow() > expires_at:
                raise HTTPException(status_code=401, detail="API key has expired")
        
        # Validate IP restrictions
        if key_info.get("allowed_ips"):
            client_ip = self._get_client_ip(request)
            if not self._validate_ip_restriction(client_ip, key_info["allowed_ips"]):
                logger.warning(f"IP restriction violation for key {api_key[:8]}... from {client_ip}")
                raise HTTPException(status_code=403, detail="IP address not allowed")
        
        # Validate domain restrictions
        if key_info.get("allowed_domains"):
            origin = request.headers.get("origin", "")
            referer = request.headers.get("referer", "")
            if not self._validate_domain_restriction(origin, referer, key_info["allowed_domains"]):
                logger.warning(f"Domain restriction violation for key {api_key[:8]}...")
                raise HTTPException(status_code=403, detail="Domain not allowed")
        
        # Check required scopes
        if required_scopes:
            key_scopes = set(key_info.get("scopes", []))
            required = set(required_scopes)
            if not required.issubset(key_scopes):
                missing = required - key_scopes
                raise HTTPException(
                    status_code=403,
                    detail=f"Missing required scopes: {', '.join(missing)}"
                )
        
        # Check service restrictions
        endpoint = str(request.url.path)
        if not self._validate_service_restriction(endpoint, key_info.get("allowed_services", [])):
            raise HTTPException(status_code=403, detail="Service not allowed for this API key")
        
        return key_info
    
    def _get_cached_key_info(self, api_key: str) -> Optional[Dict[str, Any]]:
        """Get API key info from cache."""
        if not self._redis_client:
            return self._key_cache.get(api_key)
        
        try:
            cache_key = f"api_key:{api_key}"
            cached = self._redis_client.get(cache_key)
            if cached:
                return json.loads(cached)
        except Exception as e:
            logger.error(f"Cache retrieval error: {e}")
        
        return None
    
    def _cache_key_info(self, api_key: str, key_info: Dict[str, Any]):
        """Cache API key info."""
        # Memory cache
        self._key_cache[api_key] = key_info
        
        # Redis cache
        if self._redis_client:
            try:
                cache_key = f"api_key:{api_key}"
                self._redis_client.setex(
                    cache_key,
                    self._cache_ttl,
                    json.dumps(key_info)
                )
            except Exception as e:
                logger.error(f"Cache storage error: {e}")
    
    def _validate_key_db(self, api_key: str) -> Optional[Dict[str, Any]]:
        """Validate API key against database."""
        # This would query your database
        # For now, returning mock data
        return {
            "id": 1,
            "key": api_key,
            "name": "Frontend App",
            "is_active": True,
            "expires_at": None,
            "allowed_ips": [],
            "allowed_domains": ["localhost", "luckygas.com.tw"],
            "allowed_services": ["maps", "geocoding"],
            "scopes": ["read", "write"],
            "rate_limit": 1000,
            "rate_limit_window": 3600
        }
    
    def _get_client_ip(self, request: Request) -> str:
        """Get client IP address from request."""
        # Check X-Forwarded-For header
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            # Take the first IP in the chain
            return forwarded.split(",")[0].strip()
        
        # Check X-Real-IP header
        real_ip = request.headers.get("X-Real-IP")
        if real_ip:
            return real_ip
        
        # Fall back to direct connection
        return request.client.host if request.client else "127.0.0.1"
    
    def _validate_ip_restriction(self, client_ip: str, allowed_ips: List[str]) -> bool:
        """Validate IP against allowed list."""
        if not allowed_ips:
            return True
        
        try:
            client_addr = ipaddress.ip_address(client_ip)
            
            for allowed in allowed_ips:
                # Support CIDR notation
                if "/" in allowed:
                    network = ipaddress.ip_network(allowed, strict=False)
                    if client_addr in network:
                        return True
                else:
                    if str(client_addr) == allowed:
                        return True
            
            return False
        except Exception as e:
            logger.error(f"IP validation error: {e}")
            return False
    
    def _validate_domain_restriction(
        self,
        origin: str,
        referer: str,
        allowed_domains: List[str]
    ) -> bool:
        """Validate request domain against allowed list."""
        if not allowed_domains:
            return True
        
        # Extract domain from origin/referer
        for url in [origin, referer]:
            if url:
                try:
                    from urllib.parse import urlparse
                    parsed = urlparse(url)
                    domain = parsed.netloc.lower()
                    
                    # Remove port if present
                    if ":" in domain:
                        domain = domain.split(":")[0]
                    
                    # Check exact match or subdomain match
                    for allowed in allowed_domains:
                        allowed = allowed.lower()
                        if domain == allowed or domain.endswith(f".{allowed}"):
                            return True
                except Exception as e:
                    logger.error(f"Domain parsing error: {e}")
        
        return False
    
    def _validate_service_restriction(
        self,
        endpoint: str,
        allowed_services: List[str]
    ) -> bool:
        """Validate endpoint against allowed services."""
        if not allowed_services:
            return True
        
        # Map endpoints to services
        service_map = {
            "/api/v1/maps/": "maps",
            "/api/v1/geocoding/": "geocoding",
            "/api/v1/directions/": "directions",
            "/api/v1/places/": "places"
        }
        
        for prefix, service in service_map.items():
            if endpoint.startswith(prefix) and service in allowed_services:
                return True
        
        return False


class AdaptiveRateLimiter:
    """Adaptive rate limiting with anomaly detection."""
    
    def __init__(self):
        self._redis_client = None
        self._init_redis()
        self._violation_threshold = 5  # violations before adaptive action
        self._anomaly_callbacks = []
    
    def _init_redis(self):
        """Initialize Redis connection."""
        try:
            self._redis_client = redis.Redis(
                host=settings.REDIS_HOST,
                port=settings.REDIS_PORT,
                password=settings.REDIS_PASSWORD,
                decode_responses=True
            )
            self._redis_client.ping()
        except Exception as e:
            logger.warning(f"Redis not available for rate limiting: {e}")
            self._redis_client = None
    
    async def check_rate_limit(
        self,
        key: str,
        limit: int,
        window: int,
        endpoint: str
    ) -> Tuple[bool, Dict[str, Any]]:
        """
        Check rate limit with adaptive behavior.
        
        Args:
            key: Rate limit key (e.g., api_key:user_id)
            limit: Request limit
            window: Time window in seconds
            endpoint: API endpoint being accessed
            
        Returns:
            Tuple of (allowed, metadata)
        """
        if not self._redis_client:
            return True, {"requests": 0, "remaining": limit}
        
        try:
            # Use sliding window algorithm
            now = time.time()
            window_start = now - window
            rate_key = f"rate:{key}:{endpoint}"
            
            # Remove old entries
            self._redis_client.zremrangebyscore(rate_key, 0, window_start)
            
            # Count requests in window
            current_requests = self._redis_client.zcard(rate_key)
            
            # Check for anomalies
            if current_requests > limit * 0.8:  # 80% threshold
                await self._check_anomaly(key, endpoint, current_requests, limit)
            
            # Check limit
            if current_requests >= limit:
                # Record violation
                await self._record_violation(key, endpoint)
                
                # Check if we should adapt
                violations = await self._get_violation_count(key)
                if violations >= self._violation_threshold:
                    # Reduce limit temporarily
                    adapted_limit = int(limit * 0.5)  # 50% reduction
                    logger.warning(f"Adapting rate limit for {key}: {limit} -> {adapted_limit}")
                    limit = adapted_limit
                
                return False, {
                    "requests": current_requests,
                    "remaining": 0,
                    "retry_after": int(window_start + window - now),
                    "adapted": violations >= self._violation_threshold
                }
            
            # Add current request
            self._redis_client.zadd(rate_key, {str(now): now})
            self._redis_client.expire(rate_key, window)
            
            return True, {
                "requests": current_requests + 1,
                "remaining": limit - current_requests - 1
            }
            
        except Exception as e:
            logger.error(f"Rate limit check error: {e}")
            return True, {"requests": 0, "remaining": limit}
    
    async def _check_anomaly(
        self,
        key: str,
        endpoint: str,
        requests: int,
        limit: int
    ):
        """Check for anomalous behavior."""
        # Calculate anomaly score
        usage_ratio = requests / limit
        
        # Check historical patterns
        history_key = f"rate_history:{key}:{endpoint}"
        
        try:
            # Get historical average
            historical = self._redis_client.lrange(history_key, 0, -1)
            if historical:
                avg_usage = sum(float(h) for h in historical) / len(historical)
                deviation = abs(usage_ratio - avg_usage) / (avg_usage + 0.01)
                
                if deviation > 2.0:  # 200% deviation
                    suspicious_activity_gauge.labels(api_key=key).set(deviation)
                    
                    # Trigger anomaly callbacks
                    for callback in self._anomaly_callbacks:
                        await callback(key, endpoint, deviation)
            
            # Store current usage
            self._redis_client.lpush(history_key, usage_ratio)
            self._redis_client.ltrim(history_key, 0, 23)  # Keep 24 hours
            self._redis_client.expire(history_key, 86400)
            
        except Exception as e:
            logger.error(f"Anomaly detection error: {e}")
    
    async def _record_violation(self, key: str, endpoint: str):
        """Record rate limit violation."""
        violation_key = f"violations:{key}"
        
        try:
            self._redis_client.incr(violation_key)
            self._redis_client.expire(violation_key, 3600)  # 1 hour
            
            rate_limit_violations_counter.labels(
                api_key=key,
                endpoint=endpoint
            ).inc()
            
        except Exception as e:
            logger.error(f"Violation recording error: {e}")
    
    async def _get_violation_count(self, key: str) -> int:
        """Get violation count for a key."""
        violation_key = f"violations:{key}"
        
        try:
            count = self._redis_client.get(violation_key)
            return int(count) if count else 0
        except Exception as e:
            logger.error(f"Violation count error: {e}")
            return 0
    
    def register_anomaly_callback(self, callback: Callable):
        """Register callback for anomaly detection."""
        self._anomaly_callbacks.append(callback)


class WebhookValidator:
    """Validates webhook signatures for external services."""
    
    @staticmethod
    def validate_twilio_signature(
        request_url: str,
        params: Dict[str, str],
        signature: str,
        auth_token: str
    ) -> bool:
        """
        Validate Twilio webhook signature.
        
        Args:
            request_url: Full URL of the webhook
            params: Request parameters
            signature: X-Twilio-Signature header
            auth_token: Twilio auth token
            
        Returns:
            True if valid
        """
        # Sort parameters
        sorted_params = sorted(params.items())
        
        # Build validation string
        validation_string = request_url
        for key, value in sorted_params:
            validation_string += f"{key}{value}"
        
        # Calculate expected signature
        expected = hmac.new(
            auth_token.encode('utf-8'),
            validation_string.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()
        
        # Compare signatures
        return hmac.compare_digest(expected, signature)
    
    @staticmethod
    def validate_cht_signature(
        body: bytes,
        signature: str,
        secret: str
    ) -> bool:
        """
        Validate CHT (Chunghwa Telecom) webhook signature.
        
        Args:
            body: Raw request body
            signature: Signature header
            secret: Webhook secret
            
        Returns:
            True if valid
        """
        # Calculate expected signature
        expected = hmac.new(
            secret.encode('utf-8'),
            body,
            hashlib.sha256
        ).hexdigest()
        
        # Compare signatures
        return hmac.compare_digest(expected, signature)
    
    @staticmethod
    def validate_banking_signature(
        timestamp: str,
        nonce: str,
        body: str,
        signature: str,
        api_key: str,
        api_secret: str
    ) -> bool:
        """
        Validate banking webhook signature.
        
        Args:
            timestamp: Request timestamp
            nonce: Request nonce
            body: Request body
            signature: Signature header
            api_key: Bank API key
            api_secret: Bank API secret
            
        Returns:
            True if valid
        """
        # Build signing string
        signing_string = f"{timestamp}\n{nonce}\n{api_key}\n{body}"
        
        # Calculate expected signature
        expected = hmac.new(
            api_secret.encode('utf-8'),
            signing_string.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()
        
        # Compare signatures
        return hmac.compare_digest(expected, signature)


class APISecurityMiddleware(BaseHTTPMiddleware):
    """Middleware for API security enforcement."""
    
    def __init__(self, app, validator: APIKeyValidator, rate_limiter: AdaptiveRateLimiter):
        super().__init__(app)
        self.validator = validator
        self.rate_limiter = rate_limiter
        self.bearer_scheme = HTTPBearer(auto_error=False)
    
    async def dispatch(self, request: Request, call_next):
        # Skip security for health checks and docs
        if request.url.path in ["/health", "/docs", "/openapi.json"]:
            return await call_next(request)
        
        # Extract API key
        api_key = None
        
        # Check Authorization header
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            api_key = auth_header[7:]
        
        # Check X-API-Key header
        if not api_key:
            api_key = request.headers.get("X-API-Key")
        
        # Check query parameter (less secure, discouraged)
        if not api_key and request.query_params.get("api_key"):
            api_key = request.query_params["api_key"]
        
        if not api_key:
            return Response(
                content=json.dumps({"detail": "API key required"}),
                status_code=401,
                media_type="application/json"
            )
        
        try:
            # Validate API key
            key_info = self.validator.validate_api_key(api_key, request)
            
            # Check rate limit
            rate_limit = key_info.get("rate_limit", 1000)
            rate_window = key_info.get("rate_limit_window", 3600)
            
            allowed, rate_info = await self.rate_limiter.check_rate_limit(
                key=f"api:{api_key}",
                limit=rate_limit,
                window=rate_window,
                endpoint=str(request.url.path)
            )
            
            if not allowed:
                return Response(
                    content=json.dumps({
                        "detail": "Rate limit exceeded",
                        "retry_after": rate_info.get("retry_after", 60)
                    }),
                    status_code=429,
                    headers={
                        "X-RateLimit-Limit": str(rate_limit),
                        "X-RateLimit-Remaining": "0",
                        "X-RateLimit-Reset": str(int(time.time()) + rate_info.get("retry_after", 60))
                    },
                    media_type="application/json"
                )
            
            # Add rate limit headers
            response = await call_next(request)
            response.headers["X-RateLimit-Limit"] = str(rate_limit)
            response.headers["X-RateLimit-Remaining"] = str(rate_info.get("remaining", 0))
            response.headers["X-RateLimit-Reset"] = str(int(time.time()) + rate_window)
            
            # Track metrics
            api_requests_counter.labels(
                api_key=api_key[:8] + "...",
                endpoint=str(request.url.path),
                status=response.status_code
            ).inc()
            
            return response
            
        except HTTPException as e:
            return Response(
                content=json.dumps({"detail": e.detail}),
                status_code=e.status_code,
                media_type="application/json"
            )
        except Exception as e:
            logger.error(f"Security middleware error: {e}")
            return Response(
                content=json.dumps({"detail": "Internal server error"}),
                status_code=500,
                media_type="application/json"
            )


# Decorator for endpoint-specific security
def require_api_key(scopes: Optional[List[str]] = None):
    """Decorator to require API key with specific scopes."""
    def decorator(func):
        @wraps(func)
        async def wrapper(request: Request, *args, **kwargs):
            validator = APIKeyValidator()
            
            # Extract API key
            api_key = None
            auth_header = request.headers.get("Authorization")
            if auth_header and auth_header.startswith("Bearer "):
                api_key = auth_header[7:]
            
            if not api_key:
                api_key = request.headers.get("X-API-Key")
            
            if not api_key:
                raise HTTPException(status_code=401, detail="API key required")
            
            # Validate with scopes
            key_info = validator.validate_api_key(api_key, request, scopes)
            
            # Add key info to request state
            request.state.api_key_info = key_info
            
            return await func(request, *args, **kwargs)
        
        return wrapper
    return decorator


# Initialize global instances
api_validator = APIKeyValidator()
rate_limiter = AdaptiveRateLimiter()
webhook_validator = WebhookValidator()


# Anomaly detection callback
async def security_anomaly_detected(key: str, endpoint: str, deviation: float):
    """Handle security anomaly detection."""
    if deviation > 3.0:  # 300% deviation
        await send_security_alert(
            title="API Security Anomaly Detected",
            message=f"Unusual activity detected for API key {key[:8]}... on endpoint {endpoint}. Deviation: {deviation:.2f}x normal",
            severity="high"
        )
        
        # Consider auto-blocking if severe
        if deviation > 5.0:
            logger.critical(f"Severe anomaly detected for {key}, considering auto-block")


# Register anomaly callback
rate_limiter.register_anomaly_callback(security_anomaly_detected)