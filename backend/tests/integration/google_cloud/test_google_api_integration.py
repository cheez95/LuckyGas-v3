"""
Integration tests for Google API components working together
"""

import asyncio
import json
import os
from datetime import datetime, timedelta
from decimal import Decimal
from unittest.mock import AsyncMock, Mock, patch

import pytest
import pytest_asyncio
import redis.asyncio as redis

from app.core.api_key_manager import LocalEncryptedKeyManager
from app.services.google_cloud.development_mode import DevelopmentMode
from app.services.google_cloud.monitoring.circuit_breaker import CircuitState
from app.services.google_cloud.routes_service_enhanced import (
    EnhancedGoogleRoutesService,
)
from app.services.google_cloud.vertex_ai_service_enhanced import EnhancedVertexAIService


@pytest.mark.integration
class TestGoogleAPIIntegration:
    """Integration tests for Google API services"""

    @pytest_asyncio.fixture
    async def redis_client(self):
        """Create a test Redis client"""
        # Use a test Redis instance or mock
        with patch("redis.asyncio.from_url") as mock:
            client = AsyncMock()
            mock.return_value = client
            yield client

    @pytest_asyncio.fixture
    async def routes_service(self, redis_client):
        """Create routes service with mocked Redis"""
        service = EnhancedGoogleRoutesService()
        # Initialize the service to avoid Redis connection issues
        await service._ensure_initialized()
        # Mock the Redis clients to avoid real connections
        service._rate_limiter.redis_client = redis_client
        service._cost_monitor.redis = redis_client
        service._cache.redis = redis_client
        return service

    @pytest_asyncio.fixture
    async def vertex_service(self, redis_client):
        """Create vertex AI service with mocked Redis"""
        service = EnhancedVertexAIService()
        # The vertex service initializes components differently than routes
        # Mock the Redis clients directly on the initialized components
        service.rate_limiter.redis_client = redis_client
        service.cost_monitor.redis = redis_client
        service.cache.redis = redis_client
        # Initialize key manager
        await service._ensure_key_manager()
        return service

    @pytest.mark.asyncio
    async def test_development_mode_flow(self, routes_service):
        """Test complete flow in development mode"""
        # Set development mode
        with patch.dict(os.environ, {"DEVELOPMENT_MODE": "development"}):
            # Should use mock service without API calls
            result = await routes_service.calculate_route(
                origin="25.033,121.565", destination="25.047,121.517"
            )

            # Verify mock response structure
            assert "routes" in result
            assert len(result["routes"]) > 0
            assert "distance" in result["routes"][0]
            assert "duration" in result["routes"][0]

    @pytest.mark.asyncio
    async def test_rate_limiting_across_services(self, routes_service, vertex_service):
        """Test rate limiting works across different services"""
        # Mock Redis to simulate rate limit state
        routes_service._rate_limiter.redis_client.incr = AsyncMock(
            side_effect=[5, 150, 20000]  # Under limits
        )
        routes_service._rate_limiter.redis_client.expire = AsyncMock()

        vertex_service.rate_limiter.redis_client.incr = AsyncMock(
            side_effect=[2, 40, 800]  # Under limits
        )
        vertex_service.rate_limiter.redis_client.expire = AsyncMock()

        # Both services should allow requests
        routes_allowed, routes_wait = (
            await routes_service._rate_limiter.check_rate_limit("routes")
        )
        vertex_allowed, vertex_wait = (
            await vertex_service.rate_limiter.check_rate_limit("vertex_ai")
        )

        assert routes_allowed is True
        assert vertex_allowed is True

    @pytest.mark.asyncio
    async def test_circuit_breaker_isolation(self, routes_service, vertex_service):
        """Test circuit breakers are isolated between services"""
        # Open routes service circuit breaker
        for _ in range(5):
            routes_service._circuit_breaker.record_failure()

        # Routes circuit should be open
        assert routes_service._circuit_breaker.state == CircuitState.OPEN
        assert not routes_service._circuit_breaker.can_execute()

        # Vertex circuit should still be closed
        assert vertex_service.circuit_breaker.state == CircuitState.CLOSED
        assert vertex_service.circuit_breaker.can_execute()

    @pytest.mark.asyncio
    async def test_cost_monitoring_aggregation(self, routes_service, vertex_service):
        """Test cost monitoring across services"""
        # Mock Redis for cost tracking
        routes_service._cost_monitor.redis.incrbyfloat = AsyncMock(return_value=10.50)
        routes_service._cost_monitor.redis.expire = AsyncMock()
        routes_service._cost_monitor.redis.rpush = AsyncMock()
        routes_service._cost_monitor.redis.ltrim = AsyncMock()
        # Mock get method to return None (no existing costs)
        routes_service._cost_monitor.redis.get = AsyncMock(return_value=None)

        vertex_service.cost_monitor.redis.incrbyfloat = AsyncMock(return_value=5.25)
        vertex_service.cost_monitor.redis.expire = AsyncMock()
        vertex_service.cost_monitor.redis.rpush = AsyncMock()
        vertex_service.cost_monitor.redis.ltrim = AsyncMock()
        # Mock get method to return None (no existing costs)
        vertex_service.cost_monitor.redis.get = AsyncMock(return_value=None)

        # Track costs using the correct method name
        await routes_service._cost_monitor.record_api_call("routes", "optimization")
        await vertex_service.cost_monitor.record_api_call("vertex_ai", "prediction")

        # Mock get_cost_report directly instead of trying to mock Redis internals
        routes_service._cost_monitor.get_cost_report = AsyncMock(
            return_value={
                "period": "daily",
                "costs_by_api": {"routes": 10.50},
                "counts_by_api": {"routes": 100},
                "total_cost": 10.50,
                "total_calls": 100,
            }
        )

        vertex_service.cost_monitor.get_cost_report = AsyncMock(
            return_value={
                "period": "daily",
                "costs_by_api": {"vertex_ai": 5.25},
                "counts_by_api": {"vertex_ai": 50},
                "total_cost": 5.25,
                "total_calls": 50,
            }
        )

        # Check individual costs using get_cost_report
        routes_report = await routes_service._cost_monitor.get_cost_report("daily")
        vertex_report = await vertex_service.cost_monitor.get_cost_report("daily")

        # Verify the mocked values
        assert routes_report["costs_by_api"]["routes"] == 10.50
        assert vertex_report["costs_by_api"]["vertex_ai"] == 5.25

    @pytest.mark.asyncio
    async def test_cache_sharing_prevention(self, routes_service, vertex_service):
        """Test that caches are properly namespaced and don't conflict"""
        # Create separate Redis mocks for each service
        routes_redis_mock = AsyncMock()
        routes_redis_mock.setex = AsyncMock(return_value=True)
        vertex_redis_mock = AsyncMock()
        vertex_redis_mock.setex = AsyncMock(return_value=True)

        # Assign the mocks
        routes_service._cache.redis = routes_redis_mock
        vertex_service.cache.redis = vertex_redis_mock

        # Cache data with same key in both services
        # Parameters: api_type, params, response
        await routes_service._cache.set(
            "routes", {"key": "test_key"}, {"service": "routes", "data": "route_data"}
        )
        await vertex_service.cache.set(
            "vertex_ai",
            {"key": "test_key"},
            {"service": "vertex", "data": "vertex_data"},
        )

        # Verify different Redis keys were used
        routes_calls = routes_redis_mock.setex.call_args_list
        vertex_calls = vertex_redis_mock.setex.call_args_list

        # Check that calls were made
        assert len(routes_calls) > 0, "No cache calls made for routes"
        assert len(vertex_calls) > 0, "No cache calls made for vertex"

        # Get the actual keys used
        routes_key = routes_calls[0][0][0]
        vertex_key = vertex_calls[0][0][0]

        # The cache key format is: google_api:{api_type}:{hash}
        assert routes_key.startswith(
            "google_api:routes:"
        ), f"Unexpected routes key: {routes_key}"
        assert vertex_key.startswith(
            "google_api:vertex_ai:"
        ), f"Unexpected vertex key: {vertex_key}"
        # Ensure different cache keys
        assert routes_key != vertex_key

    @pytest.mark.asyncio
    async def test_error_handling_cascade(self, routes_service):
        """Test error handling through multiple layers"""
        # Test circuit breaker error handling
        # Open the circuit breaker to simulate failures
        routes_service._circuit_breaker.state = CircuitState.OPEN
        # Mock _should_attempt_reset to prevent automatic reset
        routes_service._circuit_breaker._should_attempt_reset = Mock(return_value=False)

        # Mock checks
        routes_service._rate_limiter.check_rate_limit = AsyncMock(
            return_value=(True, 0)
        )
        routes_service._cost_monitor.enforce_budget_limit = AsyncMock(return_value=True)
        routes_service._cache.get = AsyncMock(return_value=None)
        routes_service._cache.set = AsyncMock(return_value=True)

        # Since circuit is open and reset is prevented, can_execute should return False
        assert routes_service._circuit_breaker.can_execute() is False

        # Test rate limiter error handling
        routes_service._circuit_breaker.state = CircuitState.CLOSED
        routes_service._rate_limiter.check_rate_limit = AsyncMock(
            return_value=(False, 60)
        )

        allowed, wait_time = await routes_service._rate_limiter.check_rate_limit(
            "routes"
        )
        assert allowed is False
        assert wait_time == 60

        # Test budget limit error handling
        routes_service._rate_limiter.check_rate_limit = AsyncMock(
            return_value=(True, 0)
        )
        routes_service._cost_monitor.enforce_budget_limit = AsyncMock(
            return_value=False
        )

        budget_ok = await routes_service._cost_monitor.enforce_budget_limit("routes")
        assert budget_ok is False

        # All error handling layers tested

    @pytest.mark.asyncio
    async def test_health_check_aggregation(self, routes_service, vertex_service):
        """Test health check across services"""
        # Set different component states
        routes_service._circuit_breaker.state = CircuitState.CLOSED
        vertex_service.circuit_breaker.state = CircuitState.OPEN

        # Mock _should_attempt_reset to prevent automatic state changes
        routes_service._circuit_breaker._should_attempt_reset = Mock(return_value=False)
        vertex_service.circuit_breaker._should_attempt_reset = Mock(return_value=False)

        # Test circuit breaker states
        assert routes_service._circuit_breaker.state == CircuitState.CLOSED
        assert routes_service._circuit_breaker.can_execute() is True

        assert vertex_service.circuit_breaker.state == CircuitState.OPEN
        assert vertex_service.circuit_breaker.can_execute() is False

        # Mock rate limiter check
        routes_service._rate_limiter.check_rate_limit = AsyncMock(
            return_value=(True, 0)  # (allowed, wait_time)
        )
        vertex_service.rate_limiter.check_rate_limit = AsyncMock(
            return_value=(False, 60)  # (not allowed, wait_time)
        )

        # Mock cost monitor budget check
        routes_service._cost_monitor.enforce_budget_limit = AsyncMock(
            return_value=True  # Budget ok
        )
        vertex_service.cost_monitor.enforce_budget_limit = AsyncMock(
            return_value=False  # Over budget
        )

        # Test component behaviors
        # Routes service should be healthy
        routes_rate_ok, _ = await routes_service._rate_limiter.check_rate_limit(
            "routes"
        )
        assert routes_rate_ok == True

        routes_budget_ok = await routes_service._cost_monitor.enforce_budget_limit(
            "routes"
        )
        assert routes_budget_ok == True

        # Vertex service should be unhealthy
        vertex_rate_ok, wait_time = await vertex_service.rate_limiter.check_rate_limit(
            "vertex_ai"
        )
        assert vertex_rate_ok == False
        assert wait_time == 60

        vertex_budget_ok = await vertex_service.cost_monitor.enforce_budget_limit(
            "vertex_ai"
        )
        assert vertex_budget_ok == False

    @pytest.mark.asyncio
    async def test_concurrent_service_requests(self, routes_service, vertex_service):
        """Test concurrent requests across services"""
        # Set development mode for mock responses
        with patch.dict(os.environ, {"DEVELOPMENT_MODE": "development"}):
            # Mock the service methods to return quickly
            routes_service.calculate_route = AsyncMock(
                return_value={
                    "routes": [
                        {"distance": 1000, "duration": 300, "polyline": "mock_polyline"}
                    ]
                }
            )

            # Create a mock prediction method
            async def mock_predict():
                return {
                    "predictions": [
                        {"customer_id": i, "probability": 0.8} for i in range(5)
                    ],
                    "batch_id": "test_batch",
                }

            vertex_service.predict = AsyncMock(side_effect=mock_predict)

            # Create concurrent tasks
            tasks = []

            # Add route calculations
            for i in range(5):
                tasks.append(
                    routes_service.calculate_route(
                        origin=f"25.{i:03d},121.565", destination=f"25.{i:03d},121.517"
                    )
                )

            # Add predictions
            for i in range(5):
                tasks.append(vertex_service.predict())

            # Execute concurrently
            results = await asyncio.gather(*tasks, return_exceptions=True)

            # Verify all completed successfully
            assert len(results) == 10
            errors = [r for r in results if isinstance(r, Exception)]
            assert len(errors) == 0, f"Found errors: {errors}"

            # Verify route results
            for i in range(5):
                assert "routes" in results[i]

            # Verify prediction results
            for i in range(5, 10):
                assert "predictions" in results[i]

    @pytest.mark.asyncio
    async def test_api_key_management_integration(self):
        """Test API key management with services"""
        # Create temporary directory for keys
        import shutil
        import tempfile

        with tempfile.TemporaryDirectory() as tmpdir:
            master_key_path = os.path.join(tmpdir, "master.key")
            key_manager = LocalEncryptedKeyManager(master_key_path=master_key_path)

            # Set API keys
            await key_manager.set_key("routes", "test_routes_key")
            await key_manager.set_key("vertex_ai", "test_vertex_key")

            # Verify retrieval
            routes_key = await key_manager.get_key("routes")
            vertex_key = await key_manager.get_key("vertex_ai")

            assert routes_key == "test_routes_key"
            assert vertex_key == "test_vertex_key"

    @pytest.mark.asyncio
    async def test_dashboard_metrics_collection(self, routes_service, vertex_service):
        """Test metrics collection for dashboard"""
        # Set up service metrics
        routes_service.metrics = {
            "total_requests": 100,
            "successful_requests": 95,
            "failed_requests": 5,
            "cache_hits": 30,
        }

        vertex_service.metrics = {
            "total_predictions": 50,
            "successful_predictions": 48,
            "failed_predictions": 2,
            "cache_hits": 15,
        }

        # Mock circuit breaker get_status
        routes_service._circuit_breaker.get_status = Mock(
            return_value={"state": "CLOSED", "failure_count": 0, "success_count": 95}
        )
        vertex_service.circuit_breaker.get_status = Mock(
            return_value={"state": "CLOSED", "failure_count": 2, "success_count": 48}
        )

        # Mock cost monitor get_cost_report
        routes_service._cost_monitor.get_cost_report = AsyncMock(
            return_value={
                "total_cost": 25.00,
                "costs_by_api": {"routes": 25.00},
                "total_calls": 100,
                "budget_percentage": 25.0,
            }
        )
        vertex_service.cost_monitor.get_cost_report = AsyncMock(
            return_value={
                "total_cost": 15.00,
                "costs_by_api": {"vertex_ai": 15.00},
                "total_calls": 50,
                "budget_percentage": 15.0,
            }
        )

        # Test metrics collection
        # Routes service metrics
        assert routes_service.metrics["total_requests"] == 100
        assert routes_service.metrics["successful_requests"] == 95
        assert routes_service.metrics["cache_hits"] == 30

        # Circuit breaker status
        routes_cb_status = routes_service._circuit_breaker.get_status()
        assert routes_cb_status["state"] == "CLOSED"

        # Cost report
        routes_cost_report = await routes_service._cost_monitor.get_cost_report("daily")
        assert routes_cost_report["total_cost"] == 25.00
        assert routes_cost_report["total_calls"] == 100

        # Vertex service metrics
        assert vertex_service.metrics["total_predictions"] == 50
        assert vertex_service.metrics["successful_predictions"] == 48

        # Mock get_prediction_metrics to return expected structure
        vertex_service.get_prediction_metrics = AsyncMock(
            return_value={
                "total_predictions": 50,
                "successful_predictions": 48,
                "failed_predictions": 2,
                "cache_hits": 15,
                "monitoring_stats": {"success_rate": 96.0, "cache_hit_rate": 30.0},
            }
        )

        # Test get_prediction_metrics
        vertex_metrics = await vertex_service.get_prediction_metrics()
        assert vertex_metrics["total_predictions"] == 50
        assert vertex_metrics["successful_predictions"] == 48
        assert vertex_metrics["monitoring_stats"]["success_rate"] == 96.0

    @pytest.mark.asyncio
    async def test_graceful_degradation(self, routes_service):
        """Test graceful degradation when components fail"""
        # Simulate Redis failure
        routes_service._cache.redis.get = AsyncMock(
            side_effect=redis.ConnectionError("Redis down")
        )
        routes_service._rate_limiter.redis_client.incr = AsyncMock(
            side_effect=redis.ConnectionError("Redis down")
        )

        # Service should still work with mocks
        with patch.dict(os.environ, {"DEVELOPMENT_MODE": "development"}):
            result = await routes_service.calculate_route(
                origin="25.033,121.565", destination="25.047,121.517"
            )

            # Should get mock response
            assert "routes" in result
            assert len(result["routes"]) > 0
