"""
Database utilities for testing
"""
import asyncio
from typing import Optional, List, Dict, Any
from datetime import datetime
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.pool import NullPool

from app.core.database import Base
from app.core.test_config import test_settings


class TestDatabase:
    """Utilities for test database management"""
    
    def __init__(self, database_url: str = None):
        self.database_url = database_url or test_settings.DATABASE_URL
        self.engine = None
        self.session_factory = None
    
    async def setup(self):
        """Set up test database"""
        self.engine = create_async_engine(
            self.database_url,
            poolclass=NullPool,
            echo=False
        )
        self.session_factory = async_sessionmaker(
            self.engine,
            class_=AsyncSession,
            expire_on_commit=False
        )
        
        # Create all tables
        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
    
    async def teardown(self):
        """Tear down test database"""
        if self.engine:
            # Drop all tables
            async with self.engine.begin() as conn:
                await conn.run_sync(Base.metadata.drop_all)
            
            # Dispose engine
            await self.engine.dispose()
    
    async def clear_all_tables(self):
        """Clear all data from tables without dropping them"""
        async with self.session_factory() as session:
            # Get all table names
            result = await session.execute(
                text("""
                    SELECT tablename FROM pg_tables 
                    WHERE schemaname = 'public'
                """)
            )
            tables = [row[0] for row in result]
            
            # Disable foreign key constraints temporarily
            await session.execute(text("SET session_replication_role = 'replica'"))
            
            # Truncate all tables
            for table in tables:
                if table not in ['alembic_version']:  # Skip migration table
                    await session.execute(text(f"TRUNCATE TABLE {table} CASCADE"))
            
            # Re-enable foreign key constraints
            await session.execute(text("SET session_replication_role = 'origin'"))
            
            await session.commit()
    
    async def get_session(self) -> AsyncSession:
        """Get a new database session"""
        return self.session_factory()
    
    async def seed_basic_data(self, session: AsyncSession):
        """Seed basic data required for most tests"""
        from app.models.gas_product import GasProduct
        from app.models.user import User, UserRole
        from app.core.security import get_password_hash
        
        # Create gas products
        products = [
            GasProduct(
                product_name="50kg 瓦斯桶",
                size="50kg",
                unit_price=2500.0,
                is_available=True,
                display_name="50公斤桶裝瓦斯",
                category="standard"
            ),
            GasProduct(
                product_name="20kg 瓦斯桶",
                size="20kg",
                unit_price=1000.0,
                is_available=True,
                display_name="20公斤桶裝瓦斯",
                category="standard"
            ),
            GasProduct(
                product_name="16kg 瓦斯桶",
                size="16kg",
                unit_price=800.0,
                is_available=True,
                display_name="16公斤桶裝瓦斯",
                category="standard"
            ),
            GasProduct(
                product_name="10kg 瓦斯桶",
                size="10kg",
                unit_price=500.0,
                is_available=True,
                display_name="10公斤桶裝瓦斯",
                category="standard"
            ),
            GasProduct(
                product_name="4kg 瓦斯桶",
                size="4kg",
                unit_price=200.0,
                is_available=True,
                display_name="4公斤桶裝瓦斯",
                category="standard"
            )
        ]
        
        for product in products:
            session.add(product)
        
        # Create system user
        system_user = User(
            username="system",
            email="system@luckygas.com",
            full_name="System User",
            hashed_password=get_password_hash("system_password"),
            role=UserRole.SUPER_ADMIN,
            is_active=True,
            is_verified=True
        )
        session.add(system_user)
        
        await session.commit()
    
    async def create_test_snapshot(self, session: AsyncSession) -> Dict[str, Any]:
        """Create a snapshot of current database state"""
        snapshot = {}
        
        # Get record counts for all tables
        tables = [
            'users', 'customers', 'orders', 'gas_products', 
            'routes', 'order_templates', 'payments', 'invoices'
        ]
        
        for table in tables:
            result = await session.execute(text(f"SELECT COUNT(*) FROM {table}"))
            count = result.scalar()
            snapshot[f"{table}_count"] = count
        
        snapshot['timestamp'] = datetime.now()
        return snapshot
    
    async def verify_snapshot(self, session: AsyncSession, snapshot: Dict[str, Any]) -> bool:
        """Verify database state matches snapshot"""
        for key, expected_value in snapshot.items():
            if key == 'timestamp':
                continue
            
            table = key.replace('_count', '')
            result = await session.execute(text(f"SELECT COUNT(*) FROM {table}"))
            actual_count = result.scalar()
            
            if actual_count != expected_value:
                print(f"Snapshot mismatch: {table} expected {expected_value}, got {actual_count}")
                return False
        
        return True


class DatabaseTransaction:
    """Context manager for database transactions in tests"""
    
    def __init__(self, session: AsyncSession):
        self.session = session
        self.savepoint = None
    
    async def __aenter__(self):
        """Begin a savepoint"""
        self.savepoint = await self.session.begin_nested()
        return self.session
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Rollback to savepoint"""
        if self.savepoint:
            await self.savepoint.rollback()


async def run_in_transaction(session: AsyncSession, func, *args, **kwargs):
    """Run a function within a database transaction that gets rolled back"""
    async with DatabaseTransaction(session) as tx_session:
        return await func(tx_session, *args, **kwargs)


def assert_database_empty(session: AsyncSession):
    """Assert that all tables are empty (except system tables)"""
    async def check():
        tables = [
            'users', 'customers', 'orders', 'routes', 
            'order_templates', 'payments', 'invoices'
        ]
        
        for table in tables:
            result = await session.execute(text(f"SELECT COUNT(*) FROM {table}"))
            count = result.scalar()
            assert count == 0, f"Table {table} is not empty: {count} records found"
    
    return asyncio.create_task(check())


def create_bulk_test_data(session: AsyncSession, model_class, data_list: List[Dict[str, Any]]):
    """Bulk create test data efficiently"""
    async def bulk_create():
        instances = [model_class(**data) for data in data_list]
        session.add_all(instances)
        await session.commit()
        return instances
    
    return asyncio.create_task(bulk_create())