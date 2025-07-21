"""
Test configuration and fixtures
"""
import pytest
import asyncio
from typing import AsyncGenerator, Generator
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.pool import NullPool

from app.main import app
from app.core.database import Base, get_async_session
from app.core.config import settings
from app.models.user import User, UserRole
from app.core.security import get_password_hash, create_access_token


# Test database URL (use separate test database)
TEST_DATABASE_URL = settings.DATABASE_URL.replace("/luckygas", "/luckygas_test")


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