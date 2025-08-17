import { test, expect } from '@playwright/test';
import { LoginPage } from './pages/LoginPage';
import { ConsoleMonitor, NetworkMonitor, assertNoConsoleErrors, takeScreenshot } from './helpers/testHelpers';

test.describe('Authentication Tests', () => {
  let loginPage: LoginPage;
  let consoleMonitor: ConsoleMonitor;
  let networkMonitor: NetworkMonitor;

  test.beforeEach(async ({ page }) => {
    // Initialize monitors
    consoleMonitor = new ConsoleMonitor(page);
    networkMonitor = new NetworkMonitor(page);
    
    // Initialize page object
    loginPage = new LoginPage(page);
    
    // Navigate to login page
    await loginPage.goto();
  });

  test.afterEach(async ({ page }, testInfo) => {
    // Take screenshot on failure
    if (testInfo.status !== testInfo.expectedStatus) {
      await takeScreenshot(page, `auth-failure-${testInfo.title}`);
    }
    
    // Check for console errors
    const errors = consoleMonitor.getErrors();
    if (errors.length > 0) {
      console.log('Console errors:', errors);
    }
  });

  test('should display login page correctly', async ({ page }) => {
    // Check login page elements are visible
    await expect(loginPage.loginForm).toBeVisible();
    await expect(loginPage.usernameInput).toBeVisible();
    await expect(loginPage.passwordInput).toBeVisible();
    await expect(loginPage.loginButton).toBeVisible();
    
    // Check for Lucky Gas branding
    const title = await page.title();
    expect(title).toContain('幸福氣');
    
    // No console errors should be present
    await assertNoConsoleErrors(page, consoleMonitor);
  });

  test('should login successfully with valid credentials', async ({ page }) => {
    // Perform login
    await loginPage.login('admin@luckygas.com', 'admin123');
    
    // Wait for successful navigation
    await page.waitForLoadState('networkidle');
    
    // Check if logged in
    const isLoggedIn = await loginPage.isLoggedIn();
    expect(isLoggedIn).toBeTruthy();
    
    // Verify URL changed
    const url = page.url();
    expect(url).toMatch(/dashboard|orders|customers/);
    
    // Check for successful API calls
    const apiRequests = networkMonitor.getAPIRequests();
    expect(apiRequests.length).toBeGreaterThan(0);
    
    // No failed API requests
    const failedRequests = networkMonitor.getFailedRequests();
    expect(failedRequests).toHaveLength(0);
  });

  test('should show error with invalid credentials', async ({ page }) => {
    // Try login with invalid credentials
    await loginPage.login('invalid@email.com', 'wrongpassword');
    
    // Wait for error message
    await page.waitForTimeout(2000);
    
    // Check error message is displayed
    const errorMessage = await loginPage.getErrorMessage();
    expect(errorMessage).toBeTruthy();
    
    // Should still be on login page
    const isLoggedIn = await loginPage.isLoggedIn();
    expect(isLoggedIn).toBeFalsy();
  });

  test('should handle empty form submission', async ({ page }) => {
    // Click login without entering credentials
    await loginPage.loginButton.click();
    
    // Should show validation errors
    const validationErrors = await page.locator('.ant-form-item-explain-error').count();
    expect(validationErrors).toBeGreaterThan(0);
    
    // Should still be on login page
    const isLoggedIn = await loginPage.isLoggedIn();
    expect(isLoggedIn).toBeFalsy();
  });

  test('should preserve session after page refresh', async ({ page, context }) => {
    // Login first
    await loginPage.login('admin@luckygas.com', 'admin123');
    await page.waitForLoadState('networkidle');
    
    // Verify logged in
    let isLoggedIn = await loginPage.isLoggedIn();
    expect(isLoggedIn).toBeTruthy();
    
    // Refresh page
    await page.reload();
    await page.waitForLoadState('networkidle');
    
    // Should still be logged in
    isLoggedIn = await loginPage.isLoggedIn();
    expect(isLoggedIn).toBeTruthy();
    
    // Check localStorage or cookies for token
    const token = await page.evaluate(() => {
      return localStorage.getItem('token') || sessionStorage.getItem('token');
    });
    expect(token).toBeTruthy();
  });

  test('should handle network errors gracefully', async ({ page, context }) => {
    // Simulate offline mode
    await context.setOffline(true);
    
    // Try to login
    await loginPage.login('admin@luckygas.com', 'admin123');
    
    // Should show network error
    await page.waitForTimeout(2000);
    const errorMessage = await loginPage.getErrorMessage();
    expect(errorMessage).toBeTruthy();
    
    // Re-enable network
    await context.setOffline(false);
  });

  test('should redirect to login when accessing protected route', async ({ page }) => {
    // Try to access protected route directly
    await page.goto('/#/office/orders');
    await page.waitForLoadState('networkidle');
    
    // Should be redirected to login
    await loginPage.waitForLoginPage();
    const url = page.url();
    expect(url).toMatch(/login|#\/$/);
  });

  test('should handle concurrent login attempts', async ({ page, context }) => {
    // Open second tab
    const page2 = await context.newPage();
    const loginPage2 = new LoginPage(page2);
    await loginPage2.goto();
    
    // Login in both tabs simultaneously
    await Promise.all([
      loginPage.login('admin@luckygas.com', 'admin123'),
      loginPage2.login('admin@luckygas.com', 'admin123')
    ]);
    
    // Both should be logged in
    const [isLoggedIn1, isLoggedIn2] = await Promise.all([
      loginPage.isLoggedIn(),
      loginPage2.isLoggedIn()
    ]);
    
    expect(isLoggedIn1).toBeTruthy();
    expect(isLoggedIn2).toBeTruthy();
    
    await page2.close();
  });

  test('should test forgot password link', async ({ page }) => {
    // Check forgot password link exists
    await expect(loginPage.forgotPasswordLink).toBeVisible();
    
    // Click forgot password
    await loginPage.forgotPasswordLink.click();
    
    // Should navigate to forgot password page
    await page.waitForLoadState('networkidle');
    const url = page.url();
    expect(url).toContain('forgot');
  });

  test('should handle XSS attempts in login form', async ({ page }) => {
    // Try XSS in username field
    const xssPayload = '<script>alert("XSS")</script>';
    await loginPage.login(xssPayload, 'password');
    
    // Check that no alert was triggered
    let alertTriggered = false;
    page.on('dialog', () => {
      alertTriggered = true;
    });
    
    await page.waitForTimeout(2000);
    expect(alertTriggered).toBeFalsy();
    
    // Check console for XSS attempts
    const errors = consoleMonitor.getErrors();
    const xssErrors = errors.filter(e => e.text.toLowerCase().includes('script'));
    expect(xssErrors).toHaveLength(0);
  });
});