"""
Unit tests for Google API Rate Limiter
"""

from unittest.mock import AsyncMock, Mock, patch

import pytest
import redis.asyncio as redis

from app.services.google_cloud.monitoring.rate_limiter import GoogleAPIRateLimiter


class TestGoogleAPIRateLimiter:
    """Test cases for GoogleAPIRateLimiter"""

    @pytest.fixture
    def mock_redis(self):
        """Mock Redis client"""
        mock_client = AsyncMock()
        # Mock Redis methods
        mock_client.incr = AsyncMock()
        mock_client.expire = AsyncMock()
        mock_client.get = AsyncMock()
        mock_client.hgetall = AsyncMock()
        mock_client.hdel = AsyncMock()
        mock_client.delete = AsyncMock()
        mock_client.ttl = AsyncMock()
        mock_client.pipeline = Mock()
        mock_client.close = AsyncMock()

        with patch(
            "app.services.google_cloud.monitoring.rate_limiter.get_redis_client",
            AsyncMock(return_value=mock_client),
        ):
            yield mock_client

    @pytest.fixture
    def rate_limiter(self, mock_redis):
        """Create a GoogleAPIRateLimiter instance"""
        return GoogleAPIRateLimiter()

    @pytest.mark.asyncio
    async def test_check_rate_limit_allowed(self, rate_limiter, mock_redis):
        """Test rate limit check when request is allowed"""
        # Mock Redis responses - all under limits
        mock_redis.incr.side_effect = [5, 150, 10000]  # per_second, per_minute, per_day

        # Check limit
        allowed, wait_time = await rate_limiter.check_rate_limit("routes")

        # Verify
        assert allowed is True
        assert wait_time is None
        assert mock_redis.incr.call_count == 3
        # Expire is only called when current == 1, none of our values are 1
        assert mock_redis.expire.call_count == 0

    @pytest.mark.asyncio
    async def test_check_rate_limit_denied_per_second(self, rate_limiter, mock_redis):
        """Test rate limit denied due to per - second limit"""
        # Mock Redis responses - per_second limit exceeded
        mock_redis.incr.return_value = 11  # Over the 10 / second limit for routes
        mock_redis.ttl = AsyncMock(return_value=1)  # TTL for wait time

        # Check limit
        allowed, wait_time = await rate_limiter.check_rate_limit("routes")

        # Verify
        assert allowed is False
        assert wait_time is not None
        assert mock_redis.incr.call_count == 1

    @pytest.mark.asyncio
    async def test_check_rate_limit_denied_per_minute(self, rate_limiter, mock_redis):
        """Test rate limit denied due to per - minute limit"""
        # Mock Redis responses - per_minute limit exceeded
        mock_redis.incr.side_effect = [5, 301]  # Under per_second, over per_minute
        mock_redis.ttl = AsyncMock(return_value=30)  # TTL for wait time

        # Check limit
        allowed, wait_time = await rate_limiter.check_rate_limit("routes")

        # Verify
        assert allowed is False
        assert wait_time is not None
        assert mock_redis.incr.call_count == 2

    @pytest.mark.asyncio
    async def test_check_rate_limit_denied_per_day(self, rate_limiter, mock_redis):
        """Test rate limit denied due to per - day limit"""
        # Mock Redis responses - per_day limit exceeded
        mock_redis.incr.side_effect = [5, 150, 25001]  # Under others, over per_day
        mock_redis.ttl = AsyncMock(return_value=3600)  # TTL for wait time

        # Check limit
        allowed, wait_time = await rate_limiter.check_rate_limit("routes")

        # Verify
        assert allowed is False
        assert wait_time is not None
        assert mock_redis.incr.call_count == 3

    @pytest.mark.asyncio
    async def test_different_api_types(self, rate_limiter, mock_redis):
        """Test different API types have different limits"""
        # Mock Redis responses
        mock_redis.incr.side_effect = [
            # Geocoding checks (higher limits)
            30,
            2000,
            2000,  # All under geocoding limits
            # Vertex AI checks
            2,
            40,
            800,  # All under vertex AI limits
        ]

        # Check geocoding limit
        allowed_geo, wait_time_geo = await rate_limiter.check_rate_limit("geocoding")
        assert allowed_geo is True
        assert wait_time_geo is None

        # Check vertex AI limit
        allowed_vertex, wait_time_vertex = await rate_limiter.check_rate_limit(
            "vertex_ai"
        )
        assert allowed_vertex is True
        assert wait_time_vertex is None

    @pytest.mark.asyncio
    async def test_get_usage_stats(self, rate_limiter, mock_redis):
        """Test getting current usage statistics"""
        # Mock Redis responses
        mock_redis.get.side_effect = [
            b"8",  # per_second
            b"250",  # per_minute
            b"20000",  # per_day
        ]

        # Get usage
        usage = await rate_limiter.get_usage_stats("routes")

        # Verify structure
        assert usage["api_type"] == "routes"
        assert usage["limits"]["per_second"] == 10
        assert usage["limits"]["per_minute"] == 300
        assert usage["limits"]["per_day"] == 25000
        assert usage["usage"]["second"]["current"] == 8
        assert usage["usage"]["minute"]["current"] == 250
        assert usage["usage"]["day"]["current"] == 20000
        assert "timestamp" in usage

    @pytest.mark.asyncio
    async def test_get_usage_stats_no_data(self, rate_limiter, mock_redis):
        """Test getting usage when no data exists"""
        # Mock Redis responses - no data
        mock_redis.get.return_value = None

        # Get usage
        usage = await rate_limiter.get_usage_stats("routes")

        # Verify
        assert usage["usage"]["second"]["current"] == 0
        assert usage["usage"]["minute"]["current"] == 0
        assert usage["usage"]["day"]["current"] == 0
        assert usage["usage"]["second"]["remaining"] == 10
        assert usage["usage"]["minute"]["remaining"] == 300
        assert usage["usage"]["day"]["remaining"] == 25000

    @pytest.mark.asyncio
    async def test_reset_limits(self, rate_limiter, mock_redis):
        """Test resetting rate limits"""
        # Mock Redis delete
        mock_redis.delete.return_value = 3

        # Reset limits
        result = await rate_limiter.reset_limits("routes")

        # Verify
        assert result is True
        assert (
            mock_redis.delete.call_count == 3
        )  # Should be called 3 times for each window

        # Check that correct keys were deleted
        delete_calls = [call[0][0] for call in mock_redis.delete.call_args_list]
        assert "rate_limit:routes:second" in delete_calls
        assert "rate_limit:routes:minute" in delete_calls
        assert "rate_limit:routes:day" in delete_calls

    @pytest.mark.asyncio
    async def test_redis_connection_error(self, rate_limiter, mock_redis):
        """Test handling Redis connection errors"""
        # Mock Redis error
        mock_redis.incr.side_effect = redis.ConnectionError("Connection failed")

        # Check limit - should allow request on error
        allowed, wait_time = await rate_limiter.check_rate_limit("routes")

        # Verify - fails open
        assert allowed is True
        assert wait_time is None

    @pytest.mark.asyncio
    async def test_unknown_api_type(self, rate_limiter, mock_redis):
        """Test handling unknown API type"""
        # Mock Redis responses
        mock_redis.incr.side_effect = [5, 150, 10000]

        # Check limit for unknown API
        allowed, wait_time = await rate_limiter.check_rate_limit("unknown_api")

        # Verify - allows unknown API types with warning
        assert allowed is True
        assert wait_time is None

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

        mock_redis.incr.side_effect = mock_incr

        # Make concurrent requests
        tasks = [rate_limiter.check_rate_limit("routes") for _ in range(5)]
        results = await asyncio.gather(*tasks)

        # Verify
        assert all(
            allowed for allowed, _ in results
        )  # All should be allowed (under limit)
        assert all(wait_time is None for _, wait_time in results)  # No wait times
        assert call_count == 15  # 5 requests * 3 checks each

    @pytest.mark.asyncio
    async def test_ttl_settings(self, rate_limiter, mock_redis):
        """Test that TTL is set correctly for different time windows"""
        # Mock Redis responses
        mock_redis.incr.side_effect = [1, 1, 1]

        # Check limit
        await rate_limiter.check_rate_limit("routes")

        # Verify TTL settings
        expire_calls = mock_redis.expire.call_args_list
        assert len(expire_calls) == 3

        # Check TTL values
        assert expire_calls[0][0][1] == 1  # per_second: 1 second
        assert expire_calls[1][0][1] == 60  # per_minute: 60 seconds
        assert expire_calls[2][0][1] == 86400  # per_day: 86400 seconds
