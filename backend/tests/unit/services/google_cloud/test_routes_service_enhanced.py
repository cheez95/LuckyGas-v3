"""
Unit tests for Enhanced Google Routes Service
"""

import json
from datetime import datetime
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest

from app.services.google_cloud.monitoring.circuit_breaker import CircuitState
from app.services.google_cloud.routes_service_enhanced import (
    EnhancedGoogleRoutesService,
)


class TestEnhancedGoogleRoutesService:
    """Test cases for EnhancedGoogleRoutesService"""

    @pytest.fixture
    def mock_dependencies(self):
        """Mock all dependencies"""
        # Create mock instances
        mock_rate_limiter = Mock()
        mock_rate_limiter.check_rate_limit = AsyncMock(return_value=(True, None))
        mock_rate_limiter.get_usage_stats = AsyncMock(
            return_value={
                "calls": 10,
                "limit": 100,
                "reset_time": "2024-01-01T00:00:00",
            }
        )

        mock_cost_monitor = Mock()
        mock_cost_monitor.enforce_budget_limit = AsyncMock(return_value=True)
        mock_cost_monitor.record_api_call = AsyncMock()
        mock_cost_monitor.get_cost_report = AsyncMock(
            return_value={
                "total_cost": 10.0,
                "total_calls": 100,
                "budget_percentage": 10.0,
            }
        )

        mock_cache = Mock()
        mock_cache.get = AsyncMock(return_value=None)
        mock_cache.set = AsyncMock()
        mock_cache.get_stats = AsyncMock(
            return_value={"hits": 50, "misses": 50, "hit_rate": 0.5}
        )

        mock_api_key_manager = Mock()
        mock_api_key_manager.get_key = AsyncMock(return_value="test_api_key")
        mock_api_key_manager.set_key = AsyncMock()

        mock_circuit_breaker = Mock()
        mock_circuit_breaker.is_open = False

        async def mock_circuit_breaker_call(func, *args, **kwargs):
            return await func(*args, **kwargs)

        mock_circuit_breaker.call = AsyncMock(side_effect=mock_circuit_breaker_call)
        mock_circuit_breaker.get_state = Mock(
            return_value={"state": "closed", "failures": 0}
        )

        mock_circuit_manager = Mock()
        mock_circuit_manager.get_breaker = AsyncMock(return_value=mock_circuit_breaker)

        # Create a custom exception class that accepts keyword arguments
        class MockGoogleAPIError(Exception):
            def __init__(self, message="", **kwargs):
                super().__init__(message)
                self.message = message
                for k, v in kwargs.items():
                    setattr(self, k, v)

        # Mock GoogleAPIErrorHandler to execute the function
        mock_error_handler = Mock()

        async def mock_handle_with_retry(func, *args, **kwargs):
            return await func()

        mock_error_handler.handle_with_retry = AsyncMock(
            side_effect=mock_handle_with_retry
        )

        with patch.multiple(
            "app.services.google_cloud.routes_service_enhanced",
            get_api_key_manager=AsyncMock(return_value=mock_api_key_manager),
            get_rate_limiter=AsyncMock(return_value=mock_rate_limiter),
            get_cost_monitor=AsyncMock(return_value=mock_cost_monitor),
            get_api_cache=AsyncMock(return_value=mock_cache),
            circuit_manager=mock_circuit_manager,
            GoogleAPIErrorHandler=mock_error_handler,
            GoogleAPIError=MockGoogleAPIError,
        ) as mocks:
            mocks["mock_rate_limiter"] = mock_rate_limiter
            mocks["mock_cost_monitor"] = mock_cost_monitor
            mocks["mock_cache"] = mock_cache
            mocks["mock_api_key_manager"] = mock_api_key_manager
            mocks["mock_circuit_breaker"] = mock_circuit_breaker
            yield mocks

    @pytest.fixture
    def service(self, mock_dependencies):
        """Create an EnhancedGoogleRoutesService instance"""
        service = EnhancedGoogleRoutesService()
        # Mark as already initialized to avoid async init in tests
        service._initialized = True
        service._rate_limiter = mock_dependencies["mock_rate_limiter"]
        service._cost_monitor = mock_dependencies["mock_cost_monitor"]
        service._cache = mock_dependencies["mock_cache"]
        service._api_key_manager = mock_dependencies["mock_api_key_manager"]
        service._circuit_breaker = mock_dependencies["mock_circuit_breaker"]
        return service

    @pytest.mark.asyncio
    async def test_initialization(self, service):
        """Test service initialization"""
        assert service._rate_limiter is not None
        assert service._cost_monitor is not None
        assert service._circuit_breaker is not None
        assert service._cache is not None
        assert service._api_key_manager is not None
        assert service._initialized is True

    @pytest.mark.asyncio
    async def test_optimize_route_with_cache_hit(self, service, mock_dependencies):
        """Test optimize_route with cache hit"""
        # Mock cache hit
        cached_result = {
            "optimized_route": [{"lat": 25.033, "lng": 121.565}],
            "total_distance": 1000,
            "total_duration": 120,
            "cached": True,
        }
        service._cache.get = AsyncMock(return_value=cached_result)

        # Call optimize_route
        result = await service.optimize_route(
            depot=(25.033, 121.565), stops=[{"lat": 25.047, "lng": 121.517}]
        )

        # Verify cache was used
        assert result == cached_result
        service._cache.get.assert_called_once()

    @pytest.mark.asyncio
    async def test_optimize_route_without_api_key(self, service, mock_dependencies):
        """Test optimize_route when API key is not available"""
        # Mock no API key
        service._api_key_manager.get_key = AsyncMock(return_value=None)
        service._cache.get = AsyncMock(return_value=None)

        # Mock gcp_config to have no API key
        mock_config = Mock()
        mock_config.maps_api_key = None
        service.gcp_config = mock_config

        # Call optimize_route
        result = await service.optimize_route(
            depot=(25.033, 121.565), stops=[{"lat": 25.047, "lng": 121.517}]
        )

        # Verify unoptimized route was returned
        assert "stops" in result
        assert result["optimized"] is False
        assert len(result["stops"]) == 1
        assert result["stops"][0]["lat"] == 25.047

    @pytest.mark.asyncio
    async def test_optimize_route_rate_limit_exceeded(self, service, mock_dependencies):
        """Test optimize_route when rate limit is exceeded"""
        # Setup mocks
        service._cache.get = AsyncMock(return_value=None)
        service._rate_limiter.check_rate_limit = AsyncMock(return_value=(False, 1.0))

        # Call optimize_route should raise exception
        with pytest.raises(Exception) as exc_info:
            await service.optimize_route(
                depot=(25.033, 121.565), stops=[{"lat": 25.047, "lng": 121.517}]
            )

        # Verify rate limit error
        assert "Rate limit exceeded" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_optimize_route_cost_budget_exceeded(
        self, service, mock_dependencies
    ):
        """Test optimize_route when cost budget is exceeded"""
        # Setup mocks
        service._cache.get = AsyncMock(return_value=None)
        service._rate_limiter.check_rate_limit = AsyncMock(return_value=(True, None))
        service._cost_monitor.enforce_budget_limit = AsyncMock(return_value=False)

        # Call optimize_route should raise exception
        with pytest.raises(Exception) as exc_info:
            await service.optimize_route(
                depot=(25.033, 121.565), stops=[{"lat": 25.047, "lng": 121.517}]
            )

        # Verify cost budget error
        assert "Cost budget exceeded" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_optimize_route_circuit_breaker_open(
        self, service, mock_dependencies
    ):
        """Test optimize_route when circuit breaker is open"""
        # Setup mocks
        service._cache.get = AsyncMock(return_value=None)
        service._rate_limiter.check_rate_limit = AsyncMock(return_value=(True, None))
        service._cost_monitor.enforce_budget_limit = AsyncMock(return_value=True)
        service._circuit_breaker.is_open = True

        # Mock circuit breaker to raise exception when open
        async def raise_error(func, *args, **kwargs):
            raise Exception("Circuit breaker is open")

        service._circuit_breaker.call = AsyncMock(side_effect=raise_error)

        # Call optimize_route - it should catch the exception and return unoptimized route
        result = await service.optimize_route(
            depot=(25.033, 121.565), stops=[{"lat": 25.047, "lng": 121.517}]
        )

        # Verify unoptimized route was returned
        assert "stops" in result
        assert result["optimized"] is False
        assert len(result["stops"]) == 1
        assert result["stops"][0]["lat"] == 25.047

    @pytest.mark.asyncio
    async def test_optimize_route_success_with_caching(
        self, service, mock_dependencies
    ):
        """Test successful optimize_route with result caching"""
        # Setup mocks for successful flow
        service._cache.get = AsyncMock(return_value=None)
        service._rate_limiter.check_rate_limit = AsyncMock(return_value=(True, None))
        service._cost_monitor.enforce_budget_limit = AsyncMock(return_value=True)
        service._circuit_breaker.is_open = False

        async def mock_circuit_breaker_call(func, *args, **kwargs):
            return await func(*args, **kwargs)

        service._circuit_breaker.call = AsyncMock(side_effect=mock_circuit_breaker_call)
        service._cache.set = AsyncMock(return_value=True)
        service._cost_monitor.record_api_call = AsyncMock()

        # Mock the HTTP request
        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.text = AsyncMock(
            return_value=json.dumps(
                {"routes": [{"polyline": {"encodedPolyline": "test"}}]}
            )
        )

        with patch("aiohttp.ClientSession") as mock_session_class:
            # Create the session mock with proper async context manager behavior
            mock_session = MagicMock()
            mock_session.__aenter__ = AsyncMock(return_value=mock_session)
            mock_session.__aexit__ = AsyncMock(return_value=None)
            mock_session_class.return_value = mock_session

            # Create a proper async context manager for post
            mock_post_cm = MagicMock()
            mock_post_cm.__aenter__ = AsyncMock(return_value=mock_response)
            mock_post_cm.__aexit__ = AsyncMock(return_value=None)
            mock_session.post = MagicMock(return_value=mock_post_cm)

            # Call optimize_route
            result = await service.optimize_route(
                depot=(25.033, 121.565), stops=[{"lat": 25.047, "lng": 121.517}]
            )

            # Verify success flow
            assert "stops" in result
            assert result["optimized"] is True
            service._cache.set.assert_called_once()
            service._cost_monitor.record_api_call.assert_called_once()

    @pytest.mark.asyncio
    async def test_optimize_multiple_routes(self, service, mock_dependencies):
        """Test optimize_multiple_routes with multiple drivers"""
        # Setup mocks
        service._cache.get = AsyncMock(return_value=None)
        service._rate_limiter.check_rate_limit = AsyncMock(return_value=(True, None))
        service._cost_monitor.enforce_budget_limit = AsyncMock(return_value=True)

        async def mock_circuit_breaker_call(func, *args, **kwargs):
            return await func(*args, **kwargs)

        service._circuit_breaker.call = AsyncMock(side_effect=mock_circuit_breaker_call)

        # Mock OR-Tools optimizer
        # Create mock VRPStop objects
        from app.services.optimization.ortools_optimizer import VRPStop

        mock_stops = []
        for i in range(5):
            stop = VRPStop(
                order_id=i + 1,
                customer_id=i + 1,
                customer_name=f"Customer {i+1}",
                address=f"Address {i+1}",
                latitude=25.033 + i * 0.001,
                longitude=121.565 + i * 0.001,
                demand={"20kg": 1},
                time_window=(480, 1080),  # 8am to 6pm
                service_time=10,
            )
            # Add estimated_arrival as an attribute (OR-Tools would set this)
            stop.estimated_arrival = 480 + 30 * i  # Start at 8am, 30 minutes per stop
            mock_stops.append(stop)

        mock_optimizer_result = {
            0: mock_stops[:3],  # First vehicle gets 3 stops
            1: mock_stops[3:],  # Second vehicle gets 2 stops
        }

        with patch(
            "app.services.google_cloud.routes_service_enhanced.ortools_optimizer.optimize",
            return_value=mock_optimizer_result,
        ):
            # Create mock Order objects
            from datetime import datetime

            from app.models.customer import Customer
            from app.models.order import Order

            orders = []
            for i in range(5):
                customer = Customer(
                    id=i + 1,
                    short_name=f"Customer {i+1}",
                    address=f"Address {i+1}",
                    latitude=25.033 + i * 0.001,
                    longitude=121.565 + i * 0.001,
                )
                order = Order(
                    id=i + 1,
                    customer_id=i + 1,
                    customer=customer,
                    delivery_address=f"Address {i+1}",
                    qty_20kg=1,
                )
                orders.append(order)

            # Create mock drivers
            drivers = [{"id": 1, "name": "Driver 1"}, {"id": 2, "name": "Driver 2"}]

            # Mock the Google directions API call
            service._get_google_directions_enhanced = AsyncMock(
                return_value={
                    "distance": 10,
                    "duration": 30,
                    "polyline": "test_polyline",
                }
            )

            # Call optimize_multiple_routes
            result = await service.optimize_multiple_routes(
                orders=orders, drivers=drivers, date=datetime.now()
            )

            # Verify - result is a list of route dictionaries
            assert isinstance(result, list)
            assert len(result) == 2  # Two routes for two vehicles

            # Check first route
            assert result[0]["driver_id"] == 1
            assert result[0]["driver_name"] == "Driver 1"
            assert len(result[0]["stops"]) == 3
            assert result[0]["optimized"] is True

            # Check second route
            assert result[1]["driver_id"] == 2
            assert result[1]["driver_name"] == "Driver 2"
            assert len(result[1]["stops"]) == 2
            assert result[1]["optimized"] is True

    @pytest.mark.asyncio
    async def test_get_service_health(self, service, mock_dependencies):
        """Test get_service_health method"""
        # Perform health check
        health = await service.get_service_health()

        # Verify
        assert health["service"] == "Google Routes API"
        assert health["status"] == "healthy"
        assert "components" in health
        assert "rate_limiter" in health["components"]
        assert "cost_monitor" in health["components"]
        assert "circuit_breaker" in health["components"]
        assert "cache" in health["components"]
        assert "api_key" in health["components"]

    @pytest.mark.asyncio
    async def test_error_handling_with_retry(self, service, mock_dependencies):
        """Test error handling and retry logic"""
        # Setup mocks
        service._cache.get = AsyncMock(return_value=None)
        service._rate_limiter.check_rate_limit = AsyncMock(return_value=(True, None))
        service._cost_monitor.enforce_budget_limit = AsyncMock(return_value=True)
        service._circuit_breaker.is_open = False

        # Mock GoogleAPIErrorHandler to handle retries
        mock_error_handler = Mock()
        mock_error_handler.handle_with_retry = AsyncMock(
            side_effect=Exception("API Error after retries")
        )

        with patch(
            "app.services.google_cloud.routes_service_enhanced.GoogleAPIErrorHandler",
            mock_error_handler,
        ):
            # Call should return unoptimized route after error
            result = await service.optimize_route(
                depot=(25.033, 121.565), stops=[{"lat": 25.047, "lng": 121.517}]
            )

            # Verify unoptimized route was returned as fallback
            assert "stops" in result
            assert result["optimized"] is False
            assert len(result["stops"]) == 1
            assert result["stops"][0]["lat"] == 25.047

    @pytest.mark.asyncio
    async def test_concurrent_requests(self, service, mock_dependencies):
        """Test handling concurrent requests"""
        import asyncio

        # Setup mocks for concurrent access
        service._cache.get = AsyncMock(return_value=None)
        service._rate_limiter.check_rate_limit = AsyncMock(return_value=(True, None))
        service._cost_monitor.enforce_budget_limit = AsyncMock(return_value=True)

        async def mock_circuit_breaker_call(func, *args, **kwargs):
            return await func(*args, **kwargs)

        service._circuit_breaker.call = AsyncMock(side_effect=mock_circuit_breaker_call)
        service._cache.set = AsyncMock(return_value=True)
        service._cost_monitor.record_api_call = AsyncMock()

        # Mock successful response
        mock_response = Mock()
        mock_response.status = 200
        mock_response.json = AsyncMock(
            return_value={"routes": [{"polyline": {"encodedPolyline": "test"}}]}
        )

        with patch("aiohttp.ClientSession") as mock_session_class:
            mock_session = AsyncMock()
            mock_session_class.return_value.__aenter__.return_value = mock_session
            mock_session.post.return_value.__aenter__.return_value = mock_response

            # Make concurrent requests
            tasks = [
                service.optimize_route(
                    depot=(25.033, 121.565),
                    stops=[{"lat": 25.047 + i * 0.001, "lng": 121.517}],
                )
                for i in range(5)
            ]

            results = await asyncio.gather(*tasks)

            # Verify all completed
            assert len(results) == 5
            for result in results:
                assert "stops" in result
                assert "optimized" in result
