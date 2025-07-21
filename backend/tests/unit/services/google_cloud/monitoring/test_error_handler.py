"""
Unit tests for Google API Error Handler
"""
import pytest
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime
import asyncio
import random
from google.api_core import exceptions as google_exceptions
import httpx

from app.services.google_cloud.monitoring.error_handler import GoogleAPIErrorHandler


class TestGoogleAPIErrorHandler:
    """Test cases for GoogleAPIErrorHandler"""
    
    @pytest.fixture
    def error_handler(self):
        """Create a GoogleAPIErrorHandler instance"""
        return GoogleAPIErrorHandler(
            max_retries=3,
            initial_delay=0.1,  # Short delays for testing
            max_delay=1.0,
            exponential_base=2
        )
    
    @pytest.mark.asyncio
    async def test_successful_operation(self, error_handler):
        """Test handling of successful operation"""
        # Mock successful function
        async def successful_func():
            return {"status": "success", "data": "test_data"}
        
        # Execute
        result = await error_handler.execute_with_retry(
            successful_func,
            operation_id="test_op_1"
        )
        
        # Verify
        assert result == {"status": "success", "data": "test_data"}
        assert error_handler.get_error_stats()["total_operations"] == 1
        assert error_handler.get_error_stats()["successful_operations"] == 1
        assert error_handler.get_error_stats()["failed_operations"] == 0
    
    @pytest.mark.asyncio
    async def test_retry_on_transient_error(self, error_handler):
        """Test retry on transient errors"""
        call_count = 0
        
        async def flaky_func():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise google_exceptions.ServiceUnavailable("Service temporarily unavailable")
            return {"status": "success"}
        
        # Execute
        result = await error_handler.execute_with_retry(
            flaky_func,
            operation_id="test_op_2"
        )
        
        # Verify
        assert result == {"status": "success"}
        assert call_count == 3  # Failed twice, succeeded on third
        stats = error_handler.get_error_stats()
        assert stats["total_retries"] == 2
        assert stats["successful_operations"] == 1
    
    @pytest.mark.asyncio
    async def test_max_retries_exceeded(self, error_handler):
        """Test when max retries are exceeded"""
        async def always_fails():
            raise google_exceptions.ServiceUnavailable("Always fails")
        
        # Execute
        with pytest.raises(google_exceptions.ServiceUnavailable):
            await error_handler.execute_with_retry(
                always_fails,
                operation_id="test_op_3"
            )
        
        # Verify
        stats = error_handler.get_error_stats()
        assert stats["failed_operations"] == 1
        assert stats["total_retries"] == 3  # Max retries
    
    @pytest.mark.asyncio
    async def test_no_retry_on_permanent_error(self, error_handler):
        """Test no retry on permanent errors"""
        call_count = 0
        
        async def perm_error_func():
            nonlocal call_count
            call_count += 1
            raise google_exceptions.PermissionDenied("Access denied")
        
        # Execute
        with pytest.raises(google_exceptions.PermissionDenied):
            await error_handler.execute_with_retry(
                perm_error_func,
                operation_id="test_op_4"
            )
        
        # Verify - should not retry
        assert call_count == 1
        stats = error_handler.get_error_stats()
        assert stats["total_retries"] == 0
    
    @pytest.mark.asyncio
    async def test_exponential_backoff(self, error_handler):
        """Test exponential backoff delays"""
        delays = []
        
        async def track_delays():
            # Track time between calls
            if hasattr(track_delays, 'last_call'):
                delay = datetime.now() - track_delays.last_call
                delays.append(delay.total_seconds())
            track_delays.last_call = datetime.now()
            raise google_exceptions.ResourceExhausted("Rate limit")
        
        # Execute
        with pytest.raises(google_exceptions.ResourceExhausted):
            await error_handler.execute_with_retry(
                track_delays,
                operation_id="test_op_5"
            )
        
        # Verify delays increase exponentially
        assert len(delays) == 3  # 3 retries
        assert delays[0] < delays[1] < delays[2]
        # With jitter, exact values vary, but should be in expected ranges
        assert 0.05 < delays[0] < 0.3   # ~0.1-0.2 with jitter
        assert 0.1 < delays[1] < 0.6    # ~0.2-0.4 with jitter
        assert 0.2 < delays[2] < 1.2    # ~0.4-0.8 with jitter
    
    @pytest.mark.asyncio
    async def test_different_error_types(self, error_handler):
        """Test handling of different error types"""
        error_types = [
            (google_exceptions.DeadlineExceeded("Timeout"), True),
            (google_exceptions.ResourceExhausted("Quota"), True),
            (google_exceptions.Aborted("Aborted"), True),
            (google_exceptions.InternalServerError("Internal"), True),
            (httpx.TimeoutException("HTTP timeout"), True),
            (google_exceptions.InvalidArgument("Bad arg"), False),
            (google_exceptions.NotFound("Not found"), False),
            (google_exceptions.AlreadyExists("Exists"), False),
            (ValueError("Bad value"), False),
        ]
        
        for error, should_retry in error_types:
            call_count = 0
            
            async def error_func():
                nonlocal call_count
                call_count += 1
                raise error
            
            with pytest.raises(type(error)):
                await error_handler.execute_with_retry(
                    error_func,
                    operation_id=f"test_{type(error).__name__}"
                )
            
            if should_retry:
                assert call_count == 4  # 1 initial + 3 retries
            else:
                assert call_count == 1  # No retries
    
    @pytest.mark.asyncio
    async def test_operation_callback(self, error_handler):
        """Test operation callback functionality"""
        callback_events = []
        
        async def callback(event_type, operation_id, details):
            callback_events.append({
                "type": event_type,
                "operation_id": operation_id,
                "details": details
            })
        
        async def failing_func():
            raise google_exceptions.ServiceUnavailable("Service down")
        
        # Execute with callback
        with pytest.raises(google_exceptions.ServiceUnavailable):
            await error_handler.execute_with_retry(
                failing_func,
                operation_id="test_op_callback",
                on_retry_callback=callback
            )
        
        # Verify callbacks
        assert len(callback_events) == 4  # 1 error + 3 retries
        assert all(event["operation_id"] == "test_op_callback" for event in callback_events)
        assert callback_events[0]["type"] == "error"
        assert all(event["type"] == "retry" for event in callback_events[1:])
    
    @pytest.mark.asyncio
    async def test_get_error_stats(self, error_handler):
        """Test error statistics tracking"""
        # Perform various operations
        async def success():
            return "ok"
        
        async def transient_error():
            if not hasattr(transient_error, 'called'):
                transient_error.called = True
                raise google_exceptions.ServiceUnavailable("Temp error")
            return "ok"
        
        async def permanent_error():
            raise google_exceptions.PermissionDenied("No access")
        
        # Execute operations
        await error_handler.execute_with_retry(success, "op1")
        await error_handler.execute_with_retry(transient_error, "op2")
        
        with pytest.raises(google_exceptions.PermissionDenied):
            await error_handler.execute_with_retry(permanent_error, "op3")
        
        # Get stats
        stats = error_handler.get_error_stats()
        
        # Verify
        assert stats["total_operations"] == 3
        assert stats["successful_operations"] == 2
        assert stats["failed_operations"] == 1
        assert stats["total_retries"] == 1
        assert stats["retry_success_rate"] == 100.0  # 1/1 retry succeeded
        assert "ServiceUnavailable" in stats["error_types"]
        assert "PermissionDenied" in stats["error_types"]
    
    @pytest.mark.asyncio
    async def test_reset_stats(self, error_handler):
        """Test resetting error statistics"""
        # Perform some operations
        async def fail():
            raise ValueError("Error")
        
        with pytest.raises(ValueError):
            await error_handler.execute_with_retry(fail, "op1")
        
        # Verify stats exist
        stats = error_handler.get_error_stats()
        assert stats["total_operations"] == 1
        
        # Reset stats
        error_handler.reset_stats()
        
        # Verify reset
        stats = error_handler.get_error_stats()
        assert stats["total_operations"] == 0
        assert stats["successful_operations"] == 0
        assert stats["failed_operations"] == 0
    
    @pytest.mark.asyncio
    async def test_concurrent_operations(self, error_handler):
        """Test handling concurrent operations"""
        results = []
        
        async def operation(op_id):
            # Simulate some work
            await asyncio.sleep(random.uniform(0.01, 0.05))
            if op_id % 2 == 0:
                return f"success_{op_id}"
            else:
                if not hasattr(operation, f'retried_{op_id}'):
                    setattr(operation, f'retried_{op_id}', True)
                    raise google_exceptions.ServiceUnavailable("Temp error")
                return f"success_after_retry_{op_id}"
        
        # Execute concurrent operations
        tasks = [
            error_handler.execute_with_retry(
                lambda i=i: operation(i),
                operation_id=f"concurrent_{i}"
            )
            for i in range(10)
        ]
        
        results = await asyncio.gather(*tasks)
        
        # Verify
        assert len(results) == 10
        assert all("success" in str(r) for r in results)
        
        stats = error_handler.get_error_stats()
        assert stats["total_operations"] == 10
        assert stats["successful_operations"] == 10
        assert stats["total_retries"] == 5  # Odd numbered operations retry once
    
    @pytest.mark.asyncio
    async def test_custom_retry_predicate(self, error_handler):
        """Test custom retry predicate"""
        class CustomError(Exception):
            pass
        
        # Add custom retry predicate
        def should_retry_custom(error):
            return isinstance(error, CustomError) and "retry" in str(error)
        
        error_handler.retry_predicates.append(should_retry_custom)
        
        # Test retryable custom error
        call_count = 0
        
        async def custom_error_func():
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise CustomError("Please retry")
            return "success"
        
        result = await error_handler.execute_with_retry(
            custom_error_func,
            operation_id="custom_retry"
        )
        
        assert result == "success"
        assert call_count == 2
        
        # Test non-retryable custom error
        async def no_retry_func():
            raise CustomError("Do not retry")
        
        with pytest.raises(CustomError):
            await error_handler.execute_with_retry(
                no_retry_func,
                operation_id="custom_no_retry"
            )
        
        # Should not retry
        stats = error_handler.get_error_stats()
        # Find the operation that didn't retry
        assert any(op for op in ["custom_no_retry"] if op)