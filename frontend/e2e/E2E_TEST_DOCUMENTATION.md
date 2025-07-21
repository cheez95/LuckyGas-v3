# Lucky Gas E2E Test Documentation

## 📋 Overview

This document describes the comprehensive End-to-End (E2E) test suite for the Lucky Gas delivery management system. All tests are designed to work **without requiring Google Cloud APIs**, using placeholder services when necessary.

## 🎯 Test Objectives

1. **Complete Coverage**: Test all web functions without external API dependencies
2. **User Journey Validation**: Verify complete user workflows from login to delivery completion
3. **Mobile Optimization**: Ensure driver mobile interface works flawlessly
4. **Offline Capabilities**: Validate offline functionality and sync mechanisms
5. **Error Resilience**: Test error handling and recovery scenarios
6. **Localization**: Verify Traditional Chinese UI throughout the application

## 🏗️ Test Architecture

### Page Object Model (POM)

All tests use the Page Object Model pattern for maintainability:

```
e2e/
├── pages/                    # Page objects
│   ├── BasePage.ts          # Base class with common methods
│   ├── LoginPage.ts         # Authentication page
│   ├── CustomerPage.ts      # Customer management
│   ├── OrderPage.ts         # Order operations
│   ├── RoutePage.ts         # Route planning
│   ├── DashboardPage.ts     # Main dashboard
│   ├── DriverMobilePage.ts  # Driver mobile interface
│   ├── DeliveryCompletionModal.ts  # Delivery completion
│   └── PredictionsPage.ts   # AI predictions (placeholder)
├── fixtures/                 # Test data
│   └── test-data.ts         # Taiwan-specific test data
├── utils/                    # Helper utilities
│   └── test-helpers.ts      # Common test utilities
└── *.spec.ts                # Test specifications
```

### Test Data Management

Test data is carefully crafted for Taiwan context:
- Traditional Chinese names and addresses
- Taiwan phone number formats (09XX-XXX-XXX)
- Taiwan postal codes and address formats
- Realistic gas cylinder sizes (16kg, 20kg, 50kg)

## 🧪 Test Suites

### 1. Authentication Tests (`auth.spec.ts`)
- ✅ Login with valid credentials
- ✅ Login failure with invalid credentials
- ✅ Session persistence across page refreshes
- ✅ Session timeout handling
- ✅ Role-based access control
- ✅ Concurrent login handling
- ✅ Mobile responsive login
- ✅ Traditional Chinese localization

### 2. Driver Mobile Interface (`driver-mobile.spec.ts`)
- ✅ Mobile-optimized UI with proper touch targets
- ✅ Route selection and navigation
- ✅ Delivery completion with signature capture
- ✅ Photo upload with compression (max 1MB)
- ✅ Offline delivery completion
- ✅ Sync queue persistence
- ✅ Landscape orientation support
- ✅ Network interruption recovery

### 3. Predictions & Routes (`predictions-routes.spec.ts`)
- ✅ Prediction generation using placeholder service
- ✅ Confidence level visualization
- ✅ Date and customer filtering
- ✅ Export functionality
- ✅ Route optimization without Google Routes API
- ✅ Drag-and-drop route adjustment
- ✅ Driver assignment
- ✅ Integration between predictions and routes

### 4. Offline & Error Handling (`offline-error-handling.spec.ts`)
- ✅ Offline indicator display
- ✅ Operation queuing when offline
- ✅ Queue persistence across reloads
- ✅ Automatic retry with exponential backoff
- ✅ 404 and 500 error handling
- ✅ Validation error display
- ✅ Network timeout handling
- ✅ Concurrent update conflict resolution

### 5. Customer Management (`customer.spec.ts`)
- ✅ Customer list with pagination
- ✅ Search and filtering
- ✅ Add new customer
- ✅ Edit customer details
- ✅ Delete customer (soft delete)
- ✅ Taiwan address validation
- ✅ Phone number format validation

### 6. Mobile Responsiveness (`mobile.spec.ts`)
- ✅ Responsive layout adaptation
- ✅ Touch gesture support
- ✅ Mobile navigation menu
- ✅ Form usability on mobile
- ✅ Performance on mobile devices

### 7. Localization (`localization.spec.ts`)
- ✅ Traditional Chinese throughout UI
- ✅ Date format (YYYY/MM/DD)
- ✅ Currency format (NT$)
- ✅ Error messages in Chinese
- ✅ Form validation messages

## 🚀 Running Tests

### Prerequisites
```bash
# Install dependencies
cd frontend
npm install
npx playwright install
```

### Run All Tests
```bash
# From project root
./run-all-tests.sh

# With options
./run-all-tests.sh --seed           # Seed test data
./run-all-tests.sh --report         # Generate HTML report
./run-all-tests.sh --mode mobile    # Run mobile tests only
```

