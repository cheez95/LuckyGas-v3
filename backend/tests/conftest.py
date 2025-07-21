"""
Test configuration and fixtures
"""
import pytest
import asyncio
from typing import AsyncGenerator, Generator, Dict, Any
from datetime import datetime, timedelta
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.pool import NullPool
import redis.asyncio as redis
from unittest.mock import AsyncMock, MagicMock

from app.main import app
from app.core.database import Base, get_async_session
from app.core.test_config import test_settings
from app.models.user import User, UserRole
from app.models.customer import Customer
from app.models.order import Order, OrderStatus, PaymentStatus
from app.models.gas_product import GasProduct
from app.models.route import Route
from app.models.driver import Driver
from app.core.security import get_password_hash, create_access_token
from app.core.cache import get_redis_client
from app.services.customer_service import CustomerService
from app.services.order_service import OrderService


# Override settings for tests
settings = test_settings

# Test database URL
TEST_DATABASE_URL = test_settings.DATABASE_URL


@pytest.fixture(scope="session")
def event_loop() -> Generator:
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session")
async def engine():
    """Create test database engine"""
    engine = create_async_engine(
        TEST_DATABASE_URL,
        poolclass=NullPool,
    )
    yield engine
    await engine.dispose()


@pytest.fixture(scope="function")
async def db_session(engine) -> AsyncGenerator[AsyncSession, None]:
    """Create test database session"""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    
    async_session_maker = async_sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )
    
    async with async_session_maker() as session:
        yield session


