"""
Unit tests for Google API Cost Monitor
"""
import pytest
from unittest.mock import Mock, patch, AsyncMock
from datetime import datetime, timedelta
from decimal import Decimal
import json
import redis.asyncio as redis

from app.services.google_cloud.monitoring.cost_monitor import GoogleAPICostMonitor


class TestGoogleAPICostMonitor:
    """Test cases for GoogleAPICostMonitor"""
    
    @pytest.fixture
    def mock_redis(self):
        """Mock Redis client"""
        mock_client = AsyncMock()
        with patch("app.services.google_cloud.monitoring.cost_monitor.get_redis_client", AsyncMock(return_value=mock_client)):
            yield mock_client
    
    @pytest.fixture
    def cost_monitor(self, mock_redis):
        """Create a GoogleAPICostMonitor instance"""
        return GoogleAPICostMonitor()
    
    @pytest.mark.asyncio
    async def test_track_cost(self, cost_monitor, mock_redis):
        """Test tracking API cost"""
        # Mock Redis responses
        mock_redis.incrbyfloat = AsyncMock()
        mock_redis.expire = AsyncMock()
        mock_redis.incr = AsyncMock()
        mock_redis.hset = AsyncMock()
        mock_redis.get = AsyncMock(return_value=None)  # No existing costs for threshold check
        
        # Track cost
        result = await cost_monitor.record_api_call(
            api_type="routes",
            endpoint="route_optimization",
            response_size=1024,
            processing_time=0.5
        )
        
        # Verify cost tracking (hour, day, month)
        assert mock_redis.incrbyfloat.call_count == 3
        # Cost per call for routes = $5 per 1000 = $0.005 per call
        expected_cost = 0.005
        for call in mock_redis.incrbyfloat.call_args_list:
            assert float(call[0][1]) == expected_cost
        
        # Verify expiration set
        assert mock_redis.expire.call_count >= 3
        
        # Verify metadata stored
        mock_redis.hset.assert_called_once()
        
        # Verify result
        assert result["api_type"] == "routes"
        assert result["endpoint"] == "route_optimization"
        assert result["cost"] == expected_cost
    
    @pytest.mark.asyncio
    async def test_check_budget_under_limit(self, cost_monitor, mock_redis):
        """Test budget check when under limit"""
        # Mock Redis get - under daily limit
        # The method checks hourly first, and _get_period_total loops through all API types
        mock_redis.get = AsyncMock(side_effect=[
            # First call for hourly total - checking all 5 API types
            b"8.00",  # routes
            None,     # geocoding
            None,     # places
            None,     # vertex_ai
            None,     # distance_matrix
            # Second call for daily total - checking all 5 API types
            b"45.00", # routes
            None,     # geocoding
            None,     # places
            None,     # vertex_ai
            None,     # distance_matrix
        ])
        
        # Check budget
        allowed = await cost_monitor.enforce_budget_limit("routes")
        
        # Verify
        assert allowed is True
    
    @pytest.mark.asyncio
    async def test_check_budget_over_warning(self, cost_monitor, mock_redis):
        """Test budget check when over warning threshold"""
        # Mock Redis get - over warning but under critical
        mock_redis.get = AsyncMock(side_effect=[
            # First call for hourly total - over warning (>$5) but under critical (<$10)
            b"6.00",  # routes - $6/hour is over warning threshold of $5
            None,     # geocoding
            None,     # places
            None,     # vertex_ai
            None,     # distance_matrix
            # Second call for daily total
            b"55.00", # routes
            None,     # geocoding
            None,     # places
            None,     # vertex_ai
            None,     # distance_matrix
        ])
        
        # Check budget
        allowed = await cost_monitor.enforce_budget_limit("routes")
        
        # Verify - should still allow but with warning
        assert allowed is True
    
    @pytest.mark.asyncio
    async def test_check_budget_over_critical(self, cost_monitor, mock_redis):
        """Test budget check when over critical threshold"""
        # Mock Redis get - over critical limit
        mock_redis.get = AsyncMock(side_effect=[
            # First call for hourly total - over critical (>$10)
            b"15.00", # routes - $15/hour is over critical threshold of $10
            None,     # geocoding
            None,     # places
            None,     # vertex_ai
            None,     # distance_matrix
        ])
        
        # Check budget
        allowed = await cost_monitor.enforce_budget_limit("routes")
        
        # Verify - should deny (stops at hourly check)
        assert allowed is False
    
    @pytest.mark.asyncio
    async def test_check_budget_no_data(self, cost_monitor, mock_redis):
        """Test budget check when no usage data exists"""
        # Mock Redis get - no data
        mock_redis.get = AsyncMock(return_value=None)
        
        # Check budget
        allowed = await cost_monitor.enforce_budget_limit("routes")
        
        # Verify
        assert allowed is True
    
    @pytest.mark.asyncio
    async def test_get_cost_summary(self, cost_monitor, mock_redis):
        """Test getting cost summary"""
        # Mock Redis responses - get_cost_report loops through each API type
        # For each API, it gets cost and count
        mock_redis.get = AsyncMock(side_effect=[
            # Routes API cost and count
            b"45.50", b"9100",
            # Geocoding API cost and count
            None, None,
            # Places API cost and count
            None, None,
            # Vertex AI cost and count
            None, None,
            # Distance matrix cost and count
            None, None
        ])
        
        # Get summary
        summary = await cost_monitor.get_cost_report("daily")
        
        # Verify - get_cost_report returns overall costs, not per API
        assert summary["period"] == "daily"
        assert "costs_by_api" in summary
        assert "counts_by_api" in summary
        assert "total_cost" in summary
        assert "budget_limit" in summary
        assert "budget_remaining" in summary
        
        # Check specific values
        assert summary["costs_by_api"].get("routes") == 45.50
        assert summary["total_cost"] == 45.50
        assert summary["budget_limit"] == 50.0  # Daily warning threshold
    
    @pytest.mark.asyncio
    async def test_get_cost_summary_over_budget(self, cost_monitor, mock_redis):
        """Test cost summary when over budget"""
        # Mock Redis responses - over critical for all API types
        mock_redis.get = AsyncMock(side_effect=[
            # Routes API cost and count (over critical)
            b"150.00", b"30000",
            # Geocoding API cost and count
            None, None,
            # Places API cost and count
            None, None,
            # Vertex AI cost and count
            None, None,
            # Distance matrix cost and count
            None, None
        ])
        
        # Get summary
        summary = await cost_monitor.get_cost_report("daily")
        
        # Verify warnings for over budget
        assert "warnings" in summary
        assert len(summary["warnings"]) > 0  # Should have warnings about exceeding budget
        assert summary["budget_percentage"] > 100  # Over 100% of budget
    
    @pytest.mark.asyncio
    async def test_get_api_usage(self, cost_monitor, mock_redis):
        """Test getting API usage statistics"""
        # Mock Redis responses - needs both cost and count for each hour
        mock_redis.get = AsyncMock(side_effect=[
            # First hour - cost and count
            b"75.00",   # cost
            b"15000",   # count
            # Second hour - cost and count
            b"50.00",   # cost
            b"10000",   # count
            # Third hour - cost and count
            b"25.00",   # cost
            b"5000"     # count
        ])
        
        # Get usage for a time range
        start_time = datetime.now() - timedelta(hours=2)
        end_time = datetime.now()
        usage = await cost_monitor.get_detailed_usage(
            api_type="routes",
            start_time=start_time,
            end_time=end_time
        )
        
        # Verify structure
        assert usage["api_type"] == "routes"
        assert "hourly_breakdown" in usage
        assert "total_cost" in usage
        assert "total_calls" in usage
        assert len(usage["hourly_breakdown"]) == 3
        assert usage["total_cost"] == 150.00  # 75 + 50 + 25
        assert usage["total_calls"] == 30000  # 15000 + 10000 + 5000
    
    @pytest.mark.asyncio
    async def test_reset_daily_costs(self, cost_monitor, mock_redis):
        """Test resetting daily costs"""
        # Create a proper async iterator mock
        async def async_scan_iter(*args, **kwargs):
            for key in [
                b"api_cost:day:2024-01-20:routes",
                b"api_cost:day:2024-01-20:geocoding"
            ]:
                yield key
        
        # Mock Redis scan_iter and delete
        mock_redis.scan_iter = async_scan_iter
        mock_redis.delete = AsyncMock(return_value=1)
        
        # Reset costs
        result = await cost_monitor.reset_budgets("day")
        
        # Verify
        assert result is True
        assert mock_redis.delete.call_count >= 1
    
    @pytest.mark.asyncio
    async def test_get_detailed_report(self, cost_monitor, mock_redis):
        """Test getting detailed cost report"""
        # Mock Redis responses - get_cost_report calls get for each API type in sequence
        # For daily report, it gets cost and count for each API type
        mock_redis.get = AsyncMock(side_effect=[
            # Routes API cost and count
            b"45.00", b"9000",
            # Geocoding API cost and count
            b"20.00", b"4000",
            # Places API cost and count (not in original test but part of COST_PER_1000_CALLS)
            None, None,
            # Vertex AI cost and count
            b"100.00", b"100000",
            # Distance matrix cost and count
            None, None
        ])
        
        # Get report
        report = await cost_monitor.get_cost_report("daily")
        
        # Verify structure
        assert "costs_by_api" in report
        assert "counts_by_api" in report
        assert "total_cost" in report
        assert "total_calls" in report
        assert "budget_limit" in report
        assert "budget_remaining" in report
        assert "budget_percentage" in report
        
        # Verify specific values
        assert report["costs_by_api"].get("routes") == 45.00
        assert report["costs_by_api"].get("geocoding") == 20.00
        assert report["costs_by_api"].get("vertex_ai") == 100.00
        assert report["total_cost"] == 165.00
    
    @pytest.mark.asyncio
    async def test_different_api_cost_rates(self, cost_monitor, mock_redis):
        """Test different cost rates for different APIs"""
        mock_redis.incrbyfloat = AsyncMock()
        mock_redis.expire = AsyncMock()
        mock_redis.incr = AsyncMock()
        mock_redis.hset = AsyncMock()
        mock_redis.get = AsyncMock(return_value=None)  # No existing costs for threshold checks
        
        # Track costs for different APIs
        await cost_monitor.record_api_call(api_type="routes", endpoint="optimize")
        await cost_monitor.record_api_call(api_type="geocoding", endpoint="geocode")
        await cost_monitor.record_api_call(api_type="vertex_ai", endpoint="predict")
        
        # Verify all were tracked (3 APIs * 3 time windows for costs)
        assert mock_redis.incrbyfloat.call_count == 9  # 3 APIs * 3 periods each
        
        # Verify the correct costs were recorded
        calls = mock_redis.incrbyfloat.call_args_list
        # Routes: $5 per 1000 = $0.005 per call
        assert float(calls[0][0][1]) == 0.005
        # Geocoding: $5 per 1000 = $0.005 per call
        assert float(calls[3][0][1]) == 0.005
        # Vertex AI: $1 per 1000 = $0.001 per call
        assert float(calls[6][0][1]) == 0.001
    
    @pytest.mark.asyncio
    async def test_concurrent_cost_tracking(self, cost_monitor, mock_redis):
        """Test concurrent cost tracking"""
        import asyncio
        
        mock_redis.incrbyfloat = AsyncMock(return_value=50.0)
        mock_redis.expire = AsyncMock()
        mock_redis.incr = AsyncMock()
        mock_redis.hset = AsyncMock()
        mock_redis.get = AsyncMock(return_value=None)  # No existing costs
        
        # Track costs concurrently
        tasks = [
            cost_monitor.record_api_call("routes", "optimize")
            for _ in range(5)
        ]
        await asyncio.gather(*tasks)
        
        # Verify
        assert mock_redis.incrbyfloat.call_count == 15  # 5 requests * 3 periods
    
    @pytest.mark.asyncio
    async def test_redis_error_handling(self, cost_monitor, mock_redis):
        """Test handling Redis errors gracefully"""
        # Mock Redis error
        mock_redis.get = AsyncMock(side_effect=redis.ConnectionError("Connection failed"))
        
        # Check budget - should allow on error
        allowed = await cost_monitor.enforce_budget_limit("routes")
        assert allowed is True
        
        # Get usage - should return structure even with error
        start_time = datetime.now() - timedelta(hours=1)
        end_time = datetime.now()
        usage = await cost_monitor.get_detailed_usage(
            api_type="routes",
            start_time=start_time,
            end_time=end_time
        )
        assert usage["api_type"] == "routes"
        assert "hourly_breakdown" in usage