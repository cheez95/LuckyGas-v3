"""
Circuit Breaker Pattern for API Resilience
"""

import asyncio
import logging
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Callable, Dict, Optional, TypeVar

from app.core.metrics import Counter, Gauge

logger = logging.getLogger(__name__)

T = TypeVar("T")

# Metrics
circuit_state_gauge = Gauge(
    "google_api_circuit_breaker_state",
    "Circuit breaker state (0=closed, 1=open, 2=half-open)",
    ["api_type"],
)

circuit_failures_counter = Counter(
    "google_api_circuit_breaker_failures", "Circuit breaker failure count", ["api_type"]
)


class CircuitState(Enum):
    """Circuit breaker states"""

    CLOSED = "closed"  # Normal operation
    OPEN = "open"  # Failing, reject calls
    HALF_OPEN = "half_open"  # Testing if service recovered


class CircuitBreaker:
    """
    Circuit breaker pattern implementation for API resilience

    States:
    - CLOSED: Normal operation, requests pass through
    - OPEN: Service is failing, requests are rejected immediately
    - HALF_OPEN: Testing if service has recovered
    """

    def __init__(
        self,
        api_type: str,
        failure_threshold: int = 5,
        success_threshold: int = 2,
        timeout: int = 60,
        expected_exception: type = Exception,
    ):
        """
        Initialize circuit breaker

        Args:
            api_type: API type for metrics/logging
            failure_threshold: Number of failures before opening circuit
            success_threshold: Number of successes in half-open before closing
            timeout: Seconds to wait before attempting recovery
            expected_exception: Exception type to catch
        """
        self.api_type = api_type
        self.failure_threshold = failure_threshold
        self.success_threshold = success_threshold
        self.timeout = timeout
        self.expected_exception = expected_exception

        self.failure_count = 0
        self.success_count = 0
        self.last_failure_time: Optional[datetime] = None
        self.state = CircuitState.CLOSED
        self._lock = asyncio.Lock()

        # Update metrics
        self._update_state_metric()

    def _update_state_metric(self):
        """Update Prometheus metric for circuit state"""
        state_value = {
            CircuitState.CLOSED: 0,
            CircuitState.OPEN: 1,
            CircuitState.HALF_OPEN: 2,
        }
        circuit_state_gauge.labels(api_type=self.api_type).set(state_value[self.state])

    async def call(self, func: Callable[..., T], *args, **kwargs) -> T:
        """
        Execute function through circuit breaker

        Args:
            func: Async function to execute
            *args, **kwargs: Arguments for the function

        Returns:
            Result from the function

        Raises:
            Exception: If circuit is open or function fails
        """
        async with self._lock:
            # Check if we should attempt reset
            if self.state == CircuitState.OPEN:
                if self._should_attempt_reset():
                    logger.info(f"Circuit breaker attempting reset for {self.api_type}")
                    self.state = CircuitState.HALF_OPEN
                    self.success_count = 0
                    self._update_state_metric()
                else:
                    raise Exception(
                        f"Circuit breaker is OPEN for {self.api_type}. "
                        f"Service unavailable."
                    )

        # Execute the function
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
            if self.state == CircuitState.HALF_OPEN:
                self.success_count += 1
                logger.debug(
                    f"Circuit breaker success in HALF_OPEN state for {self.api_type} "
                    f"({self.success_count}/{self.success_threshold})"
                )

                if self.success_count >= self.success_threshold:
                    # Enough successes, close the circuit
                    self.state = CircuitState.CLOSED
                    self.failure_count = 0
                    self.success_count = 0
                    self._update_state_metric()
                    logger.info(
                        f"Circuit breaker CLOSED for {self.api_type} - service recovered"
                    )

            elif self.state == CircuitState.CLOSED:
                # Reset failure count on success
                self.failure_count = 0

    async def _on_failure(self):
        """Handle failed call"""
        async with self._lock:
            self.failure_count += 1
            self.last_failure_time = datetime.now()

            # Update counter metric
            circuit_failures_counter.labels(api_type=self.api_type).inc()

            if self.state == CircuitState.CLOSED:
                if self.failure_count >= self.failure_threshold:
                    # Too many failures, open the circuit
                    self.state = CircuitState.OPEN
                    self._update_state_metric()
                    logger.warning(
                        f"Circuit breaker OPENED for {self.api_type} after "
                        f"{self.failure_count} failures"
                    )

            elif self.state == CircuitState.HALF_OPEN:
                # Failure in half-open state, reopen the circuit
                self.state = CircuitState.OPEN
                self.success_count = 0
                self._update_state_metric()
                logger.warning(
                    f"Circuit breaker REOPENED for {self.api_type} after "
                    f"failure in HALF_OPEN state"
                )

    def _should_attempt_reset(self) -> bool:
        """Check if we should try to reset the circuit"""
        if not self.last_failure_time:
            return True

        time_since_failure = datetime.now() - self.last_failure_time
        return time_since_failure > timedelta(seconds=self.timeout)

    def get_state(self) -> Dict[str, Any]:
        """Get current circuit breaker state"""
        return {
            "api_type": self.api_type,
            "state": self.state.value,
            "failure_count": self.failure_count,
            "success_count": self.success_count,
            "last_failure": (
                self.last_failure_time.isoformat() if self.last_failure_time else None
            ),
            "failure_threshold": self.failure_threshold,
            "success_threshold": self.success_threshold,
            "timeout_seconds": self.timeout,
        }

    async def reset(self):
        """Manually reset the circuit breaker"""
        async with self._lock:
            self.state = CircuitState.CLOSED
            self.failure_count = 0
            self.success_count = 0
            self.last_failure_time = None
            self._update_state_metric()
            logger.info(f"Circuit breaker manually RESET for {self.api_type}")

    async def trip(self):
        """Manually trip the circuit breaker (open it)"""
        async with self._lock:
            self.state = CircuitState.OPEN
            self.last_failure_time = datetime.now()
            self._update_state_metric()
            logger.warning(f"Circuit breaker manually TRIPPED for {self.api_type}")

    def is_open(self) -> bool:
        """Check if circuit is open"""
        return self.state == CircuitState.OPEN

    def is_closed(self) -> bool:
        """Check if circuit is closed"""
        return self.state == CircuitState.CLOSED

    def is_half_open(self) -> bool:
        """Check if circuit is half-open"""
        return self.state == CircuitState.HALF_OPEN

    def can_execute(self) -> bool:
        """Check if circuit allows execution"""
        if self.state == CircuitState.CLOSED:
            return True
        elif self.state == CircuitState.OPEN:
            if self._should_attempt_reset():
                self.state = CircuitState.HALF_OPEN
                self.success_count = 0
                self._update_state_metric()
                return True
            return False
        else:  # HALF_OPEN
            return True

    def record_success(self):
        """Manually record a successful operation (for testing)"""
        # Use a separate lock for synchronous methods
        import threading

        if not hasattr(self, "_sync_lock"):
            self._sync_lock = threading.Lock()
        with self._sync_lock:
            if self.state == CircuitState.HALF_OPEN:
                self.success_count += 1
                if self.success_count >= self.success_threshold:
                    self.state = CircuitState.CLOSED
                    self.failure_count = 0
                    self.success_count = 0
                    self._update_state_metric()
            elif self.state == CircuitState.CLOSED:
                self.failure_count = 0
                self.success_count += 1

    def record_failure(self):
        """Manually record a failed operation (for testing)"""
        # Use a separate lock for synchronous methods
        import threading

        if not hasattr(self, "_sync_lock"):
            self._sync_lock = threading.Lock()
        with self._sync_lock:
            self.failure_count += 1
            self.last_failure_time = datetime.now()
            circuit_failures_counter.labels(api_type=self.api_type).inc()

            if self.state == CircuitState.CLOSED:
                if self.failure_count >= self.failure_threshold:
                    self.state = CircuitState.OPEN
                    self._update_state_metric()
            elif self.state == CircuitState.HALF_OPEN:
                self.state = CircuitState.OPEN
                self.success_count = 0
                self._update_state_metric()

    def _get_state(self) -> CircuitState:
        """Get current state with automatic transition check"""
        if self.state == CircuitState.OPEN and self._should_attempt_reset():
            self.state = CircuitState.HALF_OPEN
            self.success_count = 0
            self._update_state_metric()
            return CircuitState.HALF_OPEN
        return self.state

    def get_status(self) -> Dict[str, Any]:
        """Get comprehensive status (alias for get_state for compatibility)"""
        return self.get_state()


