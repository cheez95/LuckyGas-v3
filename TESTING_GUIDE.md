# 🧪 Lucky Gas Testing Guide

## 📋 Overview

Lucky Gas uses a comprehensive testing strategy with multiple test types:
- **Unit Tests**: Test individual components in isolation
- **Integration Tests**: Test interactions between components
- **End-to-End Tests**: Test complete user workflows
- **Performance Tests**: Ensure system meets performance requirements
- **Security Tests**: Validate security measures

## 🚀 Quick Start

### Running All Tests
```bash
cd backend
./run_tests.sh
```

### Running Specific Test Categories
```bash
# Unit tests only
./run_tests.sh unit

# Integration tests
./run_tests.sh integration

# End-to-end tests
./run_tests.sh e2e

# Specific API tests
./run_tests.sh auth        # Authentication tests
./run_tests.sh customers   # Customer API tests
./run_tests.sh orders      # Order API tests
./run_tests.sh routes      # Route optimization tests
./run_tests.sh predictions # AI/ML prediction tests
```

### Running Tests Without Coverage
```bash
./run_tests.sh all no
```

## 📂 Test Structure

```
backend/tests/
├── conftest.py              # Pytest configuration and fixtures
├── test_utils.py            # Test utilities and helpers
├── test_api_auth.py         # Authentication API tests
├── test_api_customers.py    # Customer management tests
├── test_api_orders.py       # Order management tests
├── test_api_routes.py       # Route optimization tests
├── test_api_predictions.py  # AI/ML prediction tests
├── unit/                    # Unit tests
│   ├── test_models.py
│   ├── test_services.py
│   └── test_utils.py
├── integration/             # Integration tests
│   ├── test_workflows.py
│   └── test_external_apis.py
└── e2e/                     # End-to-end tests
    ├── test_order_flow.py
    └── test_delivery_flow.py
```

## 🔧 Test Configuration

### Environment Variables
Test environment is configured in `pytest.ini`:
```ini
[pytest]
env = 
    TESTING=1
    DATABASE_URL=postgresql+asyncpg://test:test@localhost:5432/luckygas_test
    SECRET_KEY=test-secret-key
    ENVIRONMENT=test
    LOG_LEVEL=DEBUG
```

### Test Database
Tests use a separate PostgreSQL database (`luckygas_test`) that is:
- Created automatically when running tests
- Cleaned after each test
- Isolated from development/production data

### Fixtures
Common fixtures available in all tests:
- `client`: Async HTTP client for API testing
- `db_session`: Database session for data setup
- `auth_headers`: Authentication headers for protected endpoints
- `test_data`: Pre-configured test data factory

## 📝 Writing Tests

### Basic Test Structure
```python
import pytest
from httpx import AsyncClient

class TestCustomerAPI:
    @pytest.mark.asyncio
    async def test_create_customer(self, client: AsyncClient, auth_headers):
        """Test creating a new customer"""
        response = await client.post(
            "/api/v1/customers/",
            json={
                "name": "測試客戶",
                "phone": "0912345678",
                "address": "台北市信義區",
                "district": "信義區",
                "customer_type": "residential"
            },
            headers=auth_headers
        )
        
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "測試客戶"
```

### Using Test Utilities
```python
from tests.test_utils import TestDataFactory, TestAssertions

class TestOrderFlow:
    @pytest.mark.asyncio
    async def test_complete_order_flow(self, db_session, client, auth_headers):
        # Create test data
        factory = TestDataFactory()
        customer = await factory.create_test_customer(db_session)
        product = await factory.create_test_product(db_session)
        
        # Test order creation
        response = await client.post(...)
        
        # Use common assertions
        TestAssertions.assert_pagination_response(response.json())
        TestAssertions.assert_valid_phone(customer.phone)
```

### Test Markers
```python
@pytest.mark.unit
async def test_password_hashing():
    """Unit test for password hashing"""
    pass

@pytest.mark.integration
async def test_google_routes_integration():
    """Integration test with Google Routes API"""
    pass

@pytest.mark.e2e
async def test_complete_delivery_workflow():
    """End-to-end test of delivery process"""
    pass

@pytest.mark.slow
async def test_large_route_optimization():
    """Slow test that takes > 5 seconds"""
    pass

@pytest.mark.external
async def test_vertex_ai_prediction():
    """Test requiring external services"""
    pass
```

## 🎯 Test Coverage

### Current Coverage Goals
- **Overall**: 80% minimum
- **Critical Paths**: 95% (auth, payments, orders)
- **API Endpoints**: 100%
- **Business Logic**: 90%
- **Utilities**: 70%

