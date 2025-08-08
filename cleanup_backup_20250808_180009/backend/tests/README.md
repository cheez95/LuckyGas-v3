# Lucky Gas Backend Test Infrastructure

## Overview

This directory contains comprehensive test infrastructure for the Lucky Gas backend, including unit tests, integration tests, E2E tests, and performance tests.

## Test Environment Setup

### Prerequisites

- Docker and Docker Compose installed
- PostgreSQL client tools (for database verification)
- Python 3.11+ with uv package manager

### Quick Start

1. **Start Test Services**:
   ```bash
   cd backend/tests
   docker-compose -f docker-compose.test.yml up -d
   ```

2. **Verify Services**:
   ```bash
   ./start-test-env.sh
   ```

3. **Run Integration Tests**:
   ```bash
   python run_integration_tests.py
   ```

## Test Structure

```
tests/
├── integration/          # Integration tests with real database
│   ├── test_route_optimization_integration.py
│   ├── test_websocket_realtime_integration.py
│   ├── test_epic7_complete_flow.py
│   └── test_analytics_flow.py
├── unit/                 # Unit tests with mocks
├── e2e/                  # End-to-end tests
├── contracts/            # Contract tests
├── utils/                # Test utilities and factories
│   ├── factories/        # Test data factories
│   ├── api.py           # API test helpers
│   └── database.py      # Database test helpers
└── mock-services/        # Mock external services

```

## Test Services

The test environment includes mock services for all external dependencies:

| Service | Port | Description |
|---------|------|-------------|
| PostgreSQL Test | 5433 | Test database (luckygas_test) |
| Redis Test | 6380 | Test cache and pub/sub |
| Mock GCP | 8080 | Google Cloud services mock |
| Mock SMS | 8001 | SMS gateway mock |
| Mock E-Invoice | 8002 | Taiwan e-invoice API mock |
| Mock Banking | 8003 | Banking API mock |
| MinIO | 9000 | S3-compatible storage |
| MailHog | 8025 | Email testing (Web UI) |

## Running Tests

### All Integration Tests
```bash
pytest tests/integration/
```

### Specific Test File
```bash
pytest tests/integration/test_route_optimization_integration.py -v
```

### Epic 7 Complete Flow
```bash
pytest tests/integration/test_epic7_complete_flow.py -v
```

### With Coverage
```bash
pytest tests/integration/ --cov=app --cov-report=html
```

### Performance Tests
```bash
pytest tests/integration/ -m performance
```

## Test Factories

We use factory classes to generate test data consistently:

```python
from tests.utils.factories import CustomerFactory, OrderFactory, RouteFactory

# Create test customer
customer = await CustomerFactory(db_session).create(
    customer_code="TEST001",
    area="信義區"
)

# Create batch of orders
orders = await OrderFactory(db_session).create_batch(
    10,
    customer_id=customer.id,
    scheduled_date=date.today()
)

# Create route with stops
route = await RouteFactory(db_session).create_with_stops(
    driver=driver,
    vehicle=vehicle,
    num_stops=5
)
```

## Test Utilities

### API Test Client
```python
from tests.utils.api import APITestClient

client = APITestClient(async_client)
client.set_auth_user("testuser", UserRole.OFFICE_STAFF)

response = await client.get("/api/v1/orders")
```

### Database Helpers
```python
from tests.utils.database import TestDatabase

test_db = TestDatabase()
await test_db.setup()
await test_db.seed_basic_data(session)
```

## Environment Variables

Test environment uses `.env.test` file with these key settings:

```env
ENVIRONMENT=test
POSTGRES_PORT=5433
POSTGRES_DB=luckygas_test
REDIS_URL=redis://localhost:6380/1
DEVELOPMENT_MODE=offline
```

## Writing New Tests

### Integration Test Template
```python
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

class TestFeatureName:
    @pytest.mark.asyncio
    async def test_feature_flow(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        auth_headers: dict
    ):
        # Arrange: Create test data
        
        # Act: Perform operations
        
        # Assert: Verify results
        pass
```

### Best Practices

1. **Use Factories**: Always use factories for test data creation
2. **Clean State**: Each test should start with a clean database state
3. **Mock External Services**: Use mock services for external APIs
4. **Test Real Flows**: Integration tests should test complete user flows
5. **Verify Side Effects**: Check WebSocket notifications, analytics updates, etc.

## Troubleshooting

### Services Not Starting
```bash
# Check Docker logs
docker-compose -f docker-compose.test.yml logs

# Restart specific service
docker-compose -f docker-compose.test.yml restart postgres-test
```

### Database Connection Issues
```bash
# Verify PostgreSQL is running
nc -z localhost 5433

# Check database exists
PGPASSWORD=test_password_secure_123 psql -h localhost -p 5433 -U luckygas_test -d luckygas_test -c "\dt"
```

### Test Failures
- Check if all mock services are running
- Verify test database is clean
- Look for any remaining transactions
- Check test logs for detailed errors

## Continuous Integration

The test suite is designed to run in CI/CD pipelines:

```yaml
# Example GitHub Actions workflow
- name: Run Integration Tests
  run: |
    docker-compose -f tests/docker-compose.test.yml up -d
    sleep 10  # Wait for services
    pytest tests/integration/ --cov=app
```

## Performance Benchmarks

Expected performance for Epic 7 operations:

- Route optimization (10 orders): < 2 seconds
- Route optimization (100 orders): < 10 seconds
- Real-time adjustment: < 500ms
- WebSocket broadcast: < 100ms
- Analytics calculation: < 1 second

## Maintenance

### Updating Mock Services
Mock services are in `mock-services/` directory. Update the Python/Node.js code as needed.

### Database Migrations
Test database uses the same Alembic migrations as production:
```bash
cd backend
alembic upgrade head
```

### Cleaning Test Data
```bash
# Stop and remove all test containers and volumes
docker-compose -f tests/docker-compose.test.yml down -v
```
</content>