class CircuitBreakerManager:
    """Manage multiple circuit breakers for different APIs"""

    def __init__(self):
        self._breakers: Dict[str, CircuitBreaker] = {}
        self._lock = asyncio.Lock()

    async def get_breaker(
        self,
        api_type: str,
        failure_threshold: int = 5,
        success_threshold: int = 2,
        timeout: int = 60,
    ) -> CircuitBreaker:
        """Get or create a circuit breaker for an API type"""
        async with self._lock:
            if api_type not in self._breakers:
                self._breakers[api_type] = CircuitBreaker(
                    api_type=api_type,
                    failure_threshold=failure_threshold,
                    success_threshold=success_threshold,
                    timeout=timeout,
                )
                logger.info(f"Created circuit breaker for {api_type}")

            return self._breakers[api_type]

    async def get_all_states(self) -> Dict[str, Dict[str, Any]]:
        """Get states of all circuit breakers"""
        states = {}
        async with self._lock:
            for api_type, breaker in self._breakers.items():
                states[api_type] = breaker.get_state()
        return states

    async def reset_all(self):
        """Reset all circuit breakers"""
        async with self._lock:
            for breaker in self._breakers.values():
                await breaker.reset()
        logger.info("Reset all circuit breakers")

    async def reset_breaker(self, api_type: str) -> bool:
        """Reset a specific circuit breaker"""
        async with self._lock:
            if api_type in self._breakers:
                await self._breakers[api_type].reset()
                return True
            return False


# Global circuit breaker manager
circuit_manager = CircuitBreakerManager()
