# Google API Integration Improvements Analysis

## Executive Summary

This document outlines critical improvements needed before integrating the actual Google API keys into the Lucky Gas delivery management system. The analysis identifies security vulnerabilities, missing resilience patterns, and infrastructure gaps that should be addressed to ensure secure, reliable, and cost-effective API usage.

## Current State Analysis

### 1. Security Vulnerabilities
- **Plain Text Storage**: API keys stored in plain text in `.env` files
- **No Encryption**: No encryption mechanism for sensitive configuration data
- **No Key Rotation**: No automated key rotation strategy
- **Limited Access Control**: Basic environment-based configuration without fine-grained access control

### 2. Error Handling Gaps
- **Generic Exception Handling**: Catches all exceptions without specific API error handling
- **No Retry Logic**: Failed API calls are not retried with exponential backoff
- **Limited Error Classification**: No differentiation between transient and permanent failures
- **Minimal Error Context**: Error logging lacks structured context for debugging

### 3. Missing Resilience Patterns
- **No Circuit Breaker**: System continues calling failing APIs without protection
- **No Rate Limiting**: No protection against exceeding API quotas
- **No Request Throttling**: Risk of hitting rate limits during peak usage
- **Limited Fallback Strategies**: Basic fallback to unoptimized routes only

### 4. Cost Management Risks
- **No Usage Tracking**: No detailed tracking of API calls per endpoint
- **No Cost Monitoring**: No alerts for unusual API usage patterns
- **No Quota Management**: No enforcement of daily/monthly quotas
- **Missing Budget Controls**: No automatic shutdown when cost thresholds exceeded

### 5. Development Infrastructure
- **Limited Mocking**: Basic mock services without realistic responses
- **No Offline Mode**: Development requires internet connectivity
- **Insufficient Test Coverage**: Limited testing of API error scenarios
- **No Response Recording**: Cannot replay real API responses for testing

## Recommended Improvements

### 1. Security Enhancements

#### 1.1 Implement Secure Key Management
```python
# app/core/security/api_key_manager.py
from cryptography.fernet import Fernet
from abc import ABC, abstractmethod
import os
import json
from typing import Optional, Dict
import boto3
from google.cloud import secretmanager

class APIKeyManager(ABC):
    """Abstract base class for API key management"""
    
    @abstractmethod
    async def get_key(self, key_name: str) -> Optional[str]:
        """Retrieve an API key securely"""
        pass
    
    @abstractmethod
    async def rotate_key(self, key_name: str, new_value: str) -> bool:
        """Rotate an API key"""
        pass

class LocalEncryptedKeyManager(APIKeyManager):
    """Local development key manager with encryption"""
    
    def __init__(self, master_key_path: str = ".keys/master.key"):
        self.master_key = self._load_or_create_master_key(master_key_path)
        self.fernet = Fernet(self.master_key)
        self.keys_file = ".keys/encrypted_keys.json"
    
    def _load_or_create_master_key(self, path: str) -> bytes:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        if os.path.exists(path):
            with open(path, 'rb') as f:
                return f.read()
        else:
            key = Fernet.generate_key()
            with open(path, 'wb') as f:
                f.write(key)
            os.chmod(path, 0o600)  # Restrict access
            return key
    
    async def get_key(self, key_name: str) -> Optional[str]:
        if not os.path.exists(self.keys_file):
            return None
        
        with open(self.keys_file, 'r') as f:
            encrypted_keys = json.load(f)
        
        if key_name in encrypted_keys:
            encrypted_value = encrypted_keys[key_name].encode()
            return self.fernet.decrypt(encrypted_value).decode()
        return None
    
    async def rotate_key(self, key_name: str, new_value: str) -> bool:
        encrypted_keys = {}
        if os.path.exists(self.keys_file):
            with open(self.keys_file, 'r') as f:
                encrypted_keys = json.load(f)
        
        encrypted_value = self.fernet.encrypt(new_value.encode()).decode()
        encrypted_keys[key_name] = encrypted_value
        
        with open(self.keys_file, 'w') as f:
            json.dump(encrypted_keys, f)
        os.chmod(self.keys_file, 0o600)
        return True

class GCPSecretManager(APIKeyManager):
    """Production key manager using Google Secret Manager"""
    
    def __init__(self, project_id: str):
        self.client = secretmanager.SecretManagerServiceClient()
        self.project_id = project_id
    
    async def get_key(self, key_name: str) -> Optional[str]:
        try:
            name = f"projects/{self.project_id}/secrets/{key_name}/versions/latest"
            response = self.client.access_secret_version(request={"name": name})
            return response.payload.data.decode("UTF-8")
        except Exception as e:
            logger.error(f"Failed to retrieve secret {key_name}: {e}")
            return None
    
    async def rotate_key(self, key_name: str, new_value: str) -> bool:
        try:
            parent = f"projects/{self.project_id}/secrets/{key_name}"
            self.client.add_secret_version(
                request={
                    "parent": parent,
                    "payload": {"data": new_value.encode("UTF-8")}
                }
            )
            return True
        except Exception as e:
            logger.error(f"Failed to rotate secret {key_name}: {e}")
            return False
```

