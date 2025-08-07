import { test, expect } from '@playwright/test';

// Test configuration
const BASE_URL = 'http://localhost:5173';
// const _API_URL removed - unused

// Test credentials
const TEST_USER = {
  username: 'test@example.com',
  password: 'test123'
};

test.describe('Lucky Gas Frontend - Comprehensive Functionality Test', () => {
  
  test.beforeEach(async ({ page }) => {
    // Start from the home page
    await page.goto(BASE_URL);
  });

  test.describe('1. Authentication Flow', () => {
    test('should pass comprehensive frontend tests', async ({ page }) => {
      await expect(page).toHaveURL(/login/);
      // Use more specific selector to avoid multiple matches
      await expect(page.getByRole('heading', { name: '幸福氣瓦斯配送管理系統' })).toBeVisible();
      // Try to use placeholder text if testIds are not present
      await expect(page.getByPlaceholder(/用戶名|電子郵件|Email/)).toBeVisible();
      await expect(page.getByPlaceholder(/密碼|Password/)).toBeVisible();
      await expect(page.getByRole('button', { name: /登\s*入|Login/ })).toBeVisible();
      await expect(page.getByText('忘記密碼？')).toBeVisible();
    });

  test('should pass comprehensive frontend tests - 2', async ({ page }) => {
      await page.getByPlaceholder(/用戶名|電子郵件|Email/).fill(TEST_USER.username);
      await page.getByPlaceholder(/密碼|Password/).fill(TEST_USER.password);
      await page.getByRole('button', { name: /登\s*入|Login/ }).click();
      
      // Should redirect to dashboard
      await expect(page).toHaveURL(/dashboard/, { timeout: 10000 });
      
      // Check user info in header - use more flexible selector
      await expect(page.getByText('Test User')).toBeVisible();
    });

  test('should pass comprehensive frontend tests - 3', async ({ page }) => {
      await page.getByPlaceholder(/用戶名|電子郵件|Email/).fill('wrong@example.com');
      await page.getByPlaceholder(/密碼|Password/).fill('wrongpassword');
      await page.getByRole('button', { name: /登\s*入|Login/ }).click();
      
      // Should show error message
      await expect(page.getByText(/用戶名或密碼錯誤/)).toBeVisible();
    });

  test('should pass comprehensive frontend tests - 4', async ({ page }) => {
      // Login first
      await page.getByPlaceholder(/用戶名|電子郵件|Email/).fill(TEST_USER.username);
      await page.getByPlaceholder(/密碼|Password/).fill(TEST_USER.password);
      await page.getByRole('button', { name: /登\s*入|Login/ }).click();
      await page.waitForURL(/dashboard/);
      
      // Click user menu and logout
      await page.getByText('Test User').click();
      await page.getByText('登出').click();
      
      // Should redirect to login
      await expect(page).toHaveURL(/login/);
    });
  });

  test.describe('2. Dashboard Functionality', () => {
    test.beforeEach(async ({ page }) => {
      // Login before each test
      await page.getByPlaceholder(/用戶名|電子郵件|Email/).fill(TEST_USER.username);
      await page.getByPlaceholder(/密碼|Password/).fill(TEST_USER.password);
      await page.getByRole('button', { name: /登\s*入|Login/ }).click();
      await page.waitForURL(/dashboard/);
    });

    test('should pass comprehensive frontend tests', async ({ page }) => {
      // Check main stats cards
      await expect(page.getByText('今日訂單')).toBeVisible();
      await expect(page.getByText('活躍客戶')).toBeVisible();
      await expect(page.getByText('路線上的司機')).toBeVisible();
      await expect(page.getByText('今日營收')).toBeVisible();
      
      // Check other sections
      await expect(page.getByText('AI 需求預測')).toBeVisible();
      await expect(page.getByText('今日路線進度')).toBeVisible();
      await expect(page.getByText('即時動態')).toBeVisible();
      await expect(page.getByText('系統功能概覽')).toBeVisible();
    });

  test('should pass comprehensive frontend tests - 2', async ({ page }) => {
      // Check WebSocket status indicator
      const wsStatus = page.locator('[data-testid="websocket-status"]');
      await expect(wsStatus).toBeVisible();
      
      // Could be either connected or disconnected
      const statusText = await wsStatus.textContent();
      expect(['即時連線', '離線模式']).toContain(statusText);
    });
  });

  test.describe('3. Navigation Menu', () => {
    test.beforeEach(async ({ page }) => {
      // Login before each test
      await page.getByPlaceholder(/用戶名|電子郵件|Email/).fill(TEST_USER.username);
      await page.getByPlaceholder(/密碼|Password/).fill(TEST_USER.password);
      await page.getByRole('button', { name: /登\s*入|Login/ }).click();
      await page.waitForURL(/dashboard/);
    });

    test('should pass comprehensive frontend tests', async ({ page }) => {
      // Desktop view
      if (await page.getByTestId('desktop-nav').isVisible()) {
        await expect(page.getByTestId('menu-dashboard')).toBeVisible();
        await expect(page.getByTestId('menu-customers')).toBeVisible();
        await expect(page.getByTestId('menu-orders')).toBeVisible();
        await expect(page.getByTestId('menu-routes')).toBeVisible();
        await expect(page.getByTestId('menu-driver-assignment')).toBeVisible();
        await expect(page.getByTestId('menu-emergency-dispatch')).toBeVisible();
        await expect(page.getByTestId('menu-deliveries')).toBeVisible();
      } else {
        // Mobile view - open drawer
        await page.getByTestId('mobile-menu-trigger').click();
        await expect(page.getByTestId('mobile-nav-menu')).toBeVisible();
      }
    });

  test('should pass comprehensive frontend tests - 2', async ({ page }) => {
      await page.getByTestId('menu-customers').click();
      await expect(page).toHaveURL(/customers/);
      await expect(page.getByTestId('page-title')).toHaveText('客戶管理');
    });

  test('should pass comprehensive frontend tests - 3', async ({ page }) => {
      await page.getByTestId('menu-orders').click();
      await expect(page).toHaveURL(/orders/);
      await expect(page.getByTestId('page-title')).toHaveText('訂單管理');
    });

  test('should pass comprehensive frontend tests - 4', async ({ page }) => {
      await page.getByTestId('menu-routes').click();
      await expect(page).toHaveURL(/routes/);
      await expect(page.getByTestId('page-title')).toHaveText('路線規劃');
    });
  });

  test.describe('4. Customer Management', () => {
    test.beforeEach(async ({ page }) => {
      // Login and navigate to customers
      await page.getByTestId('username-input').fill(TEST_USER.username);
      await page.getByTestId('password-input').fill(TEST_USER.password);
      await page.getByTestId('login-button').click();
      await page.waitForURL(/dashboard/);
      await page.getByTestId('menu-customers').click();
    });

    test('should pass comprehensive frontend tests', async ({ page }) => {
      // Wait for customer table
      await expect(page.getByTestId('customer-table')).toBeVisible();
      
      // Check if table has data or shows empty state
      const tableBody = page.locator('.ant-table-tbody');
      const rows = tableBody.locator('tr');
      const rowCount = await rows.count();
      
      if (rowCount > 0) {
        // Check table headers
        await expect(page.getByText('客戶名稱')).toBeVisible();
        await expect(page.getByText('電話')).toBeVisible();
        await expect(page.getByText('地址')).toBeVisible();
      } else {
        // Check empty state
        await expect(page.getByText('暫無資料')).toBeVisible();
      }
    });

  test('should pass comprehensive frontend tests - 2', async ({ page }) => {
      const searchInput = page.getByPlaceholder('搜尋客戶');
      if (await searchInput.isVisible()) {
        await searchInput.fill('測試');
        await page.keyboard.press('Enter');
        // Table should update (even if no results)
        await page.waitForTimeout(500);
      }
    });

  test('should pass comprehensive frontend tests - 3', async ({ page }) => {
      const addButton = page.getByTestId('add-customer-button');
      if (await addButton.isVisible()) {
        await addButton.click();
        // Should open modal or navigate to form
        await expect(page.getByText(/新增客戶|客戶資料/)).toBeVisible();
      }
    });
  });

  test.describe('5. Order Management', () => {
    test.beforeEach(async ({ page }) => {
      // Login and navigate to orders
      await page.getByTestId('username-input').fill(TEST_USER.username);
      await page.getByTestId('password-input').fill(TEST_USER.password);
      await page.getByTestId('login-button').click();
      await page.waitForURL(/dashboard/);
      await page.getByTestId('menu-orders').click();
    });

    test('should pass comprehensive frontend tests', async ({ page }) => {
      await expect(page.getByTestId('page-title')).toHaveText('訂單管理');
      
      // Check for filters
      await expect(page.getByText(/所有狀態|篩選/)).toBeVisible();
      
      // Check for table or empty state
      const content = page.locator('.ant-card, .ant-table, .ant-empty');
      await expect(content.first()).toBeVisible();
    });

  test('should pass comprehensive frontend tests - 2', async ({ page }) => {
      // Date range picker
      const dateRangePicker = page.locator('.ant-picker-range');
      if (await dateRangePicker.isVisible()) {
        await dateRangePicker.click();
        // Calendar should open
        await expect(page.locator('.ant-picker-panel')).toBeVisible();
        await page.keyboard.press('Escape');
      }
      
      // Status filter
      const statusFilter = page.getByText('所有狀態').first();
      if (await statusFilter.isVisible()) {
        await statusFilter.click();
        await expect(page.getByText(/待處理|進行中|已完成/)).toBeVisible();
      }
    });
  });

  test.describe('6. Responsive Design', () => {
    test('should pass comprehensive frontend tests', async ({ page }) => {
      // Set mobile viewport
      await page.setViewportSize({ width: 375, height: 667 });
      await page.goto(BASE_URL);
      
      // Login
      await page.getByTestId('username-input').fill(TEST_USER.username);
      await page.getByTestId('password-input').fill(TEST_USER.password);
      await page.getByTestId('login-button').click();
      await page.waitForURL(/dashboard/);
      
      // Check mobile menu
      await expect(page.getByTestId('mobile-menu-trigger')).toBeVisible();
      await page.getByTestId('mobile-menu-trigger').click();
      await expect(page.getByTestId('mobile-nav-menu')).toBeVisible();
    });

  test('should pass comprehensive frontend tests - 2', async ({ page }) => {
      // Set tablet viewport
      await page.setViewportSize({ width: 768, height: 1024 });
      await page.goto(BASE_URL);
      
      // Check layout adapts
      await expect(page).toHaveURL(/login/);
      await expect(page.getByText('幸福氣瓦斯配送管理系統')).toBeVisible();
    });
  });

  test.describe('7. Error Handling', () => {
    test('should pass comprehensive frontend tests', async ({ page }) => {
      await page.goto(`${BASE_URL}/non-existent-page`);
      // Should show 404 or redirect to login
      await expect(page).toHaveURL(/login|404/);
    });

  test('should pass comprehensive frontend tests - 2', async ({ page, context }) => {
      // Login first
      await page.getByTestId('username-input').fill(TEST_USER.username);
      await page.getByTestId('password-input').fill(TEST_USER.password);
      await page.getByTestId('login-button').click();
      await page.waitForURL(/dashboard/);
      
      // Block API calls
      await context.route('**/api/v1/**', route => route.abort());
      
      // Try to navigate to a page that needs API
      await page.getByTestId('menu-customers').click();
      
      // Should show error message or loading state
      await expect(page.getByText(/載入中|錯誤|失敗/)).toBeVisible();
    });
  });

  test.describe('8. Accessibility', () => {
    test('should pass comprehensive frontend tests', async ({ page }) => {
      // Tab through login form
      await page.keyboard.press('Tab');
      await expect(page.getByTestId('username-input')).toBeFocused();
      
      await page.keyboard.press('Tab');
      await expect(page.getByTestId('password-input')).toBeFocused();
      
      await page.keyboard.press('Tab');
      await expect(page.getByTestId('login-button')).toBeFocused();
    });

  test('should pass comprehensive frontend tests - 2', async ({ page }) => {
      // Check for ARIA labels on interactive elements
      const usernameInput = page.getByTestId('username-input');
      const ariaLabel = await usernameInput.getAttribute('aria-label');
      expect(ariaLabel).toBeTruthy();
    });
  });

  test.describe('9. Localization', () => {
    test('should pass comprehensive frontend tests', async ({ page }) => {
      // Check all text is in Traditional Chinese
      await expect(page.getByText('幸福氣瓦斯配送管理系統')).toBeVisible();
      await expect(page.getByText('用戶名')).toBeVisible();
      await expect(page.getByText('密碼')).toBeVisible();
      await expect(page.getByText('登入')).toBeVisible();
    });
  });

  test.describe('10. Performance', () => {
    test('should pass comprehensive frontend tests', async ({ page }) => {
      const startTime = Date.now();
      await page.goto(BASE_URL);
      await page.waitForLoadState('networkidle');
      const loadTime = Date.now() - startTime;
      
      // Page should load within 3 seconds
      expect(loadTime).toBeLessThan(3000);
    });

  test('should pass comprehensive frontend tests - 2', async ({ page }) => {
      // Monitor API calls
      const apiTimes: number[] = [];
      
      page.on('response', response => {
        if (response.url().includes('/api/v1/')) {
          const timing = response.timing();
          if (timing) {
            apiTimes.push(timing.responseEnd - timing.requestStart);
          }
        }
      });
      
      // Login to trigger API calls
      await page.getByTestId('username-input').fill(TEST_USER.username);
      await page.getByTestId('password-input').fill(TEST_USER.password);
      await page.getByTestId('login-button').click();
      await page.waitForURL(/dashboard/);
      
      // Check API response times
      if (apiTimes.length > 0) {
        const avgTime = apiTimes.reduce((a, b) => a + b, 0) / apiTimes.length;
        expect(avgTime).toBeLessThan(1000); // Average should be under 1 second
      }
    });
  });
});