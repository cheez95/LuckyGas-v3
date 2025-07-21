"""
Unit tests for Google API Rate Limiter
"""
import pytest
from unittest.mock import Mock, patch, AsyncMock
from datetime import datetime, timedelta
import redis.asyncio as redis

from app.services.google_cloud.monitoring.rate_limiter import GoogleAPIRateLimiter


class TestGoogleAPIRateLimiter:
    """Test cases for GoogleAPIRateLimiter"""
    
    @pytest.fixture
    def mock_redis(self):
        """Mock Redis client"""
        with patch("app.services.google_cloud.monitoring.rate_limiter.redis.from_url") as mock:
            mock_client = AsyncMock()
            mock.return_value = mock_client
            yield mock_client
    
    @pytest.fixture
    def rate_limiter(self, mock_redis):
        """Create a GoogleAPIRateLimiter instance"""
        return GoogleAPIRateLimiter()
    
    @pytest.mark.asyncio
    async def test_check_limit_allowed(self, rate_limiter, mock_redis):
        """Test rate limit check when request is allowed"""
        # Mock Redis responses - all under limits
        mock_redis.incr = AsyncMock(side_effect=[5, 150, 10000])  # per_second, per_minute, per_day
        mock_redis.expire = AsyncMock()
        
        # Check limit
        allowed = await rate_limiter.check_limit("routes")
        
        # Verify
        assert allowed is True
        assert mock_redis.incr.call_count == 3
        assert mock_redis.expire.call_count == 3
    
    @pytest.mark.asyncio
    async def test_check_limit_denied_per_second(self, rate_limiter, mock_redis):
        """Test rate limit denied due to per-second limit"""
        # Mock Redis responses - per_second limit exceeded
        mock_redis.incr = AsyncMock(return_value=11)  # Over the 10/second limit for routes
        
        # Check limit
        allowed = await rate_limiter.check_limit("routes")
        
        # Verify
        assert allowed is False
        assert mock_redis.incr.call_count == 1
    
    @pytest.mark.asyncio
    async def test_check_limit_denied_per_minute(self, rate_limiter, mock_redis):
        """Test rate limit denied due to per-minute limit"""
        # Mock Redis responses - per_minute limit exceeded
        mock_redis.incr = AsyncMock(side_effect=[5, 301])  # Under per_second, over per_minute
        
        # Check limit
        allowed = await rate_limiter.check_limit("routes")
        
        # Verify
        assert allowed is False
        assert mock_redis.incr.call_count == 2
    
    @pytest.mark.asyncio
    async def test_check_limit_denied_per_day(self, rate_limiter, mock_redis):
        """Test rate limit denied due to per-day limit"""
        # Mock Redis responses - per_day limit exceeded
        mock_redis.incr = AsyncMock(side_effect=[5, 150, 25001])  # Under others, over per_day
        
        # Check limit
        allowed = await rate_limiter.check_limit("routes")
        
        # Verify
        assert allowed is False
        assert mock_redis.incr.call_count == 3
    
    @pytest.mark.asyncio
    async def test_different_api_types(self, rate_limiter, mock_redis):
        """Test different API types have different limits"""
        # Mock Redis responses
        mock_redis.incr = AsyncMock(side_effect=[
            # Geocoding checks (higher limits)
            30, 2000, 2000,  # All under geocoding limits
            # Vertex AI checks
            2, 40, 800       # All under vertex AI limits
        ])
        mock_redis.expire = AsyncMock()
        
        # Check geocoding limit
        allowed_geo = await rate_limiter.check_limit("geocoding")
        assert allowed_geo is True
        
        # Check vertex AI limit
        allowed_vertex = await rate_limiter.check_limit("vertex_ai")
        assert allowed_vertex is True
    
    @pytest.mark.asyncio
    async def test_get_current_usage(self, rate_limiter, mock_redis):
        """Test getting current usage statistics"""
        # Mock Redis responses
        mock_redis.get = AsyncMock(side_effect=[
            b"8",    # per_second
            b"250",  # per_minute
            b"20000" # per_day
        ])
        
        # Get usage
        usage = await rate_limiter.get_current_usage("routes")
        
        # Verify
        assert usage == {
            "api_type": "routes",
            "limits": {
                "per_second": 10,
                "per_minute": 300,
                "per_day": 25000
            },
            "current": {
                "per_second": 8,
                "per_minute": 250,
                "per_day": 20000
            },
            "available": True,
            "timestamp": usage["timestamp"]  # Dynamic value
        }
    
    @pytest.mark.asyncio
    async def test_get_current_usage_no_data(self, rate_limiter, mock_redis):
        """Test getting usage when no data exists"""
        # Mock Redis responses - no data
        mock_redis.get = AsyncMock(return_value=None)
        
        # Get usage
        usage = await rate_limiter.get_current_usage("routes")
        
        # Verify
        assert usage["current"] == {
            "per_second": 0,
            "per_minute": 0,
            "per_day": 0
        }
        assert usage["available"] is True
    
    @pytest.mark.asyncio
    async def test_reset_limits(self, rate_limiter, mock_redis):
        """Test resetting rate limits"""
        # Mock Redis delete
        mock_redis.delete = AsyncMock(return_value=3)
        
        # Reset limits
        count = await rate_limiter.reset_limits("routes")
        
        # Verify
        assert count == 3
        mock_redis.delete.assert_called_once()
        
        # Check that correct keys were deleted
        call_args = mock_redis.delete.call_args[0]
        assert "rate_limit:routes:second" in call_args
        assert "rate_limit:routes:minute" in call_args
        assert "rate_limit:routes:day" in call_args
    
    @pytest.mark.asyncio
    async def test_redis_connection_error(self, rate_limiter, mock_redis):
        """Test handling Redis connection errors"""
        # Mock Redis error
        mock_redis.incr = AsyncMock(side_effect=redis.ConnectionError("Connection failed"))
        
        # Check limit - should allow request on error
        allowed = await rate_limiter.check_limit("routes")
        
        # Verify - fails open
        assert allowed is True
    
    @pytest.mark.asyncio
    async def test_unknown_api_type(self, rate_limiter, mock_redis):
        """Test handling unknown API type"""
        # Mock Redis responses
        mock_redis.incr = AsyncMock(side_effect=[5, 150, 10000])
        mock_redis.expire = AsyncMock()
        
        # Check limit for unknown API
        allowed = await rate_limiter.check_limit("unknown_api")
        
        # Verify - uses default limits
        assert allowed is True
    
    @pytest.mark.asyncio
    async def test_concurrent_requests(self, rate_limiter, mock_redis):
        """Test handling concurrent requests"""
        import asyncio
        
        # Mock Redis responses
        call_count = 0
        
        async def mock_incr(key):
            nonlocal call_count
            call_count += 1
            # Simulate increasing counter
            return call_count
        
        mock_redis.incr = mock_incr
        mock_redis.expire = AsyncMock()
        
        # Make concurrent requests
        tasks = [rate_limiter.check_limit("routes") for _ in range(5)]
        results = await asyncio.gather(*tasks)
        
        # Verify
        assert all(results)  # All should be allowed (under limit)
        assert call_count == 15  # 5 requests * 3 checks each
    
    @pytest.mark.asyncio
    async def test_ttl_settings(self, rate_limiter, mock_redis):
        """Test that TTL is set correctly for different time windows"""
        # Mock Redis responses
        mock_redis.incr = AsyncMock(side_effect=[1, 1, 1])
        mock_redis.expire = AsyncMock()
        
        # Check limit
        await rate_limiter.check_limit("routes")
        
        # Verify TTL settings
        expire_calls = mock_redis.expire.call_args_list
        assert len(expire_calls) == 3
        
        # Check TTL values
        assert expire_calls[0][0][1] == 1    # per_second: 1 second
        assert expire_calls[1][0][1] == 60   # per_minute: 60 seconds
        assert expire_calls[2][0][1] == 86400 # per_day: 86400 seconds