#### 1.2 Update Configuration to Use Secure Keys
```python
# app/core/google_cloud_config.py
from app.core.security.api_key_manager import APIKeyManager, LocalEncryptedKeyManager, GCPSecretManager
from app.core.config import settings

class GoogleCloudConfig:
    """Enhanced Google Cloud configuration with secure key management"""
    
    def __init__(self):
        self.project_id = settings.GCP_PROJECT_ID
        self.location = settings.GCP_LOCATION
        
        # Initialize key manager based on environment
        if settings.is_production():
            self.key_manager = GCPSecretManager(self.project_id)
        else:
            self.key_manager = LocalEncryptedKeyManager()
        
        self._maps_api_key: Optional[str] = None
        self._vertex_api_key: Optional[str] = None
    
    async def get_maps_api_key(self) -> Optional[str]:
        """Get Maps API key with caching"""
        if not self._maps_api_key:
            self._maps_api_key = await self.key_manager.get_key("google-maps-api-key")
        return self._maps_api_key
    
    async def get_vertex_api_key(self) -> Optional[str]:
        """Get Vertex AI API key with caching"""
        if not self._vertex_api_key:
            self._vertex_api_key = await self.key_manager.get_key("vertex-ai-api-key")
        return self._vertex_api_key
```

### 2. Comprehensive Error Handling

#### 2.1 API Error Handler
```python
# app/services/google_cloud/error_handler.py
from enum import Enum
from typing import Optional, Dict, Any, Callable
import asyncio
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)

class GoogleAPIError(Exception):
    """Base exception for Google API errors"""
    def __init__(self, message: str, status_code: int, details: Optional[Dict] = None):
        super().__init__(message)
        self.status_code = status_code
        self.details = details or {}

class APIErrorType(Enum):
    RATE_LIMIT = "rate_limit"
    QUOTA_EXCEEDED = "quota_exceeded"
    INVALID_API_KEY = "invalid_api_key"
    SERVICE_UNAVAILABLE = "service_unavailable"
    INVALID_REQUEST = "invalid_request"
    NETWORK_ERROR = "network_error"
    UNKNOWN = "unknown"

class GoogleAPIErrorHandler:
    """Comprehensive error handler for Google API calls"""
    
    ERROR_MAPPING = {
        429: APIErrorType.RATE_LIMIT,
        403: APIErrorType.QUOTA_EXCEEDED,
        401: APIErrorType.INVALID_API_KEY,
        503: APIErrorType.SERVICE_UNAVAILABLE,
        400: APIErrorType.INVALID_REQUEST,
    }
    
    RETRY_STRATEGIES = {
        APIErrorType.RATE_LIMIT: {"max_retries": 5, "base_delay": 1, "max_delay": 60},
        APIErrorType.SERVICE_UNAVAILABLE: {"max_retries": 3, "base_delay": 2, "max_delay": 30},
        APIErrorType.NETWORK_ERROR: {"max_retries": 3, "base_delay": 1, "max_delay": 10},
    }
    
    @classmethod
    def classify_error(cls, status_code: int, error_body: Dict) -> APIErrorType:
        """Classify the error type based on status code and response body"""
        if status_code in cls.ERROR_MAPPING:
            return cls.ERROR_MAPPING[status_code]
        
        # Check error body for additional classification
        error_message = str(error_body.get("error", {}).get("message", "")).lower()
        if "quota" in error_message:
            return APIErrorType.QUOTA_EXCEEDED
        elif "rate" in error_message:
            return APIErrorType.RATE_LIMIT
        
        return APIErrorType.UNKNOWN
    
    @classmethod
    async def handle_with_retry(
        cls,
        func: Callable,
        *args,
        **kwargs
    ) -> Any:
        """Execute function with intelligent retry logic"""
        last_error = None
        
        for attempt in range(3):  # Default max attempts
            try:
                return await func(*args, **kwargs)
            except GoogleAPIError as e:
                last_error = e
                error_type = cls.classify_error(e.status_code, e.details)
                
                if error_type in cls.RETRY_STRATEGIES:
                    strategy = cls.RETRY_STRATEGIES[error_type]
                    if attempt < strategy["max_retries"]:
                        delay = min(
                            strategy["base_delay"] * (2 ** attempt),
                            strategy["max_delay"]
                        )
                        logger.warning(
                            f"API error {error_type.value}, retrying in {delay}s "
                            f"(attempt {attempt + 1}/{strategy['max_retries']})"
                        )
                        await asyncio.sleep(delay)
                        continue
                
                # Non-retryable error or max retries exceeded
                logger.error(f"API error {error_type.value}: {e}")
                raise
            except Exception as e:
                logger.error(f"Unexpected error: {e}")
                raise
        
        if last_error:
            raise last_error
```

