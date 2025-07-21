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
        with patch("app.services.google_cloud.monitoring.cost_monitor.redis.from_url") as mock:
            mock_client = AsyncMock()
            mock.return_value = mock_client
            yield mock_client
    
    @pytest.fixture
    def cost_monitor(self, mock_redis):
        """Create a GoogleAPICostMonitor instance"""
        return GoogleAPICostMonitor()
    
    @pytest.mark.asyncio
    async def test_track_cost(self, cost_monitor, mock_redis):
        """Test tracking API cost"""
        # Mock Redis responses
        mock_redis.incrbyfloat = AsyncMock(side_effect=[10.50, 100.50, 500.50])
        mock_redis.expire = AsyncMock()
        mock_redis.rpush = AsyncMock()
        mock_redis.ltrim = AsyncMock()
        
        # Track cost
        await cost_monitor.track_cost(
            "routes",
            "route_optimization",
            Decimal("10.50"),
            {"route_id": "12345"}
        )
        
        # Verify daily, monthly, yearly increments
        assert mock_redis.incrbyfloat.call_count == 3
        incr_calls = mock_redis.incrbyfloat.call_args_list
        assert float(incr_calls[0][0][1]) == 10.50
        
        # Verify expiration set
        assert mock_redis.expire.call_count >= 1
        
        # Verify cost log
        mock_redis.rpush.assert_called_once()
        log_data = json.loads(mock_redis.rpush.call_args[0][1])
        assert log_data["api_type"] == "routes"
        assert log_data["operation"] == "route_optimization"
        assert float(log_data["amount"]) == 10.50
        assert log_data["metadata"]["route_id"] == "12345"
    
    @pytest.mark.asyncio
    async def test_check_budget_under_limit(self, cost_monitor, mock_redis):
        """Test budget check when under limit"""
        # Mock Redis get - under daily limit
        mock_redis.get = AsyncMock(return_value=b"45.00")
        
        # Check budget
        allowed = await cost_monitor.check_budget("routes", Decimal("5.00"))
        
        # Verify
        assert allowed is True
    
    @pytest.mark.asyncio
    async def test_check_budget_over_warning(self, cost_monitor, mock_redis):
        """Test budget check when over warning threshold"""
        # Mock Redis get - over warning but under critical
        mock_redis.get = AsyncMock(return_value=b"55.00")
        
        # Check budget
        allowed = await cost_monitor.check_budget("routes", Decimal("10.00"))
        
        # Verify - should still allow but with warning
        assert allowed is True
    
    @pytest.mark.asyncio
    async def test_check_budget_over_critical(self, cost_monitor, mock_redis):
        """Test budget check when over critical threshold"""
        # Mock Redis get - over critical limit
        mock_redis.get = AsyncMock(return_value=b"105.00")
        
        # Check budget
        allowed = await cost_monitor.check_budget("routes", Decimal("10.00"))
        
        # Verify - should deny
        assert allowed is False
    
    @pytest.mark.asyncio
    async def test_check_budget_no_data(self, cost_monitor, mock_redis):
        """Test budget check when no usage data exists"""
        # Mock Redis get - no data
        mock_redis.get = AsyncMock(return_value=None)
        
        # Check budget
        allowed = await cost_monitor.check_budget("routes", Decimal("10.00"))
        
        # Verify
        assert allowed is True
    
    @pytest.mark.asyncio
    async def test_get_cost_summary(self, cost_monitor, mock_redis):
        """Test getting cost summary"""
        # Mock Redis responses
        mock_redis.get = AsyncMock(side_effect=[
            b"45.50",   # daily
            b"450.00",  # monthly
            b"5000.00"  # yearly
        ])
        
        # Mock cost logs
        cost_logs = [
            json.dumps({
                "timestamp": datetime.now().isoformat(),
                "api_type": "routes",
                "operation": "optimize",
                "amount": "10.50",
                "metadata": {}
            }),
            json.dumps({
                "timestamp": datetime.now().isoformat(),
                "api_type": "routes",
                "operation": "matrix",
                "amount": "5.00",
                "metadata": {}
            })
        ]
        mock_redis.lrange = AsyncMock(return_value=[log.encode() for log in cost_logs])
        
        # Get summary
        summary = await cost_monitor.get_cost_summary("routes")
        
        # Verify
        assert summary["api_type"] == "routes"
        assert float(summary["daily_total"]) == 45.50
        assert float(summary["monthly_total"]) == 450.00
        assert float(summary["yearly_total"]) == 5000.00
        assert len(summary["recent_operations"]) == 2
        assert summary["budget_status"]["daily_remaining"] == "54.50"
        assert summary["budget_status"]["is_over_warning"] is False
        assert summary["budget_status"]["is_over_critical"] is False
    
    @pytest.mark.asyncio
    async def test_get_cost_summary_over_budget(self, cost_monitor, mock_redis):
        """Test cost summary when over budget"""
        # Mock Redis responses - over critical
        mock_redis.get = AsyncMock(side_effect=[
            b"150.00",  # daily (over critical)
            b"1500.00", # monthly
            b"15000.00" # yearly
        ])
        mock_redis.lrange = AsyncMock(return_value=[])
        
        # Get summary
        summary = await cost_monitor.get_cost_summary("routes")
        
        # Verify
        assert summary["budget_status"]["is_over_warning"] is True
        assert summary["budget_status"]["is_over_critical"] is True
        assert float(summary["budget_status"]["daily_remaining"]) == -50.00
    
    @pytest.mark.asyncio
    async def test_get_api_usage(self, cost_monitor, mock_redis):
        """Test getting API usage statistics"""
        # Mock Redis responses
        mock_redis.get = AsyncMock(side_effect=[
            b"75.00",   # daily
            b"750.00",  # monthly
            b"7500.00"  # yearly
        ])
        
        # Get usage
        usage = await cost_monitor.get_api_usage("routes")
        
        # Verify
        assert usage["api_type"] == "routes"
        assert float(usage["daily_cost"]) == 75.00
        assert usage["daily_percentage"] == 75.0  # 75% of $100 budget
        assert usage["over_budget"] is False
        assert float(usage["thresholds"]["daily_warning"]) == 50.00
        assert float(usage["thresholds"]["daily_critical"]) == 100.00
    
    @pytest.mark.asyncio
    async def test_reset_daily_costs(self, cost_monitor, mock_redis):
        """Test resetting daily costs"""
        # Mock Redis scan and delete
        mock_redis.scan = AsyncMock(return_value=(0, [
            b"cost:routes:daily:2024-01-20",
            b"cost:geocoding:daily:2024-01-20"
        ]))
        mock_redis.delete = AsyncMock(return_value=2)
        
        # Reset costs
        count = await cost_monitor.reset_daily_costs()
        
        # Verify
        assert count == 2
        mock_redis.delete.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_get_detailed_report(self, cost_monitor, mock_redis):
        """Test getting detailed cost report"""
        # Mock Redis responses
        mock_redis.get = AsyncMock(side_effect=[
            # Routes API
            b"45.00", b"450.00", b"4500.00",
            # Geocoding API
            b"20.00", b"200.00", b"2000.00",
            # Vertex AI
            b"100.00", b"1000.00", b"10000.00"
        ])
        
        # Get report
        report = await cost_monitor.get_detailed_report()
        
        # Verify
        assert "routes" in report
        assert "geocoding" in report
        assert "vertex_ai" in report
        
        assert float(report["routes"]["daily"]) == 45.00
        assert float(report["geocoding"]["daily"]) == 20.00
        assert float(report["vertex_ai"]["daily"]) == 100.00
        
        assert float(report["total"]["daily"]) == 165.00
        assert float(report["total"]["monthly"]) == 1650.00
        assert float(report["total"]["yearly"]) == 16500.00
    
    @pytest.mark.asyncio
    async def test_different_api_cost_rates(self, cost_monitor, mock_redis):
        """Test different cost rates for different APIs"""
        mock_redis.incrbyfloat = AsyncMock()
        mock_redis.expire = AsyncMock()
        mock_redis.rpush = AsyncMock()
        mock_redis.ltrim = AsyncMock()
        
        # Track costs for different APIs
        await cost_monitor.track_cost("routes", "optimize", Decimal("0.01"), {})
        await cost_monitor.track_cost("geocoding", "geocode", Decimal("0.005"), {})
        await cost_monitor.track_cost("vertex_ai", "predict", Decimal("0.05"), {})
        
        # Verify all were tracked
        assert mock_redis.incrbyfloat.call_count == 9  # 3 APIs * 3 periods each
    
    @pytest.mark.asyncio
    async def test_concurrent_cost_tracking(self, cost_monitor, mock_redis):
        """Test concurrent cost tracking"""
        import asyncio
        
        mock_redis.incrbyfloat = AsyncMock(return_value=50.0)
        mock_redis.expire = AsyncMock()
        mock_redis.rpush = AsyncMock()
        mock_redis.ltrim = AsyncMock()
        
        # Track costs concurrently
        tasks = [
            cost_monitor.track_cost("routes", "optimize", Decimal("10.00"), {})
            for _ in range(5)
        ]
        await asyncio.gather(*tasks)
        
        # Verify
        assert mock_redis.incrbyfloat.call_count == 15  # 5 requests * 3 periods
        assert mock_redis.rpush.call_count == 5
    
    @pytest.mark.asyncio
    async def test_redis_error_handling(self, cost_monitor, mock_redis):
        """Test handling Redis errors gracefully"""
        # Mock Redis error
        mock_redis.get = AsyncMock(side_effect=redis.ConnectionError("Connection failed"))
        
        # Check budget - should allow on error
        allowed = await cost_monitor.check_budget("routes", Decimal("10.00"))
        assert allowed is True
        
        # Get usage - should return safe defaults
        usage = await cost_monitor.get_api_usage("routes")
        assert usage["daily_cost"] == 0.0
        assert usage["over_budget"] is False