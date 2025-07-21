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
            failure_threshold=3,
            timeout=1,  # 1 second timeout for faster tests
            half_open_retries=2
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
        
        # Verify circuit is OPEN
        assert circuit_breaker.state == CircuitState.OPEN
        assert circuit_breaker.failure_count == 3
        assert circuit_breaker.can_execute() is False
        assert circuit_breaker.last_failure_time is not None
    
    def test_circuit_stays_open_during_timeout(self, circuit_breaker):
        """Test circuit stays OPEN during timeout period"""
        # Open the circuit
        for _ in range(3):
            circuit_breaker.record_failure()
        
        # Verify can't execute during timeout
        assert circuit_breaker.can_execute() is False
        assert circuit_breaker.state == CircuitState.OPEN
    
    def test_circuit_transitions_to_half_open(self, circuit_breaker):
        """Test circuit transitions to HALF_OPEN after timeout"""
        # Open the circuit
        for _ in range(3):
            circuit_breaker.record_failure()
        
        # Mock time to simulate timeout expiry
        with patch('app.services.google_cloud.monitoring.circuit_breaker.datetime') as mock_datetime:
            mock_datetime.now.return_value = datetime.now() + timedelta(seconds=2)
            
            # First check should transition to HALF_OPEN
            can_execute = circuit_breaker.can_execute()
            
            assert can_execute is True
            assert circuit_breaker.state == CircuitState.HALF_OPEN
            assert circuit_breaker.half_open_attempts == 0
    
    def test_half_open_success_closes_circuit(self, circuit_breaker):
        """Test successful operations in HALF_OPEN state close the circuit"""
        # Open the circuit
        for _ in range(3):
            circuit_breaker.record_failure()
        
        # Transition to HALF_OPEN
        with patch('app.services.google_cloud.monitoring.circuit_breaker.datetime') as mock_datetime:
            mock_datetime.now.return_value = datetime.now() + timedelta(seconds=2)
            circuit_breaker.can_execute()
            
            # Record successes in HALF_OPEN
            circuit_breaker.record_success()
            assert circuit_breaker.state == CircuitState.HALF_OPEN
            assert circuit_breaker.half_open_attempts == 1
            
            circuit_breaker.record_success()
            
            # Circuit should be CLOSED after required successes
            assert circuit_breaker.state == CircuitState.CLOSED
            assert circuit_breaker.failure_count == 0
            assert circuit_breaker.half_open_attempts == 0
    
    def test_half_open_failure_reopens_circuit(self, circuit_breaker):
        """Test failure in HALF_OPEN state reopens the circuit"""
        # Open the circuit
        for _ in range(3):
            circuit_breaker.record_failure()
        
        # Transition to HALF_OPEN
        with patch('app.services.google_cloud.monitoring.circuit_breaker.datetime') as mock_datetime:
            mock_datetime.now.return_value = datetime.now() + timedelta(seconds=2)
            circuit_breaker.can_execute()
            
            # Record failure in HALF_OPEN
            circuit_breaker.record_failure()
            
            # Circuit should be OPEN again
            assert circuit_breaker.state == CircuitState.OPEN
            assert circuit_breaker.half_open_attempts == 0
    
    def test_mixed_results_in_half_open(self, circuit_breaker):
        """Test mixed success/failure in HALF_OPEN state"""
        # Open the circuit
        for _ in range(3):
            circuit_breaker.record_failure()
        
        # Transition to HALF_OPEN
        with patch('app.services.google_cloud.monitoring.circuit_breaker.datetime') as mock_datetime:
            mock_datetime.now.return_value = datetime.now() + timedelta(seconds=2)
            circuit_breaker.can_execute()
            
            # Mixed results
            circuit_breaker.record_success()
            circuit_breaker.record_failure()  # This reopens the circuit
            
            assert circuit_breaker.state == CircuitState.OPEN
    
    def test_get_status(self, circuit_breaker):
        """Test getting circuit breaker status"""
        # Initial status
        status = circuit_breaker.get_status()
        assert status["state"] == "CLOSED"
        assert status["failure_count"] == 0
        assert status["success_count"] == 0
        assert status["can_execute"] is True
        
        # Open the circuit
        for _ in range(3):
            circuit_breaker.record_failure()
        
        status = circuit_breaker.get_status()
        assert status["state"] == "OPEN"
        assert status["failure_count"] == 3
        assert status["can_execute"] is False
        assert "last_failure_time" in status
    
    def test_reset(self, circuit_breaker):
        """Test resetting the circuit breaker"""
        # Open the circuit
        for _ in range(3):
            circuit_breaker.record_failure()
        
        assert circuit_breaker.state == CircuitState.OPEN
        
        # Reset
        circuit_breaker.reset()
        
        # Verify reset to initial state
        assert circuit_breaker.state == CircuitState.CLOSED
        assert circuit_breaker.failure_count == 0
        assert circuit_breaker.success_count == 0
        assert circuit_breaker.last_failure_time is None
        assert circuit_breaker.half_open_attempts == 0
    
    def test_custom_thresholds(self):
        """Test circuit breaker with custom thresholds"""
        cb = CircuitBreaker(
            failure_threshold=5,
            timeout=10,
            half_open_retries=3
        )
        
        # Should take 5 failures to open
        for i in range(4):
            cb.record_failure()
            assert cb.state == CircuitState.CLOSED
        
        cb.record_failure()
        assert cb.state == CircuitState.OPEN
        
        # Should require 3 successes in HALF_OPEN to close
        with patch('app.services.google_cloud.monitoring.circuit_breaker.datetime') as mock_datetime:
            mock_datetime.now.return_value = datetime.now() + timedelta(seconds=11)
            cb.can_execute()
            
            cb.record_success()
            cb.record_success()
            assert cb.state == CircuitState.HALF_OPEN
            
            cb.record_success()
            assert cb.state == CircuitState.CLOSED
    
    def test_concurrent_operations(self, circuit_breaker):
        """Test thread-safe concurrent operations"""
        import threading
        
        def record_failures():
            for _ in range(2):
                circuit_breaker.record_failure()
        
        def record_successes():
            for _ in range(3):
                circuit_breaker.record_success()
        
        # Create threads
        threads = []
        for _ in range(3):
            threads.append(threading.Thread(target=record_failures))
            threads.append(threading.Thread(target=record_successes))
        
        # Start all threads
        for t in threads:
            t.start()
        
        # Wait for completion
        for t in threads:
            t.join()
        
        # Verify counts are correct
        total_failures = circuit_breaker.failure_count
        total_successes = circuit_breaker.success_count
        
        # Should have recorded all operations
        assert total_failures >= 3  # At least threshold reached
        assert total_successes == 9  # 3 threads * 3 successes each
    
    def test_state_transitions(self, circuit_breaker):
        """Test all possible state transitions"""
        # CLOSED -> CLOSED (success)
        circuit_breaker.record_success()
        assert circuit_breaker.state == CircuitState.CLOSED
        
        # CLOSED -> OPEN (threshold failures)
        for _ in range(3):
            circuit_breaker.record_failure()
        assert circuit_breaker.state == CircuitState.OPEN
        
        # OPEN -> HALF_OPEN (timeout)
        with patch('app.services.google_cloud.monitoring.circuit_breaker.datetime') as mock_datetime:
            mock_datetime.now.return_value = datetime.now() + timedelta(seconds=2)
            circuit_breaker.can_execute()
            assert circuit_breaker.state == CircuitState.HALF_OPEN
            
            # HALF_OPEN -> OPEN (failure)
            circuit_breaker.record_failure()
            assert circuit_breaker.state == CircuitState.OPEN
            
            # OPEN -> HALF_OPEN again
            mock_datetime.now.return_value = datetime.now() + timedelta(seconds=4)
            circuit_breaker.can_execute()
            assert circuit_breaker.state == CircuitState.HALF_OPEN
            
            # HALF_OPEN -> CLOSED (successes)
            circuit_breaker.record_success()
            circuit_breaker.record_success()
            assert circuit_breaker.state == CircuitState.CLOSED
    
    def test_statistics_tracking(self, circuit_breaker):
        """Test that statistics are properly tracked"""
        # Record various operations
        circuit_breaker.record_success()
        circuit_breaker.record_success()
        circuit_breaker.record_failure()
        circuit_breaker.record_success()
        circuit_breaker.record_failure()
        
        status = circuit_breaker.get_status()
        assert status["success_count"] == 3
        assert status["failure_count"] == 2
        assert status["total_count"] == 5
        assert status["failure_rate"] == 40.0  # 2/5 = 40%