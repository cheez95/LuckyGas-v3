"""
Unit tests for Circuit Breaker pattern implementation
"""
import pytest
from unittest.mock import Mock, patch
from datetime import datetime, timedelta
import asyncio

from app.services.google_cloud.monitoring.circuit_breaker import CircuitBreaker, CircuitState


class TestCircuitBreaker:
    """Test cases for CircuitBreaker"""
    
    @pytest.fixture
    def circuit_breaker(self):
        """Create a CircuitBreaker instance with test-friendly settings"""
        return CircuitBreaker(
            api_type="routes",  # Add required api_type parameter
            failure_threshold=3,
            timeout=1,  # 1 second timeout for faster tests (as integer)
            success_threshold=2  # Changed from half_open_retries
        )
    
    def test_initial_state(self, circuit_breaker):
        """Test circuit breaker starts in CLOSED state"""
        assert circuit_breaker.state == CircuitState.CLOSED
        assert circuit_breaker.failure_count == 0
        assert circuit_breaker.success_count == 0
        assert circuit_breaker.can_execute() is True
    
    def test_success_in_closed_state(self, circuit_breaker):
        """Test successful operations in CLOSED state"""
        # Record successes
        for _ in range(5):
            circuit_breaker.record_success()
        
        # Verify state remains CLOSED
        assert circuit_breaker.state == CircuitState.CLOSED
        assert circuit_breaker.failure_count == 0
        assert circuit_breaker.success_count == 5
        assert circuit_breaker.can_execute() is True
    
    def test_failures_below_threshold(self, circuit_breaker):
        """Test failures below threshold keep circuit CLOSED"""
        # Record failures below threshold
        circuit_breaker.record_failure()
        circuit_breaker.record_failure()
        
        # Verify state remains CLOSED
        assert circuit_breaker.state == CircuitState.CLOSED
        assert circuit_breaker.failure_count == 2
        assert circuit_breaker.can_execute() is True
    
    def test_circuit_opens_on_threshold(self, circuit_breaker):
        """Test circuit opens when failure threshold is reached"""
        # Record failures to reach threshold
        for _ in range(3):
            circuit_breaker.record_failure()
        
        # Verify circuit is now OPEN
        assert circuit_breaker.state == CircuitState.OPEN
        assert circuit_breaker.failure_count == 3
        assert circuit_breaker.can_execute() is False
    
    def test_circuit_stays_open_during_timeout(self, circuit_breaker):
        """Test circuit remains OPEN during timeout period"""
        # Open the circuit
        for _ in range(3):
            circuit_breaker.record_failure()
        
        # Should still be OPEN
        assert circuit_breaker.state == CircuitState.OPEN
        assert circuit_breaker.can_execute() is False
    
    def test_circuit_transitions_to_half_open(self, circuit_breaker):
        """Test circuit transitions to HALF_OPEN after timeout"""
        # Open the circuit
        for _ in range(3):
            circuit_breaker.record_failure()
        
        # Mock time passage
        circuit_breaker.last_failure_time = datetime.now() - timedelta(seconds=2)
        
        # Check state - should be HALF_OPEN
        assert circuit_breaker._get_state() == CircuitState.HALF_OPEN
        assert circuit_breaker.can_execute() is True
    
    def test_half_open_success_closes_circuit(self, circuit_breaker):
        """Test successful operations in HALF_OPEN state close the circuit"""
        # Open the circuit
        for _ in range(3):
            circuit_breaker.record_failure()
        
        # Transition to HALF_OPEN
        circuit_breaker.last_failure_time = datetime.now() - timedelta(seconds=2)
        circuit_breaker.state = CircuitState.HALF_OPEN  # Simulate transition
        
        # Record successes to reach success threshold
        circuit_breaker.record_success()
        circuit_breaker.record_success()
        
        # Should be CLOSED again
        assert circuit_breaker.state == CircuitState.CLOSED
        assert circuit_breaker.failure_count == 0
        # Success count is reset to 0 when transitioning from HALF_OPEN to CLOSED
    
    def test_half_open_failure_reopens_circuit(self, circuit_breaker):
        """Test failure in HALF_OPEN state reopens the circuit"""
        # Open the circuit
        for _ in range(3):
            circuit_breaker.record_failure()
        
        # Transition to HALF_OPEN
        circuit_breaker.last_failure_time = datetime.now() - timedelta(seconds=2)
        circuit_breaker.state = CircuitState.HALF_OPEN  # Simulate transition
        
        # Record a failure
        circuit_breaker.record_failure()
        
        # Should be OPEN again
        assert circuit_breaker.state == CircuitState.OPEN
        assert circuit_breaker.success_count == 0  # Success count is reset when reopening
    
    def test_mixed_results_in_half_open(self, circuit_breaker):
        """Test mixed success/failure in HALF_OPEN state"""
        # Open the circuit
        for _ in range(3):
            circuit_breaker.record_failure()
        
        # Transition to HALF_OPEN
        circuit_breaker.last_failure_time = datetime.now() - timedelta(seconds=2)
        circuit_breaker.state = CircuitState.HALF_OPEN  # Simulate transition
        
        # Mix of success and failure
        circuit_breaker.record_success()
        circuit_breaker.record_failure()  # This should reopen
        
        # Should be OPEN due to failure
        assert circuit_breaker.state == CircuitState.OPEN
    
    def test_get_status(self, circuit_breaker):
        """Test getting circuit breaker status"""
        status = circuit_breaker.get_status()
        
        assert status["state"] == CircuitState.CLOSED.value
        assert status["failure_count"] == 0
        assert status["success_count"] == 0
        assert status["failure_threshold"] == 3
        assert status["success_threshold"] == 2
        assert status["api_type"] == "routes"
        assert status["timeout_seconds"] == 1
    
    @pytest.mark.asyncio
    async def test_reset(self, circuit_breaker):
        """Test resetting circuit breaker"""
        # Cause some failures
        for _ in range(3):
            circuit_breaker.record_failure()
        
        # Reset
        await circuit_breaker.reset()
        
        # Should be in initial state
        assert circuit_breaker.state == CircuitState.CLOSED
        assert circuit_breaker.failure_count == 0
        assert circuit_breaker.success_count == 0
    
    def test_custom_thresholds(self):
        """Test circuit breaker with custom thresholds"""
        # Create with different thresholds
        cb = CircuitBreaker(
            api_type="vertex_ai",
            failure_threshold=1,
            success_threshold=3,
            timeout=1  # Use integer seconds
        )
        
        # One failure should open it
        cb.record_failure()
        assert cb.state == CircuitState.OPEN
        
        # Wait for timeout
        cb.last_failure_time = datetime.now() - timedelta(seconds=1)
        # Manually set state to HALF_OPEN after timeout
        cb.state = CircuitState.HALF_OPEN
        
        # Need 3 successes to close
        cb.record_success()
        cb.record_success()
        assert cb.state == CircuitState.HALF_OPEN  # Still half open after 2 successes
        
        cb.record_success()  # Third success
        assert cb.state == CircuitState.CLOSED
    
    @pytest.mark.asyncio
    async def test_concurrent_operations(self, circuit_breaker):
        """Test circuit breaker under concurrent operations"""
        # Track if operations have checked can_execute
        checks_done = []
        
        async def operation(should_fail: bool):
            # All operations check can_execute "at the same time"
            can_exec = circuit_breaker.can_execute()
            checks_done.append(can_exec)
            
            # Simulate delay before recording result
            await asyncio.sleep(0.001)
            
            if can_exec:
                if should_fail:
                    circuit_breaker.record_failure()
                else:
                    circuit_breaker.record_success()
                return not should_fail
            return False
        
        # Run concurrent operations
        tasks = []
        # First 4 operations fail (indices 0, 1, 2, 3)
        for i in range(4):
            tasks.append(operation(True))
        # Next 6 succeed
        for i in range(6):
            tasks.append(operation(False))
        
        results = await asyncio.gather(*tasks)
        
        # Check final state - at least 3 failures should have been recorded
        assert circuit_breaker.failure_count >= 3
        assert circuit_breaker.state == CircuitState.OPEN
    
    def test_state_transitions(self, circuit_breaker):
        """Test complete state transition cycle"""
        # Start CLOSED
        assert circuit_breaker.state == CircuitState.CLOSED
        
        # CLOSED -> OPEN
        for _ in range(3):
            circuit_breaker.record_failure()
        assert circuit_breaker.state == CircuitState.OPEN
        
        # OPEN -> HALF_OPEN (after timeout)
        circuit_breaker.last_failure_time = datetime.now() - timedelta(seconds=2)
        circuit_breaker._get_state()
        assert circuit_breaker.state == CircuitState.HALF_OPEN
        
        # HALF_OPEN -> CLOSED (after successes)
        circuit_breaker.record_success()
        circuit_breaker.record_success()
        assert circuit_breaker.state == CircuitState.CLOSED
        
        # Back to OPEN
        for _ in range(3):
            circuit_breaker.record_failure()
        assert circuit_breaker.state == CircuitState.OPEN
        
        # HALF_OPEN -> OPEN (on failure)
        circuit_breaker.last_failure_time = datetime.now() - timedelta(seconds=2)
        circuit_breaker._get_state()
        circuit_breaker.record_failure()
        assert circuit_breaker.state == CircuitState.OPEN
    
    def test_statistics_tracking(self, circuit_breaker):
        """Test statistics tracking"""
        # Record various operations
        circuit_breaker.record_success()
        circuit_breaker.record_success()
        circuit_breaker.record_failure()
        
        stats = circuit_breaker.get_status()
        assert stats["success_count"] == 2
        assert stats["failure_count"] == 1
        # Note: total_count is not included in the get_status() method
        
        # After opening
        circuit_breaker.record_failure()
        circuit_breaker.record_failure()
        
        stats = circuit_breaker.get_status()
        assert stats["state"] == CircuitState.OPEN.value
        assert stats["failure_count"] == 3