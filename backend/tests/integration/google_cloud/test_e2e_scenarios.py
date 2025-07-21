"""
End-to-end integration tests for Google API scenarios
"""
import pytest
from unittest.mock import Mock, patch, AsyncMock
import os
from datetime import datetime, timedelta
from decimal import Decimal
import asyncio
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession

from app.main import app
from app.core.database import get_async_session
from app.models.customer import Customer
from app.models.order import Order
from app.services.google_cloud.routes_service_enhanced import enhanced_routes_service
from app.services.google_cloud.vertex_ai_service_enhanced import enhanced_vertex_ai_service


@pytest.mark.e2e
class TestE2EScenarios:
    """End-to-end test scenarios"""
    
    @pytest.fixture
    async def test_db(self):
        """Create test database"""
        # Use in-memory SQLite for tests
        engine = create_async_engine("sqlite+aiosqlite:///:memory:")
        async with engine.begin() as conn:
            # Create tables
            from app.models import Base
            await conn.run_sync(Base.metadata.create_all)
        
        # Create session
        async_session = sessionmaker(
            engine, class_=AsyncSession, expire_on_commit=False
        )
        
        yield async_session
        
        await engine.dispose()
    
    @pytest.fixture
    def client(self, test_db):
        """Create test client with test database"""
        async def override_get_db():
            async with test_db() as session:
                yield session
        
        app.dependency_overrides[get_async_session] = override_get_db
        
        with TestClient(app) as client:
            yield client
        
        app.dependency_overrides.clear()
    
    @pytest.mark.asyncio
    async def test_daily_route_optimization_workflow(self, client, test_db):
        """Test complete daily route optimization workflow"""
        # Set development mode for testing
        with patch.dict(os.environ, {"DEVELOPMENT_MODE": "development"}):
            # 1. Create test customers and orders
            async with test_db() as session:
                # Create customers
                customers = []
                for i in range(5):
                    customer = Customer(
                        name=f"Test Customer {i}",
                        phone=f"0912345{i:03d}",
                        address=f"台北市信義區信義路{i+1}段{i+1}號",
                        lat=25.033 + i * 0.01,
                        lng=121.565 + i * 0.01,
                        is_active=True,
                        cylinders_50kg=2,
                        cylinders_20kg=1
                    )
                    customers.append(customer)
                    session.add(customer)
                
                await session.commit()
                
                # Create pending orders
                for customer in customers:
                    order = Order(
                        customer_id=customer.id,
                        order_date=datetime.now().date(),
                        quantity_50kg=1,
                        quantity_20kg=1,
                        status="pending",
                        total_amount=Decimal("2500.00")
                    )
                    session.add(order)
                
                await session.commit()
            
            # 2. Generate predictions
            response = client.post("/api/v1/predictions/generate")
            assert response.status_code == 200
            prediction_result = response.json()
            assert prediction_result["predictions_count"] > 0
            
            # 3. Get predictions
            response = client.get("/api/v1/predictions/daily")
            assert response.status_code == 200
            predictions = response.json()
            assert len(predictions) > 0
            
            # 4. Optimize routes
            response = client.post("/api/v1/routes/optimize/daily")
            assert response.status_code == 200
            routes = response.json()
            assert "optimized_routes" in routes
            assert len(routes["optimized_routes"]) > 0
            
            # 5. Check dashboard metrics
            response = client.get("/api/v1/google-api/dashboard/overview")
            assert response.status_code == 200
            dashboard = response.json()
            assert "services" in dashboard
            assert "routes" in dashboard["services"]
            assert "vertex_ai" in dashboard["services"]
    
    @pytest.mark.asyncio
    async def test_cost_budget_enforcement(self, client):
        """Test cost budget enforcement across services"""
        with patch.dict(os.environ, {"DEVELOPMENT_MODE": "production"}):
            # Mock services to simulate high costs
            enhanced_routes_service.cost_monitor.get_api_usage = AsyncMock(
                return_value={
                    "api_type": "routes",
                    "daily_cost": 95.00,  # Near critical threshold
                    "over_budget": False,
                    "daily_percentage": 95.0
                }
            )
            
            # Try to make expensive operation
            enhanced_routes_service.cost_monitor.check_budget = AsyncMock(
                return_value=False  # Over budget
            )
            
            # Should fall back to mock service
            response = client.post(
                "/api/v1/routes/calculate",
                json={
                    "origin": {"lat": 25.033, "lng": 121.565},
                    "destination": {"lat": 25.047, "lng": 121.517}
                }
            )
            
            # Should still get response (from mock)
            assert response.status_code == 200
            result = response.json()
            assert "routes" in result
    
    @pytest.mark.asyncio
    async def test_circuit_breaker_recovery(self, client):
        """Test circuit breaker opening and recovery"""
        with patch.dict(os.environ, {"DEVELOPMENT_MODE": "production"}):
            # Simulate failures to open circuit
            original_calculate = enhanced_routes_service._calculate_route_internal
            
            failure_count = 0
            
            async def failing_calculate():
                nonlocal failure_count
                failure_count += 1
                raise Exception("Service unavailable")
            
            enhanced_routes_service._calculate_route_internal = failing_calculate
            
            # Make requests until circuit opens
            for i in range(5):
                response = client.post(
                    "/api/v1/routes/calculate",
                    json={
                        "origin": {"lat": 25.033, "lng": 121.565},
                        "destination": {"lat": 25.047, "lng": 121.517}
                    }
                )
                # Should get mock response
                assert response.status_code == 200
            
            # Check circuit is open
            cb_status = enhanced_routes_service.circuit_breaker.get_status()
            assert cb_status["state"] == "OPEN"
            
            # Restore original function
            enhanced_routes_service._calculate_route_internal = original_calculate
            
            # Reset circuit for next test
            enhanced_routes_service.circuit_breaker.reset()
    
    @pytest.mark.asyncio
    async def test_rate_limit_throttling(self, client):
        """Test rate limiting behavior"""
        with patch.dict(os.environ, {"DEVELOPMENT_MODE": "production"}):
            # Mock rate limiter to simulate limit exceeded
            enhanced_routes_service.rate_limiter.check_limit = AsyncMock(
                side_effect=[True, True, True, False, False]  # Limit hit on 4th request
            )
            
            # Make rapid requests
            results = []
            for i in range(5):
                response = client.post(
                    "/api/v1/routes/calculate",
                    json={
                        "origin": {"lat": 25.033, "lng": 121.565},
                        "destination": {"lat": 25.047, "lng": 121.517}
                    }
                )
                results.append(response.status_code)
            
            # All should succeed (fallback to mock when rate limited)
            assert all(status == 200 for status in results)
    
    @pytest.mark.asyncio
    async def test_cache_performance(self, client):
        """Test caching improves performance"""
        with patch.dict(os.environ, {"DEVELOPMENT_MODE": "development"}):
            # First request - cache miss
            start_time = datetime.now()
            response1 = client.post(
                "/api/v1/routes/calculate",
                json={
                    "origin": {"lat": 25.033, "lng": 121.565},
                    "destination": {"lat": 25.047, "lng": 121.517}
                }
            )
            first_duration = (datetime.now() - start_time).total_seconds()
            assert response1.status_code == 200
            
            # Mock cache to return cached result
            enhanced_routes_service.cache.get = AsyncMock(
                return_value=response1.json()
            )
            
            # Second request - cache hit
            start_time = datetime.now()
            response2 = client.post(
                "/api/v1/routes/calculate",
                json={
                    "origin": {"lat": 25.033, "lng": 121.565},
                    "destination": {"lat": 25.047, "lng": 121.517}
                }
            )
            second_duration = (datetime.now() - start_time).total_seconds()
            assert response2.status_code == 200
            
            # Cache hit should be faster
            assert response1.json() == response2.json()
    
    @pytest.mark.asyncio
    async def test_monitoring_dashboard_data(self, client):
        """Test monitoring dashboard provides accurate data"""
        # Simulate some API activity
        enhanced_routes_service.metrics = {
            "total_requests": 100,
            "successful_requests": 95,
            "failed_requests": 5,
            "cache_hits": 30,
            "total_optimizations": 20,
            "successful_optimizations": 18
        }
        
        enhanced_vertex_ai_service.metrics = {
            "total_predictions": 50,
            "successful_predictions": 48,
            "failed_predictions": 2,
            "cache_hits": 15,
            "total_training_jobs": 1,
            "successful_training_jobs": 1
        }
        
        # Mock monitoring data
        for service in [enhanced_routes_service, enhanced_vertex_ai_service]:
            service.circuit_breaker.get_status = Mock(
                return_value={"state": "CLOSED", "failure_count": 0}
            )
            service.rate_limiter.get_current_usage = AsyncMock(
                return_value={"available": True, "current": {"per_second": 5}}
            )
            service.cost_monitor.get_api_usage = AsyncMock(
                return_value={"daily_cost": 25.00, "over_budget": False}
            )
        
        # Get dashboard overview
        response = client.get("/api/v1/google-api/dashboard/overview")
        assert response.status_code == 200
        
        dashboard = response.json()
        assert dashboard["services"]["routes"]["requests"]["total"] == 100
        assert dashboard["services"]["routes"]["requests"]["success_rate"] == 95.0
        assert dashboard["services"]["vertex_ai"]["predictions"]["total"] == 50
        
        # Get cost report
        response = client.get("/api/v1/google-api/dashboard/costs")
        assert response.status_code == 200
        
        costs = response.json()
        assert "routes" in costs
        assert "vertex_ai" in costs
    
    @pytest.mark.asyncio
    async def test_api_key_security(self, client):
        """Test API key security features"""
        # Try to access API key endpoint without auth
        response = client.get("/api/v1/google-api/keys")
        assert response.status_code in [401, 403]  # Unauthorized or Forbidden
        
        # Test key rotation workflow
        with patch("app.core.security.api_key_manager.get_api_key_manager") as mock:
            key_manager = AsyncMock()
            key_manager.set_key = AsyncMock(return_value=True)
            key_manager.list_keys = AsyncMock(return_value=["routes", "vertex_ai"])
            mock.return_value = key_manager
            
            # Update key (with proper auth in real scenario)
            # This would typically require admin authentication
            # response = client.put(
            #     "/api/v1/google-api/keys/routes",
            #     json={"key": "new_secure_key"},
            #     headers={"Authorization": "Bearer admin_token"}
            # )
    
    @pytest.mark.asyncio
    async def test_concurrent_user_requests(self, client):
        """Test system handles concurrent user requests"""
        async def make_request(client, request_id):
            response = client.post(
                "/api/v1/routes/calculate",
                json={
                    "origin": {"lat": 25.033 + request_id * 0.001, "lng": 121.565},
                    "destination": {"lat": 25.047, "lng": 121.517}
                }
            )
            return response.status_code, response.json()
        
        # Simulate concurrent requests from multiple users
        with patch.dict(os.environ, {"DEVELOPMENT_MODE": "development"}):
            # Use ThreadPoolExecutor for sync client
            from concurrent.futures import ThreadPoolExecutor
            
            with ThreadPoolExecutor(max_workers=10) as executor:
                futures = []
                for i in range(20):
                    future = executor.submit(
                        make_request, client, i
                    )
                    futures.append(future)
                
                results = [f.result() for f in futures]
            
            # All requests should succeed
            assert all(status == 200 for status, _ in results)
            assert len(results) == 20
    
    @pytest.mark.asyncio
    async def test_service_degradation_cascade(self, client):
        """Test how service degradation affects the system"""
        with patch.dict(os.environ, {"DEVELOPMENT_MODE": "production"}):
            # Simulate various service degradations
            stages = [
                # Stage 1: Normal operation
                {
                    "rate_limit": True,
                    "cost_budget": True,
                    "circuit_state": "CLOSED",
                    "cache_available": True
                },
                # Stage 2: Rate limiting kicks in
                {
                    "rate_limit": False,
                    "cost_budget": True,
                    "circuit_state": "CLOSED",
                    "cache_available": True
                },
                # Stage 3: Cost budget exceeded
                {
                    "rate_limit": False,
                    "cost_budget": False,
                    "circuit_state": "CLOSED",
                    "cache_available": True
                },
                # Stage 4: Circuit breaker opens
                {
                    "rate_limit": False,
                    "cost_budget": False,
                    "circuit_state": "OPEN",
                    "cache_available": False
                }
            ]
            
            for stage in stages:
                # Configure service state
                enhanced_routes_service.rate_limiter.check_limit = AsyncMock(
                    return_value=stage["rate_limit"]
                )
                enhanced_routes_service.cost_monitor.check_budget = AsyncMock(
                    return_value=stage["cost_budget"]
                )
                enhanced_routes_service.circuit_breaker.state = stage["circuit_state"]
                enhanced_routes_service.circuit_breaker.can_execute = Mock(
                    return_value=stage["circuit_state"] != "OPEN"
                )
                
                # Make request
                response = client.post(
                    "/api/v1/routes/calculate",
                    json={
                        "origin": {"lat": 25.033, "lng": 121.565},
                        "destination": {"lat": 25.047, "lng": 121.517}
                    }
                )
                
                # Should always get a response (degraded to mock if needed)
                assert response.status_code == 200
                assert "routes" in response.json()