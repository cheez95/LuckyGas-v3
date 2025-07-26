"""
Integration test configuration and fixtures
"""
import asyncio
import pytest
import pytest_asyncio
from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.pool import NullPool
from httpx import AsyncClient, ASGITransport
import redis.asyncio as redis
from datetime import datetime, timedelta

from app.main import app
from app.core.database import Base, get_async_session
from app.core.cache import get_redis_client
from app.core.config import settings
from app.models.user import User, UserRole
from app.models.customer import Customer, CustomerType
from app.models.order import Order, OrderStatus
from app.models.invoice import Invoice, InvoiceStatus
from app.core.security import get_password_hash, create_access_token

# Test database URL - use a separate test database
TEST_DATABASE_URL = settings.DATABASE_URL.replace("/luckygas", "/luckygas_test")


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(scope="session")
async def test_engine():
    """Create test database engine that persists for the session"""
    engine = create_async_engine(
        TEST_DATABASE_URL,
        poolclass=NullPool,
        echo=False
    )
    
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
    client = await redis.from_url(
        settings.REDIS_URL.replace("/0", "/1"),  # Use database 1 for tests
        decode_responses=True
    )
    
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
        is_active=True
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
        is_active=True
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
        is_active=True
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
        is_active=True
    )
    db_session.add(customer)
    await db_session.commit()
    await db_session.refresh(customer)
    return customer


@pytest_asyncio.fixture(scope="function")
async def test_order(db_session: AsyncSession, test_customer: Customer) -> Order:
    """Create test order"""
    order = Order(
        order_number=f"ORD{datetime.now().strftime('%Y%m%d%H%M%S')}",
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
        total_amount=4800,  # (2*1500) + (1*600) + (3*300)
        delivery_address=test_customer.address,
        is_taxable=True
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
    mock = mocker.patch('app.services.dispatch.google_routes_service.GoogleRoutesService.optimize_route')
    mock.return_value = {
        "optimized_waypoint_order": [0, 1, 2],
        "total_distance_meters": 15000,
        "total_duration_seconds": 3600,
        "warnings": []
    }
    return mock


@pytest.fixture
def mock_einvoice_api(mocker):
    """Mock Taiwan E-Invoice API responses"""
    mock = mocker.patch('app.services.einvoice_service.EInvoiceService.submit_invoice')
    mock.return_value = {
        "success": True,
        "invoice_number": "AB12345678",
        "message": "發票開立成功",
        "timestamp": datetime.now().isoformat()
    }
    return mock


@pytest.fixture
def mock_websocket_manager(mocker):
    """Mock WebSocket manager for real-time updates"""
    mock = mocker.patch('app.services.websocket_service.websocket_manager.broadcast')
    mock.return_value = None
    return mock