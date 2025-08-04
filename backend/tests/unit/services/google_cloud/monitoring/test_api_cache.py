"""
Unit tests for Google API Cache
"""

import json
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, Mock, patch

import pytest
import redis.asyncio as redis

from app.services.google_cloud.monitoring.api_cache import GoogleAPICache


class TestGoogleAPICache:
    """Test cases for GoogleAPICache"""

    @pytest.fixture
    def mock_redis(self):
        """Mock Redis client"""
        mock_client = AsyncMock()
        # Set up the mock attributes that will be used
        mock_client.get = AsyncMock(return_value=None)
        mock_client.setex = AsyncMock(return_value=True)
        mock_client.delete = AsyncMock(return_value=0)
        mock_client.scan = AsyncMock(return_value=(0, []))
        mock_client.exists = AsyncMock(return_value=0)
        mock_client.ttl = AsyncMock(return_value=-1)
        mock_client.memory_usage = AsyncMock(return_value=0)
        return mock_client

    @pytest.fixture
    def api_cache(self, mock_redis):
        """Create a GoogleAPICache instance with mocked Redis"""
        # Patch the get_redis_client function to return our mock
        with patch(
            "app.services.google_cloud.monitoring.api_cache.get_redis_client",
            AsyncMock(return_value=mock_redis),
        ):
            cache = GoogleAPICache()
            # Set the redis client directly to avoid initialization
            cache.redis = mock_redis
            cache._initialized = True
            return cache

    @pytest.mark.asyncio
    async def test_set_and_get_cache(self, api_cache, mock_redis):
        """Test setting and getting cached data"""
        # Test data
        test_data = {
            "routes": [
                {"distance": 1000, "duration": 120},
                {"distance": 2000, "duration": 240},
            ],
            "timestamp": datetime.now().isoformat(),
        }
        params = {"origin": "台北市", "destination": "新北市"}

        # Mock Redis set
        mock_redis.setex = AsyncMock(return_value=True)

        # Set cache
        success = await api_cache.set(
            "routes", params, test_data, ttl_override=timedelta(seconds=3600)
        )

        assert success is True

        # Verify Redis was called correctly
        mock_redis.setex.assert_called_once()

        # Mock Redis get
        mock_redis.get = AsyncMock(return_value=json.dumps(test_data).encode())

        # Get cache
        cached_data = await api_cache.get("routes", params)

        assert cached_data["routes"] == test_data["routes"]
        assert cached_data["_cache_hit"] is True

    @pytest.mark.asyncio
    async def test_cache_miss(self, api_cache, mock_redis):
        """Test cache miss returns None"""
        # Mock Redis get returning None
        mock_redis.get = AsyncMock(return_value=None)

        # Get non-existent cache
        params = {"origin": "台北市", "destination": "新北市"}
        result = await api_cache.get("routes", params)

        assert result is None

    @pytest.mark.asyncio
    async def test_cache_expiry(self, api_cache, mock_redis):
        """Test cache with TTL expiry"""
        # Set cache with short TTL
        mock_redis.setex = AsyncMock(return_value=True)

        params = {"address": "台北市信義區"}
        await api_cache.set(
            "geocoding",
            params,
            {"lat": 25.0, "lng": 121.5},
            ttl_override=timedelta(seconds=1),  # 1 second
        )

        # Verify TTL was set
        call_args = mock_redis.setex.call_args
        assert call_args[0][1] == 1

    @pytest.mark.asyncio
    async def test_invalidate_cache(self, api_cache, mock_redis):
        """Test invalidating cached data"""
        # Mock Redis delete
        mock_redis.delete = AsyncMock(return_value=1)

        # Invalidate cache
        params = {"origin": "台北市", "destination": "新北市"}
        invalidated = await api_cache.invalidate("routes", params)

        assert invalidated is True
        mock_redis.delete.assert_called_once()

    @pytest.mark.asyncio
    async def test_invalidate_nonexistent(self, api_cache, mock_redis):
        """Test invalidating non-existent cache"""
        # Mock Redis delete returning 0 (not found)
        mock_redis.delete = AsyncMock(return_value=0)

        # Invalidate non-existent
        params = {"origin": "台北市", "destination": "新北市"}
        invalidated = await api_cache.invalidate("routes", params)

        assert invalidated is False

    @pytest.mark.asyncio
    async def test_invalidate_pattern(self, api_cache, mock_redis):
        """Test invalidating cache by pattern"""

        # Mock Redis scan_iter to return keys as an async generator
        async def mock_scan_iter(match=None, count=100):
            keys = [
                "google_api:routes:key1",
                "google_api:routes:key2",
                "google_api:routes:key3",
            ]
            for key in keys:
                yield key

        mock_redis.scan_iter = mock_scan_iter
        mock_redis.delete = AsyncMock(return_value=3)

        # Invalidate by pattern
        count = await api_cache.invalidate_pattern("routes*")

        assert count == 3
        mock_redis.delete.assert_called_once()

    @pytest.mark.asyncio
    async def test_clear_all_cache(self, api_cache, mock_redis):
        """Test clearing all cache"""

        # Mock Redis scan_iter for all APIs
        async def mock_scan_iter(match=None):
            keys = [
                "google_api:routes:key1",
                "google_api:routes:key2",
                "google_api:geocoding:key1",
                "google_api:vertex_ai:key1",
                "google_api:vertex_ai:key2",
            ]
            for key in keys:
                yield key

        mock_redis.scan_iter = mock_scan_iter
        mock_redis.delete = AsyncMock(return_value=5)

        # Clear all
        total = await api_cache.clear_all()

        assert total == 5
        mock_redis.delete.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_stats(self, api_cache, mock_redis):
        """Test getting cache statistics"""
        # Mock Redis scan_iter for different API types
        call_count = 0

        async def mock_scan_iter(match=None, count=100):
            nonlocal call_count
            if "routes" in match:
                keys = ["key1", "key2"]
            elif "geocoding" in match:
                keys = ["key1"]
            else:
                keys = []
            for key in keys:
                yield key
            call_count += 1

        mock_redis.scan_iter = mock_scan_iter
        mock_redis.info = AsyncMock(return_value={"used_memory": 1048576})  # 1MB

        # Get stats
        stats = await api_cache.get_stats()

        assert "cache_types" in stats
        assert "total_entries" in stats
        assert "memory_used_mb" in stats
        assert stats["memory_used_mb"] == 1.0

    # Note: exists and get_ttl methods are not implemented in the actual api_cache.py
    # These tests have been removed to match the actual implementation

    @pytest.mark.asyncio
    async def test_complex_data_serialization(self, api_cache, mock_redis):
        """Test caching complex data structures"""
        # Complex nested data
        complex_data = {
            "routes": [
                {
                    "legs": [
                        {
                            "steps": [
                                {"instruction": "Turn left", "distance": 100},
                                {"instruction": "Turn right", "distance": 200},
                            ],
                            "duration": 300,
                        }
                    ],
                    "waypoints": ["台北市", "新竹市", "台中市"],
                }
            ],
            "metadata": {"timestamp": datetime.now().isoformat(), "version": "1.0"},
        }

        mock_redis.setex = AsyncMock(return_value=True)
        mock_redis.get = AsyncMock(return_value=json.dumps(complex_data).encode())

        # Set and get
        params = {"waypoints": ["台北市", "新竹市", "台中市"]}
        await api_cache.set("routes", params, complex_data)
        cached = await api_cache.get("routes", params)

        assert cached["routes"][0]["legs"][0]["steps"][0]["instruction"] == "Turn left"

    @pytest.mark.asyncio
    async def test_concurrent_operations(self, api_cache, mock_redis):
        """Test concurrent cache operations"""
        import asyncio

        # Mock Redis operations
        mock_redis.setex = AsyncMock(return_value=True)
        mock_redis.get = AsyncMock(return_value=json.dumps({"result": "test"}).encode())

        # Concurrent operations
        async def cache_operation(i):
            params = {"id": i}
            await api_cache.set("routes", params, {"result": f"test_{i}"})
            return await api_cache.get("routes", params)

        # Run concurrently
        results = await asyncio.gather(*[cache_operation(i) for i in range(10)])

        assert len(results) == 10
        assert all(r is not None for r in results)

    @pytest.mark.asyncio
    async def test_redis_error_handling(self, api_cache, mock_redis):
        """Test handling Redis errors gracefully"""
        # Mock Redis error
        mock_redis.get = AsyncMock(side_effect=redis.RedisError("Connection failed"))

        # Should return None on error
        params = {"origin": "台北市", "destination": "新北市"}
        result = await api_cache.get("routes", params)

        assert result is None

        # Mock set error
        mock_redis.setex = AsyncMock(side_effect=redis.RedisError("Connection failed"))

        # Should return False on error
        success = await api_cache.set("routes", params, {"data": "test"})

        assert success is False

    @pytest.mark.asyncio
    async def test_cache_key_patterns(self, api_cache, mock_redis):
        """Test cache key generation patterns"""
        # Test different parameter combinations
        test_cases = [
            {"params": {"origin": "台北", "destination": "高雄"}, "api_type": "routes"},
            {
                "params": {"address": "台北市信義區信義路五段7號"},
                "api_type": "geocoding",
            },
            {
                "params": {"lat": 25.033, "lng": 121.565},
                "api_type": "reverse_geocoding",
            },
        ]

        mock_redis.setex = AsyncMock(return_value=True)

        for case in test_cases:
            await api_cache.set(case["api_type"], case["params"], {"result": "test"})

        # Verify different keys were generated
        assert mock_redis.setex.call_count == 3

        # Check that keys are different
        calls = [call[0][0] for call in mock_redis.setex.call_args_list]
        assert len(set(calls)) == 3  # All keys should be unique
