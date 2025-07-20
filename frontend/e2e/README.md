# E2E Testing with Playwright

This directory contains end-to-end tests for the Lucky Gas frontend application using Playwright.

## Setup

1. Install Playwright browsers (first time only):
```bash
npx playwright install
```

2. Make sure the frontend is running:
```bash
npm run dev
```

3. Make sure the backend is running:
```bash
cd ../backend
uv run uvicorn app.main:app --reload
```

## Running Tests

### Run all tests
```bash
npm run test:e2e
```

### Run tests in UI mode (recommended for development)
```bash
npm run test:e2e:ui
```

### Run tests with visible browser
```bash
npm run test:e2e:headed
```

### Run specific test suites
```bash
npm run test:e2e:auth      # Authentication tests
npm run test:e2e:customer  # Customer management tests
npm run test:e2e:mobile    # Mobile responsiveness tests
npm run test:e2e:i18n      # Localization tests
```

### Debug tests
```bash
npm run test:e2e:debug
```

### View test report
```bash
npm run test:e2e:report
```

## Test Structure

```
e2e/
├── pages/                 # Page Object Model
│   ├── BasePage.ts       # Base page with common methods
│   ├── LoginPage.ts      # Login page object
│   ├── DashboardPage.ts  # Dashboard page object
│   ├── CustomerPage.ts   # Customer management page object
│   ├── OrderPage.ts      # Order management page object
│   └── RoutePage.ts      # Route planning page object
├── auth.spec.ts          # Authentication tests
├── customer.spec.ts      # Customer CRUD tests
├── mobile.spec.ts        # Mobile responsiveness tests
└── localization.spec.ts  # Traditional Chinese localization tests
```

## Writing Tests

### Using Page Objects

```typescript
import { test, expect } from '@playwright/test';
import { LoginPage } from './pages/LoginPage';

test('should login successfully', async ({ page }) => {
  const loginPage = new LoginPage(page);
  
  await loginPage.navigateToLogin();
  await loginPage.login('admin', 'admin123');
  await loginPage.waitForLoginSuccess();
  
  await expect(page).toHaveURL(/.*\/dashboard/);
});
```

### Testing Mobile Responsiveness

```typescript
import { devices } from '@playwright/test';

test.use(devices['iPhone 12']);

test('mobile layout', async ({ page }) => {
  // Test mobile-specific behavior
});
```

### Testing Localization

```typescript
test('should display in Traditional Chinese', async ({ page }) => {
  const isChineseLocalized = await customerPage.checkChineseLocalization();
  expect(isChineseLocalized).toBe(true);
});
```

## Best Practices

1. **Use Page Objects**: All page interactions should go through page objects
2. **Test User Journeys**: Focus on real user workflows
3. **Check Accessibility**: Ensure all interactive elements are accessible
4. **Test Error Cases**: Don't just test happy paths
5. **Mobile First**: Always test mobile layouts
6. **Localization**: Verify all text is properly localized

## Configuration

See `playwright.config.ts` for test configuration including:
- Browser settings
- Viewport sizes
- Base URL
- Timeout settings
- Test retries
- Screenshot/video settings

## Debugging Tips

1. Use `page.pause()` to pause execution
2. Use `--debug` flag to step through tests
3. Use UI mode for visual debugging
4. Check screenshots in `test-results/` for failures
5. Use `console.log()` for debugging values

## CI/CD Integration

To run tests in CI:

```bash
# Install dependencies
npm ci

# Install Playwright browsers
npx playwright install --with-deps

# Run tests
npm run test:e2e
```

## Common Issues

### Tests timing out
- Increase timeout in specific tests: `test.setTimeout(60000)`
- Check if backend is running
- Check network conditions

### Locator not found
- Use Playwright Inspector to find correct selectors
- Check if element is in viewport
- Wait for element to be visible

### Mobile tests failing
- Ensure responsive design is implemented
- Check viewport sizes in test
- Verify touch targets are large enough