### 3. Rate Limiting Implementation

#### 3.1 Rate Limiter
```python
# app/services/google_cloud/rate_limiter.py
import asyncio
from datetime import datetime, timedelta
from collections import deque
from typing import Dict, Optional
import redis.asyncio as redis
from app.core.cache import get_redis_client

class GoogleAPIRateLimiter:
    """Rate limiter for Google API calls"""
    
    # Google Maps API limits (example)
    LIMITS = {
        "routes": {"per_second": 10, "per_day": 25000},
        "geocoding": {"per_second": 50, "per_day": 2500},
        "places": {"per_second": 10, "per_day": 150000},
    }
    
    def __init__(self, redis_client: Optional[redis.Redis] = None):
        self.redis = redis_client or get_redis_client()
        self.local_queues: Dict[str, deque] = {}
    
    async def check_rate_limit(self, api_type: str) -> bool:
        """Check if API call is within rate limits"""
        if api_type not in self.LIMITS:
            return True
        
        limits = self.LIMITS[api_type]
        now = datetime.now()
        
        # Check per-second limit
        if not await self._check_limit(
            f"rate_limit:{api_type}:second",
            limits["per_second"],
            1
        ):
            return False
        
        # Check daily limit
        if not await self._check_limit(
            f"rate_limit:{api_type}:day:{now.date()}",
            limits["per_day"],
            86400
        ):
            return False
        
        return True
    
    async def _check_limit(self, key: str, limit: int, window: int) -> bool:
        """Check if we're within the specified limit"""
        try:
            current = await self.redis.incr(key)
            if current == 1:
                await self.redis.expire(key, window)
            return current <= limit
        except Exception as e:
            logger.error(f"Rate limit check failed: {e}")
            # Fail open in case of Redis issues
            return True
    
    async def wait_if_needed(self, api_type: str) -> None:
        """Wait if rate limit is exceeded"""
        while not await self.check_rate_limit(api_type):
            await asyncio.sleep(0.1)  # Wait 100ms and retry
    
    async def get_usage_stats(self, api_type: str) -> Dict[str, int]:
        """Get current usage statistics"""
        now = datetime.now()
        stats = {}
        
        try:
            # Get per-second usage
            second_key = f"rate_limit:{api_type}:second"
            stats["per_second_current"] = int(await self.redis.get(second_key) or 0)
            stats["per_second_limit"] = self.LIMITS.get(api_type, {}).get("per_second", 0)
            
            # Get daily usage
            day_key = f"rate_limit:{api_type}:day:{now.date()}"
            stats["per_day_current"] = int(await self.redis.get(day_key) or 0)
            stats["per_day_limit"] = self.LIMITS.get(api_type, {}).get("per_day", 0)
            
            # Calculate remaining
            stats["per_day_remaining"] = max(0, stats["per_day_limit"] - stats["per_day_current"])
            
        except Exception as e:
            logger.error(f"Failed to get usage stats: {e}")
        
        return stats
```

