# LuckyGas E2E Test Suite

Comprehensive end-to-end test suite for the LuckyGas delivery management system using Playwright.

## 🚀 Quick Start

```bash
# Install dependencies
npm install

# Run all tests
./run-tests.sh all

# Run specific test suites
./run-tests.sh auth      # Authentication tests
./run-tests.sh customer  # Customer journey tests
./run-tests.sh driver    # Driver workflow tests
./run-tests.sh websocket # Real-time WebSocket tests
```

## 📁 Project Structure

```
tests/e2e/
├── fixtures/               # Test data and helpers
│   ├── test-data.ts       # Taiwan-specific test data
│   └── test-helpers.ts    # Utility functions
├── pages/                 # Page Object Models
│   ├── LoginPage.ts       # Login page interactions
│   ├── DashboardPage.ts   # Dashboard operations
│   └── CustomerPage.ts    # Customer management
├── specs/                 # Test specifications
│   ├── auth.spec.ts              # Authentication tests (22 tests)
│   ├── customer-journey.spec.ts  # Customer workflows (18 tests)
│   ├── driver-workflow.spec.ts   # Driver operations (24 tests)
│   └── websocket-realtime.spec.ts # Real-time updates (10 tests)
├── playwright.config.ts   # Playwright configuration
├── package.json          # Dependencies
└── run-tests.sh         # Test runner script
```

## 🧪 Test Coverage

### Authentication & Security
- ✅ Multi-role login (Admin, Manager, Staff, Driver, Customer)
- ✅ Session management and JWT handling
- ✅ Rate limiting and security features
- ✅ Traditional Chinese UI validation

### Customer Management
- ✅ Customer CRUD operations
- ✅ Taiwan phone/address validation
- ✅ Order creation workflows
- ✅ Real-time order tracking

### Driver Operations
- ✅ Mobile-optimized interface
- ✅ Route navigation with GPS
- ✅ Delivery completion (signature/photo)
- ✅ Offline functionality

### Real-time Features
- ✅ WebSocket synchronization
- ✅ Multi-user updates
- ✅ Connection recovery
- ✅ Role-based channels

## 🌏 Taiwan-Specific Features

- Traditional Chinese (繁體中文) UI
- Taiwan phone formats: `09XX-XXX-XXX`
- Taiwan address autocomplete
- ROC date format (民國年)
- NT$ currency formatting

## 📱 Multi-Device Testing

```bash
# Desktop browsers
./run-tests.sh all

# Mobile viewports
./run-tests.sh mobile

# Specific browser
npm run test:chrome
npm run test:firefox
npm run test:webkit
```

## 🎯 Performance Targets

- Page Load: < 3 seconds
- API Response: < 200ms
- Login Flow: < 3 seconds
- Route Optimization: < 5 seconds

## 🔧 Development

### Debug Mode
```bash
# Interactive debugging
./run-tests.sh debug

# Playwright UI mode
./run-tests.sh ui

# Generate new tests
npx playwright codegen http://localhost:3000
```

### Test Reports
```bash
# View HTML report
./run-tests.sh report

# CI-friendly reports
npm run test:ci
```

## 🚦 CI/CD Integration

```yaml
# GitHub Actions example
- name: E2E Tests
  run: |
    cd tests/e2e
    npm ci
    npx playwright install --with-deps
    npm run test:ci
```

## 📊 Test Statistics

- **Total Tests**: 74
- **Page Objects**: 5
- **Supported Browsers**: Chrome, Firefox, Safari, Edge
- **Mobile Viewports**: iOS, Android
- **Execution Time**: ~5-10 minutes (parallel)

## 🛠️ Troubleshooting

### Services Not Running
```bash
# Start backend
cd backend && uv run uvicorn app.main:app

# Start frontend
cd frontend && npm run dev
```

### Test Failures
1. Check service health
2. Verify test data exists
3. Clear browser cache
4. Review trace files: `npx playwright show-trace`

## 📚 Resources

- [Playwright Documentation](https://playwright.dev/)
- [Test Report](./COMPREHENSIVE_E2E_TEST_REPORT.md)
- [Project README](../../README.md)

---

Built with ❤️ for LuckyGas (幸福氣) using Playwright