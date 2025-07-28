# Test Infrastructure Fix Action Plan

## Priority 1: Environment Setup (Day 1)

### 1. Fix Python Dependencies
```bash
# Add to pyproject.toml dependencies:
"jinja2>=3.1.6"
"pytest-json-report>=1.5.0"
"aiofiles>=24.1.0"
"beautifulsoup4>=4.12.3"

# Sync environment
uv sync
```

### 2. Fix Import Issues
- Fix deprecated `maps_api_key` access
- Update import paths in test files
- Ensure PYTHONPATH is set correctly

### 3. Create Test Setup Script
```bash
#!/bin/bash
# setup_tests.sh
export PYTHONPATH="/Users/lgee258/Desktop/LuckyGas-v3/backend:$PYTHONPATH"
export ENVIRONMENT="test"
export DATABASE_URL="postgresql://test:test@localhost:5432/luckygas_test"

# Start test database
docker-compose -f docker-compose.test.yml up -d

# Run migrations
uv run alembic upgrade head

# Seed test data
uv run python app/scripts/setup_test_users.py
```

## Priority 2: Chaos Engineering Suite (Day 2-3)

### 1. Create Chaos Test Framework
```python
# tests/chaos/test_service_failures.py
import asyncio
import pytest
from httpx import AsyncClient

class TestServiceFailures:
    @pytest.mark.asyncio
    async def test_database_connection_failure(self):
        """Test system behavior when database becomes unavailable."""
        # Simulate DB failure
        # Verify circuit breaker activation
        # Check graceful degradation
        
    @pytest.mark.asyncio
    async def test_redis_failure_recovery(self):
        """Test system behavior when Redis fails."""
        # Kill Redis connection
        # Verify fallback to DB
        # Test recovery when Redis returns
        
    @pytest.mark.asyncio
    async def test_external_api_timeout(self):
        """Test timeout handling for external APIs."""
        # Mock slow API responses
        # Verify timeout behavior
        # Check fallback mechanisms
```

### 2. Network Partition Tests
```python
# tests/chaos/test_network_partitions.py
class TestNetworkPartitions:
    @pytest.mark.asyncio
    async def test_partial_network_failure(self):
        """Test behavior during partial network failures."""
        # Simulate 50% packet loss
        # Verify retry mechanisms
        # Check data consistency
        
    @pytest.mark.asyncio
    async def test_complete_network_isolation(self):
        """Test behavior when completely isolated."""
        # Block all external connections
        # Verify offline mode
        # Test data sync on reconnection
```

### 3. Resource Exhaustion Tests
```python
# tests/chaos/test_resource_exhaustion.py
class TestResourceExhaustion:
    @pytest.mark.asyncio
    async def test_memory_exhaustion(self):
        """Test behavior at memory limits."""
        # Consume available memory
        # Verify graceful degradation
        # Check memory leak prevention
        
    @pytest.mark.asyncio
    async def test_cpu_throttling(self):
        """Test behavior under CPU constraints."""
        # Simulate high CPU load
        # Verify request prioritization
        # Check performance degradation
        
    @pytest.mark.asyncio
    async def test_disk_space_limits(self):
        """Test behavior when disk is full."""
        # Fill available disk space
        # Verify log rotation
        # Check data handling
```

## Priority 3: E2E Test Fixes (Day 2)

### 1. Fix Test Configuration
```python
# tests/conftest.py
import os
os.environ["ENVIRONMENT"] = "test"
os.environ["DISABLE_GOOGLE_APIS"] = "true"

# Fix async event loop
import asyncio
import pytest

@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()
```

### 2. Fix Individual Test Files
- Update async test patterns
- Fix fixture dependencies
- Add proper test isolation

## Priority 4: Performance Testing (Day 3-4)

### 1. Load Testing Suite
```python
# tests/performance/test_load.py
import locust

class UserBehavior(locust.TaskSet):
    @locust.task
    def create_order(self):
        # Test order creation under load
        
    @locust.task
    def update_delivery_status(self):
        # Test status updates under load
```

### 2. Baseline Measurements
- API response times (p50, p95, p99)
- Database query performance
- WebSocket message latency
- Migration processing speed

## Priority 5: Feature Flag Testing (Day 4)

### 1. Pilot Scenario Tests
```python
# tests/e2e/test_feature_flags_pilot.py
class TestFeatureFlagPilot:
    async def test_5_customer_pilot(self):
        """Test enabling feature for 5 specific customers."""
        
    async def test_percentage_rollout(self):
        """Test gradual percentage-based rollout."""
        
    async def test_emergency_kill_switch(self):
        """Test immediate feature disablement."""
        
    async def test_ab_testing(self):
        """Test A/B variant distribution."""
```

## Priority 6: Migration Testing (Day 5)

### 1. Production-Like Data Tests
```python
# tests/integration/test_migration_production.py
class TestProductionMigration:
    async def test_10k_customer_migration(self):
        """Test migrating 10,000 customers."""
        
    async def test_concurrent_migrations(self):
        """Test multiple simultaneous migrations."""
        
    async def test_migration_rollback(self):
        """Test rollback with data integrity."""
```

## Validation Checklist

- [ ] All dependencies installed
- [ ] Test environment starts cleanly
- [ ] All E2E tests pass (>95%)
- [ ] Chaos tests implemented and passing
- [ ] Performance baselines established
- [ ] Feature flag scenarios tested
- [ ] Migration tools validated
- [ ] Monitoring verified
- [ ] Documentation updated

## Success Criteria

1. **E2E Tests**: >95% pass rate
2. **Unit Tests**: >99% pass rate
3. **Chaos Tests**: All scenarios handled gracefully
4. **Performance**: Meets defined SLAs
5. **Feature Flags**: All pilot scenarios work
6. **Migrations**: <5min for 10K customers
7. **Monitoring**: All alerts fire correctly

---
*Timeline: 5 days minimum*
*Resources: 2-3 developers*
*Priority: CRITICAL for pilot*