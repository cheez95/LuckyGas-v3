# Lucky Gas Week 1 Testing Framework

**Generated**: 2025-07-26  
**Purpose**: Immediate testing infrastructure for critical Week 1 actions  
**Approach**: Parallel execution where possible

## 🎯 Testing Scope for Current 28% Implementation

### What CAN Be Tested Now
1. **Existing Features** (28% of system)
   - Customer CRUD operations
   - Authentication flows
   - WebSocket connections
   - Driver dashboard components
   
2. **Infrastructure**
   - Database connections
   - API endpoints
   - Frontend routing
   - Build processes

3. **Data Validation**
   - Existing customer data
   - Taiwan-specific formats
   - Import/export functions

### What CANNOT Be Tested (72% not built)
- ❌ E-Invoice integration (no API access)
- ❌ Dispatch operations (not implemented)
- ❌ Financial modules (not implemented)
- ❌ Complete order workflow (partial only)
- ❌ GPS tracking (not integrated)
- ❌ Offline mode (not implemented)

---

## 🧪 Day 1: Fix Test Infrastructure

### Frontend Test Setup
```bash
#!/bin/bash
# frontend-test-setup.sh

cd frontend

# Install test dependencies
npm install --save-dev \
  jest \
  @testing-library/react \
  @testing-library/jest-dom \
  @testing-library/user-event \
  jest-environment-jsdom \
  @types/jest

# Create Jest configuration
cat > jest.config.js << 'EOF'
module.exports = {
  preset: 'ts-jest',
  testEnvironment: 'jsdom',
  moduleNameMapper: {
    '\\.(css|less|scss|sass)$': 'identity-obj-proxy',
    '^@/(.*)$': '<rootDir>/src/$1'
  },
  setupFilesAfterEnv: ['<rootDir>/src/setupTests.ts'],
  testMatch: [
    '**/__tests__/**/*.{ts,tsx}',
    '**/*.{test,spec}.{ts,tsx}'
  ]
};
EOF

# Create setup file
cat > src/setupTests.ts << 'EOF'
import '@testing-library/jest-dom';

// Mock WebSocket
global.WebSocket = jest.fn(() => ({
  send: jest.fn(),
  close: jest.fn(),
  addEventListener: jest.fn(),
  removeEventListener: jest.fn(),
}));
EOF

# Update package.json
npm pkg set scripts.test="jest"
npm pkg set scripts.test:watch="jest --watch"
npm pkg set scripts.test:coverage="jest --coverage"
```

### Backend Test Fix
```bash
#!/bin/bash
# backend-test-fix.sh

cd backend

# Fix Python path
echo "export PYTHONPATH=\$PYTHONPATH:\$PWD" >> ~/.bashrc
source ~/.bashrc

# Create test configuration
cat > pytest.ini << 'EOF'
[pytest]
testpaths = tests
python_files = test_*.py
python_classes = Test*
python_functions = test_*
addopts = -v --tb=short --strict-markers
asyncio_mode = auto
EOF

# Fix conftest.py
cat > tests/conftest.py << 'EOF'
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.main import app
from app.database import Base, get_db

# Test database
SQLALCHEMY_DATABASE_URL = "sqlite:///./test.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

@pytest.fixture(scope="function")
def db():
    Base.metadata.create_all(bind=engine)
    yield TestingSessionLocal()
    Base.metadata.drop_all(bind=engine)

@pytest.fixture(scope="function")
def client(db):
    def override_get_db():
        try:
            yield db
        finally:
            db.close()
    
    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
EOF
```

---

## 🔄 Parallel Test Execution Plan

### Test Suite 1: Authentication & Users
```typescript
// frontend/src/__tests__/auth.test.tsx
describe('Authentication Flow', () => {
  test.concurrent('Login with valid credentials', async () => {
    // Test implementation
  });
  
  test.concurrent('Login with invalid credentials', async () => {
    // Test implementation
  });
  
  test.concurrent('JWT token refresh', async () => {
    // Test implementation
  });
  
  test.concurrent('Role-based access control', async () => {
    // Test implementation
  });
});
```

### Test Suite 2: Customer Management
```python
# backend/tests/test_customers.py
import pytest
from httpx import AsyncClient

class TestCustomersParallel:
    @pytest.mark.asyncio
    async def test_create_customer(self, client):
        """Test customer creation with Taiwan validation"""
        customer_data = {
            "customer_code": "C-20250126-0001",
            "short_name": "測試客戶",
            "phone": "0912345678",
            "tax_id": "53212539",
            "address": "台北市中正區重慶南路一段122號"
        }
        response = await client.post("/api/v1/customers", json=customer_data)
        assert response.status_code == 201
    
    @pytest.mark.asyncio
    async def test_taiwan_phone_validation(self, client):
        """Test Taiwan phone number formats"""
        # Test cases for different formats
        pass
    
    @pytest.mark.asyncio
    async def test_tax_id_validation(self, client):
        """Test Taiwan tax ID validation"""
        # Test valid and invalid tax IDs
        pass
```

### Test Suite 3: WebSocket Real-time
```typescript
// frontend/src/__tests__/websocket.test.ts
import { renderHook, act } from '@testing-library/react';
import { useWebSocketContext } from '../contexts/WebSocketContext';

describe('WebSocket Integration', () => {
  test.concurrent('Auto-reconnection on disconnect', async () => {
    // Test reconnection logic
  });
  
  test.concurrent('Message queuing when offline', async () => {
    // Test offline message queue
  });
  
  test.concurrent('Real-time order updates', async () => {
    // Test order status broadcasts
  });
});
```