### Viewing Coverage Reports
After running tests with coverage:
```bash
# Terminal report
# Automatically shown after test run

# HTML report
open htmlcov/index.html

# Generate XML report for CI
pytest --cov-report=xml
```

## 🔍 Test Categories

### 1. Authentication Tests (`test_api_auth.py`)
- Login/logout functionality
- Token generation and refresh
- Role-based access control
- Password security
- Session management

### 2. Customer Tests (`test_api_customers.py`)
- CRUD operations
- Search and filtering
- Pagination
- Data validation
- Bulk operations

### 3. Order Tests (`test_api_orders.py`)
- Order creation and updates
- Status transitions
- Recurring orders
- Payment processing
- Delivery scheduling

### 4. Route Tests (`test_api_routes.py`)
- Route optimization algorithms
- Real-time updates
- Driver assignments
- Distance calculations
- Performance metrics

### 5. Prediction Tests (`test_api_predictions.py`)
- Demand forecasting
- Revenue predictions
- Route optimization
- Anomaly detection
- Model accuracy tracking

## 🐛 Debugging Tests

### Running Specific Tests
```bash
# Run single test file
pytest tests/test_api_customers.py

# Run single test class
pytest tests/test_api_orders.py::TestOrderAPI

# Run single test method
pytest tests/test_api_auth.py::TestAuthenticationAPI::test_login_success

# Run tests matching pattern
pytest -k "test_create"
```

### Verbose Output
```bash
# Show print statements
pytest -s

# Show detailed test output
pytest -vv

# Show local variables on failure
pytest -l
```

### Debugging with PDB
```python
def test_complex_logic():
    import pdb; pdb.set_trace()  # Debugger breakpoint
    # Test code here
```

## 🚦 Continuous Integration

### GitHub Actions Workflow
```yaml
name: Tests
on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    
    services:
      postgres:
        image: postgres:15
        env:
          POSTGRES_PASSWORD: test
          POSTGRES_DB: luckygas_test
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
      
      redis:
        image: redis:7
        options: >-
          --health-cmd "redis-cli ping"
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
    
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      
      - name: Install dependencies
        run: |
          pip install uv
          cd backend
          uv pip install -r requirements.txt
          uv pip install pytest pytest-asyncio pytest-cov
      
      - name: Run tests
        run: |
          cd backend
          ./run_tests.sh
```

## 📊 Performance Testing

### Load Testing with Locust
```python
# locustfile.py
from locust import HttpUser, task, between

class LuckyGasUser(HttpUser):
    wait_time = between(1, 3)
    
    @task
    def list_orders(self):
        self.client.get("/api/v1/orders/")
    
    @task
    def create_order(self):
        self.client.post("/api/v1/orders/", json={...})
```

Run load tests:
```bash
locust -f locustfile.py --host=http://localhost:8000
```

## 🔒 Security Testing

### Running Security Scans
```bash
# Dependency vulnerability scan
pip-audit

# Static security analysis
bandit -r app/

# SQL injection testing
sqlmap -u "http://localhost:8000/api/v1/customers/?search=test"
```

## 💡 Best Practices

### 1. Test Isolation
- Each test should be independent
- Use fixtures for setup/teardown
- Don't rely on test execution order

### 2. Test Data
- Use factories for consistent test data
- Clean up after tests
- Avoid hardcoded IDs

### 3. Assertions
- Be specific in assertions
- Test both success and failure cases
- Verify side effects

### 4. Async Testing
- Always use `@pytest.mark.asyncio`
- Properly await async operations
- Use async fixtures when needed

### 5. External Services
- Mock external API calls
- Use test doubles for third-party services
- Mark tests requiring external services

## 🆘 Troubleshooting

### Common Issues

1. **Database Connection Errors**
   ```bash
   # Ensure PostgreSQL is running
   brew services start postgresql
   
   # Create test database
   createdb luckygas_test
   ```

2. **Redis Connection Errors**
   ```bash
   # Start Redis
   brew services start redis
   ```

3. **Import Errors**
   ```bash
   # Ensure you're in the backend directory
   cd backend
   
   # Install dependencies
   uv pip install -r requirements.txt
   ```

4. **Async Test Failures**
   - Ensure `@pytest.mark.asyncio` decorator is used
   - Check for missing `await` keywords
   - Verify event loop configuration

## 📚 Additional Resources

- [Pytest Documentation](https://docs.pytest.org/)
- [Testing FastAPI Applications](https://fastapi.tiangolo.com/tutorial/testing/)
- [AsyncIO Testing](https://pytest-asyncio.readthedocs.io/)
- [Test-Driven Development](https://testdriven.io/)