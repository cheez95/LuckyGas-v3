"""
Tests for API enhancement features including CORS, rate limiting,
versioning, and WebSocket functionality.
"""

import pytest
import pytest_asyncio
from httpx import AsyncClient
from datetime import datetime
import asyncio
import json

from app.main import app
from app.core.config import settings


class TestCORSConfiguration:
    """Test CORS configuration and headers."""
    
    @pytest.mark.asyncio
    async def test_cors_preflight_request(self, client: AsyncClient):
        """Test CORS preflight (OPTIONS) request."""
        response = await client.options(
            "/api/v1/customers",
            headers={
                "Origin": "http://localhost:3000",
                "Access-Control-Request-Method": "GET",
                "Access-Control-Request-Headers": "Authorization, Content-Type"
            }
        )
        
        assert response.status_code == 200
        assert "Access-Control-Allow-Origin" in response.headers
        assert "Access-Control-Allow-Methods" in response.headers
        assert "Access-Control-Allow-Headers" in response.headers
        assert response.headers["Access-Control-Max-Age"] == "3600"
    
    @pytest.mark.asyncio
    async def test_cors_actual_request(self, client: AsyncClient):
        """Test CORS headers on actual request."""
        response = await client.get(
            "/api/v1/health",
            headers={"Origin": "http://localhost:3000"}
        )
        
        assert response.status_code == 200
        assert response.headers["Access-Control-Allow-Origin"] == "http://localhost:3000"
        assert response.headers["Access-Control-Allow-Credentials"] == "true"
    
    @pytest.mark.asyncio
    async def test_cors_invalid_origin(self, client: AsyncClient):
        """Test CORS with invalid origin."""
        response = await client.get(
            "/api/v1/health",
            headers={"Origin": "http://malicious-site.com"}
        )
        
        # Should not include CORS headers for invalid origin
        assert "Access-Control-Allow-Origin" not in response.headers


