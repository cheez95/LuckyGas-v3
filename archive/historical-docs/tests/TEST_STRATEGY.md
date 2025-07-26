# Lucky Gas Comprehensive Test Strategy

## Overview

This document outlines the test strategy for the Lucky Gas delivery management system, based on the comprehensive test execution analysis with Playwright integration.

## Current State Assessment

### Coverage Baseline
- **Overall Coverage**: 35%
- **Critical Gaps**: Google Cloud services (0%), E2E tests (0%), Integration tests (15%)
- **Infrastructure**: Functional but misconfigured

### Test Distribution
- **Total Tests**: 230
- **Unit Tests**: ~120 (52%)
- **Integration Tests**: ~70 (30%)
- **E2E Tests**: ~40 (18%)

## Test Pyramid Strategy

```
        /\
       /E2E\      10% - Critical user journeys
      /------\
     /  Integ \   30% - Service integration
    /----------\
   /    Unit    \ 60% - Business logic
  /--------------\
```

## Testing Layers

### 1. Unit Tests (Target: 80% Coverage)

#### Focus Areas
- **Models**: Validation logic, computed properties
- **Services**: Business logic, data transformation
- **Utilities**: Helper functions, validators
- **Schemas**: Pydantic validation, serialization

#### Best Practices
```python
# Example: Testing Taiwan-specific validation
@pytest.mark.asyncio
async def test_taiwan_phone_validation():
    with pytest.raises(ValidationError):
        Customer(phone="123")  # Invalid format
    
    customer = Customer(phone="0912-345-678")  # Valid
    assert customer.phone == "0912-345-678"
```

### 2. Integration Tests (Target: 70% Coverage)

#### Focus Areas
- **Database Operations**: CRUD with transactions
- **External Services**: Google Cloud API integration
- **Cache Layer**: Redis operations
- **Message Queue**: WebSocket/real-time features

#### Mock Strategy
```python
# Controlled mocking for external services
@pytest.fixture
def mock_vertex_ai():
    with patch('app.services.google_cloud.vertex_ai') as mock:
        mock.predict.return_value = {
            "predictions": [100, 95, 110],
            "deployedModelId": "test-model"
        }
        yield mock
```

### 3. E2E Tests with Playwright (Target: Critical Paths)

#### Test Scenarios
1. **Customer Journey**
   - Registration → Order → Delivery tracking
   - Traditional Chinese UI validation
   - Mobile responsiveness

2. **Driver Workflow**
   - Login → Route assignment → Delivery completion
   - Offline mode → Sync
   - Real-time updates

3. **Admin Operations**
   - Dashboard metrics
   - Route optimization
   - Report generation

#### Playwright Configuration
```python
# Locale-specific testing
@pytest.fixture
async def taiwan_context(browser):
    context = await browser.new_context(
        locale='zh-TW',
        timezone_id='Asia/Taipei',
        viewport={'width': 390, 'height': 844},  # iPhone 12
        device_scale_factor=3,
    )
    yield context
    await context.close()
```

## Test Data Management

### 1. Factory Pattern
```python
class TestDataFactory:
    @staticmethod
    def create_customer(**overrides):
        defaults = {
            "name": fake.name_taiwan(),
            "phone": fake.phone_number_taiwan(),
            "address": fake.address_taiwan(),
            "area": random.choice(["信義區", "大安區", "中山區"])
        }
        return Customer(**{**defaults, **overrides})
```

### 2. Fixtures Hierarchy
```python
# Session-scoped for expensive operations
@pytest.fixture(scope="session")
async def base_data(db_session):
    # Create base products, areas, etc.

# Function-scoped for test isolation
@pytest.fixture
async def customer_with_orders(db_session, base_data):
    # Create test-specific data
```

### 3. Data Cleanup Strategy
- Transaction rollback for unit tests
- Database truncation for integration tests
- Full reset for E2E tests

## Performance Testing