### Run Specific Tests
```bash
cd frontend

# All tests
npm run test:e2e

# Specific test file
npm run test:e2e auth.spec.ts

# Mobile tests only
npm run test:e2e -- --project="Mobile Chrome"

# With UI mode for debugging
npm run test:e2e:ui

# In headed mode
npm run test:e2e:headed
```

### Test Modes
- **Standard**: Runs in headless mode
- **Headed**: Shows browser (`--headed`)
- **Debug**: Step through tests (`--debug`)
- **UI Mode**: Interactive test runner (`--ui`)

## 🔧 Configuration

### Environment Setup

The tests automatically configure the environment to use placeholder services:

```typescript
// Placeholder services are activated when these are empty
GOOGLE_CLOUD_PROJECT=
VERTEX_AI_LOCATION=
GOOGLE_APPLICATION_CREDENTIALS=
```

### Browser Configuration

Tests run on multiple browsers:
- Chromium (Desktop & Mobile)
- Firefox
- WebKit (Safari)
- Mobile viewports (iPhone 12, Pixel 5)

### Network Conditions

Tests simulate various network conditions:
- 3G network speeds
- Offline mode
- Network interruptions
- High latency

## 📊 Test Reports

### HTML Report
```bash
# Generate report after tests
npm run test:e2e:report

# View report
open playwright-report/index.html
```

### CI/CD Integration

GitHub Actions workflow runs tests on:
- Every push to main/develop
- Every pull request
- Daily schedule (2 AM UTC)

Test artifacts are uploaded:
- HTML reports (30 days retention)
- Screenshots on failure (7 days)
- Videos on failure (7 days)

## 🛠️ Debugging Failed Tests

### 1. Check Screenshots
Failed tests automatically capture screenshots:
```
test-results/
└── test-name/
    └── screenshot.png
```

### 2. Review Videos
Video recordings help understand failures:
```
test-results/
└── test-name/
    └── video.webm
```

### 3. Use Debug Mode
```bash
npm run test:e2e:debug
```

### 4. Check Console Logs
Tests capture browser console logs for debugging JavaScript errors.

## 📈 Performance Benchmarks

Expected performance metrics:
- Page load: < 3 seconds
- API responses: < 200ms
- Mobile 3G load: < 3 seconds
- Route optimization: < 5 seconds for 100 stops
- Photo compression: < 2 seconds per photo

## 🔒 Security Testing

While not comprehensive penetration testing, E2E tests verify:
- Authentication flows
- Session management
- Role-based access control
- Input validation
- XSS prevention (basic)

## 🌏 Localization Testing

Special attention to Taiwan-specific features:
- Traditional Chinese characters (繁體中文)
- Taiwan address formats
- Local phone number validation
- ROC calendar support (民國年)
- NT$ currency format

## 📝 Best Practices

### 1. Test Independence
Each test should be independent and not rely on the state from other tests.

### 2. Explicit Waits
Use explicit waits instead of arbitrary timeouts:
```typescript
await page.waitForSelector('[data-testid="element"]');
```

### 3. Test Data Cleanup
Tests should clean up any data they create:
```typescript
test.afterEach(async ({ page }) => {
  await cleanupTestData(page);
});
```

### 4. Meaningful Assertions
Use descriptive assertions:
```typescript
await expect(page.locator('.error')).toContainText('請輸入有效的電話號碼');
```

### 5. Page Object Methods
Keep page objects focused on element interaction:
```typescript
async fillCustomerForm(data: CustomerData) {
  await this.nameInput.fill(data.name);
  await this.phoneInput.fill(data.phone);
  await this.addressInput.fill(data.address);
}
```

## 🚧 Known Limitations

1. **Google API Mocking**: Tests use placeholder services instead of actual Google APIs
2. **Load Testing**: E2E tests don't cover high-load scenarios
3. **Browser Compatibility**: Limited to Playwright-supported browsers
4. **Real Device Testing**: Mobile tests use emulation, not real devices

## 🔄 Maintenance

### Regular Updates
- Update test data monthly
- Review and update selectors quarterly
- Refresh screenshots for visual regression
- Update dependencies monthly

### Adding New Tests
1. Create page object if needed
2. Add test data to fixtures
3. Write test following existing patterns
4. Update this documentation
5. Ensure CI/CD passes

## 🤝 Contributing

When adding new E2E tests:
1. Follow the existing patterns
2. Use Traditional Chinese for user-facing text
3. Include mobile viewport tests
4. Test offline scenarios
5. Document any new utilities or patterns

## 📞 Support

For test-related issues:
1. Check the test report for details
2. Review screenshots and videos
3. Run in debug mode locally
4. Check CI/CD logs
5. Consult this documentation

---

Last Updated: 2024-07-21
Test Coverage: ~95% of user-facing features
Total Test Cases: 100+
Average Execution Time: 15-20 minutes (full suite)