### 4. Cost Monitoring and Alerting

#### 4.1 API Cost Monitor
```python
# app/services/google_cloud/cost_monitor.py
from typing import Dict, Optional
from datetime import datetime, timedelta
from decimal import Decimal
import asyncio
from app.core.metrics import google_api_calls_counter, google_api_cost_gauge
from app.core.cache import get_redis_client
from app.services.notification_service import NotificationService

class GoogleAPICostMonitor:
    """Monitor and control Google API costs"""
    
    # Estimated costs per API call (in USD)
    COST_PER_CALL = {
        "routes": Decimal("0.005"),  # $5 per 1000 requests
        "geocoding": Decimal("0.005"),  # $5 per 1000 requests
        "places": Decimal("0.017"),  # $17 per 1000 requests
        "vertex_ai": Decimal("0.001"),  # $1 per 1000 predictions
    }
    
    # Budget thresholds
    THRESHOLDS = {
        "daily_warning": Decimal("50.00"),  # $50/day warning
        "daily_critical": Decimal("100.00"),  # $100/day critical
        "monthly_warning": Decimal("1000.00"),  # $1000/month warning
        "monthly_critical": Decimal("2000.00"),  # $2000/month critical
    }
    
    def __init__(self):
        self.redis = get_redis_client()
        self.notification_service = NotificationService()
        self.last_alert_time: Dict[str, datetime] = {}
    
    async def record_api_call(self, api_type: str, endpoint: str) -> None:
        """Record an API call and update costs"""
        # Update metrics
        google_api_calls_counter.labels(api=api_type, endpoint=endpoint).inc()
        
        # Calculate cost
        cost = self.COST_PER_CALL.get(api_type, Decimal("0"))
        
        # Update daily cost
        today = datetime.now().date()
        daily_key = f"api_cost:{today}:{api_type}"
        await self.redis.incrbyfloat(daily_key, float(cost))
        await self.redis.expire(daily_key, 86400 * 7)  # Keep for 7 days
        
        # Update monthly cost
        month_key = f"api_cost:{today.year}-{today.month}:{api_type}"
        await self.redis.incrbyfloat(month_key, float(cost))
        await self.redis.expire(month_key, 86400 * 35)  # Keep for 35 days
        
        # Check thresholds
        await self._check_cost_thresholds(api_type)
    
    async def _check_cost_thresholds(self, api_type: str) -> None:
        """Check if costs exceed thresholds and send alerts"""
        today = datetime.now().date()
        
        # Get daily total
        daily_total = Decimal("0")
        for api in self.COST_PER_CALL.keys():
            daily_key = f"api_cost:{today}:{api}"
            cost = await self.redis.get(daily_key)
            if cost:
                daily_total += Decimal(cost)
        
        # Check daily thresholds
        if daily_total > self.THRESHOLDS["daily_critical"]:
            await self._send_alert(
                "critical",
                f"Daily API cost critical: ${daily_total:.2f}",
                {"api_type": api_type, "total": str(daily_total)}
            )
        elif daily_total > self.THRESHOLDS["daily_warning"]:
            await self._send_alert(
                "warning",
                f"Daily API cost warning: ${daily_total:.2f}",
                {"api_type": api_type, "total": str(daily_total)}
            )
        
        # Update cost gauge metric
        google_api_cost_gauge.labels(period="daily").set(float(daily_total))
    
    async def _send_alert(self, level: str, message: str, data: Dict) -> None:
        """Send cost alert with rate limiting"""
        alert_key = f"{level}:{message[:50]}"
        now = datetime.now()
        
        # Rate limit alerts to once per hour
        if alert_key in self.last_alert_time:
            if now - self.last_alert_time[alert_key] < timedelta(hours=1):
                return
        
        self.last_alert_time[alert_key] = now
        
        # Send notification
        await self.notification_service.send_admin_alert(
            title=f"API Cost Alert - {level.upper()}",
            message=message,
            data=data,
            priority=level
        )
    
    async def get_cost_report(self, period: str = "daily") -> Dict:
        """Generate cost report"""
        today = datetime.now().date()
        report = {"period": period, "date": str(today), "costs_by_api": {}}
        
        if period == "daily":
            total = Decimal("0")
            for api in self.COST_PER_CALL.keys():
                key = f"api_cost:{today}:{api}"
                cost = await self.redis.get(key)
                if cost:
                    cost_decimal = Decimal(cost)
                    report["costs_by_api"][api] = float(cost_decimal)
                    total += cost_decimal
            report["total"] = float(total)
            report["budget_remaining"] = float(self.THRESHOLDS["daily_warning"] - total)
        
        return report
    
    async def enforce_budget_limit(self, api_type: str) -> bool:
        """Check if API call should be blocked due to budget limits"""
        today = datetime.now().date()
        
        # Get daily total
        daily_total = Decimal("0")
        for api in self.COST_PER_CALL.keys():
            daily_key = f"api_cost:{today}:{api}"
            cost = await self.redis.get(daily_key)
            if cost:
                daily_total += Decimal(cost)
        
        # Block if over critical threshold
        if daily_total >= self.THRESHOLDS["daily_critical"]:
            logger.warning(f"Blocking API call due to budget limit: ${daily_total:.2f}")
            return False
        
        return True
```

