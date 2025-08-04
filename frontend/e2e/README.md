# Lucky Gas Frontend E2E Test Suite

Comprehensive end-to-end testing for the Lucky Gas delivery management system using Playwright.

## 📁 Test Structure

```
e2e/
├── critical/           # Business-critical user journeys
│   ├── order-flow.spec.ts
│   ├── route-optimization.spec.ts
│   └── delivery-tracking.spec.ts
├── visual/            # Visual regression tests
│   └── visual-regression.spec.ts
├── performance/       # Performance benchmarks
│   └── performance.spec.ts
├── api/              # API contract tests
│   └── contract-tests.spec.ts
├── resilience/       # Error recovery tests
│   └── error-recovery.spec.ts
├── helpers/          # Test utilities
│   └── auth.helper.ts
└── screenshots/      # Visual test baselines
```

## 🚀 Quick Start

### Run All Tests
```bash
npm run test:e2e
```

### Run Specific Test Suites

#### Critical Path Tests (Priority 1)
```bash
npm run test:e2e -- --project=critical
```

#### Visual Regression Tests
```bash
npm run test:e2e -- --project=visual
```

#### Performance Tests
```bash
npm run test:e2e -- --project=performance
```

#### API Contract Tests
```bash
npm run test:e2e -- --project=api
```

#### Error Recovery Tests
```bash
npm run test:e2e -- --project=resilience
```

### Run Tests in Debug Mode
```bash
npm run test:e2e:debug
```

### Run Tests with UI Mode
```bash
npm run test:e2e:ui
```

## 📊 Test Categories

### 1. Critical Path Tests (`critical/`)
These tests cover the most important user journeys that directly impact business operations:

- **Order Creation Flow**: Complete order journey from login to confirmation
- **Route Optimization**: Optimize delivery routes and assign drivers
- **Delivery Tracking**: Real-time tracking and status updates

### 2. Visual Regression Tests (`visual/`)
Captures screenshots to detect unintended UI changes:

- Login page across viewports
- Dashboard layouts
- Component consistency
- Theme variations

### 3. Performance Tests (`performance/`)
Ensures the application meets performance targets:

- Page load times < 3 seconds
- Core Web Vitals (LCP, FID, CLS)
- API response times < 1 second
- Memory leak detection
- Bundle size limits

### 4. API Contract Tests (`api/`)
Validates API responses match expected schemas:

- Authentication endpoints
- Customer data structure
- Order management
- Route optimization
- Predictions API

### 5. Error Recovery Tests (`resilience/`)
Verifies graceful handling of failures:

- Network failures
- API errors
- Session timeouts
- Slow connections
- Partial data loading

## 🔧 Configuration

### Environment Variables
Create `.env.test` file:
```env
VITE_API_URL=http://localhost:8000
VITE_APP_URL=http://localhost:5173
```

### Test Users
The test suite expects these users to exist:
- `test@example.com` / `test123` (default test user)
- `manager@luckygas.com` / `manager123` (manager role)
- `driver@luckygas.com` / `driver123` (driver role)
- `customer@luckygas.com` / `customer123` (customer role)

## 📈 Performance Targets

- **Page Load**: < 3 seconds
- **First Contentful Paint**: < 1.5 seconds
- **Largest Contentful Paint**: < 2.5 seconds
- **Cumulative Layout Shift**: < 0.1
- **API Response**: < 1 second average
- **Bundle Size**: < 600KB total

## 🏃 Running Tests in CI/CD

### GitHub Actions
```yaml
- name: Run E2E Tests
  run: |
    npm run test:e2e -- --project=critical
  env:
    CI: true
```

### Parallel Execution
Tests run in parallel by default. Control with:
```bash
npm run test:e2e -- --workers=4
```

## 📸 Visual Testing

### Update Visual Baselines
```bash
npm run test:e2e -- --project=visual --update-snapshots
```

### View Visual Differences
Failed visual tests generate diff images in `test-results/`.

## 📊 Test Reports

### HTML Report
```bash
npm run test:e2e:report
```

### JSON Report
Results are saved to `test-results/results.json`.

## 🐛 Debugging

### Debug Single Test
```bash
npm run test:e2e -- -g "test name" --debug
```

### View Browser
```bash
npm run test:e2e:headed
```

### Slow Motion
```bash
SLOW_MO=500 npm run test:e2e
```

## ✅ Best Practices

1. **Use Page Object Model** for maintainable tests
2. **Keep tests independent** - each test should run in isolation
3. **Use data-testid** attributes for reliable element selection
4. **Mock external services** in API tests
5. **Set reasonable timeouts** for different operations
6. **Clean up test data** after tests complete

## 🔍 Troubleshooting

### Tests Timing Out
- Check if backend is running on port 8000
- Verify frontend is running on port 5173
- Increase timeout in playwright.config.ts

### Visual Tests Failing
- Update snapshots if UI changes are intentional
- Ensure consistent viewport sizes
- Disable animations in tests

### API Tests Failing
- Verify backend API is accessible
- Check authentication tokens
- Ensure test user exists in database

## 📝 Writing New Tests

### Test Template
```typescript
import { test, expect } from '@playwright/test';
import { loginAsTestUser } from '../helpers/auth.helper';

test.describe('Feature Name', () => {
  test.beforeEach(async ({ page }) => {
    await loginAsTestUser(page);
  });

  test('should do something', async ({ page }) => {
    // Arrange
    await page.goto('/feature');
    
    // Act
    await page.click('button:has-text("Action")');
    
    // Assert
    await expect(page.locator('.result')).toBeVisible();
  });
});
```

## 🎯 Coverage Goals

- **Critical Paths**: 100% coverage
- **API Contracts**: All endpoints tested
- **Visual Regression**: Key pages and components
- **Performance**: All user-facing pages
- **Error Recovery**: Common failure scenarios