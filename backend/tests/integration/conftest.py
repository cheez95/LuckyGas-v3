"""
Integration test configuration and fixtures
"""

import asyncio
import os
from datetime import datetime, timedelta
from pathlib import Path
from typing import AsyncGenerator

import pytest
import pytest_asyncio
import redis.asyncio as redis
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

# Set test environment before importing app
os.environ["ENVIRONMENT"] = "test"
os.environ["TESTING"] = "1"

# Load test environment from .env.test
test_env_path = Path(__file__).parent.parent.parent / ".env.test"
if test_env_path.exists():
    from dotenv import load_dotenv

    load_dotenv(test_env_path)

from app.core.config import settings
from app.core.database import Base, get_async_session
from app.core.security import create_access_token, get_password_hash
from app.main import app
from app.models.customer import Customer, CustomerType
from app.models.order import Order, OrderStatus
from app.models.user import User, UserRole

# Test database URL - use PostgreSQL test database from docker - compose
TEST_DATABASE_URL = f"postgresql + asyncpg://{settings.POSTGRES_USER}:{settings.POSTGRES_PASSWORD}@{settings.POSTGRES_SERVER}:{settings.POSTGRES_PORT}/{settings.POSTGRES_DB}"


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(scope="session")
async def test_engine():
    """Create test database engine that persists for the session"""
    engine = create_async_engine(TEST_DATABASE_URL, poolclass=NullPool, echo=False)

    # Create all tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)

    yield engine

    # Clean up
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

    await engine.dispose()


