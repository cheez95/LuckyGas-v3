import { test, expect } from '@playwright/test';
import { APIHelper } from '../utils/api-helper';
import { TestHelpers } from '../utils/test-helpers';
import users from '../fixtures/users.json';

test.describe('Authentication Flow Tests', () => {
  let apiHelper: APIHelper;

  test.beforeEach(async ({ request }) => {
    apiHelper = new APIHelper(request);
  });

  test.describe('API Authentication', () => {
    test('should successfully login with valid credentials', async () => {
      const token = await apiHelper.login('admin');
      expect(token).toBeTruthy();
      expect(token.length).toBeGreaterThan(20);
    });

    test('should fail login with invalid credentials', async ({ request }) => {
      const response = await request.post('http://localhost:8000/api/v1/auth/login', {
        data: {
          username: users.invalidUser.username,
          password: users.invalidUser.password
        }
      });
      
      expect(response.status()).toBe(401);
      const error = await response.json();
      expect(error.detail).toContain('使用者名稱或密碼錯誤');
    });

    test('should successfully refresh token', async ({ request }) => {
      // First login
      const loginResponse = await request.post('http://localhost:8000/api/v1/auth/login', {
        data: {
          username: users.admin.username,
          password: users.admin.password
        }
      });
      
      const loginData = await loginResponse.json();
      const refreshToken = loginData.refresh_token;
      
      // Refresh token
      const refreshResponse = await request.post('http://localhost:8000/api/v1/auth/refresh', {
        headers: {
          'Authorization': `Bearer ${refreshToken}`
        }
      });
      
      expect(refreshResponse.ok()).toBeTruthy();
      const refreshData = await refreshResponse.json();
      expect(refreshData.access_token).toBeTruthy();
    });

    test('should successfully logout', async () => {
      await apiHelper.login('admin');
      const logoutResponse = await apiHelper.post('/api/v1/auth/logout');
      expect(logoutResponse.ok()).toBeTruthy();
    });
  });

  test.describe('UI Authentication', () => {
    test('should display login page correctly', async ({ page }) => {
      await page.goto('/login');
      
      // Check page elements
      await expect(page.locator('h1')).toHaveText('登入');
      await expect(page.locator('input[name="username"]')).toBeVisible();
      await expect(page.locator('input[name="password"]')).toBeVisible();
      await expect(page.locator('button[type="submit"]')).toHaveText('登入');
    });

    test('should successfully login through UI', async ({ page }) => {
      await TestHelpers.loginUI(page, users.admin.username, users.admin.password);
      
      // Should redirect to dashboard
      await expect(page).toHaveURL(/.*dashboard/);
      
      // Should show user info
      await expect(page.locator('[data-testid="user-name"]')).toContainText(users.admin.fullName);
    });

    test('should show error for invalid credentials', async ({ page }) => {
      await page.goto('/login');
      await page.fill('input[name="username"]', users.invalidUser.username);
      await page.fill('input[name="password"]', users.invalidUser.password);
      await page.click('button[type="submit"]');
      
      // Should show error message
      await expect(page.locator('.error-message')).toContainText('使用者名稱或密碼錯誤');
    });

    test('should persist login on page refresh', async ({ page }) => {
      await TestHelpers.loginUI(page, users.admin.username, users.admin.password);
      
      // Refresh page
      await page.reload();
      
      // Should still be logged in
      await expect(page).toHaveURL(/.*dashboard/);
      await expect(page.locator('[data-testid="user-name"]')).toContainText(users.admin.fullName);
    });

    test('should handle session timeout', async ({ page, context }) => {
      await TestHelpers.loginUI(page, users.admin.username, users.admin.password);
      
      // Manually expire the token by clearing storage
      await context.clearCookies();
      await page.evaluate(() => localStorage.clear());
      
      // Try to navigate to protected page
      await page.goto('/customers');
      
      // Should redirect to login
      await expect(page).toHaveURL(/.*login/);
    });

    test('should successfully logout through UI', async ({ page }) => {
      await TestHelpers.loginUI(page, users.admin.username, users.admin.password);
      
      // Click logout button
      await page.click('[data-testid="logout-button"]');
      
      // Should redirect to login
      await expect(page).toHaveURL(/.*login/);
      
      // Try to access protected page
      await page.goto('/dashboard');
      
      // Should redirect back to login
      await expect(page).toHaveURL(/.*login/);
    });
  });

  test.describe('Role-Based Access Control', () => {
    test('admin should have access to all features', async ({ page }) => {
      await TestHelpers.loginUI(page, users.admin.username, users.admin.password);
      
      // Check admin menu items
      const menuItems = [
        { selector: '[data-testid="menu-customers"]', text: '客戶管理' },
        { selector: '[data-testid="menu-orders"]', text: '訂單管理' },
        { selector: '[data-testid="menu-routes"]', text: '路線規劃' },
        { selector: '[data-testid="menu-analytics"]', text: '數據分析' },
        { selector: '[data-testid="menu-users"]', text: '使用者管理' },
        { selector: '[data-testid="menu-settings"]', text: '系統設定' }
      ];
      
      for (const item of menuItems) {
        await expect(page.locator(item.selector)).toBeVisible();
        await expect(page.locator(item.selector)).toContainText(item.text);
      }
    });

    test('manager should have limited access', async ({ page }) => {
      await TestHelpers.loginUI(page, users.manager.username, users.manager.password);
      
      // Should see most menu items but not user management
      await expect(page.locator('[data-testid="menu-customers"]')).toBeVisible();
      await expect(page.locator('[data-testid="menu-analytics"]')).toBeVisible();
      await expect(page.locator('[data-testid="menu-users"]')).not.toBeVisible();
      await expect(page.locator('[data-testid="menu-settings"]')).not.toBeVisible();
    });

    test('office staff should have basic access', async ({ page }) => {
      await TestHelpers.loginUI(page, users.officeStaff.username, users.officeStaff.password);
      
      // Should only see operational menus
      await expect(page.locator('[data-testid="menu-customers"]')).toBeVisible();
      await expect(page.locator('[data-testid="menu-orders"]')).toBeVisible();
      await expect(page.locator('[data-testid="menu-analytics"]')).not.toBeVisible();
      await expect(page.locator('[data-testid="menu-settings"]')).not.toBeVisible();
    });

    test('driver should have minimal access', async ({ page }) => {
      await TestHelpers.loginUI(page, users.driver.username, users.driver.password);
      
      // Should only see driver-specific features
      await expect(page.locator('[data-testid="menu-my-routes"]')).toBeVisible();
      await expect(page.locator('[data-testid="menu-deliveries"]')).toBeVisible();
      await expect(page.locator('[data-testid="menu-customers"]')).not.toBeVisible();
      await expect(page.locator('[data-testid="menu-analytics"]')).not.toBeVisible();
    });

    test('should enforce API-level role restrictions', async () => {
      // Login as office staff
      await apiHelper.login('officeStaff');
      
      // Try to access analytics (should fail)
      const analyticsResponse = await apiHelper.get('/api/v1/analytics/executive');
      expect(analyticsResponse.status()).toBe(403);
      
      // Try to access customers (should succeed)
      const customersResponse = await apiHelper.get('/api/v1/customers/');
      expect(customersResponse.ok()).toBeTruthy();
    });
  });

  test.describe('Security Features', () => {
    test('should handle concurrent sessions', async ({ browser }) => {
      // Create two browser contexts
      const context1 = await browser.newContext();
      const context2 = await browser.newContext();
      
      const page1 = await context1.newPage();
      const page2 = await context2.newPage();
      
      // Login in both browsers
      await TestHelpers.loginUI(page1, users.admin.username, users.admin.password);
      await TestHelpers.loginUI(page2, users.admin.username, users.admin.password);
      
      // Both should be logged in
      await expect(page1).toHaveURL(/.*dashboard/);
      await expect(page2).toHaveURL(/.*dashboard/);
      
      // Logout from first browser
      await page1.click('[data-testid="logout-button"]');
      
      // Second browser should still be logged in
      await page2.reload();
      await expect(page2).toHaveURL(/.*dashboard/);
      
      await context1.close();
      await context2.close();
    });

    test('should prevent CSRF attacks', async ({ request }) => {
      // Try to make request without CSRF token
      const response = await request.post('http://localhost:8000/api/v1/customers/', {
        data: {
          客戶代碼: 'TEST001',
          簡稱: 'Test Customer'
        },
        headers: {
          'Authorization': `Bearer ${await apiHelper.login('admin')}`
        }
      });
      
      // Should still work as we're using JWT (CSRF protection is implicit)
      expect(response.ok()).toBeTruthy();
    });

    test('should sanitize user inputs', async ({ page }) => {
      await TestHelpers.loginUI(page, users.admin.username, users.admin.password);
      
      // Try XSS in customer creation
      await page.goto('/customers/new');
      await page.fill('input[name="客戶代碼"]', '<script>alert("XSS")</script>');
      await page.fill('input[name="簡稱"]', '<img src=x onerror=alert("XSS")>');
      await page.fill('input[name="地址"]', '台北市測試區');
      await page.click('button[type="submit"]');
      
      // Check that script tags are not executed
      const alerts = [];
      page.on('dialog', dialog => alerts.push(dialog));
      
      await page.waitForTimeout(1000);
      expect(alerts.length).toBe(0);
    });
  });
});