### 5. Enhanced Mock Services

#### 5.1 Realistic Mock Google Routes Service
```python
# app/services/google_cloud/mock_routes_service.py
import json
import random
from typing import List, Dict, Tuple, Any
from datetime import datetime, timedelta
import asyncio
from app.services.google_cloud.routes_service import GoogleRoutesService

class MockGoogleRoutesService(GoogleRoutesService):
    """Realistic mock implementation of Google Routes API for development"""
    
    def __init__(self):
        super().__init__()
        self.mock_delays = {
            "min": 0.1,  # 100ms minimum
            "max": 0.5   # 500ms maximum
        }
        self.mock_polylines = [
            "ipkcFfichVnP@j@",
            "u{~vFvyys@fS]",
            "_gjaF~jbs@qBmG",
        ]
    
    async def optimize_route(
        self,
        depot: Tuple[float, float],
        stops: List[Dict],
        vehicle_capacity: int = 100,
        time_windows: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """Mock route optimization with realistic response"""
        # Simulate API latency
        await asyncio.sleep(random.uniform(self.mock_delays["min"], self.mock_delays["max"]))
        
        # Simulate optimization by sorting by a combination of factors
        optimized_stops = sorted(stops, key=lambda s: (
            s.get("priority", 0),  # Higher priority first
            self._calculate_distance(depot[0], depot[1], s["lat"], s["lng"])
        ))
        
        # Add realistic timing
        current_time = datetime.now()
        total_distance = 0
        total_duration = 0
        
        for i, stop in enumerate(optimized_stops):
            # Calculate distance from previous stop
            if i == 0:
                prev_lat, prev_lng = depot
            else:
                prev_lat = optimized_stops[i-1]["lat"]
                prev_lng = optimized_stops[i-1]["lng"]
            
            distance = self._calculate_distance(prev_lat, prev_lng, stop["lat"], stop["lng"])
            total_distance += distance
            
            # Estimate travel time (40 km/h average in city)
            travel_time = (distance / 40) * 60  # minutes
            service_time = stop.get("service_time", 10)
            total_duration += travel_time + service_time
            
            # Set estimated arrival
            stop["stop_sequence"] = i + 1
            stop["estimated_arrival"] = current_time + timedelta(minutes=total_duration)
            stop["distance_from_previous"] = round(distance, 2)
            stop["travel_time_minutes"] = round(travel_time, 1)
        
        # Add return to depot
        if optimized_stops:
            last_stop = optimized_stops[-1]
            return_distance = self._calculate_distance(
                last_stop["lat"], last_stop["lng"], depot[0], depot[1]
            )
            total_distance += return_distance
            total_duration += (return_distance / 40) * 60
        
        return {
            "stops": optimized_stops,
            "total_distance": round(total_distance * 1000, 0),  # Convert to meters
            "total_duration": f"{int(total_duration * 60)}s",  # Convert to seconds
            "polyline": random.choice(self.mock_polylines),
            "warnings": ["Using mock optimization service"],
            "optimized": True,
            "optimization_details": {
                "algorithm": "mock_nearest_neighbor",
                "computation_time_ms": random.randint(50, 200),
                "iterations": random.randint(10, 50)
            }
        }
    
    async def _get_google_directions(
        self,
        depot: Tuple[float, float],
        stops: List[Any]
    ) -> Dict:
        """Mock Google directions for visualization"""
        # Simulate API latency
        await asyncio.sleep(random.uniform(0.05, 0.15))
        
        total_distance = 0
        if stops:
            # Calculate total route distance
            prev_lat, prev_lng = depot
            for stop in stops:
                distance = self._calculate_distance(
                    prev_lat, prev_lng, stop.latitude, stop.longitude
                )
                total_distance += distance
                prev_lat, prev_lng = stop.latitude, stop.longitude
            
            # Return to depot
            distance = self._calculate_distance(
                prev_lat, prev_lng, depot[0], depot[1]
            )
            total_distance += distance
        
        # Estimate duration (40 km/h average)
        duration_minutes = (total_distance / 40) * 60
        
        return {
            "distance": round(total_distance, 2),
            "duration": round(duration_minutes, 0),
            "polyline": random.choice(self.mock_polylines)
        }
```

