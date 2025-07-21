"""
Unit tests for Enhanced Google Routes Service
"""
import pytest
from unittest.mock import Mock, patch, AsyncMock, MagicMock
from datetime import datetime
from decimal import Decimal
import json

from app.services.google_cloud.routes_service_enhanced import EnhancedGoogleRoutesService
from app.services.google_cloud.monitoring.circuit_breaker import CircuitState


class TestEnhancedGoogleRoutesService:
    """Test cases for EnhancedGoogleRoutesService"""
    
    @pytest.fixture
    def mock_dependencies(self):
        """Mock all dependencies"""
        with patch.multiple(
            "app.services.google_cloud.routes_service_enhanced",
            GoogleAPIRateLimiter=Mock,
            GoogleAPICostMonitor=Mock,
            GoogleAPIErrorHandler=Mock,
            CircuitBreaker=Mock,
            GoogleAPICache=Mock,
            DevelopmentModeManager=Mock,
            MockGoogleRoutesService=Mock,
            get_api_key_manager=AsyncMock
        ) as mocks:
            yield mocks
    
    @pytest.fixture
    def service(self, mock_dependencies):
        """Create an EnhancedGoogleRoutesService instance"""
        return EnhancedGoogleRoutesService()
    
    @pytest.mark.asyncio
    async def test_initialization(self, service):
        """Test service initialization"""
        assert service.rate_limiter is not None
        assert service.cost_monitor is not None
        assert service.error_handler is not None
        assert service.circuit_breaker is not None
        assert service.cache is not None
        assert service.dev_mode_manager is not None
        assert service.mock_service is not None
        assert service.metrics["total_requests"] == 0
    
    @pytest.mark.asyncio
    async def test_calculate_route_with_cache_hit(self, service):
        """Test calculate_route with cache hit"""
        # Mock cache hit
        cached_result = {
            "routes": [{"distance": 1000, "duration": 120}],
            "cached": True
        }
        service.cache.get = AsyncMock(return_value=cached_result)
        
        # Call calculate_route
        result = await service.calculate_route(
            origin="25.033,121.565",
            destination="25.047,121.517"
        )
        
        # Verify cache was used
        assert result == cached_result
        assert service.metrics["cache_hits"] == 1
        service.cache.get.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_calculate_route_development_mode(self, service):
        """Test calculate_route in development mode"""
        # Mock development mode
        service.dev_mode_manager.detect_mode = AsyncMock(
            return_value=service.dev_mode_manager.development_mode.DEVELOPMENT
        )
        service.cache.get = AsyncMock(return_value=None)
        
        # Mock mock service response
        mock_response = {"routes": [{"distance": 2000, "duration": 240}]}
        service.mock_service.calculate_route = AsyncMock(return_value=mock_response)
        
        # Call calculate_route
        result = await service.calculate_route(
            origin="25.033,121.565",
            destination="25.047,121.517"
        )
        
        # Verify mock service was used
        assert result == mock_response
        service.mock_service.calculate_route.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_calculate_route_rate_limit_exceeded(self, service):
        """Test calculate_route when rate limit is exceeded"""
        # Setup mocks
        service.dev_mode_manager.detect_mode = AsyncMock(
            return_value=service.dev_mode_manager.development_mode.PRODUCTION
        )
        service.cache.get = AsyncMock(return_value=None)
        service.rate_limiter.check_limit = AsyncMock(return_value=False)
        
        # Mock fallback response
        mock_response = {"routes": [{"distance": 1500, "duration": 180}]}
        service.mock_service.calculate_route = AsyncMock(return_value=mock_response)
        
        # Call calculate_route
        result = await service.calculate_route(
            origin="25.033,121.565",
            destination="25.047,121.517"
        )
        
        # Verify fallback was used
        assert result == mock_response
        service.mock_service.calculate_route.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_calculate_route_cost_budget_exceeded(self, service):
        """Test calculate_route when cost budget is exceeded"""
        # Setup mocks
        service.dev_mode_manager.detect_mode = AsyncMock(
            return_value=service.dev_mode_manager.development_mode.PRODUCTION
        )
        service.cache.get = AsyncMock(return_value=None)
        service.rate_limiter.check_limit = AsyncMock(return_value=True)
        service.cost_monitor.check_budget = AsyncMock(return_value=False)
        
        # Mock fallback response
        mock_response = {"routes": [{"distance": 1500, "duration": 180}]}
        service.mock_service.calculate_route = AsyncMock(return_value=mock_response)
        
        # Call calculate_route
        result = await service.calculate_route(
            origin="25.033,121.565",
            destination="25.047,121.517"
        )
        
        # Verify fallback was used
        assert result == mock_response
    
    @pytest.mark.asyncio
    async def test_calculate_route_circuit_breaker_open(self, service):
        """Test calculate_route when circuit breaker is open"""
        # Setup mocks
        service.dev_mode_manager.detect_mode = AsyncMock(
            return_value=service.dev_mode_manager.development_mode.PRODUCTION
        )
        service.cache.get = AsyncMock(return_value=None)
        service.rate_limiter.check_limit = AsyncMock(return_value=True)
        service.cost_monitor.check_budget = AsyncMock(return_value=True)
        service.circuit_breaker.can_execute = Mock(return_value=False)
        
        # Mock fallback response
        mock_response = {"routes": [{"distance": 1500, "duration": 180}]}
        service.mock_service.calculate_route = AsyncMock(return_value=mock_response)
        
        # Call calculate_route
        result = await service.calculate_route(
            origin="25.033,121.565",
            destination="25.047,121.517"
        )
        
        # Verify fallback was used
        assert result == mock_response
    
    @pytest.mark.asyncio
    async def test_calculate_route_success_with_caching(self, service):
        """Test successful calculate_route with result caching"""
        # Setup mocks for successful flow
        service.dev_mode_manager.detect_mode = AsyncMock(
            return_value=service.dev_mode_manager.development_mode.PRODUCTION
        )
        service.cache.get = AsyncMock(return_value=None)
        service.rate_limiter.check_limit = AsyncMock(return_value=True)
        service.cost_monitor.check_budget = AsyncMock(return_value=True)
        service.circuit_breaker.can_execute = Mock(return_value=True)
        service.circuit_breaker.record_success = Mock()
        service.cache.set = AsyncMock(return_value=True)
        service.cost_monitor.track_cost = AsyncMock()
        
        # Mock parent class method
        parent_response = {"routes": [{"distance": 3000, "duration": 360}]}
        with patch.object(
            service.__class__.__bases__[0],
            'calculate_route',
            AsyncMock(return_value=parent_response)
        ):
            # Mock error handler
            service.error_handler.execute_with_retry = AsyncMock(
                side_effect=lambda func, **kwargs: func()
            )
            
            # Call calculate_route
            result = await service.calculate_route(
                origin="25.033,121.565",
                destination="25.047,121.517"
            )
            
            # Verify success flow
            assert result == parent_response
            assert service.metrics["total_requests"] == 1
            assert service.metrics["successful_requests"] == 1
            service.cache.set.assert_called_once()
            service.cost_monitor.track_cost.assert_called_once()
            service.circuit_breaker.record_success.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_optimize_route_with_multiple_stops(self, service):
        """Test optimize_route with multiple waypoints"""
        # Setup mocks
        service.dev_mode_manager.detect_mode = AsyncMock(
            return_value=service.dev_mode_manager.development_mode.PRODUCTION
        )
        service.cache.get = AsyncMock(return_value=None)
        service.rate_limiter.check_limit = AsyncMock(return_value=True)
        service.cost_monitor.check_budget = AsyncMock(return_value=True)
        service.circuit_breaker.can_execute = Mock(return_value=True)
        service.cache.set = AsyncMock(return_value=True)
        service.cost_monitor.track_cost = AsyncMock()
        
        # Mock waypoints
        waypoints = [
            {"lat": 25.033, "lng": 121.565},
            {"lat": 25.040, "lng": 121.550},
            {"lat": 25.047, "lng": 121.517}
        ]
        
        # Mock parent response
        parent_response = {
            "optimized_route": waypoints,
            "total_distance": 5000,
            "total_duration": 600
        }
        
        with patch.object(
            service.__class__.__bases__[0],
            'optimize_route',
            AsyncMock(return_value=parent_response)
        ):
            service.error_handler.execute_with_retry = AsyncMock(
                side_effect=lambda func, **kwargs: func()
            )
            
            # Call optimize_route
            result = await service.optimize_route(waypoints)
            
            # Verify
            assert result == parent_response
            # Cost should be based on number of waypoints
            cost_call = service.cost_monitor.track_cost.call_args
            assert float(cost_call[0][2]) == 0.001 * len(waypoints)
    
    @pytest.mark.asyncio
    async def test_get_route_metrics(self, service):
        """Test getting enhanced route metrics"""
        # Setup service metrics
        service.metrics = {
            "total_requests": 100,
            "successful_requests": 95,
            "failed_requests": 5,
            "cache_hits": 30,
            "total_optimizations": 20,
            "successful_optimizations": 18
        }
        
        # Mock monitoring components
        service.circuit_breaker.get_status = Mock(return_value={
            "state": "CLOSED",
            "failure_count": 2
        })
        service.rate_limiter.get_current_usage = AsyncMock(return_value={
            "available": True,
            "current": {"per_second": 5}
        })
        service.cost_monitor.get_api_usage = AsyncMock(return_value={
            "daily_cost": 45.50,
            "over_budget": False
        })
        
        # Mock parent metrics
        with patch.object(
            service.__class__.__bases__[0],
            'get_route_metrics',
            AsyncMock(return_value={"base_metric": "value"})
        ):
            # Get metrics
            metrics = await service.get_route_metrics()
            
            # Verify enhanced metrics
            assert metrics["base_metric"] == "value"
            assert metrics["monitoring_stats"]["total_requests"] == 100
            assert metrics["monitoring_stats"]["success_rate"] == 95.0
            assert metrics["monitoring_stats"]["cache_hit_rate"] == 30.0
            assert metrics["circuit_breaker_status"]["state"] == "CLOSED"
            assert metrics["rate_limit_status"]["available"] is True
            assert metrics["cost_status"]["daily_cost"] == 45.50
    
    @pytest.mark.asyncio
    async def test_health_check(self, service):
        """Test comprehensive health check"""
        # Mock component statuses
        service.circuit_breaker.get_status = Mock(return_value={
            "state": "CLOSED",
            "failure_count": 0
        })
        service.rate_limiter.get_current_usage = AsyncMock(return_value={
            "available": True,
            "current": {"per_second": 3}
        })
        service.cost_monitor.get_api_usage = AsyncMock(return_value={
            "daily_cost": 25.00,
            "over_budget": False
        })
        
        # Perform health check
        health = await service.health_check()
        
        # Verify
        assert health["service"] == "google_routes"
        assert health["status"] == "healthy"
        assert health["components"]["circuit_breaker"]["status"] == "healthy"
        assert health["components"]["rate_limiter"]["status"] == "healthy"
        assert health["components"]["cost_monitor"]["status"] == "healthy"
        assert len(health["components"]) >= 3
    
    @pytest.mark.asyncio
    async def test_error_handling_with_retry(self, service):
        """Test error handling and retry logic"""
        # Setup mocks
        service.dev_mode_manager.detect_mode = AsyncMock(
            return_value=service.dev_mode_manager.development_mode.PRODUCTION
        )
        service.cache.get = AsyncMock(return_value=None)
        service.rate_limiter.check_limit = AsyncMock(return_value=True)
        service.cost_monitor.check_budget = AsyncMock(return_value=True)
        service.circuit_breaker.can_execute = Mock(return_value=True)
        service.circuit_breaker.record_failure = Mock()
        
        # Simulate error in parent method
        with patch.object(
            service.__class__.__bases__[0],
            'calculate_route',
            AsyncMock(side_effect=Exception("API Error"))
        ):
            # Mock error handler to propagate error
            service.error_handler.execute_with_retry = AsyncMock(
                side_effect=Exception("API Error")
            )
            
            # Mock fallback
            mock_response = {"routes": [{"distance": 1000, "duration": 120}]}
            service.mock_service.calculate_route = AsyncMock(return_value=mock_response)
            
            # Call should fall back to mock
            result = await service.calculate_route(
                origin="25.033,121.565",
                destination="25.047,121.517"
            )
            
            # Verify fallback and failure recording
            assert result == mock_response
            assert service.metrics["failed_requests"] == 1
            service.circuit_breaker.record_failure.assert_called()
    
    @pytest.mark.asyncio
    async def test_concurrent_requests(self, service):
        """Test handling concurrent requests"""
        import asyncio
        
        # Setup mocks for concurrent access
        service.dev_mode_manager.detect_mode = AsyncMock(
            return_value=service.dev_mode_manager.development_mode.PRODUCTION
        )
        service.cache.get = AsyncMock(return_value=None)
        service.rate_limiter.check_limit = AsyncMock(return_value=True)
        service.cost_monitor.check_budget = AsyncMock(return_value=True)
        service.circuit_breaker.can_execute = Mock(return_value=True)
        service.cache.set = AsyncMock(return_value=True)
        service.cost_monitor.track_cost = AsyncMock()
        
        # Mock parent response
        async def mock_calculate(*args, **kwargs):
            await asyncio.sleep(0.01)  # Simulate API delay
            return {"routes": [{"distance": 1000, "duration": 120}]}
        
        with patch.object(
            service.__class__.__bases__[0],
            'calculate_route',
            mock_calculate
        ):
            service.error_handler.execute_with_retry = AsyncMock(
                side_effect=lambda func, **kwargs: func()
            )
            
            # Make concurrent requests
            tasks = [
                service.calculate_route(
                    origin=f"25.{i:03d},121.565",
                    destination=f"25.{i:03d},121.517"
                )
                for i in range(10)
            ]
            
            results = await asyncio.gather(*tasks)
            
            # Verify all completed
            assert len(results) == 10
            assert service.metrics["total_requests"] == 10
            assert service.metrics["successful_requests"] == 10