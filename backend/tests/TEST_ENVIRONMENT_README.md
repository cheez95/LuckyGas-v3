# Lucky Gas v3 Test Environment

This directory contains a complete test environment for Lucky Gas v3, including mock services, test data, and integration test suites.

## 🚀 Quick Start

```bash
# Start the test environment
./start-test-env.sh

# Run integration tests
./run-integration-tests.sh

# Stop the test environment
./stop-test-env.sh
```

## 📋 Components

### Docker Services

1. **PostgreSQL Test Database** (port 5433)
   - Pre-configured with test schema and extensions
   - Test user: `luckygas_test` / `test_password_secure_123`
   - Database: `luckygas_test`

2. **Redis Test Instance** (port 6380)
   - Configured with password authentication
   - Memory limit: 256MB
   - LRU eviction policy

3. **Mock Google Cloud Services** (port 8080)
   - Google Maps API endpoints
   - Google Routes API
   - Vertex AI predictions
   - Distance Matrix API
   - Places Autocomplete

4. **Mock SMS Gateway** (port 8001)
   - SMS sending simulation
   - Delivery status tracking
   - Bulk SMS support
   - Taiwan phone number validation

5. **Mock E-Invoice Service** (port 8002)
   - Taiwan E-Invoice API simulation
   - Invoice issuance and voiding
   - QR code and barcode generation
   - Winning number checking

6. **Mock Banking API** (port 8003)
   - Account balance inquiry
   - Transfer operations
   - ACH payment orders
   - Account validation

7. **MinIO (S3-compatible storage)** (ports 9000/9001)
   - Mock Google Cloud Storage
   - Web console for file management
   - Default bucket: `lucky-gas-storage`

8. **Mailhog** (ports 1025/8025)
   - SMTP server for email testing
   - Web UI to view sent emails

## 📁 Directory Structure

```
tests/
├── docker-compose.test.yml      # Docker services configuration
├── .env.test                    # Test environment variables
├── init_test_data.py           # Test data seeding script
├── mock-services/              # Mock service implementations
│   ├── gcp/                    # Google Cloud mock services
│   ├── sms/                    # SMS gateway mock
│   ├── einvoice/              # E-Invoice mock service
│   └── banking/               # Banking API mock
├── init-scripts/              # Database initialization
├── start-test-env.sh          # Start test environment
├── stop-test-env.sh           # Stop test environment
└── run-integration-tests.sh   # Run all tests
```

## 🔧 Configuration

### Environment Variables

The `.env.test` file contains all necessary configuration:

- **Database**: PostgreSQL connection settings
- **Redis**: Cache configuration
- **API Keys**: Mock API keys for testing
- **Service URLs**: Mock service endpoints
- **Feature Flags**: Enable/disable features
- **Test Settings**: Data generation parameters

### Test Data

The `init_test_data.py` script creates:

- **Users**: 16+ users with different roles
  - Super Admin, Managers, Office Staff
  - 10 Drivers, Customer Service
- **Customers**: 50 test customers
  - Various types (residential, restaurant, etc.)
  - Taiwan addresses and phone numbers
  - Credit limits and payment terms
- **Products**: 8 gas products and accessories
- **Orders**: 200 historical orders
- **Routes**: 7 days of planned routes
- **Vehicles**: 8 delivery vehicles
- **Delivery History**: Completed deliveries
- **Notifications**: Sample notifications
- **Order Templates**: Regular customer templates

## 🧪 Running Tests

### Start Test Environment

```bash
./start-test-env.sh
```

This will:
1. Stop any existing containers
2. Start all Docker services
3. Wait for services to be healthy
4. Run database migrations
5. Initialize test data

### Run Integration Tests

```bash
./run-integration-tests.sh
```

This runs:
- Unit tests
- Integration tests
- API endpoint tests
- Service tests
- End-to-end tests
- Generates HTML and coverage reports

### Run Specific Test Suites

```bash
# Unit tests only
pytest unit/ -v

# Integration tests only
pytest integration/ -v

# E2E tests only
pytest e2e/ -v

# With coverage
pytest --cov=app --cov-report=html
```

