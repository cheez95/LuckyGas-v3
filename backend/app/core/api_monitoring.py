"""
API Monitoring and Circuit Breaker implementation for LuckyGas production APIs.

This module provides centralized monitoring, circuit breakers, and health checks
for all external API integrations including E-Invoice, Banking, and SMS providers.
"""

import asyncio
import time
import logging
from typing import Dict, Any, Optional, Callable, List
from datetime import datetime, timedelta
from enum import Enum
from dataclasses import dataclass, field
from functools import wraps
import httpx
from prometheus_client import Counter, Histogram, Gauge, Summary

from app.core.config import settings

logger = logging.getLogger(__name__)


class CircuitState(Enum):
    """Circuit breaker states"""
    CLOSED = "closed"      # Normal operation
    OPEN = "open"          # Blocking calls
    HALF_OPEN = "half_open"  # Testing recovery


@dataclass
class CircuitBreakerConfig:
    """Configuration for circuit breaker"""
    failure_threshold: int = 5
    recovery_timeout: int = 300  # 5 minutes
    success_threshold: int = 3  # Successes needed in half-open state
    timeout: float = 30.0  # Request timeout
    expected_exceptions: tuple = (httpx.HTTPError, asyncio.TimeoutError)


@dataclass
class CircuitBreakerState:
    """State tracking for circuit breaker"""
    state: CircuitState = CircuitState.CLOSED
    failure_count: int = 0
    success_count: int = 0
    last_failure_time: Optional[datetime] = None
    last_success_time: Optional[datetime] = None
    consecutive_successes: int = 0
    total_requests: int = 0
    total_failures: int = 0
    metrics: Dict[str, Any] = field(default_factory=dict)


