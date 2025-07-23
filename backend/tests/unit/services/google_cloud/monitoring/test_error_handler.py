"""
Unit tests for Google API Error Handler
"""
import pytest
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime
import asyncio
import random
import aiohttp

from app.services.google_cloud.monitoring.error_handler import (
    GoogleAPIErrorHandler,
    GoogleAPIError,
    APIErrorType
)


class TestGoogleAPIErrorHandler:
    """Test cases for GoogleAPIErrorHandler"""
    
    def test_classify_error_by_status_code(self):
        """Test error classification by status code"""
        # Test known status codes
        assert GoogleAPIErrorHandler.classify_error(status_code=400) == APIErrorType.INVALID_REQUEST
        assert GoogleAPIErrorHandler.classify_error(status_code=401) == APIErrorType.INVALID_API_KEY
        assert GoogleAPIErrorHandler.classify_error(status_code=403) == APIErrorType.PERMISSION_DENIED
        assert GoogleAPIErrorHandler.classify_error(status_code=404) == APIErrorType.NOT_FOUND
        assert GoogleAPIErrorHandler.classify_error(status_code=429) == APIErrorType.RATE_LIMIT
        assert GoogleAPIErrorHandler.classify_error(status_code=500) == APIErrorType.INTERNAL_ERROR
        assert GoogleAPIErrorHandler.classify_error(status_code=503) == APIErrorType.SERVICE_UNAVAILABLE
        
        # Test unknown status code
        assert GoogleAPIErrorHandler.classify_error(status_code=418) == APIErrorType.UNKNOWN
    
    def test_classify_error_by_exception(self):
        """Test error classification by exception type"""
        # Test timeout error
        timeout_error = asyncio.TimeoutError("Request timed out")
        assert GoogleAPIErrorHandler.classify_error(exception=timeout_error) == APIErrorType.TIMEOUT
        
        # Test network error
        client_error = aiohttp.ClientError("Connection failed")
        assert GoogleAPIErrorHandler.classify_error(exception=client_error) == APIErrorType.NETWORK_ERROR
        
        # Test connection error
        conn_error = ConnectionError("Connection refused")
        assert GoogleAPIErrorHandler.classify_error(exception=conn_error) == APIErrorType.NETWORK_ERROR
    
    def test_classify_error_by_response_body(self):
        """Test error classification by response body"""
        # Test quota error in body
        quota_body = {"error": {"message": "Quota exceeded for this API"}}
        assert GoogleAPIErrorHandler.classify_error(error_body=quota_body) == APIErrorType.QUOTA_EXCEEDED
        
        # Test rate limit error
        rate_body = {"message": "Rate limit exceeded"}
        assert GoogleAPIErrorHandler.classify_error(error_body=rate_body) == APIErrorType.RATE_LIMIT
        
        # Test invalid API key
        key_body = {"error": {"message": "Invalid API key provided"}}
        assert GoogleAPIErrorHandler.classify_error(error_body=key_body) == APIErrorType.INVALID_API_KEY
        
        # Test permission error
        perm_body = {"message": "Permission denied for this resource"}
        assert GoogleAPIErrorHandler.classify_error(error_body=perm_body) == APIErrorType.PERMISSION_DENIED
    
    def test_should_retry(self):
        """Test retry logic for different error types"""
        # Retryable errors
        assert GoogleAPIErrorHandler.should_retry(APIErrorType.RATE_LIMIT) is True
        assert GoogleAPIErrorHandler.should_retry(APIErrorType.SERVICE_UNAVAILABLE) is True
        assert GoogleAPIErrorHandler.should_retry(APIErrorType.INTERNAL_ERROR) is True
        assert GoogleAPIErrorHandler.should_retry(APIErrorType.NETWORK_ERROR) is True
        assert GoogleAPIErrorHandler.should_retry(APIErrorType.TIMEOUT) is True
        
        # Non-retryable errors
        assert GoogleAPIErrorHandler.should_retry(APIErrorType.INVALID_API_KEY) is False
        assert GoogleAPIErrorHandler.should_retry(APIErrorType.INVALID_REQUEST) is False
        assert GoogleAPIErrorHandler.should_retry(APIErrorType.NOT_FOUND) is False
        assert GoogleAPIErrorHandler.should_retry(APIErrorType.PERMISSION_DENIED) is False
        assert GoogleAPIErrorHandler.should_retry(APIErrorType.QUOTA_EXCEEDED) is False
    
    def test_get_retry_delay(self):
        """Test retry delay calculation"""
        # Test rate limit delay
        delay = GoogleAPIErrorHandler.get_retry_delay(APIErrorType.RATE_LIMIT, attempt=0)
        assert 0.8 <= delay <= 1.2  # 1.0 base with ±20% jitter
        
        delay = GoogleAPIErrorHandler.get_retry_delay(APIErrorType.RATE_LIMIT, attempt=1)
        assert 1.6 <= delay <= 2.4  # 2.0 with jitter
        
        # Test with retry-after header
        delay = GoogleAPIErrorHandler.get_retry_delay(APIErrorType.RATE_LIMIT, attempt=0, retry_after=5)
        assert delay == 5.0
        
        # Test service unavailable
        delay = GoogleAPIErrorHandler.get_retry_delay(APIErrorType.SERVICE_UNAVAILABLE, attempt=0)
        assert 1.6 <= delay <= 2.4  # 2.0 base with jitter
        
        # Test timeout (non-exponential)
        delay = GoogleAPIErrorHandler.get_retry_delay(APIErrorType.TIMEOUT, attempt=0)
        assert delay == 2.0  # No exponential backoff for timeout
        
        # Test unknown error type
        delay = GoogleAPIErrorHandler.get_retry_delay(APIErrorType.UNKNOWN, attempt=0)
        assert delay == 0.0
    
    @pytest.mark.asyncio
    async def test_handle_with_retry_success(self):
        """Test successful operation without retries"""
        # Mock successful function
        async def successful_func():
            return {"status": "success", "data": "test_data"}
        
        # Execute
        result = await GoogleAPIErrorHandler.handle_with_retry(
            successful_func,
            api_type="test",
            endpoint="test_endpoint"
        )
        
        # Verify
        assert result == {"status": "success", "data": "test_data"}
    
    @pytest.mark.asyncio
    async def test_handle_with_retry_transient_error(self):
        """Test retry on transient errors"""
        call_count = 0
        
        async def flaky_func():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                # Simulate a 503 error
                error = aiohttp.ClientResponseError(
                    request_info=Mock(),
                    history=(),
                    status=503,
                    message="Service Unavailable"
                )
                error.headers = {}  # Add empty headers
                raise error
            return {"status": "success"}
        
        # Mock sleep to speed up test
        with patch('asyncio.sleep'):
            # Execute
            result = await GoogleAPIErrorHandler.handle_with_retry(
                flaky_func,
                api_type="test",
                endpoint="test_endpoint"
            )
        
        # Verify
        assert result == {"status": "success"}
        assert call_count == 3  # Failed twice, succeeded on third
    
    @pytest.mark.asyncio
    async def test_handle_with_retry_non_retryable(self):
        """Test no retry on permanent errors"""
        call_count = 0
        
        async def perm_error_func():
            nonlocal call_count
            call_count += 1
            # Simulate a 403 permission denied error
            error = aiohttp.ClientResponseError(
                request_info=Mock(),
                history=(),
                status=403,
                message="Permission Denied"
            )
            error.headers = {}  # Add empty headers
            raise error
        
        # Execute
        with pytest.raises(GoogleAPIError) as exc_info:
            await GoogleAPIErrorHandler.handle_with_retry(
                perm_error_func,
                api_type="test",
                endpoint="test_endpoint"
            )
        
        # Verify - should not retry
        assert call_count == 1
        assert exc_info.value.status_code == 403
        assert exc_info.value.api_type == "test"
        assert exc_info.value.endpoint == "test_endpoint"
    
    @pytest.mark.asyncio
    async def test_handle_with_retry_max_retries(self):
        """Test max retries exceeded"""
        call_count = 0
        
        async def always_fails():
            nonlocal call_count
            call_count += 1
            error = aiohttp.ClientResponseError(
                request_info=Mock(),
                history=(),
                status=503,
                message="Service Unavailable"
            )
            error.headers = {}  # Add empty headers
            raise error
        
        # Mock sleep to speed up test
        with patch('asyncio.sleep'):
            # Execute
            with pytest.raises(GoogleAPIError) as exc_info:
                await GoogleAPIErrorHandler.handle_with_retry(
                    always_fails,
                    api_type="test",
                    endpoint="test_endpoint"
                )
        
        # Verify - should hit max retries for SERVICE_UNAVAILABLE (3 retries + 1 initial = 4)
        assert call_count == 4
        assert exc_info.value.status_code == 503
    
    @pytest.mark.asyncio
    async def test_handle_with_retry_network_error(self):
        """Test retry on network errors"""
        call_count = 0
        
        async def network_error_func():
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise aiohttp.ClientError("Network error")
            return {"status": "success"}
        
        # Mock sleep to speed up test
        with patch('asyncio.sleep'):
            # Execute
            result = await GoogleAPIErrorHandler.handle_with_retry(
                network_error_func,
                api_type="test",
                endpoint="test_endpoint"
            )
        
        # Verify
        assert result == {"status": "success"}
        assert call_count == 2
    
    @pytest.mark.asyncio
    async def test_handle_with_retry_timeout_error(self):
        """Test retry on timeout errors"""
        call_count = 0
        
        async def timeout_func():
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise asyncio.TimeoutError("Request timed out")
            return {"status": "success"}
        
        # Mock sleep to speed up test
        with patch('asyncio.sleep'):
            # Execute
            result = await GoogleAPIErrorHandler.handle_with_retry(
                timeout_func,
                api_type="test",
                endpoint="test_endpoint"
            )
        
        # Verify
        assert result == {"status": "success"}
        assert call_count == 2
    
    @pytest.mark.asyncio
    async def test_handle_with_retry_unexpected_error(self):
        """Test handling of unexpected errors"""
        async def unexpected_error_func():
            raise ValueError("Unexpected error")
        
        # Execute
        with pytest.raises(GoogleAPIError) as exc_info:
            await GoogleAPIErrorHandler.handle_with_retry(
                unexpected_error_func,
                api_type="test",
                endpoint="test_endpoint"
            )
        
        # Verify
        assert "Unexpected error" in str(exc_info.value)
        assert exc_info.value.details["error_type"] == APIErrorType.UNKNOWN.value
    
    def test_extract_error_details(self):
        """Test error detail extraction"""
        # Test Google API error format
        google_error = '{"error": {"code": 403, "message": "Permission denied", "status": "PERMISSION_DENIED"}}'
        details = GoogleAPIErrorHandler.extract_error_details(google_error)
        assert details["code"] == 403
        assert details["message"] == "Permission denied"
        assert details["status"] == "PERMISSION_DENIED"
        
        # Test simple JSON format
        simple_error = '{"message": "Error occurred", "code": "ERROR_CODE"}'
        details = GoogleAPIErrorHandler.extract_error_details(simple_error)
        assert details["message"] == "Error occurred"
        assert details["code"] == "ERROR_CODE"
        
        # Test non-JSON string
        plain_error = "Plain text error message"
        details = GoogleAPIErrorHandler.extract_error_details(plain_error)
        assert details["message"] == "Plain text error message"
    
    def test_google_api_error(self):
        """Test GoogleAPIError class"""
        error = GoogleAPIError(
            message="Test error",
            status_code=500,
            details={"foo": "bar"},
            api_type="test_api",
            endpoint="/test/endpoint"
        )
        
        assert str(error) == "Test error"
        assert error.status_code == 500
        assert error.details == {"foo": "bar"}
        assert error.api_type == "test_api"
        assert error.endpoint == "/test/endpoint"
        assert isinstance(error.timestamp, datetime)
        
        # Test to_dict
        error_dict = error.to_dict()
        assert error_dict["message"] == "Test error"
        assert error_dict["status_code"] == 500
        assert error_dict["details"] == {"foo": "bar"}
        assert error_dict["api_type"] == "test_api"
        assert error_dict["endpoint"] == "/test/endpoint"
        assert "timestamp" in error_dict