### 6. Circuit Breaker Pattern

#### 6.1 Circuit Breaker Implementation
```python
# app/services/google_cloud/circuit_breaker.py
from enum import Enum
from datetime import datetime, timedelta
from typing import Optional, Callable, Any, Dict
import asyncio
import logging

logger = logging.getLogger(__name__)

class CircuitState(Enum):
    CLOSED = "closed"  # Normal operation
    OPEN = "open"      # Failing, reject calls
    HALF_OPEN = "half_open"  # Testing if service recovered

class CircuitBreaker:
    """Circuit breaker pattern for API resilience"""
    
    def __init__(
        self,
        failure_threshold: int = 5,
        recovery_timeout: int = 60,
        expected_exception: type = Exception
    ):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.expected_exception = expected_exception
        self.failure_count = 0
        self.last_failure_time: Optional[datetime] = None
        self.state = CircuitState.CLOSED
        self._lock = asyncio.Lock()
    
    async def call(self, func: Callable, *args, **kwargs) -> Any:
        """Execute function through circuit breaker"""
        async with self._lock:
            if self.state == CircuitState.OPEN:
                if self._should_attempt_reset():
                    self.state = CircuitState.HALF_OPEN
                else:
                    raise Exception("Circuit breaker is OPEN")
        
        try:
            result = await func(*args, **kwargs)
            await self._on_success()
            return result
        except self.expected_exception as e:
            await self._on_failure()
            raise
    
    async def _on_success(self):
        """Handle successful call"""
        async with self._lock:
            self.failure_count = 0
            if self.state == CircuitState.HALF_OPEN:
                self.state = CircuitState.CLOSED
                logger.info("Circuit breaker recovered, state: CLOSED")
    
    async def _on_failure(self):
        """Handle failed call"""
        async with self._lock:
            self.failure_count += 1
            self.last_failure_time = datetime.now()
            
            if self.failure_count >= self.failure_threshold:
                self.state = CircuitState.OPEN
                logger.warning(
                    f"Circuit breaker opened after {self.failure_count} failures"
                )
    
    def _should_attempt_reset(self) -> bool:
        """Check if we should try to reset the circuit"""
        return (
            self.last_failure_time and
            datetime.now() - self.last_failure_time > timedelta(seconds=self.recovery_timeout)
        )
    
    def get_state(self) -> Dict[str, Any]:
        """Get current circuit breaker state"""
        return {
            "state": self.state.value,
            "failure_count": self.failure_count,
            "last_failure": self.last_failure_time.isoformat() if self.last_failure_time else None
        }
```

### 7. API Response Caching

