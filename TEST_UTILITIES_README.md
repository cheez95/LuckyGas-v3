# Lucky Gas Test Utilities Documentation

This document describes the comprehensive test utilities available for both backend and frontend testing in the Lucky Gas project.

## Backend Test Utilities

### 1. Test Data Factories

Located in `backend/tests/utils/factories/`

#### UserFactory
```python
from tests.utils import UserFactory

# Create factory
user_factory = UserFactory(db_session)

# Create different user types
admin = await user_factory.create_admin()
driver = await user_factory.create_driver(vehicle_plate="ABC-1234")
office_staff = await user_factory.create_office_staff()

# Create multiple users
users = await user_factory.create_batch(10, role=UserRole.OFFICE_STAFF)

# Create with specific password
user = await user_factory.create_with_password("custom_password")
```

#### CustomerFactory
```python
from tests.utils import CustomerFactory

customer_factory = CustomerFactory(db_session)

# Create different customer types
residential = await customer_factory.create_residential()
business = await customer_factory.create_business(credit_limit=100000)
restaurant = await customer_factory.create_restaurant()
factory = await customer_factory.create_factory()

# Create with specific attributes
subscription_customer = await customer_factory.create_subscription(
    subscription_frequency="weekly"
)
```

#### OrderFactory
```python
from tests.utils import OrderFactory

order_factory = OrderFactory(db_session)

# Create different order states
pending = await order_factory.create_pending(customer_id=1)
confirmed = await order_factory.create_confirmed(customer_id=1)
delivered = await order_factory.create_delivered(customer_id=1, driver_id=2)

# Create with specific products
order = await order_factory.create_with_specific_products(
    customer_id=1,
    qty_50kg=2,
    qty_20kg=3,
    discount_percentage=10
)
```

### 2. API Testing Utilities

#### APITestClient
Enhanced HTTP client with authentication support:

```python
from tests.utils import APITestClient

api_client = APITestClient(client)

# Set authentication
api_client.set_auth_user("admin", UserRole.SUPER_ADMIN)

# Make authenticated requests
response = await api_client.get("/api/v1/customers")
response = await api_client.post("/api/v1/orders", json=data)

# Pagination support
response = await api_client.paginated_get("/api/v1/orders", page=2, size=10)

# Get all pages
all_items = await api_client.get_all_pages("/api/v1/customers")
```

#### APIResponseValidator
Validate API responses:

```python
from tests.utils import APIResponseValidator

# Assert successful response
APIResponseValidator.assert_success(response, status_code=200)

# Assert error response
APIResponseValidator.assert_error(response, 400, "Invalid input")

# Assert pagination structure
APIResponseValidator.assert_pagination(response)

# Assert item exists in list
APIResponseValidator.assert_item_in_list(response, "customer_code", "C001")
```

### 3. Mock Services

#### MockGoogleRoutesService
```python
from tests.utils import MockGoogleRoutesService

routes_service = MockGoogleRoutesService()

# Set custom response
routes_service.set_response("optimize_route", {
    "total_distance_km": 25.5,
    "optimized_stops": []
})

# Use in test
result = await routes_service.optimize_route(stops)

# Check call count
assert routes_service.get_call_count("optimize_route") == 1
```

#### MockRedisClient
```python
from tests.utils import MockRedisClient

redis = MockRedisClient()
await redis.set("key", "value", ex=60)  # With expiration
value = await redis.get("key")
exists = await redis.exists("key")
```

### 4. Database Utilities

#### TestDatabase
```python
from tests.utils import TestDatabase

test_db = TestDatabase()

# Setup and teardown
await test_db.setup()
await test_db.teardown()

# Clear all tables
await test_db.clear_all_tables()

# Create snapshot
snapshot = await test_db.create_test_snapshot(session)

# Seed basic data
await test_db.seed_basic_data(session)
```

#### Database Transaction
```python
from tests.utils import DatabaseTransaction, run_in_transaction

# Use as context manager
async with DatabaseTransaction(session) as tx_session:
    # All changes will be rolled back
    customer = await customer_factory.create()

# Or use helper function
result = await run_in_transaction(session, my_function, arg1, arg2)
```

### 5. Performance Testing

#### PerformanceMonitor
```python
from tests.utils import PerformanceMonitor

monitor = PerformanceMonitor()

# Measure single operation
async with monitor.measure("create_customer"):
    await customer_factory.create()

# Measure concurrent operations
metric = await monitor.measure_concurrent(
    "concurrent_creation",
    create_func,
    concurrency=10,
    iterations=100
)

# Get summary
summary = monitor.get_summary()

# Assert performance
monitor.assert_performance(
    "create_customer",
    max_duration_ms=100,
    max_memory_mb=10,
    max_cpu_percent=50
)
```

#### LoadTester
```python
from tests.utils import LoadTester

load_tester = LoadTester()

# Run load test
results = await load_tester.run_load_test(
    func=api_call,
    duration_seconds=60,
    rps=100  # Requests per second
)

print(f"Success rate: {1 - results['error_rate']:.2%}")
print(f"P95 latency: {results['latency']['p95_ms']}ms")
```

## Frontend Test Utilities

### 1. Enhanced Rendering

Located in `frontend/src/tests/utils/render.tsx`