class CircuitBreaker:
    """
    Enhanced circuit breaker with monitoring and metrics.
    
    Features:
    - Configurable failure thresholds
    - Half-open state with success requirements
    - Prometheus metrics integration
    - Detailed state tracking
    """
    
    def __init__(self, name: str, config: Optional[CircuitBreakerConfig] = None):
        self.name = name
        self.config = config or CircuitBreakerConfig()
        self.state = CircuitBreakerState()
        self._lock = asyncio.Lock()
        self._init_metrics()
        
    def _init_metrics(self):
        """Initialize Prometheus metrics"""
        try:
            self.metrics = {
                "state": Gauge(
                    f'circuit_breaker_state_{self.name}',
                    f'Circuit breaker state for {self.name} (0=closed, 1=open, 2=half-open)'
                ),
                "failures": Counter(
                    f'circuit_breaker_failures_{self.name}',
                    f'Total failures for {self.name}'
                ),
                "requests": Counter(
                    f'circuit_breaker_requests_{self.name}',
                    f'Total requests for {self.name}',
                    ['result']
                ),
                "state_changes": Counter(
                    f'circuit_breaker_state_changes_{self.name}',
                    f'State changes for {self.name}',
                    ['from_state', 'to_state']
                )
            }
            self._update_state_metric()
        except ImportError:
            logger.warning(f"Prometheus not available for circuit breaker {self.name}")
            self.metrics = None
            
    def _update_state_metric(self):
        """Update state metric"""
        if self.metrics:
            state_values = {
                CircuitState.CLOSED: 0,
                CircuitState.OPEN: 1,
                CircuitState.HALF_OPEN: 2
            }
            self.metrics["state"].set(state_values[self.state.state])
            
    async def _transition_state(self, new_state: CircuitState):
        """Transition to new state with logging and metrics"""
        old_state = self.state.state
        if old_state != new_state:
            self.state.state = new_state
            logger.info(f"Circuit breaker {self.name}: {old_state.value} -> {new_state.value}")
            
            if self.metrics:
                self.metrics["state_changes"].labels(
                    from_state=old_state.value,
                    to_state=new_state.value
                ).inc()
                
            self._update_state_metric()
            
    async def _should_attempt_reset(self) -> bool:
        """Check if circuit should attempt reset"""
        if self.state.last_failure_time:
            time_since_failure = (datetime.utcnow() - self.state.last_failure_time).total_seconds()
            return time_since_failure >= self.config.recovery_timeout
        return False
        
    async def _record_success(self):
        """Record successful call"""
        async with self._lock:
            self.state.success_count += 1
            self.state.consecutive_successes += 1
            self.state.last_success_time = datetime.utcnow()
            
            if self.metrics:
                self.metrics["requests"].labels(result="success").inc()
                
            if self.state.state == CircuitState.HALF_OPEN:
                if self.state.consecutive_successes >= self.config.success_threshold:
                    await self._transition_state(CircuitState.CLOSED)
                    self.state.failure_count = 0
                    self.state.consecutive_successes = 0
                    
    async def _record_failure(self, error: Exception):
        """Record failed call"""
        async with self._lock:
            self.state.failure_count += 1
            self.state.total_failures += 1
            self.state.consecutive_successes = 0
            self.state.last_failure_time = datetime.utcnow()
            
            if self.metrics:
                self.metrics["failures"].inc()
                self.metrics["requests"].labels(result="failure").inc()
                
            if self.state.state == CircuitState.CLOSED:
                if self.state.failure_count >= self.config.failure_threshold:
                    await self._transition_state(CircuitState.OPEN)
            elif self.state.state == CircuitState.HALF_OPEN:
                await self._transition_state(CircuitState.OPEN)
                
    async def call(self, func: Callable, *args, **kwargs):
        """Execute function with circuit breaker protection"""
        async with self._lock:
            self.state.total_requests += 1
            
            if self.state.state == CircuitState.OPEN:
                if await self._should_attempt_reset():
                    await self._transition_state(CircuitState.HALF_OPEN)
                else:
                    recovery_time = self.state.last_failure_time + timedelta(
                        seconds=self.config.recovery_timeout
                    )
                    raise Exception(
                        f"Circuit breaker {self.name} is OPEN. "
                        f"Service unavailable until {recovery_time.isoformat()}"
                    )
                    
        # Execute the function
        try:
            # Add timeout protection
            result = await asyncio.wait_for(
                func(*args, **kwargs),
                timeout=self.config.timeout
            )
            await self._record_success()
            return result
        except self.config.expected_exceptions as e:
            await self._record_failure(e)
            raise
            
    def get_state(self) -> Dict[str, Any]:
        """Get current circuit breaker state"""
        return {
            "name": self.name,
            "state": self.state.state.value,
            "failure_count": self.state.failure_count,
            "success_count": self.state.success_count,
            "consecutive_successes": self.state.consecutive_successes,
            "total_requests": self.state.total_requests,
            "total_failures": self.state.total_failures,
            "failure_rate": (
                self.state.total_failures / self.state.total_requests 
                if self.state.total_requests > 0 else 0
            ),
            "last_failure": self.state.last_failure_time.isoformat() if self.state.last_failure_time else None,
            "last_success": self.state.last_success_time.isoformat() if self.state.last_success_time else None,
        }


