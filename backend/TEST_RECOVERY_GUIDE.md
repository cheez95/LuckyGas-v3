# Test Infrastructure Recovery Guide

## 🚨 URGENT: Test Infrastructure Recovery for Lucky Gas v3

This guide provides step-by-step instructions to recover and rebuild the test infrastructure for the Lucky Gas v3 pilot launch.

## Quick Start (5 minutes)

```bash
# 1. Install missing dependencies
uv sync

# 2. Fix import issues
python fix_test_imports.py

# 3. Setup test environment
./setup_tests.sh

# 4. Validate infrastructure
python tests/validate_test_infrastructure.py

# 5. Run all tests
./run_all_tests.sh
```

## Detailed Recovery Steps

### 1. Environment Setup (Day 1)

#### Fix Python Dependencies
```bash
# Dependencies have been added to pyproject.toml:
# - jinja2>=3.1.6
# - pytest-json-report>=1.5.0
# - aiofiles>=24.1.0
# - beautifulsoup4>=4.12.3

# Sync all dependencies
uv sync
```

#### Setup Test Database
```bash
# Start test containers
docker-compose -f docker-compose.test.yml up -d

# Run migrations
uv run alembic upgrade head

# Seed test data
uv run python app/scripts/setup_test_users.py
```

### 2. Fix Import Issues

Common issues and fixes:
- **maps_api_key**: Changed to `GOOGLE_MAPS_API_KEY`
- **Async fixtures**: Use `@pytest_asyncio.fixture`
- **Event loop**: Single session-scoped fixture
- **Import paths**: Use absolute imports from `app`

Run the automatic fixer:
```bash
python fix_test_imports.py
```

### 3. Test Data Fixtures

Test data is now centralized in `tests/fixtures/test_data.py`:
- 5 sample customers with Taiwan addresses
- Order history with proper dates
- Payment records
- Invoice data
- Migration scenarios

### 4. Chaos Engineering Tests

Located in `tests/chaos/`:
- **Pod Failure Recovery**: `test_pod_failure.py`
- **Network Chaos**: `test_network_chaos.py`
- **Database Chaos**: `test_database_chaos.py`
- **External API Failures**: `test_external_api_chaos.py`
- **Resource Exhaustion**: `test_resource_exhaustion.py`

Run chaos tests:
```bash
cd tests/chaos
python run_chaos_tests.py
```

### 5. E2E Test Fixes

E2E tests use Playwright for browser automation:
```bash
# Install Playwright browsers
uv run playwright install

# Run E2E tests
uv run pytest tests/e2e -m e2e -v
```

## Test Execution Strategy

### Priority 1: Critical Path Tests
These must pass for pilot launch:
```bash
# Authentication
uv run pytest tests/test_auth.py -v

# Customer Management
uv run pytest tests/test_customers.py -v
uv run pytest tests/e2e/test_customer_management.py -v

# Order Processing
uv run pytest tests/test_orders.py -v
uv run pytest tests/e2e/test_order_flow.py -v

# Payment & Invoicing
uv run pytest tests/test_credit_limit.py -v
uv run pytest tests/services/test_einvoice_service.py -v
```

### Priority 2: Integration Tests
```bash
# External APIs
uv run pytest tests/integration/test_einvoice_integration.py -v
uv run pytest tests/integration/test_banking_integration.py -v

# Real-time Features
uv run pytest tests/integration/test_websocket_realtime.py -v
```

### Priority 3: Chaos Tests
```bash
# Run in staging environment only
RUN_CHAOS_TESTS=true ./run_all_tests.sh
```

## Common Issues & Solutions

### Issue: "Module 'maps_api_key' not found"
**Solution**: Run `python fix_test_imports.py` to update deprecated imports

### Issue: "Event loop is closed"
**Solution**: Ensure single event_loop fixture in conftest.py

### Issue: "Database connection failed"
**Solution**: 
```bash
docker-compose -f docker-compose.test.yml down
docker-compose -f docker-compose.test.yml up -d
```

### Issue: "Redis connection refused"
**Solution**: Check Redis is running on port 6379

### Issue: "Playwright not found"
**Solution**: `uv run playwright install`

## Validation Checklist

- [ ] All dependencies installed (`uv sync`)
- [ ] Test database accessible
- [ ] Redis connected
- [ ] All test files present
- [ ] Import issues fixed
- [ ] E2E tests passing (>95%)
- [ ] Chaos tests implemented
- [ ] Coverage >80%

## Performance Baselines

Expected test execution times:
- Unit tests: <30 seconds
- Integration tests: <2 minutes
- E2E tests: <5 minutes
- Chaos tests: <10 minutes
- Full suite: <20 minutes

## CI/CD Integration

GitHub Actions workflow:
```yaml
name: Tests
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Setup Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.12'
      - name: Install dependencies
        run: |
          pip install uv
          uv sync
      - name: Run tests
        run: ./run_all_tests.sh
```

## Monitoring Test Health

1. **Daily Checks**:
   - Run validation script: `python tests/validate_test_infrastructure.py`
   - Check test coverage trend
   - Review flaky test reports

2. **Weekly Tasks**:
   - Run full chaos test suite
   - Update test data fixtures
   - Review and fix slow tests

3. **Before Each Release**:
   - Full test suite pass
   - Coverage >80%
   - No flaky tests
   - Chaos tests in staging

## Emergency Contacts

- **Test Infrastructure**: DevOps team
- **E2E Tests**: QA team  
- **Chaos Tests**: SRE team
- **Performance Tests**: Performance team

---

**Remember**: A robust test suite is critical for the pilot launch. Invest time in fixing tests now to prevent production issues later.