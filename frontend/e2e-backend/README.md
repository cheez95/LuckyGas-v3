# End-to-End Tests with Playwright

This directory contains end-to-end tests for the Lucky Gas delivery management system using Playwright.

## Prerequisites

1. Install Playwright and its dependencies:
```bash
pip install pytest-playwright
playwright install chromium
```

2. Ensure the application is running:
```bash
# Backend
cd backend
uvicorn app.main:app --reload --port 8000

# Frontend
cd frontend
npm run dev
```

## Running Tests

### Run all E2E tests:
```bash
pytest tests/e2e -m e2e
```

### Run specific test categories:
```bash
# Critical path tests only
pytest tests/e2e -m critical

# Mobile tests only
pytest tests/e2e -m mobile

# Smoke tests
pytest tests/e2e -m smoke
```

### Run specific test files:
```bash
# Login flow tests
pytest tests/e2e/test_login_flow.py

# Customer management tests
pytest tests/e2e/test_customer_management.py

# Order flow tests
pytest tests/e2e/test_order_flow.py

# Driver mobile tests
pytest tests/e2e/test_driver_mobile_flow.py
```

### Run with visible browser (non-headless):
```bash
E2E_HEADLESS=false pytest tests/e2e -m e2e
```

### Run with slow motion (for debugging):
```bash
E2E_SLOW_MO=1000 pytest tests/e2e -m e2e
```

## Environment Variables

- `E2E_BASE_URL`: Frontend URL (default: http://localhost:3000)
- `E2E_API_URL`: Backend API URL (default: http://localhost:8000)
- `E2E_HEADLESS`: Run in headless mode (default: true)
- `E2E_SLOW_MO`: Slow down operations by milliseconds (default: 0)

## Test Structure

### Login Flow Tests (`test_login_flow.py`)
- Successful login
- Failed login (invalid password)
- Logout flow
- Session persistence
- Protected route redirects
- Role-based access control
- Mobile responsive login

### Customer Management Tests (`test_customer_management.py`)
- Create new customer
- Search customers
- Filter by area
- Edit customer
- View customer details
- Deactivate customer (admin only)
- Bulk import from Excel
- Pagination

### Order Flow Tests (`test_order_flow.py`)
- Create new order
- View and filter orders
- View order details
- Confirm order
- Assign to delivery route
- Update order quantities
- Cancel order
- View statistics dashboard

### Driver Mobile Tests (`test_driver_mobile_flow.py`)
- Mobile login
- View assigned routes
- Start delivery route
- Complete delivery with signature/photo
- Handle delivery issues
- Offline mode and sync
- Route navigation
- End of day summary
- Emergency contacts

## Test Data Setup

Tests use fixtures to create test data via API calls. See `conftest.py` for available fixtures:

- `create_test_customer`: Create test customers
- `create_test_order`: Create test orders
- `authenticated_page`: Pre-authenticated page for office staff
- `admin_authenticated_page`: Pre-authenticated page for admin
- `driver_authenticated_page`: Pre-authenticated page for driver

## Screenshots

Failed tests automatically capture screenshots to `tests/e2e/screenshots/`.

To manually capture screenshots in tests:
```python
async def test_example(page, take_screenshot):
    # ... test code ...
    await take_screenshot("test_state")
```

## Writing New Tests

1. Create test file following naming convention: `test_*.py`
2. Mark tests with appropriate decorators:
```python
@pytest.mark.e2e
@pytest.mark.critical  # If it's a critical path
class TestNewFeature:
    async def test_feature(self, page):
        # Test implementation
```

3. Use page object pattern for reusable components:
```python
class CustomerPage:
    def __init__(self, page: Page):
        self.page = page
        
    async def create_customer(self, data):
        await self.page.click('[data-testid="add-customer"]')
        # ... fill form ...
```

4. Use data-testid attributes for reliable element selection:
```html
<button data-testid="submit-order">提交訂單</button>
```

## Debugging Tips

1. Run with headed browser:
```bash
E2E_HEADLESS=false pytest tests/e2e/test_login_flow.py::TestLoginFlow::test_successful_login -s
```

2. Add breakpoints:
```python
import pdb; pdb.set_trace()
# or
await page.pause()  # Playwright inspector
```

3. Slow down execution:
```bash
E2E_SLOW_MO=1000 pytest tests/e2e -m e2e
```

4. Take screenshots on demand:
```python
await page.screenshot(path="debug.png")
```

5. Use Playwright inspector:
```bash
PWDEBUG=1 pytest tests/e2e/test_login_flow.py -s
```

## CI/CD Integration

Add to your CI pipeline:

```yaml
# GitHub Actions example
- name: Install Playwright
  run: |
    pip install pytest-playwright
    playwright install chromium
    playwright install-deps

- name: Run E2E tests
  run: |
    pytest tests/e2e -m smoke --html=report.html
  env:
    E2E_BASE_URL: ${{ secrets.E2E_BASE_URL }}
    E2E_API_URL: ${{ secrets.E2E_API_URL }}
```

## Best Practices

1. **Use data-testid**: Always use data-testid attributes for element selection
2. **Wait for elements**: Use `expect()` for auto-waiting instead of manual waits
3. **Test isolation**: Each test should be independent and not rely on others
4. **Clean test data**: Tests should clean up after themselves
5. **Meaningful assertions**: Use specific assertions that clearly indicate what failed
6. **Page objects**: Use page object pattern for complex UI interactions
7. **Mobile testing**: Test critical flows on mobile viewports
8. **Accessibility**: Include accessibility checks in your tests

## Troubleshooting

### Tests timeout
- Increase timeout in pytest.ini or specific tests
- Check if application is running
- Verify URLs in environment variables

### Element not found
- Check data-testid attributes match
- Ensure element is visible (not hidden by CSS)
- Add explicit waits if needed

### Authentication issues
- Verify test user credentials
- Check auth token handling
- Ensure cookies are properly set

### Flaky tests
- Add proper waits instead of sleep
- Check for race conditions
- Use more specific selectors
- Ensure test data is consistent