### Test Options

```bash
# Run with specific markers
pytest -m "not slow"

# Run specific test file
pytest integration/test_orders.py

# Run with debugging
pytest -vv -s --tb=long

# Parallel execution
pytest -n 4
```

## 🔑 Test Credentials

### Application Users

| Role | Email | Password |
|------|-------|----------|
| Admin | admin@test.luckygas.tw | TestAdmin123! |
| Manager | manager1@test.luckygas.tw | Manager123! |
| Staff | staff1@test.luckygas.tw | Staff123! |
| Driver | driver1@test.luckygas.tw | Driver123! |

### Service Credentials

- **Database**: luckygas_test / test_password_secure_123
- **MinIO**: minioadmin / minioadmin123
- **Redis**: Password: test_redis_password_123

## 🛠️ Troubleshooting

### Services Won't Start

```bash
# Check Docker status
docker ps -a

# View logs
docker-compose -f docker-compose.test.yml logs [service-name]

# Restart specific service
docker-compose -f docker-compose.test.yml restart [service-name]
```

### Database Issues

```bash
# Connect to test database
psql -h localhost -p 5433 -U luckygas_test -d luckygas_test

# Reset database
docker-compose -f docker-compose.test.yml exec postgres-test psql -U luckygas_test -c "SELECT test_data.reset_test_database();"
```

### Port Conflicts

If you have port conflicts, update the ports in `docker-compose.test.yml`:
- PostgreSQL: 5433 → another port
- Redis: 6380 → another port
- Mock services: 8001-8003 → other ports

### Clean Everything

```bash
# Stop and remove all containers and volumes
docker-compose -f docker-compose.test.yml down -v

# Remove all test data
rm -rf test-report.html htmlcov/ .pytest_cache/
```

## 📊 Test Reports

After running tests, check:
- **HTML Test Report**: `test-report.html`
- **Coverage Report**: `htmlcov/index.html`
- **Docker Logs**: `docker-compose -f docker-compose.test.yml logs`

## 🔄 Continuous Integration

For CI/CD pipelines:

```yaml
# Example GitHub Actions
- name: Start Test Environment
  run: |
    cd backend/tests
    ./start-test-env.sh
    
- name: Run Tests
  run: |
    cd backend/tests
    ./run-integration-tests.sh
    
- name: Upload Coverage
  uses: codecov/codecov-action@v3
  with:
    files: ./backend/tests/coverage.xml
```

## 📝 Writing New Tests

### Test Structure

```python
# tests/integration/test_new_feature.py
import pytest
from httpx import AsyncClient
from app.main import app

@pytest.mark.asyncio
async def test_new_feature():
    async with AsyncClient(app=app, base_url="http://test") as ac:
        response = await ac.get("/api/v1/new-feature")
        assert response.status_code == 200
```

### Using Mock Services

```python
# Mock services are automatically available
async def test_with_mock_sms():
    # SMS will be sent to mock service at http://localhost:8001
    result = await send_sms("+886912345678", "Test message")
    assert result.status == "sent"
```

### Test Fixtures

Common fixtures are available in `conftest.py`:
- `mock_db`: Mock database session
- `mock_user`: Test user object
- `mock_order`: Test order object
- Authentication helpers

## 🚨 Important Notes

1. **Never use test environment for production data**
2. **Mock services are for testing only**
3. **Test data is reset on each start (optional)**
4. **All external API calls go to mock services**
5. **Email sending goes to Mailhog, not real emails**

## 💡 Tips

- Use `docker-compose logs -f` to monitor services
- Check MinIO console at http://localhost:9001 for files
- View sent emails at http://localhost:8025
- Mock services return realistic responses with delays
- Test data uses Taiwan-specific formats and data

## 🤝 Contributing

When adding new tests:
1. Use appropriate test categories (unit, integration, e2e)
2. Mock external dependencies
3. Clean up test data after tests
4. Document any new test utilities
5. Keep tests fast and independent