@pytest.fixture(scope="function")
async def client(db_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    """Create test client with database override"""
    
    async def override_get_db():
        yield db_session
    
    app.dependency_overrides[get_async_session] = override_get_db
    
    async with AsyncClient(app=app, base_url="http://test") as ac:
        yield ac
    
    app.dependency_overrides.clear()


@pytest.fixture
async def test_user(db_session: AsyncSession) -> User:
    """Create test user"""
    user = User(
        email="test@example.com",
        username="testuser",
        full_name="Test User",
        hashed_password=get_password_hash("testpassword"),
        role=UserRole.OFFICE_STAFF,
        is_active=True
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest.fixture
async def test_admin(db_session: AsyncSession) -> User:
    """Create test admin user"""
    admin = User(
        email="admin@example.com",
        username="admin",
        full_name="Admin User",
        hashed_password=get_password_hash("adminpassword"),
        role=UserRole.SUPER_ADMIN,
        is_active=True
    )
    db_session.add(admin)
    await db_session.commit()
    await db_session.refresh(admin)
    return admin


@pytest.fixture
async def test_driver(db_session: AsyncSession) -> User:
    """Create test driver user"""
    driver = User(
        email="driver@example.com",
        username="driver",
        full_name="Driver User",
        hashed_password=get_password_hash("driverpassword"),
        role=UserRole.DRIVER,
        is_active=True
    )
    db_session.add(driver)
    await db_session.commit()
    await db_session.refresh(driver)
    return driver


@pytest.fixture
async def auth_headers(test_user: User) -> dict:
    """Create authentication headers for test user"""
    access_token = create_access_token(data={"sub": test_user.email})
    return {"Authorization": f"Bearer {access_token}"}


@pytest.fixture
async def admin_auth_headers(test_admin: User) -> dict:
    """Create authentication headers for admin user"""
    access_token = create_access_token(data={"sub": test_admin.email})
    return {"Authorization": f"Bearer {access_token}"}


@pytest.fixture
async def driver_auth_headers(test_driver: User) -> dict:
    """Create authentication headers for driver user"""
    access_token = create_access_token(data={"sub": test_driver.email})
    return {"Authorization": f"Bearer {access_token}"}


# Sample data fixtures
@pytest.fixture
def sample_customer_data():
    """Sample customer data for testing"""
    return {
        "customer_code": "C001",
        "short_name": "測試客戶",
        "invoice_title": "測試公司",
        "tax_id": "12345678",
        "address": "台北市信義區測試路123號",
        "phone1": "0912-345-678",
        "contact_person": "王小明",
        "area": "信義區",
        "is_corporate": True
    }


@pytest.fixture
def sample_order_data():
    """Sample order data for testing"""
    return {
        "customer_id": 1,
        "scheduled_date": "2024-12-25",
        "qty_50kg": 2,
        "qty_20kg": 1,
        "qty_16kg": 0,
        "qty_10kg": 0,
        "qty_4kg": 3,
        "delivery_notes": "請於下午送達",
        "is_urgent": False
    }


@pytest.fixture
def sample_route_data():
    """Sample route data for testing"""
    return {
        "route_date": "2024-12-25",
        "area": "信義區",
        "driver_id": 1,
        "vehicle_id": 1,
        "stops": []
    }


# Redis fixtures
@pytest.fixture
async def redis_client():
    """Create test Redis client"""
    client = await redis.from_url(test_settings.REDIS_URL, decode_responses=True)
    yield client
    await client.flushdb()
    await client.close()


@pytest.fixture
def mock_redis_client():
    """Mock Redis client for unit tests"""
    mock = AsyncMock()
    mock.get.return_value = None
    mock.set.return_value = True
    mock.delete.return_value = True
    mock.exists.return_value = False
    return mock


# Service fixtures
@pytest.fixture
async def customer_service(db_session: AsyncSession) -> CustomerService:
    """Create customer service instance"""
    return CustomerService(db_session)


@pytest.fixture
async def order_service(db_session: AsyncSession) -> OrderService:
    """Create order service instance"""
    return OrderService(db_session)


# Mock external services
@pytest.fixture
def mock_google_routes_service():
    """Mock Google Routes service"""
    mock = MagicMock()
    mock.optimize_route.return_value = {
        "total_distance_km": 50.5,
        "total_duration_minutes": 120,
        "optimized_stops": []
    }
    mock.optimize_multiple_routes.return_value = [
        {
            "route_number": "R001",
            "driver_id": 1,
            "total_stops": 10,
            "estimated_duration_minutes": 240,
            "stops": []
        }
    ]
    return mock


@pytest.fixture
def mock_vertex_ai_service():
    """Mock Vertex AI service"""
    mock = MagicMock()
    mock.predict_order_volume.return_value = {
        "predictions": [
            {"customer_id": 1, "predicted_quantity": 5, "confidence": 0.85}
        ]
    }
    return mock


# Model factories
@pytest.fixture
async def gas_product_factory(db_session: AsyncSession):
    """Factory for creating gas products"""
    async def create_gas_product(
        product_name: str = "50kg 瓦斯桶",
        size: str = "50kg",
        unit_price: float = 2500.0,
        is_available: bool = True
    ) -> GasProduct:
        product = GasProduct(
            product_name=product_name,
            size=size,
            unit_price=unit_price,
            is_available=is_available,
            display_name=product_name,
            category="standard"
        )
        db_session.add(product)
        await db_session.commit()
        await db_session.refresh(product)
        return product
    
    return create_gas_product


@pytest.fixture
async def customer_factory(db_session: AsyncSession):
    """Factory for creating customers"""
    async def create_customer(
        customer_code: str = None,
        short_name: str = "測試客戶",
        area: str = "信義區",
        **kwargs
    ) -> Customer:
        if not customer_code:
            customer_code = f"C{datetime.now().microsecond:06d}"
        
        customer_data = {
            "customer_code": customer_code,
            "short_name": short_name,
            "invoice_title": kwargs.get("invoice_title", short_name),
            "tax_id": kwargs.get("tax_id", "12345678"),
            "address": kwargs.get("address", f"台北市{area}測試路123號"),
            "phone1": kwargs.get("phone1", "0912-345-678"),
            "contact_person": kwargs.get("contact_person", "測試聯絡人"),
            "area": area,
            "is_corporate": kwargs.get("is_corporate", False),
            "is_terminated": kwargs.get("is_terminated", False),
            "is_subscription": kwargs.get("is_subscription", False),
            "customer_type": kwargs.get("customer_type", "regular")
        }
        
        customer = Customer(**customer_data)
        db_session.add(customer)
        await db_session.commit()
        await db_session.refresh(customer)
        return customer
    
    return create_customer


@pytest.fixture
async def order_factory(db_session: AsyncSession):
    """Factory for creating orders"""
    async def create_order(
        customer_id: int,
        scheduled_date: datetime = None,
        status: OrderStatus = OrderStatus.PENDING,
        **kwargs
    ) -> Order:
        if not scheduled_date:
            scheduled_date = datetime.now() + timedelta(days=1)
        
        order_data = {
            "order_number": kwargs.get("order_number", f"ORD-{datetime.now().microsecond:06d}"),
            "customer_id": customer_id,
            "scheduled_date": scheduled_date,
            "status": status,
            "payment_status": kwargs.get("payment_status", PaymentStatus.PENDING),
            "qty_50kg": kwargs.get("qty_50kg", 0),
            "qty_20kg": kwargs.get("qty_20kg", 0),
            "qty_16kg": kwargs.get("qty_16kg", 0),
            "qty_10kg": kwargs.get("qty_10kg", 0),
            "qty_4kg": kwargs.get("qty_4kg", 0),
            "total_amount": kwargs.get("total_amount", 0),
            "discount_amount": kwargs.get("discount_amount", 0),
            "final_amount": kwargs.get("final_amount", 0),
            "delivery_address": kwargs.get("delivery_address", "測試地址"),
            "delivery_notes": kwargs.get("delivery_notes", ""),
            "is_urgent": kwargs.get("is_urgent", False),
            "payment_method": kwargs.get("payment_method", "現金")
        }
        
        order = Order(**order_data)
        db_session.add(order)
        await db_session.commit()
        await db_session.refresh(order)
        return order
    
    return create_order


@pytest.fixture
async def driver_factory(db_session: AsyncSession):
    """Factory for creating drivers"""
    async def create_driver(
        user_id: int,
        driver_code: str = None,
        **kwargs
    ) -> Driver:
        if not driver_code:
            driver_code = f"D{datetime.now().microsecond:04d}"
        
        driver = Driver(
            user_id=user_id,
            driver_code=driver_code,
            full_name=kwargs.get("full_name", "測試司機"),
            phone=kwargs.get("phone", "0987-654-321"),
            vehicle_number=kwargs.get("vehicle_number", "ABC-123"),
            is_active=kwargs.get("is_active", True)
        )
        db_session.add(driver)
        await db_session.commit()
        await db_session.refresh(driver)
        return driver
    
    return create_driver


# Authenticated client fixtures
@pytest.fixture
async def authenticated_client(
    client: AsyncClient,
    auth_headers: Dict[str, str]
) -> AsyncClient:
    """Client with authentication headers"""
    client.headers.update(auth_headers)
    return client


@pytest.fixture
async def admin_client(
    client: AsyncClient,
    admin_auth_headers: Dict[str, str]
) -> AsyncClient:
    """Client with admin authentication"""
    client.headers.update(admin_auth_headers)
    return client


@pytest.fixture
async def driver_client(
    client: AsyncClient,
    driver_auth_headers: Dict[str, str]
) -> AsyncClient:
    """Client with driver authentication"""
    client.headers.update(driver_auth_headers)
    return client


# Cleanup fixture
@pytest.fixture(autouse=True)
async def cleanup_database(db_session: AsyncSession):
    """Ensure database is clean after each test"""
    yield
    # Cleanup is handled by the db_session fixture