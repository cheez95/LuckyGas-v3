"""
Shared fixtures for migration tests
Author: Sam (QA Specialist)
"""

import pytest
import asyncio
import os
import sys
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import text

# Add parent directory to path
sys.path.append(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
)

from app.core.config import settings


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
async def test_database():
    """Create a test database for migration tests"""
    # Use a dedicated test database
    test_db_url = settings.DATABASE_URL.replace(
        "luckygas_db", "luckygas_migration_test"
    )

    # Create engine
    engine = create_async_engine(test_db_url)

    # Ensure clean state
    async with engine.begin() as conn:
        # Drop existing tables
        await conn.execute(text("DROP TABLE IF EXISTS customers CASCADE"))
        await conn.execute(text("DROP TABLE IF EXISTS migration_audit CASCADE"))
        await conn.execute(text("DROP TABLE IF EXISTS rollback_checkpoints CASCADE"))

        # Create customers table with all fields
        await conn.execute(
            text(
                """
            CREATE TABLE customers (
                id SERIAL PRIMARY KEY,
                client_code VARCHAR(50) UNIQUE NOT NULL,
                invoice_title VARCHAR(255),
                unified_number VARCHAR(20),
                name VARCHAR(100) NOT NULL,
                contact_name VARCHAR(100),
                phone VARCHAR(20),
                mobile VARCHAR(20),
                fax VARCHAR(20),
                email VARCHAR(100),
                address TEXT,
                delivery_address TEXT,
                is_corporate BOOLEAN DEFAULT false,
                is_active BOOLEAN DEFAULT true,
                cylinder_qty_50kg INTEGER DEFAULT 0,
                cylinder_qty_20kg INTEGER DEFAULT 0,
                cylinder_qty_16kg INTEGER DEFAULT 0,
                cylinder_qty_10kg INTEGER DEFAULT 0,
                cylinder_qty_4kg INTEGER DEFAULT 0,
                cylinder_qty_2kg INTEGER DEFAULT 0,
                total_cylinders INTEGER DEFAULT 0,
                pricing_type VARCHAR(50),
                payment_terms VARCHAR(50),
                business_type VARCHAR(50),
                delivery_area VARCHAR(50),
                is_subscription BOOLEAN DEFAULT false,
                requires_same_day_delivery BOOLEAN DEFAULT false,
                closed_days VARCHAR(50),
                monthly_volume FLOAT,
                avg_daily_usage FLOAT,
                max_delivery_cycle_days INTEGER,
                delivery_delay_tolerance INTEGER,
                preferred_delivery_times TEXT,
                notes TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                created_by VARCHAR(50),
                updated_by VARCHAR(50)
            )
        """
            )
        )

        # Create indexes
        await conn.execute(
            text("CREATE INDEX idx_customers_active ON customers(is_active)")
        )
        await conn.execute(
            text("CREATE INDEX idx_customers_corporate ON customers(is_corporate)")
        )
        await conn.execute(
            text("CREATE INDEX idx_customers_area ON customers(delivery_area)")
        )

    # Create session maker
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    yield engine, async_session

    # Cleanup
    await engine.dispose()


@pytest.fixture
def mock_excel_file(tmp_path):
    """Create a mock Excel file for testing"""
    import pandas as pd

    # Create test data
    data = {
        "客戶": ["1234567", "2345678", "3456789"],
        "電子發票抬頭": ["測試公司A", "測試公司B", "測試公司C"],
        "統一編號": ["12345678", "23456789", "34567890"],
        "客戶簡稱": ["公司A", "公司B", "公司C"],
        "聯絡人": ["張三", "李四", "王五"],
        "電話": ["02-12345678", "02-23456789", "02-34567890"],
        "手機": ["0912-345678", "0923-456789", "0934-567890"],
        "地址": [
            "台北市信義區信義路1號",
            "台北市大安區忠孝東路2號",
            "台北市中山區中山北路3號",
        ],
        "系統上鋼瓶數量": [10, 20, 30],
        "50KG": [2, 4, 6],
        "20KG": [3, 5, 7],
        "16KG": [1, 2, 3],
        "10KG": [2, 4, 6],
        "4KG": [2, 5, 8],
        "2KG": [0, 0, 0],
        "計價方式": ["固定價格", "浮動價格", "固定價格"],
        "結帳方式": ["月結", "現金", "月結"],
        "訂閱式會員": [1, 0, 1],
        "需要當天配送": [0, 1, 0],
        "公休日": ["週日", "週六日", "週日"],
        "區域": ["台北", "台北", "台北"],
        "類型": ["餐廳", "飯店", "工廠"],
        "已解約": [0, 0, 1],
        "月配送量": [100.5, 200.0, 150.0],
        "平均日使用": [3.5, 6.5, 5.0],
        "最大週期": [30, 25, 28],
        "可延後天數": [3, 2, 5],
        "備註": ["VIP客戶", "需要特殊處理", "即將解約"],
    }

    # Add time slots
    for hour in range(8, 20):
        slot = f"{hour}~{hour+1}"
        data[slot] = [1 if i == 0 else 0 for i in range(3)]

    # Create Excel file
    excel_path = tmp_path / "test_clients.xlsx"
    df = pd.DataFrame(data)
    df.to_excel(excel_path, index=False)

    return str(excel_path)


@pytest.fixture
async def clean_database(test_database):
    """Ensure database is clean before each test"""
    engine, async_session = test_database

    async with async_session() as session:
        await session.execute(text("DELETE FROM customers"))
        await session.commit()

    yield engine, async_session


@pytest.fixture
def performance_monitor():
    """Monitor test performance"""
    import time
    import psutil

    class PerformanceMonitor:
        def __init__(self):
            self.start_time = None
            self.start_memory = None
            self.process = psutil.Process()

        def start(self):
            self.start_time = time.time()
            self.start_memory = self.process.memory_info().rss / 1024 / 1024  # MB

        def stop(self):
            elapsed_time = time.time() - self.start_time
            end_memory = self.process.memory_info().rss / 1024 / 1024  # MB
            memory_used = end_memory - self.start_memory

            return {
                "elapsed_time": elapsed_time,
                "memory_used_mb": memory_used,
                "start_memory_mb": self.start_memory,
                "end_memory_mb": end_memory,
            }

    return PerformanceMonitor()