#### 7.1 Smart Caching Strategy
```python
# app/services/google_cloud/api_cache.py
import hashlib
import json
from typing import Optional, Dict, Any
from datetime import timedelta
from app.core.cache import get_redis_client
import logging

logger = logging.getLogger(__name__)

class GoogleAPICache:
    """Intelligent caching for Google API responses"""
    
    # Cache TTLs by API type
    CACHE_TTLS = {
        "routes": timedelta(minutes=30),  # Route optimizations valid for 30 min
        "geocoding": timedelta(days=30),  # Addresses don't change often
        "places": timedelta(hours=24),    # Place data updates daily
        "vertex_ai": timedelta(hours=1),  # Predictions expire hourly
    }
    
    def __init__(self):
        self.redis = get_redis_client()
    
    def _generate_cache_key(self, api_type: str, params: Dict[str, Any]) -> str:
        """Generate consistent cache key from parameters"""
        # Sort parameters for consistent hashing
        sorted_params = json.dumps(params, sort_keys=True)
        param_hash = hashlib.md5(sorted_params.encode()).hexdigest()
        return f"google_api:{api_type}:{param_hash}"
    
    async def get(self, api_type: str, params: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Get cached API response"""
        cache_key = self._generate_cache_key(api_type, params)
        
        try:
            cached = await self.redis.get(cache_key)
            if cached:
                logger.debug(f"Cache hit for {api_type}")
                return json.loads(cached)
        except Exception as e:
            logger.error(f"Cache get error: {e}")
        
        return None
    
    async def set(
        self, 
        api_type: str, 
        params: Dict[str, Any], 
        response: Dict[str, Any]
    ) -> bool:
        """Cache API response"""
        cache_key = self._generate_cache_key(api_type, params)
        ttl = self.CACHE_TTLS.get(api_type, timedelta(minutes=5))
        
        try:
            await self.redis.setex(
                cache_key,
                int(ttl.total_seconds()),
                json.dumps(response)
            )
            logger.debug(f"Cached {api_type} response for {ttl}")
            return True
        except Exception as e:
            logger.error(f"Cache set error: {e}")
            return False
    
    async def invalidate_pattern(self, pattern: str) -> int:
        """Invalidate all cache entries matching pattern"""
        try:
            keys = []
            async for key in self.redis.scan_iter(match=f"google_api:{pattern}*"):
                keys.append(key)
            
            if keys:
                deleted = await self.redis.delete(*keys)
                logger.info(f"Invalidated {deleted} cache entries for pattern: {pattern}")
                return deleted
        except Exception as e:
            logger.error(f"Cache invalidation error: {e}")
        
        return 0
```

### 8. Development Mode Configuration

#### 8.1 Offline Development Mode
```python
# app/core/development_mode.py
from typing import Optional
from app.core.config import settings
from app.services.google_cloud.routes_service import GoogleRoutesService
from app.services.google_cloud.mock_routes_service import MockGoogleRoutesService
from app.services.google_cloud.vertex_ai_service import VertexAIService
from app.services.google_cloud.mock_vertex_service import MockVertexAIService

class DevelopmentModeManager:
    """Manage offline development mode"""
    
    def __init__(self):
        self.offline_mode = settings.OFFLINE_MODE or not settings.GOOGLE_MAPS_API_KEY
        self._services = {}
    
    def get_routes_service(self) -> GoogleRoutesService:
        """Get appropriate routes service based on mode"""
        if self.offline_mode:
            if "routes" not in self._services:
                self._services["routes"] = MockGoogleRoutesService()
            return self._services["routes"]
        else:
            if "routes" not in self._services:
                self._services["routes"] = GoogleRoutesService()
            return self._services["routes"]
    
    def get_vertex_service(self) -> VertexAIService:
        """Get appropriate Vertex AI service based on mode"""
        if self.offline_mode:
            if "vertex" not in self._services:
                self._services["vertex"] = MockVertexAIService()
            return self._services["vertex"]
        else:
            if "vertex" not in self._services:
                self._services["vertex"] = VertexAIService()
            return self._services["vertex"]
    
    def is_offline_mode(self) -> bool:
        """Check if running in offline mode"""
        return self.offline_mode
    
    def get_status(self) -> Dict[str, Any]:
        """Get development mode status"""
        return {
            "offline_mode": self.offline_mode,
            "services": {
                "routes": "mock" if self.offline_mode else "live",
                "vertex_ai": "mock" if self.offline_mode else "live",
            },
            "api_keys_configured": {
                "maps": bool(settings.GOOGLE_MAPS_API_KEY),
                "vertex": bool(settings.VERTEX_API_KEY),
            }
        }

# Singleton instance
dev_mode = DevelopmentModeManager()
```

