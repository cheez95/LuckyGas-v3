"""
Integration tests for Google API components working together
"""
import pytest
from unittest.mock import Mock, patch, AsyncMock
import os
from datetime import datetime, timedelta
from decimal import Decimal
import json
import asyncio
import redis.asyncio as redis

from app.services.google_cloud.routes_service_enhanced import EnhancedGoogleRoutesService
from app.services.google_cloud.vertex_ai_service_enhanced import EnhancedVertexAIService
from app.services.google_cloud.monitoring.circuit_breaker import CircuitState
from app.core.security.api_key_manager import LocalEncryptedKeyManager
from app.services.google_cloud.development_mode import DevelopmentMode


@pytest.mark.integration
class TestGoogleAPIIntegration:
    """Integration tests for Google API services"""
    
    @pytest.fixture
    async def redis_client(self):
        """Create a test Redis client"""
        # Use a test Redis instance or mock
        with patch("redis.asyncio.from_url") as mock:
            client = AsyncMock()
            mock.return_value = client
            yield client
    
    @pytest.fixture
    async def routes_service(self, redis_client):
        """Create routes service with mocked Redis"""
        service = EnhancedGoogleRoutesService()
        return service
    
    @pytest.fixture
    async def vertex_service(self, redis_client):
        """Create vertex AI service with mocked Redis"""
        service = EnhancedVertexAIService()
        return service
    
    @pytest.mark.asyncio
    async def test_development_mode_flow(self, routes_service):
        """Test complete flow in development mode"""
        # Set development mode
        with patch.dict(os.environ, {"DEVELOPMENT_MODE": "development"}):
            # Should use mock service without API calls
            result = await routes_service.calculate_route(
                origin="25.033,121.565",
                destination="25.047,121.517"
            )
            
            # Verify mock response structure
            assert "routes" in result
            assert len(result["routes"]) > 0
            assert "distance" in result["routes"][0]
            assert "duration" in result["routes"][0]
            
            # No API costs should be tracked
            cost_status = await routes_service.cost_monitor.get_api_usage("routes")
            assert cost_status["daily_cost"] == 0.0
    
    @pytest.mark.asyncio
    async def test_rate_limiting_across_services(self, routes_service, vertex_service):
        """Test rate limiting works across different services"""
        # Mock Redis to simulate rate limit state
        routes_service.rate_limiter.redis_client.incr = AsyncMock(
            side_effect=[5, 150, 20000]  # Under limits
        )
        routes_service.rate_limiter.redis_client.expire = AsyncMock()
        
        vertex_service.rate_limiter.redis_client.incr = AsyncMock(
            side_effect=[2, 40, 800]  # Under limits
        )
        vertex_service.rate_limiter.redis_client.expire = AsyncMock()
        
        # Both services should allow requests
        routes_allowed = await routes_service.rate_limiter.check_limit("routes")
        vertex_allowed = await vertex_service.rate_limiter.check_limit("vertex_ai")
        
        assert routes_allowed is True
        assert vertex_allowed is True
    
    @pytest.mark.asyncio
    async def test_circuit_breaker_isolation(self, routes_service, vertex_service):
        """Test circuit breakers are isolated between services"""
        # Open routes service circuit breaker
        for _ in range(5):
            routes_service.circuit_breaker.record_failure()
        
        # Routes circuit should be open
        assert routes_service.circuit_breaker.state == CircuitState.OPEN
        assert not routes_service.circuit_breaker.can_execute()
        
        # Vertex circuit should still be closed
        assert vertex_service.circuit_breaker.state == CircuitState.CLOSED
        assert vertex_service.circuit_breaker.can_execute()
    
    @pytest.mark.asyncio
    async def test_cost_monitoring_aggregation(self, routes_service, vertex_service):
        """Test cost monitoring across services"""
        # Mock Redis for cost tracking
        routes_service.cost_monitor.redis_client.incrbyfloat = AsyncMock(
            return_value=10.50
        )
        routes_service.cost_monitor.redis_client.expire = AsyncMock()
        routes_service.cost_monitor.redis_client.rpush = AsyncMock()
        routes_service.cost_monitor.redis_client.ltrim = AsyncMock()
        
        vertex_service.cost_monitor.redis_client.incrbyfloat = AsyncMock(
            return_value=5.25
        )
        vertex_service.cost_monitor.redis_client.expire = AsyncMock()
        vertex_service.cost_monitor.redis_client.rpush = AsyncMock()
        vertex_service.cost_monitor.redis_client.ltrim = AsyncMock()
        
        # Track costs
        await routes_service.cost_monitor.track_cost(
            "routes", "optimization", Decimal("10.50"), {}
        )
        await vertex_service.cost_monitor.track_cost(
            "vertex_ai", "prediction", Decimal("5.25"), {}
        )
        
        # Get aggregated report
        routes_service.cost_monitor.redis_client.get = AsyncMock(
            side_effect=[b"10.50", b"105.00", b"1050.00"]
        )
        vertex_service.cost_monitor.redis_client.get = AsyncMock(
            side_effect=[b"5.25", b"52.50", b"525.00"]
        )
        
        # Check individual costs
        routes_cost = await routes_service.cost_monitor.get_api_usage("routes")
        vertex_cost = await vertex_service.cost_monitor.get_api_usage("vertex_ai")
        
        assert float(routes_cost["daily_cost"]) == 10.50
        assert float(vertex_cost["daily_cost"]) == 5.25
    
    @pytest.mark.asyncio
    async def test_cache_sharing_prevention(self, routes_service, vertex_service):
        """Test that caches are properly namespaced and don't conflict"""
        # Mock Redis for caching
        routes_service.cache.redis_client.setex = AsyncMock(return_value=True)
        vertex_service.cache.redis_client.setex = AsyncMock(return_value=True)
        
        # Cache data with same key in both services
        await routes_service.cache.set(
            "test_key",
            {"service": "routes", "data": "route_data"},
            "routes"
        )
        await vertex_service.cache.set(
            "test_key",
            {"service": "vertex", "data": "vertex_data"},
            "vertex_ai"
        )
        
        # Verify different Redis keys were used
        routes_call = routes_service.cache.redis_client.setex.call_args
        vertex_call = vertex_service.cache.redis_client.setex.call_args
        
        assert "cache:routes:test_key" in routes_call[0]
        assert "cache:vertex_ai:test_key" in vertex_call[0]
    
    @pytest.mark.asyncio
    async def test_error_handling_cascade(self, routes_service):
        """Test error handling through multiple layers"""
        # Set production mode
        with patch.dict(os.environ, {"DEVELOPMENT_MODE": "production"}):
            # Mock all checks to pass
            routes_service.rate_limiter.check_limit = AsyncMock(return_value=True)
            routes_service.cost_monitor.check_budget = AsyncMock(return_value=True)
            routes_service.circuit_breaker.can_execute = Mock(return_value=True)
            routes_service.cache.get = AsyncMock(return_value=None)
            
            # Mock parent method to fail
            with patch.object(
                routes_service.__class__.__bases__[0],
                'calculate_route',
                AsyncMock(side_effect=Exception("API Error"))
            ):
                # Mock error handler to simulate retries then failure
                call_count = 0
                
                async def mock_retry(func, **kwargs):
                    nonlocal call_count
                    call_count += 1
                    if call_count <= 3:
                        raise Exception("API Error")
                    return await func()
                
                routes_service.error_handler.execute_with_retry = mock_retry
                
                # Should fall back to mock service
                routes_service.mock_service.calculate_route = AsyncMock(
                    return_value={"routes": [{"distance": 1000}]}
                )
                
                result = await routes_service.calculate_route(
                    origin="25.033,121.565",
                    destination="25.047,121.517"
                )
                
                # Verify fallback was used
                assert result["routes"][0]["distance"] == 1000
                assert routes_service.metrics["failed_requests"] == 1
    
    @pytest.mark.asyncio
    async def test_health_check_aggregation(self, routes_service, vertex_service):
        """Test health check across services"""
        # Set different component states
        routes_service.circuit_breaker.state = CircuitState.CLOSED
        vertex_service.circuit_breaker.state = CircuitState.OPEN
        
        # Mock rate limiter status
        routes_service.rate_limiter.get_current_usage = AsyncMock(
            return_value={"available": True}
        )
        vertex_service.rate_limiter.get_current_usage = AsyncMock(
            return_value={"available": False}
        )
        
        # Mock cost monitor status
        routes_service.cost_monitor.get_api_usage = AsyncMock(
            return_value={"over_budget": False}
        )
        vertex_service.cost_monitor.get_api_usage = AsyncMock(
            return_value={"over_budget": True}
        )
        
        # Get health status
        routes_health = await routes_service.health_check()
        vertex_health = await vertex_service.health_check()
        
        # Routes should be healthy
        assert routes_health["status"] == "healthy"
        
        # Vertex should be degraded
        assert vertex_health["status"] == "degraded"
        assert "circuit_breaker" in vertex_health["unhealthy_components"]
    
    @pytest.mark.asyncio
    async def test_concurrent_service_requests(self, routes_service, vertex_service):
        """Test concurrent requests across services"""
        # Mock successful responses
        routes_service.dev_mode_manager.detect_mode = AsyncMock(
            return_value=DevelopmentMode.DEVELOPMENT
        )
        vertex_service.dev_mode_manager.detect_mode = AsyncMock(
            return_value=DevelopmentMode.DEVELOPMENT
        )
        
        # Create concurrent tasks
        tasks = []
        
        # Add route calculations
        for i in range(5):
            tasks.append(
                routes_service.calculate_route(
                    origin=f"25.{i:03d},121.565",
                    destination=f"25.{i:03d},121.517"
                )
            )
        
        # Add predictions
        for i in range(5):
            tasks.append(
                vertex_service.predict_demand_batch()
            )
        
        # Execute concurrently
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Verify all completed
        assert len(results) == 10
        assert not any(isinstance(r, Exception) for r in results)
    
    @pytest.mark.asyncio
    async def test_api_key_management_integration(self):
        """Test API key management with services"""
        # Create temporary key manager
        import tempfile
        with tempfile.NamedTemporaryFile(delete=False) as tmp:
            key_manager = LocalEncryptedKeyManager(key_file=tmp.name)
            
            # Set API keys
            await key_manager.set_key("routes", "test_routes_key")
            await key_manager.set_key("vertex_ai", "test_vertex_key")
            
            # Verify retrieval
            routes_key = await key_manager.get_key("routes")
            vertex_key = await key_manager.get_key("vertex_ai")
            
            assert routes_key == "test_routes_key"
            assert vertex_key == "test_vertex_key"
            
            # Clean up
            os.unlink(tmp.name)
    
    @pytest.mark.asyncio
    async def test_dashboard_metrics_collection(self, routes_service, vertex_service):
        """Test metrics collection for dashboard"""
        # Simulate some activity
        routes_service.metrics = {
            "total_requests": 100,
            "successful_requests": 95,
            "failed_requests": 5,
            "cache_hits": 30
        }
        
        vertex_service.metrics = {
            "total_predictions": 50,
            "successful_predictions": 48,
            "failed_predictions": 2,
            "cache_hits": 15
        }
        
        # Mock monitoring components
        for service in [routes_service, vertex_service]:
            service.circuit_breaker.get_status = Mock(
                return_value={"state": "CLOSED"}
            )
            service.rate_limiter.get_current_usage = AsyncMock(
                return_value={"available": True}
            )
            service.cost_monitor.get_api_usage = AsyncMock(
                return_value={"daily_cost": 25.00}
            )
        
        # Collect metrics
        routes_metrics = await routes_service.get_route_metrics()
        vertex_metrics = await vertex_service.get_prediction_metrics()
        
        # Verify metrics structure
        assert routes_metrics["monitoring_stats"]["success_rate"] == 95.0
        assert vertex_metrics["monitoring_stats"]["success_rate"] == 96.0
    
    @pytest.mark.asyncio
    async def test_graceful_degradation(self, routes_service):
        """Test graceful degradation when components fail"""
        # Simulate Redis failure
        routes_service.cache.redis_client.get = AsyncMock(
            side_effect=redis.ConnectionError("Redis down")
        )
        routes_service.rate_limiter.redis_client.incr = AsyncMock(
            side_effect=redis.ConnectionError("Redis down")
        )
        
        # Service should still work with mocks
        with patch.dict(os.environ, {"DEVELOPMENT_MODE": "development"}):
            result = await routes_service.calculate_route(
                origin="25.033,121.565",
                destination="25.047,121.517"
            )
            
            # Should get mock response
            assert "routes" in result
            assert len(result["routes"]) > 0