class APIMonitor:
    """
    Centralized API monitoring system for all external integrations.
    
    Features:
    - Health checks for all APIs
    - Circuit breaker management
    - Metrics collection
    - Alert generation
    """
    
    def __init__(self):
        self.circuit_breakers: Dict[str, CircuitBreaker] = {}
        self.health_checks: Dict[str, Callable] = {}
        self._monitoring_task = None
        self._init_metrics()
        
    def _init_metrics(self):
        """Initialize monitoring metrics"""
        try:
            self.metrics = {
                "api_health": Gauge(
                    'api_health_status',
                    'API health status (1=healthy, 0=unhealthy)',
                    ['api_name']
                ),
                "health_check_duration": Histogram(
                    'api_health_check_duration_seconds',
                    'Health check duration',
                    ['api_name']
                ),
                "api_errors": Counter(
                    'api_errors_total',
                    'Total API errors',
                    ['api_name', 'error_type']
                )
            }
        except ImportError:
            logger.warning("Prometheus not available for API monitoring")
            self.metrics = None
            
    def register_circuit_breaker(
        self, 
        name: str, 
        config: Optional[CircuitBreakerConfig] = None
    ) -> CircuitBreaker:
        """Register a new circuit breaker"""
        if name not in self.circuit_breakers:
            self.circuit_breakers[name] = CircuitBreaker(name, config)
        return self.circuit_breakers[name]
        
    def register_health_check(self, name: str, check_func: Callable):
        """Register a health check function"""
        self.health_checks[name] = check_func
        
    async def check_health(self, name: str) -> Dict[str, Any]:
        """Execute health check for specific API"""
        if name not in self.health_checks:
            return {"status": "unknown", "error": "No health check registered"}
            
        start_time = time.time()
        try:
            result = await self.health_checks[name]()
            duration = time.time() - start_time
            
            if self.metrics:
                self.metrics["api_health"].labels(api_name=name).set(
                    1 if result.get("healthy", False) else 0
                )
                self.metrics["health_check_duration"].labels(api_name=name).observe(duration)
                
            return {
                "status": "healthy" if result.get("healthy", False) else "unhealthy",
                "duration": duration,
                "details": result
            }
        except Exception as e:
            duration = time.time() - start_time
            logger.error(f"Health check failed for {name}: {e}")
            
            if self.metrics:
                self.metrics["api_health"].labels(api_name=name).set(0)
                self.metrics["api_errors"].labels(
                    api_name=name,
                    error_type=type(e).__name__
                ).inc()
                
            return {
                "status": "unhealthy",
                "duration": duration,
                "error": str(e)
            }
            
    async def check_all_health(self) -> Dict[str, Any]:
        """Check health of all registered APIs"""
        results = {}
        tasks = []
        
        for name in self.health_checks:
            tasks.append(self.check_health(name))
            
        health_results = await asyncio.gather(*tasks, return_exceptions=True)
        
        for name, result in zip(self.health_checks.keys(), health_results):
            if isinstance(result, Exception):
                results[name] = {
                    "status": "error",
                    "error": str(result)
                }
            else:
                results[name] = result
                
        return results
        
    async def start_monitoring(self, interval: int = 300):
        """Start background health monitoring"""
        async def monitor():
            while True:
                try:
                    await self.check_all_health()
                    await asyncio.sleep(interval)
                except Exception as e:
                    logger.error(f"Monitoring error: {e}")
                    await asyncio.sleep(60)  # Retry after 1 minute
                    
        self._monitoring_task = asyncio.create_task(monitor())
        logger.info(f"Started API monitoring with {interval}s interval")
        
    def get_circuit_breaker_states(self) -> Dict[str, Any]:
        """Get all circuit breaker states"""
        return {
            name: cb.get_state()
            for name, cb in self.circuit_breakers.items()
        }
        
    def get_dashboard_data(self) -> Dict[str, Any]:
        """Get comprehensive dashboard data"""
        return {
            "timestamp": datetime.utcnow().isoformat(),
            "circuit_breakers": self.get_circuit_breaker_states(),
            "apis_monitored": list(self.health_checks.keys()),
            "environment": settings.ENVIRONMENT
        }


# Global monitor instance
api_monitor = APIMonitor()


def with_circuit_breaker(
    name: str,
    config: Optional[CircuitBreakerConfig] = None
):
    """Decorator for adding circuit breaker to async functions"""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            cb = api_monitor.register_circuit_breaker(name, config)
            return await cb.call(func, *args, **kwargs)
        return wrapper
    return decorator


# Initialize default circuit breakers
def init_api_monitoring():
    """Initialize API monitoring with default configurations"""
    
    # E-Invoice API circuit breaker
    api_monitor.register_circuit_breaker(
        "einvoice",
        CircuitBreakerConfig(
            failure_threshold=5,
            recovery_timeout=300,
            success_threshold=3,
            timeout=30.0
        )
    )
    
    # Banking SFTP circuit breakers (per bank)
    for bank in ["mega", "ctbc", "esun", "first", "taishin"]:
        api_monitor.register_circuit_breaker(
            f"banking_{bank}",
            CircuitBreakerConfig(
                failure_threshold=3,
                recovery_timeout=600,  # 10 minutes for banking
                success_threshold=2,
                timeout=60.0
            )
        )
    
    # SMS provider circuit breakers
    for provider in ["twilio", "every8d", "mitake"]:
        api_monitor.register_circuit_breaker(
            f"sms_{provider}",
            CircuitBreakerConfig(
                failure_threshold=5,
                recovery_timeout=180,  # 3 minutes for SMS
                success_threshold=3,
                timeout=10.0
            )
        )
    
    logger.info("API monitoring initialized")