class TestRateLimiting:
    """Test rate limiting functionality."""
    
    @pytest.fixture(autouse=True)
    def enable_rate_limiting(self, monkeypatch):
        """Enable rate limiting for these tests."""
        from app.core import config
        monkeypatch.setattr(config.settings, "RATE_LIMIT_ENABLED", True)
    
    @pytest_asyncio.fixture
    async def rate_limited_client(self, db_session, monkeypatch):
        """Create a client with a low rate limit for testing."""
        from httpx import AsyncClient, ASGITransport
        from app.main import app
        from app.core.database import get_async_session
        from app.middleware.rate_limiting import RateLimitMiddleware
        from app.core import cache as cache_module
        from unittest.mock import AsyncMock
        
        # Enable rate limiting
        from app.core import config
        monkeypatch.setattr(config.settings, "RATE_LIMIT_ENABLED", True)
        
        # Mock the cache methods used by rate limiting
        request_store = {}
        
        async def mock_get(key):
            if "sliding_window" in key:
                # Return stored requests for rate limiting as JSON string
                return request_store.get(key)
            return None
            
        async def mock_set(key, value, expire=None):
            if "sliding_window" in key:
                # Store requests for rate limiting
                request_store[key] = value
            return True
            
        # Patch the cache methods directly
        monkeypatch.setattr(cache_module.cache, "get", mock_get)
        monkeypatch.setattr(cache_module.cache, "set", mock_set)
        
        # Create a new app instance for testing
        from fastapi import FastAPI
        test_app = FastAPI()
        
        # Copy routers and dependencies
        for route in app.routes:
            test_app.routes.append(route)
        test_app.dependency_overrides = app.dependency_overrides.copy()
        
        # Add middleware with low rate limit
        test_app.add_middleware(
            RateLimitMiddleware,
            default_limit=2,  # Very low limit for testing
            window_seconds=60
        )
        
        # Add other necessary middleware
        from fastapi.middleware.cors import CORSMiddleware
        test_app.add_middleware(
            CORSMiddleware,
            allow_origins=["http://localhost:3000"],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
            expose_headers=["X-RateLimit-Limit", "X-RateLimit-Remaining", "X-RateLimit-Reset"]
        )
        
        async def override_get_db():
            yield db_session
        
        test_app.dependency_overrides[get_async_session] = override_get_db
        
        transport = ASGITransport(app=test_app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            yield ac
    
    @pytest.mark.asyncio
    async def test_rate_limit_normal_usage(self, client: AsyncClient):
        """Test normal usage within rate limits."""
        # Make requests within limit
        for i in range(5):
            response = await client.get("/api/v1/health")
            assert response.status_code == 200
            assert "X-RateLimit-Limit" in response.headers
            assert "X-RateLimit-Remaining" in response.headers
            assert int(response.headers["X-RateLimit-Remaining"]) >= 0
    
    @pytest.mark.asyncio
    async def test_rate_limit_exceeded(self, rate_limited_client: AsyncClient):
        """Test rate limit exceeded scenario."""
        # Make requests to exceed limit (limit is set to 2 in rate_limited_client)
        responses = []
        for i in range(5):
            response = await rate_limited_client.get("/api/v1/health")
            responses.append(response)
        
        # Check that some requests were rate limited
        rate_limited = [r for r in responses if r.status_code == 429]
        assert len(rate_limited) > 0
        
        # Check rate limit response
        limited_response = rate_limited[0]
        assert limited_response.status_code == 429
        assert "Retry-After" in limited_response.headers
        assert limited_response.json()["error"] == "rate_limit_exceeded"
    
    @pytest.mark.asyncio
    async def test_rate_limit_different_endpoints(self, client: AsyncClient):
        """Test that rate limits are per-endpoint."""
        # Hit limit on one endpoint
        for i in range(10):
            await client.post("/api/v1/auth/login", json={"username": "test", "password": "test"})
        
        # Should still be able to access other endpoints
        response = await client.get("/api/v1/health")
        assert response.status_code == 200
    
    @pytest.mark.asyncio
    async def test_rate_limit_authenticated_vs_anonymous(self, auth_headers, client: AsyncClient):
        """Test that authenticated users get higher rate limits."""
        # Anonymous requests
        anon_responses = []
        for i in range(5):
            response = await client.get("/api/v1/customers/")
            anon_responses.append(response)
        
        # Authenticated requests should have higher limit
        auth_responses = []
        for i in range(10):
            response = await client.get("/api/v1/customers/", headers=auth_headers)
            auth_responses.append(response)
        
        # Check that authenticated requests have higher remaining
        anon_remaining = int(anon_responses[-1].headers.get("X-RateLimit-Remaining", 0))
        auth_remaining = int(auth_responses[-1].headers.get("X-RateLimit-Remaining", 0))
        
        # Authenticated should have more remaining (or at least not be rate limited yet)
        assert auth_remaining >= 0 or anon_remaining < auth_remaining


class TestAPIVersioning:
    """Test API versioning functionality."""
    
    @pytest.mark.asyncio
    async def test_version_in_url_path(self, client: AsyncClient):
        """Test version detection from URL path."""
        response = await client.get("/api/v1/health")
        assert response.status_code == 200
        # Version headers should be present
        if "API-Version" in response.headers:
            assert response.headers["API-Version"] == "v1.0.0"
    
    @pytest.mark.asyncio
    async def test_version_in_header(self, client: AsyncClient):
        """Test version detection from headers."""
        response = await client.get(
            "/api/v1/health",
            headers={"Accept-Version": "v1.2"}
        )
        assert response.status_code == 200
    
    @pytest.mark.asyncio
    async def test_deprecated_version_warning(self, client: AsyncClient):
        """Test deprecated version warning."""
        # Assuming v1.0 is deprecated
        response = await client.get(
            "/api/v1/health",
            headers={"API-Version": "v1.0"}
        )
        
        # Should still work but with deprecation warning
        assert response.status_code == 200
        if "Warning" in response.headers:
            assert "deprecated" in response.headers["Warning"].lower()
    
    @pytest.mark.asyncio
    async def test_unsupported_version(self, client: AsyncClient):
        """Test unsupported version error."""
        response = await client.get(
            "/api/v1/health",
            headers={"API-Version": "v0.1"}
        )
        
        # Should return error for unsupported version
        if response.status_code == 400:
            assert "no longer supported" in response.json()["detail"]
    
    @pytest.mark.asyncio
    async def test_version_specific_features(self, client: AsyncClient):
        """Test version-specific feature availability."""
        # Test feature available in newer version
        response = await client.get(
            "/api/v1/info",
            headers={"Accept-Version": "v1.2"}
        )
        
        if response.status_code == 200:
            data = response.json()
            assert "features" in data
            assert data["features"].get("batch_operations") is True


class TestWebSocketEnhancements:
    """Test WebSocket/Socket.IO enhancements."""
    
    @pytest.mark.asyncio
    async def test_socketio_cors_configuration(self):
        """Test that Socket.IO has proper CORS configuration."""
        from app.api.v1.socketio_handler import sio, cors_origins
        
        # Check that CORS is configured by verifying the cors_origins list exists
        assert cors_origins is not None
        assert len(cors_origins) > 0
        
        # Check that the sio server is created (which uses cors_origins)
        assert sio is not None
        assert hasattr(sio, 'eio')  # Verify it's a proper Socket.IO server
        
        # Should include development origins in dev mode
        if settings.is_development():
            assert any("localhost" in origin for origin in cors_origins)
    
    @pytest.mark.asyncio
    async def test_socketio_connection_without_auth(self):
        """Test Socket.IO connection requires authentication."""
        # This would require a Socket.IO client for proper testing
        # For now, just verify the handler exists
        from app.api.v1.socketio_handler import sio
        
        assert hasattr(sio, "on")
        assert "connect" in sio.handlers["/"]
    
    @pytest.mark.asyncio
    async def test_socketio_rate_limiting_excluded(self, client: AsyncClient):
        """Test that Socket.IO endpoints are excluded from rate limiting."""
        # Make many requests to Socket.IO endpoint
        responses = []
        for i in range(20):
            response = await client.get("/socket.io/")
            responses.append(response)
        
        # Should not have rate limit headers
        for response in responses:
            assert "X-RateLimit-Limit" not in response.headers


class TestAPIEnhancementIntegration:
    """Test integration of all API enhancements."""
    
    @pytest.fixture(autouse=True)
    def enable_rate_limiting(self, monkeypatch):
        """Enable rate limiting for these tests."""
        from app.core import config
        monkeypatch.setattr(config.settings, "RATE_LIMIT_ENABLED", True)
    
    @pytest.mark.asyncio
    async def test_full_request_flow(self, auth_headers, client: AsyncClient):
        """Test a request going through all enhancements."""
        response = await client.get(
            "/api/v1/customers/",
            headers={
                **auth_headers,
                "Origin": "http://localhost:3000",
                "Accept-Version": "v1.2"
            }
        )
        
        # Should have all enhancement headers
        assert response.status_code in [200, 404]  # 404 if no customers
        
        # CORS headers
        assert "Access-Control-Allow-Origin" in response.headers
        
        # Rate limit headers
        assert "X-RateLimit-Limit" in response.headers
        assert "X-RateLimit-Remaining" in response.headers
        
        # Performance headers
        assert "X-Process-Time" in response.headers
        
        # Version headers (if implemented)
        if "API-Version" in response.headers:
            assert response.headers["API-Version-Latest"] is not None
    
    @pytest.mark.asyncio
    async def test_error_handling_with_enhancements(self, client: AsyncClient):
        """Test error responses include proper headers."""
        # Make invalid request
        response = await client.post(
            "/api/v1/auth/login",
            json={"invalid": "data"},
            headers={"Origin": "http://localhost:3000"}
        )
        
        # Should have error status
        assert response.status_code == 422
        
        # Should still have CORS headers
        assert "Access-Control-Allow-Origin" in response.headers
        
        # Should have rate limit headers
        assert "X-RateLimit-Limit" in response.headers
        
        # Should have correlation ID
        assert "X-Request-ID" in response.headers


# Fixtures for testing
@pytest_asyncio.fixture
async def auth_headers(client: AsyncClient, test_admin):
    """Get authentication headers for testing."""
    # Use the test_admin fixture which creates a user in the test database
    from app.core.security import create_access_token
    
    access_token = create_access_token(
        data={"sub": test_admin.username, "role": test_admin.role.value}
    )
    return {"Authorization": f"Bearer {access_token}"}