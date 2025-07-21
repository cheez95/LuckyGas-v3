import { test, expect } from '@playwright/test';
import { LoginPage } from './pages/LoginPage';
import { DashboardPage } from './pages/DashboardPage';

test.describe('Authentication', () => {
  let loginPage: LoginPage;
  let dashboardPage: DashboardPage;

  test.beforeAll(async ({ browserName }) => {
    // Skip tests for browsers that are not installed
    if (browserName === 'microsoft-edge' && process.env.CI) {
      test.skip();
    }
  });

  test.beforeEach(async ({ page }) => {
    loginPage = new LoginPage(page);
    dashboardPage = new DashboardPage(page);
    await loginPage.navigateToLogin();
  });

  test('should display login form in Traditional Chinese', async ({ page }) => {
    // Check page title
    await expect(loginPage.loginTitle).toContainText('幸福氣瓦斯配送管理系統');
    
    // Check form elements are visible
    await expect(loginPage.usernameInput).toBeVisible();
    await expect(loginPage.passwordInput).toBeVisible();
    await expect(loginPage.loginButton).toBeVisible();
    
    // Check Chinese localization
    const isChineseLocalized = await loginPage.checkChineseLocalization();
    expect(isChineseLocalized).toBe(true);
  });

  test('should login successfully with valid credentials', async ({ page }) => {
    // Fill in credentials
    await loginPage.fillUsername('admin');
    await loginPage.fillPassword('admin123');
    
    // Submit form
    await loginPage.clickLogin();
    
    // Wait for redirect to dashboard
    await loginPage.waitForLoginSuccess();
    
    // Verify we're on dashboard
    await expect(page).toHaveURL(/.*\/dashboard/);
    await expect(dashboardPage.pageTitle).toBeVisible();
  });

  test('should show error message with invalid credentials', async ({ page }) => {
    // Fill in invalid credentials
    await loginPage.fillUsername('invalid');
    await loginPage.fillPassword('wrong');
    
    // Submit form
    await loginPage.clickLogin();
    
    // Check error message appears
    await expect(loginPage.errorAlert).toBeVisible();
    const errorMessage = await loginPage.getErrorMessage();
    expect(errorMessage).toMatch(/帳號或密碼錯誤|網路連線失敗/);
    
    // Should still be on login page
    await expect(page).toHaveURL(/.*\/login/);
  });

  test('should redirect to login when accessing protected routes without auth', async ({ page }) => {
    // Try to access dashboard directly
    await page.goto('/dashboard');
    
    // Should be redirected to login
    await expect(page).toHaveURL(/.*\/login/);
    await expect(loginPage.usernameInput).toBeVisible();
  });

  test('should logout successfully', async ({ page }) => {
    // First login
    await loginPage.login('admin', 'admin123');
    await loginPage.waitForLoginSuccess();
    
    // Verify on dashboard
    await expect(dashboardPage.pageTitle).toBeVisible();
    
    // Logout
    await dashboardPage.logout();
    
    // Should be back on login page
    await expect(page).toHaveURL(/.*\/login/);
    await expect(loginPage.usernameInput).toBeVisible();
  });

  test('should persist authentication on page refresh', async ({ page }) => {
    // Login
    await loginPage.login('admin', 'admin123');
    await loginPage.waitForLoginSuccess();
    
    // Wait for dashboard to be fully loaded
    await expect(dashboardPage.pageTitle).toBeVisible();
    
    // Refresh page
    await page.reload();
    
    // Wait for page to reload and auth to be restored
    await page.waitForLoadState('networkidle');
    
    // Should still be on dashboard
    await expect(page).toHaveURL(/.*\/dashboard/);
    
    // Wait for dashboard content to load after auth restoration
    await expect(dashboardPage.pageTitle).toBeVisible({ timeout: 10000 });
  });

  test('should handle session expiry gracefully', async ({ page }) => {
    // Login
    await loginPage.login('admin', 'admin123');
    await loginPage.waitForLoginSuccess();
    
    // Simulate session expiry by clearing local storage
    await page.evaluate(() => {
      localStorage.removeItem('access_token');
    });
    
    // Reload the page to trigger re-authentication check
    await page.reload();
    
    // Should be redirected to login
    await page.waitForURL(/.*\/login/);
    
    // Should be redirected to login with session expired message
    await expect(page).toHaveURL(/.*\/login/);
    // Optionally check for session expired message
  });

  test('should display login form correctly on mobile', async ({ page }) => {
    // Set mobile viewport
    await page.setViewportSize({ width: 375, height: 812 });
    
    // Check mobile layout
    const isMobileLayout = await loginPage.checkMobileLayout();
    expect(isMobileLayout).toBe(true);
    
    // Form should still be functional
    await expect(loginPage.usernameInput).toBeVisible();
    await expect(loginPage.passwordInput).toBeVisible();
    await expect(loginPage.loginButton).toBeVisible();
  });

  test('should handle concurrent login attempts', async ({ page, context }) => {
    // Create a second page
    const page2 = await context.newPage();
    const loginPage2 = new LoginPage(page2);
    await loginPage2.navigateToLogin();
    
    // Login on first page
    await loginPage.login('admin', 'admin123');
    await loginPage.waitForLoginSuccess();
    
    // Login on second page with same credentials
    await loginPage2.login('admin', 'admin123');
    await loginPage2.waitForLoginSuccess();
    
    // Both should be logged in
    await expect(page).toHaveURL(/.*\/dashboard/);
    await expect(page2).toHaveURL(/.*\/dashboard/);
    
    // Cleanup
    await page2.close();
  });

  test('should validate required fields', async ({ page }) => {
    // Try to login without filling any fields
    await loginPage.clickLogin();
    
    // Should show validation errors
    const usernameError = page.locator('#login_username_help');
    const passwordError = page.locator('#login_password_help');
    
    await expect(usernameError).toBeVisible();
    await expect(passwordError).toBeVisible();
    
    // Should still be on login page
    await expect(page).toHaveURL(/.*\/login/);
  });

  test('should handle network errors gracefully', async ({ page }) => {
    // Simulate network failure
    await page.route('**/api/v1/auth/login', route => route.abort('failed'));
    
    // Try to login
    await loginPage.login('admin', 'admin123');
    
    // Should show network error
    await expect(loginPage.errorAlert).toBeVisible();
    const errorMessage = await loginPage.getErrorMessage();
    expect(errorMessage).toContain('網路連線');
  });

  test('should clear form after successful login', async ({ page, context }) => {
    // Login successfully
    await loginPage.login('admin', 'admin123');
    await loginPage.waitForLoginSuccess();
    
    // Logout
    await dashboardPage.logout();
    
    // Check form is cleared
    await expect(loginPage.usernameInput).toHaveValue('');
    await expect(loginPage.passwordInput).toHaveValue('');
  });
});

test.describe('Role-based Access Control', () => {
  test.skip('should show different menu items based on user role', async ({ page }) => {
    // Skip this test until seed data for different user roles is created
    const loginPage = new LoginPage(page);
    const dashboardPage = new DashboardPage(page);
    
    // Test admin role
    await loginPage.navigateToLogin();
    await loginPage.login('admin', 'admin123');
    await loginPage.waitForLoginSuccess();
    
    // Admin should see all menu items
    await expect(dashboardPage.customersMenuItem).toBeVisible();
    await expect(dashboardPage.ordersMenuItem).toBeVisible();
    await expect(dashboardPage.routesMenuItem).toBeVisible();
    
    // Logout
    await dashboardPage.logout();
    
    // Test office staff role
    await loginPage.login('office1', 'office123');
    await loginPage.waitForLoginSuccess();
    
    // Office staff might not see routes menu
    await expect(dashboardPage.customersMenuItem).toBeVisible();
    await expect(dashboardPage.ordersMenuItem).toBeVisible();
    // Routes might be hidden for office staff
  });
});