@pytest_asyncio.fixture(scope="function")
async def db_session(test_engine) -> AsyncGenerator[AsyncSession, None]:
    """Create a test database session"""
    async_session_maker = async_sessionmaker(
        test_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    async with async_session_maker() as session:
        yield session
        await session.rollback()


@pytest_asyncio.fixture(scope="function")
async def client(db_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    """Create test client with database override"""

    # Override database dependency
    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_async_session] = override_get_db

    # Create test client
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

    # Clear overrides
    app.dependency_overrides.clear()


@pytest_asyncio.fixture(scope="function")
async def redis_client():
    """Create test Redis client"""
    # Use the test Redis instance from docker - compose
    redis_url = (
        settings.REDIS_URL or "redis://:test_redis_password_123@localhost:6380 / 1"
    )

    client = await redis.from_url(redis_url, decode_responses=True)

    # Clear test database
    await client.flushdb()

    yield client

    # Cleanup
    await client.flushdb()
    await client.close()


@pytest_asyncio.fixture(scope="function")
async def test_admin_user(db_session: AsyncSession) -> User:
    """Create test admin user"""
    user = User(
        email="admin@test.com",
        username="testadmin",
        full_name="Test Admin",
        hashed_password=get_password_hash("admin123"),
        role=UserRole.SUPER_ADMIN,
        is_active=True,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest_asyncio.fixture(scope="function")
async def test_office_user(db_session: AsyncSession) -> User:
    """Create test office staff user"""
    user = User(
        email="office@test.com",
        username="testoffice",
        full_name="Test Office",
        hashed_password=get_password_hash("office123"),
        role=UserRole.OFFICE_STAFF,
        is_active=True,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest_asyncio.fixture(scope="function")
async def test_driver_user(db_session: AsyncSession) -> User:
    """Create test driver user"""
    user = User(
        email="driver@test.com",
        username="testdriver",
        full_name="Test Driver",
        hashed_password=get_password_hash("driver123"),
        role=UserRole.DRIVER,
        is_active=True,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest_asyncio.fixture(scope="function")
async def test_customer(db_session: AsyncSession) -> Customer:
    """Create test customer"""
    customer = Customer(
        customer_code="TEST001",
        short_name="測試客戶",
        full_name="測試客戶有限公司",
        tax_id="12345678",
        address="台北市信義區測試路123號",
        phone="0912345678",
        area="信義區",
        customer_type=CustomerType.COMMERCIAL,
        credit_limit=100000,
        payment_terms=30,
        is_active=True,
    )
    db_session.add(customer)
    await db_session.commit()
    await db_session.refresh(customer)
    return customer


@pytest_asyncio.fixture(scope="function")
async def test_order(db_session: AsyncSession, test_customer: Customer) -> Order:
    """Create test order"""
    order = Order(
        order_number=f"ORD{datetime.now().strftime('%Y % m % d % H % M % S')}",
        customer_id=test_customer.id,
        order_date=datetime.now(),
        scheduled_date=datetime.now().date() + timedelta(days=1),
        status=OrderStatus.PENDING,
        qty_50kg=2,
        qty_20kg=1,
        qty_16kg=0,
        qty_10kg=3,
        qty_4kg=0,
        unit_price_50kg=1500,
        unit_price_20kg=600,
        unit_price_16kg=480,
        unit_price_10kg=300,
        unit_price_4kg=120,
        total_amount=4800,  # (2 * 1500) + (1 * 600) + (3 * 300)
        delivery_address=test_customer.address,
        is_taxable=True,
    )
    db_session.add(order)
    await db_session.commit()
    await db_session.refresh(order)
    return order


@pytest_asyncio.fixture
async def auth_headers(test_admin_user: User) -> dict:
    """Create authentication headers for admin user"""
    access_token = create_access_token(
        data={"sub": test_admin_user.username, "role": test_admin_user.role.value}
    )
    return {"Authorization": f"Bearer {access_token}"}


@pytest_asyncio.fixture
async def office_auth_headers(test_office_user: User) -> dict:
    """Create authentication headers for office user"""
    access_token = create_access_token(
        data={"sub": test_office_user.username, "role": test_office_user.role.value}
    )
    return {"Authorization": f"Bearer {access_token}"}


@pytest_asyncio.fixture
async def driver_auth_headers(test_driver_user: User) -> dict:
    """Create authentication headers for driver user"""
    access_token = create_access_token(
        data={"sub": test_driver_user.username, "role": test_driver_user.role.value}
    )
    return {"Authorization": f"Bearer {access_token}"}


# Mock external services


@pytest.fixture
def mock_google_routes_api(mocker):
    """Mock Google Routes API responses"""
    mock = mocker.patch(
        "app.services.optimization.google_routes_service.GoogleRoutesService.optimize_route"
    )
    mock.return_value = {
        "optimized_waypoint_order": [0, 1, 2],
        "total_distance_meters": 15000,
        "total_duration_seconds": 3600,
        "warnings": [],
    }
    return mock


@pytest.fixture
def mock_einvoice_api(mocker):
    """Mock Taiwan E - Invoice API responses"""
    mock = mocker.patch("app.services.einvoice_service.EInvoiceService.submit_invoice")
    mock.return_value = {
        "success": True,
        "invoice_number": "AB12345678",
        "message": "發票開立成功",
        "timestamp": datetime.now().isoformat(),
    }
    return mock


@pytest.fixture
def mock_websocket_manager(mocker):
    """Mock WebSocket manager for real - time updates"""
    mock = mocker.patch("app.services.websocket_service.websocket_manager.broadcast")
    mock.return_value = None
    return mock


# Additional fixtures for integration tests


@pytest_asyncio.fixture
async def test_route(db_session: AsyncSession, test_driver_user: User) -> None:
    """Create test route"""
    from app.models.route import Route
    from app.models.vehicle import Vehicle

    # Create vehicle first
    vehicle = Vehicle(
        license_plate="TEST - 001", type="truck", capacity_kg=1000, status="active"
    )
    db_session.add(vehicle)
    await db_session.commit()
    await db_session.refresh(vehicle)

    route = Route(
        route_date=date.today(),
        driver_id=test_driver_user.id,
        vehicle_id=vehicle.id,
        status="pending",
        total_distance_km=0,
        total_duration_minutes=0,
    )
    db_session.add(route)
    await db_session.commit()
    await db_session.refresh(route)
    return route


@pytest_asyncio.fixture
async def test_gas_products(db_session: AsyncSession) -> list:
    """Create test gas products"""
    from app.models.gas_product import GasProduct

    products = [
        GasProduct(
            product_name="50kg 瓦斯桶",
            size="50kg",
            unit_price=1500.0,
            is_available=True,
        ),
        GasProduct(
            product_name="20kg 瓦斯桶", size="20kg", unit_price=600.0, is_available=True
        ),
        GasProduct(
            product_name="16kg 瓦斯桶", size="16kg", unit_price=480.0, is_available=True
        ),
        GasProduct(
            product_name="10kg 瓦斯桶", size="10kg", unit_price=300.0, is_available=True
        ),
        GasProduct(
            product_name="4kg 瓦斯桶", size="4kg", unit_price=120.0, is_available=True
        ),
    ]

    for product in products:
        db_session.add(product)

    await db_session.commit()
    return products
