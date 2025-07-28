# LuckyGas Production Validation Test Suites

Comprehensive production validation and testing framework for the LuckyGas delivery management system.

## Test Suite Overview

### 1. Load Testing (`/tests/load/`)
- **Tool**: k6
- **Purpose**: Validate system performance under 2x peak traffic load
- **Key Scenarios**:
  - Login surge (morning shift start)
  - Order creation peak (lunch time)
  - Report generation (end of day)
  - Database connection pool stress
  - Mixed realistic load (1000 concurrent users)

### 2. Chaos Engineering (`/tests/chaos/`)
- **Tool**: Chaos Mesh + Custom Scripts
- **Purpose**: Test system resilience and recovery
- **Key Scenarios**:
  - Pod failure tests
  - Network latency injection
  - Database connection drops
  - External API timeouts
  - Memory/CPU stress
  - Cascading failure simulation

### 3. API Integration Tests (`/tests/integration/`)
- **Framework**: Pytest + AsyncIO
- **Purpose**: Validate external API integrations
- **Coverage**:
  - E-Invoice Government API
  - Banking SFTP transfers
  - SMS Gateway
  - Circuit breaker behavior
  - Retry mechanisms

### 4. Rollback Verification (`/tests/rollback/`)
- **Framework**: Pytest + Kubernetes Client
- **Purpose**: Ensure safe rollback procedures
- **Coverage**:
  - Database migration rollback
  - Kubernetes deployment rollback
  - Feature flag rollback
  - Data consistency checks

### 5. Performance Benchmarking (`/tests/performance/`)
- **Framework**: Pytest + Performance Profiling Tools
- **Purpose**: Establish performance baselines
- **Metrics**:
  - API endpoint response times
  - Database query performance
  - Memory usage profiling
  - CPU utilization
  - System resource monitoring

## Running the Tests

### Prerequisites
```bash
# Install test dependencies
pip install -r tests/requirements.txt

# Install k6 for load testing
brew install k6  # macOS
# or
sudo apt-get install k6  # Ubuntu

# Install Chaos Mesh (Kubernetes cluster required)
kubectl apply -f https://mirrors.chaos-mesh.org/v2.5.1/install.yaml
```

### Load Testing
```bash
# Run basic load test
k6 run tests/load/k6-load-test.js

# Run with custom parameters
k6 run -e BASE_URL=https://api.luckygas.com.tw -e MAX_VUS=2000 tests/load/k6-load-test.js

# Run specific scenario
k6 run --scenario=order_creation_peak tests/load/k6-load-test.js
```

### Chaos Engineering
```bash
# Apply chaos scenarios
kubectl apply -f tests/chaos/chaos-scenarios.yaml

# Run chaos test suite
./tests/chaos/run-chaos-tests.sh

# Run specific chaos experiment
kubectl apply -f tests/chaos/scenarios/pod-failure.yaml
```

### Integration Tests
```bash
# Run all integration tests
pytest tests/integration/api_integration_test.py -v

# Run specific test class
pytest tests/integration/api_integration_test.py::TestEInvoiceIntegration -v

# Run with coverage
pytest tests/integration/ --cov=app.services --cov-report=html
```

### Rollback Tests
```bash
# Run rollback verification suite
pytest tests/rollback/rollback_verification_test.py -v

# Test specific rollback scenario
pytest tests/rollback/rollback_verification_test.py::TestDatabaseMigrationRollback -v
```

### Performance Benchmarks
```bash
# Run full benchmark suite
pytest tests/performance/performance_benchmark.py -v

# Run with memory profiling
python -m memory_profiler tests/performance/performance_benchmark.py

# Generate performance report
pytest tests/performance/ --benchmark-only --benchmark-json=benchmark.json
```

## Performance Targets

### API Response Times
- P95: < 200ms
- P99: < 500ms
- Error rate: < 1%

### Database Queries
- Simple queries: < 10ms
- Complex queries: < 100ms
- Connection pool: < 5ms acquisition

### System Resources
- CPU usage: < 80% under normal load
- Memory: < 500MB per pod
- Disk I/O: < 100MB/s sustained

### External APIs
- Circuit breaker activation: 3 failures
- Retry strategy: 3 attempts with exponential backoff
- Timeout: 30s for government APIs, 10s for SMS

## Test Data

Test data files are located in:
- `/tests/load/test-data/` - Load testing data
- `/tests/fixtures/` - General test fixtures

## Monitoring During Tests

### Prometheus Queries
```promql
# API availability
avg_over_time(up{job="luckygas-api"}[5m]) * 100

# Request rate
sum(rate(http_requests_total[5m]))

# Error rate
sum(rate(http_requests_total{status=~"5.."}[5m])) / sum(rate(http_requests_total[5m]))

# P95 response time
histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m]))
```

### Grafana Dashboards
- Load Test Dashboard: `http://grafana.luckygas.local/d/load-test`
- Chaos Engineering: `http://grafana.luckygas.local/d/chaos-eng`
- Performance Metrics: `http://grafana.luckygas.local/d/performance`

## CI/CD Integration

### GitHub Actions
```yaml
name: Production Validation Tests

on:
  schedule:
    - cron: '0 2 * * 6'  # Weekly on Saturday 2 AM
  workflow_dispatch:

jobs:
  load-test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Run Load Tests
        run: |
          k6 run tests/load/k6-load-test.js \
            --out influxdb=http://influxdb:8086/k6
  
  chaos-test:
    runs-on: self-hosted  # Requires Kubernetes access
    steps:
      - uses: actions/checkout@v3
      - name: Run Chaos Tests
        run: ./tests/chaos/run-chaos-tests.sh
```

## Troubleshooting

### Common Issues

1. **k6 connection errors**
   - Verify API endpoint is accessible
   - Check firewall rules
   - Ensure test data exists

2. **Chaos Mesh not working**
   - Verify Chaos Mesh is installed: `kubectl get pods -n chaos-mesh`
   - Check RBAC permissions
   - Ensure target namespace exists

3. **Integration test timeouts**
   - Increase timeout values for slow external APIs
   - Check network connectivity
   - Verify API credentials

4. **Performance degradation**
   - Check database indexes
   - Review connection pool settings
   - Monitor garbage collection

## Best Practices

1. **Run tests in isolated environment**
   - Use dedicated test namespace
   - Separate test database
   - Mock external services when possible

2. **Monitor resource usage**
   - Set resource limits for test pods
   - Monitor cluster capacity
   - Clean up after tests

3. **Version test data**
   - Keep test data in version control
   - Document data dependencies
   - Maintain data consistency

4. **Regular execution**
   - Schedule weekly chaos tests
   - Run load tests before releases
   - Continuous performance monitoring

## Contact

For questions or issues with the test suites:
- Engineering Team: engineering@luckygas.com.tw
- DevOps Team: devops@luckygas.com.tw