---

## 📊 Data Validation Tests

### Taiwan-Specific Validation Suite
```python
# backend/tests/test_taiwan_validators.py
import pytest
from app.core.validators import TaiwanValidators

class TestTaiwanValidation:
    @pytest.mark.parametrize("phone,expected", [
        ("0912345678", True),      # Mobile
        ("0912-345-678", True),    # Mobile with dashes
        ("02-2312-3456", True),    # Taipei landline
        ("037-123456", True),      # Other area
        ("1234567890", False),     # Invalid format
    ])
    def test_phone_validation(self, phone, expected):
        assert TaiwanValidators.validate_phone(phone) == expected
    
    @pytest.mark.parametrize("tax_id,expected", [
        ("53212539", True),        # Valid
        ("12345678", False),       # Invalid checksum
        ("5321253", False),        # Too short
    ])
    def test_tax_id_validation(self, tax_id, expected):
        assert TaiwanValidators.validate_tax_id(tax_id) == expected
```

---

## 🚀 E2E Test Framework

### Critical Path Tests
```typescript
// tests/e2e/critical-paths.spec.ts
import { test, expect } from '@playwright/test';

test.describe.parallel('Critical User Paths', () => {
  test('Customer registration flow', async ({ page }) => {
    await page.goto('/customers');
    await page.click('button:has-text("新增客戶")');
    
    // Fill form with Taiwan data
    await page.fill('input[name="name"]', '測試瓦斯行');
    await page.fill('input[name="phone"]', '0912345678');
    await page.fill('input[name="taxId"]', '53212539');
    
    await page.click('button[type="submit"]');
    await expect(page.locator('.ant-message-success')).toBeVisible();
  });
  
  test('Order creation flow', async ({ page }) => {
    // Test order creation when implemented
  });
  
  test('Driver delivery flow', async ({ page }) => {
    await page.goto('/driver');
    // Test delivery workflow
  });
});
```

---

## 📈 Performance Testing

### Load Test Configuration
```javascript
// k6-load-test.js
import http from 'k6/http';
import { check, sleep } from 'k6';

export let options = {
  stages: [
    { duration: '2m', target: 10 },   // Ramp up
    { duration: '5m', target: 50 },   // Stay at 50 users
    { duration: '2m', target: 100 },  // Spike to 100
    { duration: '2m', target: 0 },    // Ramp down
  ],
  thresholds: {
    http_req_duration: ['p(95)<500'], // 95% of requests under 500ms
    http_req_failed: ['rate<0.1'],    // Error rate under 10%
  },
};

export default function() {
  // Test customer list API
  let response = http.get('http://localhost:8000/api/v1/customers');
  check(response, {
    'status is 200': (r) => r.status === 200,
    'response time < 500ms': (r) => r.timings.duration < 500,
  });
  
  sleep(1);
}
```

---

## 🔍 Integration Test Stubs

### E-Invoice API Mock
```python
# backend/tests/mocks/einvoice_mock.py
from fastapi import FastAPI, Response
from pydantic import BaseModel

mock_einvoice = FastAPI()

class InvoiceRequest(BaseModel):
    seller_id: str
    buyer_id: str
    amount: float
    items: list

@mock_einvoice.post("/Invoice/Issue")
async def mock_issue_invoice(invoice: InvoiceRequest):
    """Mock Taiwan e-invoice API for testing"""
    return {
        "invoice_number": "AA12345678",
        "status": "success",
        "qr_code": "mock_qr_code_data"
    }

# Run with: uvicorn tests.mocks.einvoice_mock:mock_einvoice --port 8001
```

---

## 📋 Test Execution Schedule

### Day 1: Infrastructure
- [ ] Frontend test setup (2 hours)
- [ ] Backend test fix (2 hours)
- [ ] Run first test suite (1 hour)
- [ ] Document results (1 hour)

### Day 2: Unit Tests
- [ ] Auth tests (morning)
- [ ] Customer tests (morning)
- [ ] WebSocket tests (afternoon)
- [ ] Taiwan validators (afternoon)

### Day 3: Integration Tests
- [ ] API integration tests
- [ ] Database tests
- [ ] WebSocket integration
- [ ] Mock external services

### Day 4: E2E Tests
- [ ] Critical path scenarios
- [ ] Cross-browser testing
- [ ] Mobile responsiveness
- [ ] Performance baseline

### Day 5: Test Automation
- [ ] CI/CD pipeline setup
- [ ] Automated test runs
- [ ] Coverage reports
- [ ] Test documentation

---

## 🎯 Success Metrics

| Metric | Current | Day 5 Target | Required for Production |
|--------|---------|--------------|------------------------|
| Test Coverage | <5% | 40% | 80% |
| Unit Tests | 0 | 50 | 200+ |
| Integration Tests | 0 | 20 | 100+ |
| E2E Tests | 3 | 10 | 50+ |
| Load Test | None | Baseline | 100 users |
| CI/CD | None | Basic | Full automation |

---

## ⚠️ Important Notes

1. **This framework tests what EXISTS (28%)**
2. **Cannot test unbuilt features (72%)**
3. **Focus on quality over quantity**
4. **Parallel execution where possible**
5. **Document all test failures**

The remaining 72% of features need to be BUILT before they can be tested!