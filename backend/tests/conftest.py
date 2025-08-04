"""Pytest configuration and fixtures."""

import asyncio
import os
import sys
from pathlib import Path
from typing import Any, AsyncGenerator, Dict, Generator, List

# Add backend to Python path
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

# Set test environment variables
os.environ["TESTING"] = "1"
os.environ["DATABASE_URL"] = (
    "postgresql+asyncpg://test:test@localhost:5432/luckygas_test"
)
os.environ["SECRET_KEY"] = "test-secret-key-for-testing-with-32-chars-minimum"
os.environ["ENVIRONMENT"] = "test"
os.environ["REDIS_URL"] = "redis://localhost:6379/1"

# Mock Google Cloud credentials for testing
os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = "/dev/null"
os.environ["GOOGLE_CLOUD_PROJECT"] = "test-project"

from datetime import datetime, timedelta
from unittest.mock import AsyncMock, Mock

import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import (AsyncSession, async_sessionmaker,
                                    create_async_engine)
from sqlalchemy.pool import NullPool

from app.api.deps import get_db
# Import after environment setup
from app.core.database import Base
from app.main import app

# Create test engine
test_engine = create_async_engine(
    os.environ["DATABASE_URL"], poolclass=NullPool, echo=False
)

# Create test session factory
TestSessionLocal = async_sessionmaker(
    test_engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


@pytest.fixture(scope="session")
def event_loop() -> Generator:
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(scope="function")
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    """Create a new database session for a test."""
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with TestSessionLocal() as session:
        yield session
        await session.rollback()

    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture(scope="function")
async def client(db_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    """Create a test client with database session override."""

    async def get_test_db():
        yield db_session

    app.dependency_overrides[get_db] = get_test_db

    async with AsyncClient(
        app=app, base_url="http://test", headers={"Content-Type": "application/json"}
    ) as ac:
        yield ac

    app.dependency_overrides.clear()


# Mock models and services for testing
@pytest.fixture
def mock_db():
    """Mock database session."""
    db = AsyncMock()
    db.commit = AsyncMock()
    db.refresh = AsyncMock()
    db.close = AsyncMock()
    return db


@pytest.fixture
def mock_route():
    """Mock route object."""
    route = Mock()
    route.id = "route-test-1"
    route.driver_id = "driver-1"
    route.status = "in_progress"
    route.stops = []
    route.total_distance_km = 50.0
    route.total_duration_minutes = 120
    route.vehicle = Mock(capacity=100)
    route.depot_location = (25.0330, 121.5654)
    return route


@pytest.fixture
def mock_order():
    """Mock order object."""
    order = Mock()
    order.id = "order-test-1"
    order.delivery_latitude = 25.0340
    order.delivery_longitude = 121.5655
    order.total_quantity = 20
    order.priority = "normal"
    order.customer_name = "Test Customer"
    return order


@pytest.fixture
def mock_websocket_manager():
    """Mock WebSocket manager."""
    manager = AsyncMock()
    manager.send_to_channel = AsyncMock()
    manager.broadcast = AsyncMock()
    return manager


@pytest.fixture
def mock_vrp_optimizer():
    """Mock VRP optimizer."""
    optimizer = Mock()
    optimizer.optimize_routes = AsyncMock(
        return_value={
            "routes": [],
            "total_distance": 50.0,
            "total_duration": 120,
            "unassigned_orders": [],
        }
    )
    return optimizer


@pytest.fixture
def mock_google_routes_service():
    """Mock Google Routes service."""
    service = AsyncMock()
    service.calculate_route_matrix = AsyncMock(
        return_value={"routes": [{"distanceMeters": 5000, "duration": "300s"}]}
    )
    return service


# Auto-use fixture to patch imports
@pytest.fixture(autouse=True)
def mock_imports(monkeypatch):
    """Mock imports that might not be available in test environment."""
    # Mock cache module
    mock_cache = Mock()
    mock_cache.get = AsyncMock(return_value=None)
    mock_cache.set = AsyncMock()
    mock_cache.delete = AsyncMock()
    mock_cache.intelligent_cache = lambda **kwargs: lambda func: func

    # Mock monitoring
    mock_monitoring = Mock()
    mock_monitoring.track_route_adjustment = AsyncMock()

    # Patch imports
    monkeypatch.setattr("app.core.cache.cache", mock_cache)
    # Mock intelligent_cache from the correct module
    monkeypatch.setattr(
        "app.services.google_cloud.monitoring.intelligent_cache.get_intelligent_cache",
        AsyncMock(return_value=mock_cache),
    )
    monkeypatch.setattr("app.core.monitoring.monitoring", mock_monitoring)

    # Mock WebSocket manager
    mock_ws = AsyncMock()
    mock_ws.send_to_channel = AsyncMock()
    monkeypatch.setattr("app.services.websocket_service.websocket_manager", mock_ws)

    # Mock other services
    monkeypatch.setattr("app.services.optimization.vrp_optimizer.VRPOptimizer", Mock)
    monkeypatch.setattr(
        "app.services.optimization.google_routes_service.GoogleRoutesService", AsyncMock
    )