```tsx
import { render, renderAsAdmin, renderAsDriver, renderUnauthenticated } from '../tests/utils';

// Basic render with custom options
render(<Component />, {
  user: customUser,
  initialRoute: '/orders',
  wsConnected: true,
  locale: 'zh-TW'
});

// Role-specific rendering
renderAsAdmin(<AdminComponent />);
renderAsDriver(<DriverComponent />);
renderUnauthenticated(<PublicComponent />);
```

### 2. Mock Data Generators

```tsx
import { 
  createMockCustomer, 
  createMockOrder, 
  createMockOrders,
  createPaginatedResponse 
} from '../tests/utils';

// Create single items
const customer = createMockCustomer({ area: '大安區' });
const order = createMockOrder({ status: 'delivered' });

// Create multiple items
const customers = createMockCustomers(50);
const orders = createMockOrders(100);

// Create API responses
const response = createPaginatedResponse(customers, page=1, size=20);
```

### 3. Mock API Setup

```tsx
import { setupMockServer, mockApiSuccess, mockApiError, mockApiDelay } from '../tests/utils';

// Setup server for all tests
setupMockServer();

// Mock specific endpoints
mockApiSuccess('get', '/api/v1/customers', { items: customers });
mockApiError('/api/v1/orders', 500, 'Server Error');
mockApiDelay('/api/v1/routes', 2000); // 2 second delay
```

### 4. Test Helpers

#### Form Helpers
```tsx
import { fillForm, submitForm, selectOption, selectDate } from '../tests/utils';

// Fill form fields
await fillForm({
  '客戶名稱': '測試客戶',
  '地區': '信義區',
  '企業客戶': true  // Checkbox
});

// Select from dropdown
await selectOption('付款方式', '月結');

// Select date
await selectDate('預定日期', new Date('2024-12-25'));

// Submit form
await submitForm('提交');
```

#### Table Helpers
```tsx
import { getTableRows, findRowByText, getTableCellValue } from '../tests/utils';

// Get all rows
const rows = getTableRows();

// Find specific row
const row = findRowByText('C001');

// Get cell value
const value = getTableCellValue(row, 2); // 3rd column
```

#### Wait Helpers
```tsx
import { waitForLoadingToFinish, waitForModal, waitForElementToBeRemoved } from '../tests/utils';

// Wait for loading to complete
await waitForLoadingToFinish();

// Wait for modal
await waitForModal('編輯客戶');

// Wait for element removal
await waitForElementToBeRemoved(loadingSpinner);
```

#### Message Helpers
```tsx
import { expectSuccessMessage, expectErrorMessage } from '../tests/utils';

// Assert messages appear
await expectSuccessMessage('保存成功');
await expectErrorMessage('網絡錯誤');
```

### 5. WebSocket Mocking

```tsx
import { WebSocketMock, createWebSocketMessage } from '../tests/utils';

// Create mock WebSocket
const ws = new WebSocketMock('ws://localhost:8000/ws');

// Simulate receiving messages
ws.simulateMessage({
  type: 'order_update',
  data: { order_id: 1, status: 'delivered' }
});

// Simulate error
ws.simulateError();
```

## Best Practices

### 1. Use Factories for Test Data
```python
# Good
customer = await customer_factory.create_business()

# Avoid
customer = Customer(
    customer_code="C001",
    short_name="Test",
    # ... many more fields
)
```

### 2. Use Performance Monitoring in Critical Tests
```python
async with monitor.measure("critical_operation"):
    result = await perform_operation()

monitor.assert_performance("critical_operation", max_duration_ms=50)
```

### 3. Mock External Services
```python
# Setup mock
google_routes = MockGoogleRoutesService()
app.dependency_overrides[get_google_routes] = lambda: google_routes

# Configure response
google_routes.set_response("optimize_route", test_response)
```

### 4. Use Role-Based Rendering
```tsx
// Test admin-specific features
renderAsAdmin(<AdminDashboard />);

// Test public features
renderUnauthenticated(<LandingPage />);
```

### 5. Batch API Calls in Tests
```python
# Use get_all_pages for complete data
all_customers = await api_client.get_all_pages("/api/v1/customers")

# Instead of multiple paginated calls
```

## Running Tests

### Backend
```bash
cd backend

# Run all tests
pytest

# Run with coverage
pytest --cov=app --cov-report=html

# Run specific test file
pytest tests/examples/test_with_utilities.py

# Run with performance profiling
pytest --profile
```

### Frontend
```bash
cd frontend

# Run all tests
npm test

# Run with coverage
npm run test:coverage

# Run in watch mode
npm run test:watch

# Run specific test
npm test ExampleWithUtilities.test.tsx
```

## Troubleshooting

### Backend Issues

1. **Database connection errors**: Ensure PostgreSQL is running and test database exists
2. **Import errors**: Run `uv pip install -e .` in backend directory
3. **Async warnings**: Use `pytest-asyncio` fixtures properly

### Frontend Issues

1. **Module not found**: Check `tsconfig.json` paths configuration
2. **Act warnings**: Wrap state updates in `act()` or use `waitFor()`
3. **WebSocket errors**: Ensure mock WebSocket is properly initialized

## Contributing

When adding new test utilities:

1. Follow existing patterns and naming conventions
2. Add TypeScript/Python type hints
3. Include docstrings/JSDoc comments
4. Add examples to this README
5. Ensure utilities are exported in index files