### Load Testing with K6
```javascript
// scenarios/daily-operations.js
export let options = {
    stages: [
        { duration: '5m', target: 100 },  // Ramp up
        { duration: '10m', target: 100 }, // Stay at 100 users
        { duration: '5m', target: 0 },    // Ramp down
    ],
    thresholds: {
        http_req_duration: ['p(95)<500'], // 95% of requests under 500ms
        http_req_failed: ['rate<0.01'],   // Error rate under 1%
    },
};
```

### WebSocket Stress Testing
```python
# Test concurrent connections
async def test_websocket_100_connections():
    connections = []
    for i in range(100):
        conn = await websocket_connect(f"/ws?token={get_token(i)}")
        connections.append(conn)
    
    # Verify all connected
    # Send messages
    # Check performance
```

## Security Testing

### OWASP Test Cases
1. **SQL Injection**: Parameterized queries validation
2. **Authentication Bypass**: JWT token security
3. **XSS Prevention**: Input sanitization
4. **CSRF Protection**: Token validation
5. **Rate Limiting**: Request throttling

### Taiwan-Specific Security
- ROC ID number validation
- Traditional Chinese input handling
- Local compliance requirements

## CI/CD Integration

### GitHub Actions Workflow
```yaml
name: Test Suite
on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    services:
      postgres:
        image: postgres:14
        env:
          POSTGRES_PASSWORD: luckygas123
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
      redis:
        image: redis:7
        options: >-
          --health-cmd "redis-cli ping"
          --health-interval 10s

    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with:
          python-version: '3.12'
      
      - name: Install dependencies
        run: |
          pip install uv
          uv pip install -r requirements.txt
          uv pip install -r requirements-test.txt
          playwright install
      
      - name: Run tests
        run: |
          pytest --cov=app --cov-report=xml
          
      - name: Upload coverage
        uses: codecov/codecov-action@v3
```

### Quality Gates
- Minimum coverage: 70%
- All tests must pass
- No security vulnerabilities
- Performance benchmarks met

## Test Execution Strategy

### Daily Development
```bash
# Quick unit tests during development
pytest tests/unit -v

# Pre-commit full suite
./scripts/run-tests.sh all true
```

### Pull Request
- Automated test execution
- Coverage report
- Performance regression check
- Security scan

### Release Testing
1. Full regression suite
2. E2E smoke tests
3. Performance benchmarks
4. Security audit

## Monitoring & Metrics

### Key Metrics
1. **Test Coverage Trend**: Track weekly
2. **Test Execution Time**: <5 minutes target
3. **Flaky Test Rate**: <1% target
4. **Bug Escape Rate**: Track production issues

### Test Health Dashboard
```python
# Generate test metrics
def generate_test_report():
    return {
        "total_tests": count_tests(),
        "coverage": get_coverage_percentage(),
        "execution_time": measure_execution_time(),
        "flaky_tests": identify_flaky_tests(),
        "last_run": datetime.now()
    }
```

## Implementation Roadmap

### Week 1: Infrastructure
- ✅ Fix database configuration
- ✅ Complete async test decorators
- ✅ Set up Playwright
- 🔄 Implement missing mocks

### Week 2: Unit Tests
- Achieve 60% coverage
- Fix all import errors
- Add Taiwan-specific validators
- Complete service tests

### Week 3: Integration Tests
- Google Cloud service tests
- Database transaction tests
- Cache layer verification
- WebSocket functionality

### Week 4: E2E Tests
- Critical user journeys
- Mobile experience
- Performance testing
- Security validation

### Ongoing
- Maintain >70% coverage
- Monitor test health
- Optimize execution time
- Update test data

## Success Criteria

1. **Coverage Goals**
   - Overall: >70%
   - Critical paths: 100%
   - New code: >80%

2. **Reliability**
   - Zero flaky tests
   - <5% test maintenance
   - Consistent execution

3. **Performance**
   - Unit tests: <30s
   - Integration: <2m
   - E2E: <5m
   - Total: <10m

4. **Developer Experience**
   - Easy to write tests
   - Fast feedback loop
   - Clear error messages
   - Good documentation

## Conclusion

This comprehensive test strategy provides a roadmap to achieve reliable, maintainable test coverage for the Lucky Gas system. The combination of unit, integration, and E2E tests with Playwright ensures both code quality and user experience validation.