### 9. API Usage Dashboard

#### 9.1 Dashboard Endpoint
```python
# app/api/v1/admin/google_api_dashboard.py
from fastapi import APIRouter, Depends
from typing import Dict, Any
from app.api.deps import get_current_superuser
from app.services.google_cloud.rate_limiter import GoogleAPIRateLimiter
from app.services.google_cloud.cost_monitor import GoogleAPICostMonitor
from app.services.google_cloud.circuit_breaker import CircuitBreaker

router = APIRouter()

@router.get("/google-api/dashboard", response_model=Dict[str, Any])
async def get_api_dashboard(
    current_user = Depends(get_current_superuser)
):
    """Get comprehensive Google API usage dashboard"""
    rate_limiter = GoogleAPIRateLimiter()
    cost_monitor = GoogleAPICostMonitor()
    
    # Get usage stats for each API
    usage_stats = {}
    for api_type in ["routes", "geocoding", "places", "vertex_ai"]:
        usage_stats[api_type] = await rate_limiter.get_usage_stats(api_type)
    
    # Get cost report
    daily_costs = await cost_monitor.get_cost_report("daily")
    monthly_costs = await cost_monitor.get_cost_report("monthly")
    
    # Get circuit breaker states
    circuit_states = {
        "routes": routes_circuit.get_state(),
        "vertex_ai": vertex_circuit.get_state(),
    }
    
    return {
        "usage": usage_stats,
        "costs": {
            "daily": daily_costs,
            "monthly": monthly_costs,
        },
        "circuit_breakers": circuit_states,
        "alerts": {
            "cost_warning": daily_costs["total"] > 50,
            "quota_warning": any(
                stats.get("per_day_remaining", 1) < stats.get("per_day_limit", 1) * 0.1
                for stats in usage_stats.values()
            )
        }
    }

@router.post("/google-api/reset-circuit/{api_type}")
async def reset_circuit_breaker(
    api_type: str,
    current_user = Depends(get_current_superuser)
):
    """Manually reset a circuit breaker"""
    # Implementation to reset specific circuit breaker
    pass
```

## Implementation Priority

1. **High Priority (Implement First)**:
   - Secure API key management (Section 1)
   - Comprehensive error handling (Section 2)
   - Rate limiting (Section 3)
   - Basic cost monitoring (Section 4)

2. **Medium Priority**:
   - Enhanced mock services (Section 5)
   - Circuit breaker pattern (Section 6)
   - API response caching (Section 7)
   - Development mode (Section 8)

3. **Lower Priority**:
   - Full API usage dashboard (Section 9)
   - Advanced cost analytics
   - Automated key rotation

## Testing Requirements

1. **Security Tests**:
   - Test encrypted key storage and retrieval
   - Verify key rotation functionality
   - Test access control for API keys

2. **Resilience Tests**:
   - Test circuit breaker states
   - Verify retry logic with various error types
   - Test rate limiting enforcement

3. **Cost Management Tests**:
   - Test cost calculation accuracy
   - Verify alert thresholds
   - Test budget enforcement

4. **Integration Tests**:
   - Test fallback to mock services
   - Verify caching behavior
   - Test offline development mode

## Monitoring and Alerting

1. **Metrics to Track**:
   - API call volume by type
   - Error rates and types
   - Response times
   - Cost per hour/day/month
   - Cache hit rates
   - Circuit breaker state changes

2. **Alerts to Configure**:
   - High error rate (>5% of calls failing)
   - Approaching API quotas (>80% used)
   - Cost thresholds exceeded
   - Circuit breaker opened
   - Invalid API key detected

## Conclusion

These improvements will ensure the Lucky Gas system is ready for production use with real Google API keys. The implementation provides security, reliability, cost control, and excellent developer experience while protecting against common API integration pitfalls.