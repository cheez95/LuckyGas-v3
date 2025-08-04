"""
Test utilities for Lucky Gas backend
"""

from .auth import get_test_token
from .customer import create_test_customer
from .order import create_test_order
from .database import (
    TestDatabase,
    DatabaseTransaction,
    run_in_transaction,
    assert_database_empty,
    create_bulk_test_data,
)
from .api import (
    APITestClient,
    APIResponseValidator,
    create_test_token as create_token,
    decode_token,
    MockExternalAPI,
    assert_websocket_message,
    create_form_data,
)
from .mocks import (
    MockService,
    MockGoogleRoutesService,
    MockVertexAIService,
    MockSMSService,
    MockEInvoiceService,
    MockRedisClient,
    create_mock_websocket,
    create_mock_file_upload,
)
from .performance import (
    PerformanceMonitor,
    LoadTester,
    benchmark,
    stress_test_database,
    PerformanceMetrics,
)
from .factories import UserFactory, CustomerFactory, OrderFactory

__all__ = [
    # Auth utilities
    "get_test_token",
    "create_token",
    "decode_token",
    # Customer utilities
    "create_test_customer",
    # Order utilities
    "create_test_order",
    # Database utilities
    "TestDatabase",
    "DatabaseTransaction",
    "run_in_transaction",
    "assert_database_empty",
    "create_bulk_test_data",
    # API utilities
    "APITestClient",
    "APIResponseValidator",
    "MockExternalAPI",
    "assert_websocket_message",
    "create_form_data",
    # Mock utilities
    "MockService",
    "MockGoogleRoutesService",
    "MockVertexAIService",
    "MockSMSService",
    "MockEInvoiceService",
    "MockRedisClient",
    "create_mock_websocket",
    "create_mock_file_upload",
    # Performance utilities
    "PerformanceMonitor",
    "LoadTester",
    "benchmark",
    "stress_test_database",
    "PerformanceMetrics",
    # Factories
    "UserFactory",
    "CustomerFactory",
    "OrderFactory",
]
