"""
Unit tests for Google API Cache
"""
import pytest
from unittest.mock import Mock, patch, AsyncMock
from datetime import datetime, timedelta
import json
import redis.asyncio as redis

from app.services.google_cloud.monitoring.api_cache import GoogleAPICache


class TestGoogleAPICache:
    """Test cases for GoogleAPICache"""
    
    @pytest.fixture
    def mock_redis(self):
        """Mock Redis client"""
        with patch("app.services.google_cloud.monitoring.api_cache.redis.from_url") as mock:
            mock_client = AsyncMock()
            mock.return_value = mock_client
            yield mock_client
    
    @pytest.fixture
    def api_cache(self, mock_redis):
        """Create a GoogleAPICache instance"""
        return GoogleAPICache()
    
    @pytest.mark.asyncio
    async def test_set_and_get_cache(self, api_cache, mock_redis):
        """Test setting and getting cached data"""
        # Test data
        test_data = {
            "routes": [
                {"distance": 1000, "duration": 120},
                {"distance": 2000, "duration": 240}
            ],
            "timestamp": datetime.now().isoformat()
        }
        
        # Mock Redis set
        mock_redis.setex = AsyncMock(return_value=True)
        
        # Set cache
        success = await api_cache.set(
            "route_matrix_123",
            test_data,
            "routes",
            ttl=3600
        )
        
        assert success is True
        
        # Verify Redis was called correctly
        mock_redis.setex.assert_called_once()
        call_args = mock_redis.setex.call_args
        assert "cache:routes:route_matrix_123" in call_args[0]
        assert call_args[0][1] == 3600  # TTL
        assert json.loads(call_args[0][2]) == test_data
        
        # Mock Redis get
        mock_redis.get = AsyncMock(return_value=json.dumps(test_data).encode())
        
        # Get cache
        cached_data = await api_cache.get("route_matrix_123", "routes")
        
        assert cached_data == test_data
    
    @pytest.mark.asyncio
    async def test_cache_miss(self, api_cache, mock_redis):
        """Test cache miss returns None"""
        # Mock Redis get returning None
        mock_redis.get = AsyncMock(return_value=None)
        
        # Get non-existent cache
        result = await api_cache.get("nonexistent_key", "routes")
        
        assert result is None
    
    @pytest.mark.asyncio
    async def test_cache_expiry(self, api_cache, mock_redis):
        """Test cache with TTL expiry"""
        # Set cache with short TTL
        mock_redis.setex = AsyncMock(return_value=True)
        
        await api_cache.set(
            "temp_data",
            {"value": "test"},
            "routes",
            ttl=1  # 1 second
        )
        
        # Verify TTL was set
        call_args = mock_redis.setex.call_args
        assert call_args[0][1] == 1
    
    @pytest.mark.asyncio
    async def test_delete_cache(self, api_cache, mock_redis):
        """Test deleting cached data"""
        # Mock Redis delete
        mock_redis.delete = AsyncMock(return_value=1)
        
        # Delete cache
        deleted = await api_cache.delete("route_matrix_123", "routes")
        
        assert deleted is True
        mock_redis.delete.assert_called_once_with("cache:routes:route_matrix_123")
    
    @pytest.mark.asyncio
    async def test_delete_nonexistent(self, api_cache, mock_redis):
        """Test deleting non-existent cache"""
        # Mock Redis delete returning 0 (not found)
        mock_redis.delete = AsyncMock(return_value=0)
        
        # Delete non-existent
        deleted = await api_cache.delete("nonexistent", "routes")
        
        assert deleted is False
    
    @pytest.mark.asyncio
    async def test_clear_api_cache(self, api_cache, mock_redis):
        """Test clearing all cache for specific API"""
        # Mock Redis scan and delete
        mock_redis.scan = AsyncMock(return_value=(
            0,
            [
                b"cache:routes:key1",
                b"cache:routes:key2",
                b"cache:routes:key3"
            ]
        ))
        mock_redis.delete = AsyncMock(return_value=3)
        
        # Clear cache
        count = await api_cache.clear_api_cache("routes")
        
        assert count == 3
        mock_redis.delete.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_clear_all_cache(self, api_cache, mock_redis):
        """Test clearing all cache"""
        # Mock Redis scan for multiple APIs
        mock_redis.scan = AsyncMock(side_effect=[
            (0, [b"cache:routes:key1", b"cache:routes:key2"]),
            (0, [b"cache:geocoding:key1"]),
            (0, [b"cache:vertex_ai:key1", b"cache:vertex_ai:key2"])
        ])
        mock_redis.delete = AsyncMock(side_effect=[2, 1, 2])
        
        # Clear all cache
        count = await api_cache.clear_all_cache()
        
        assert count == 5  # Total of all deleted keys
        assert mock_redis.delete.call_count == 3
    
    @pytest.mark.asyncio
    async def test_get_cache_stats(self, api_cache, mock_redis):
        """Test getting cache statistics"""
        # Mock Redis scan and ttl
        mock_redis.scan = AsyncMock(return_value=(
            0,
            [
                b"cache:routes:key1",
                b"cache:routes:key2",
                b"cache:geocoding:key1",
                b"cache:vertex_ai:key1"
            ]
        ))
        
        # Mock memory usage info
        mock_redis.memory_usage = AsyncMock(side_effect=[
            1024,  # 1KB
            2048,  # 2KB
            512,   # 0.5KB
            4096   # 4KB
        ])
        
        # Mock TTL values
        mock_redis.ttl = AsyncMock(side_effect=[
            3600,  # 1 hour
            1800,  # 30 minutes
            -1,    # No expiry
            7200   # 2 hours
        ])
        
        # Get stats
        stats = await api_cache.get_cache_stats()
        
        # Verify stats
        assert stats["total_keys"] == 4
        assert stats["total_memory_bytes"] == 7680  # Sum of all
        assert stats["by_api"]["routes"]["count"] == 2
        assert stats["by_api"]["routes"]["memory_bytes"] == 3072
        assert stats["by_api"]["geocoding"]["count"] == 1
        assert stats["by_api"]["vertex_ai"]["count"] == 1
        assert "timestamp" in stats
    
    @pytest.mark.asyncio
    async def test_exists(self, api_cache, mock_redis):
        """Test checking if cache key exists"""
        # Mock Redis exists
        mock_redis.exists = AsyncMock(return_value=1)
        
        # Check existence
        exists = await api_cache.exists("route_matrix_123", "routes")
        
        assert exists is True
        mock_redis.exists.assert_called_once_with("cache:routes:route_matrix_123")
        
        # Test non-existent
        mock_redis.exists = AsyncMock(return_value=0)
        exists = await api_cache.exists("nonexistent", "routes")
        assert exists is False
    
    @pytest.mark.asyncio
    async def test_get_ttl(self, api_cache, mock_redis):
        """Test getting remaining TTL"""
        # Mock Redis ttl
        mock_redis.ttl = AsyncMock(return_value=1800)  # 30 minutes
        
        # Get TTL
        ttl = await api_cache.get_ttl("route_matrix_123", "routes")
        
        assert ttl == 1800
        mock_redis.ttl.assert_called_once_with("cache:routes:route_matrix_123")
        
        # Test expired/non-existent
        mock_redis.ttl = AsyncMock(return_value=-2)
        ttl = await api_cache.get_ttl("expired", "routes")
        assert ttl == -2
    
    @pytest.mark.asyncio
    async def test_complex_data_serialization(self, api_cache, mock_redis):
        """Test caching complex data structures"""
        complex_data = {
            "routes": [
                {
                    "legs": [
                        {"distance": {"value": 1000}, "duration": {"value": 120}},
                        {"distance": {"value": 2000}, "duration": {"value": 240}}
                    ],
                    "waypoints": [
                        {"location": {"lat": 25.033, "lng": 121.565}},
                        {"location": {"lat": 25.047, "lng": 121.517}}
                    ]
                }
            ],
            "status": "OK",
            "timestamp": datetime.now().isoformat()
        }
        
        # Mock Redis operations
        mock_redis.setex = AsyncMock(return_value=True)
        stored_data = None
        
        async def capture_setex(key, ttl, data):
            nonlocal stored_data
            stored_data = data
            return True
        
        mock_redis.setex = capture_setex
        
        # Set complex data
        await api_cache.set("complex_route", complex_data, "routes")
        
        # Verify it can be deserialized
        deserialized = json.loads(stored_data)
        assert deserialized == complex_data
    
    @pytest.mark.asyncio
    async def test_concurrent_operations(self, api_cache, mock_redis):
        """Test concurrent cache operations"""
        import asyncio
        
        # Mock Redis operations
        mock_redis.setex = AsyncMock(return_value=True)
        mock_redis.get = AsyncMock(side_effect=[
            json.dumps({"data": i}).encode()
            for i in range(10)
        ])
        
        # Concurrent set operations
        set_tasks = [
            api_cache.set(f"key_{i}", {"data": i}, "routes")
            for i in range(10)
        ]
        
        set_results = await asyncio.gather(*set_tasks)
        assert all(set_results)
        assert mock_redis.setex.call_count == 10
        
        # Reset mock
        mock_redis.get.call_count = 0
        
        # Concurrent get operations
        get_tasks = [
            api_cache.get(f"key_{i}", "routes")
            for i in range(10)
        ]
        
        get_results = await asyncio.gather(*get_tasks)
        assert len(get_results) == 10
    
    @pytest.mark.asyncio
    async def test_redis_error_handling(self, api_cache, mock_redis):
        """Test handling Redis errors gracefully"""
        # Mock Redis connection error
        mock_redis.setex = AsyncMock(side_effect=redis.ConnectionError("Connection failed"))
        
        # Set should return False on error
        success = await api_cache.set("key", {"data": "test"}, "routes")
        assert success is False
        
        # Get should return None on error
        mock_redis.get = AsyncMock(side_effect=redis.ConnectionError("Connection failed"))
        result = await api_cache.get("key", "routes")
        assert result is None
        
        # Delete should return False on error
        mock_redis.delete = AsyncMock(side_effect=redis.ConnectionError("Connection failed"))
        deleted = await api_cache.delete("key", "routes")
        assert deleted is False
    
    @pytest.mark.asyncio
    async def test_cache_key_patterns(self, api_cache, mock_redis):
        """Test cache key generation patterns"""
        # Test various key formats
        test_cases = [
            ("simple_key", "routes", "cache:routes:simple_key"),
            ("key_with_spaces", "geocoding", "cache:geocoding:key_with_spaces"),
            ("key/with/slashes", "vertex_ai", "cache:vertex_ai:key/with/slashes"),
            ("key:with:colons", "routes", "cache:routes:key:with:colons"),
        ]
        
        mock_redis.setex = AsyncMock(return_value=True)
        
        for key, api_type, expected_redis_key in test_cases:
            await api_cache.set(key, {"test": "data"}, api_type)
            
            # Check the Redis key used
            call_args = mock_redis.setex.call_args
            assert call_args[0][0] == expected_redis_key