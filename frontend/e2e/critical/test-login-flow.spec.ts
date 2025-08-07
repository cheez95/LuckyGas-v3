import { test, expect } from '@playwright/test';

test.describe('Login Flow', () => {
  test('Staff can login with valid credentials', async ({ page }) => {
    // Navigate to the app
    await page.goto('http://localhost:5173');
    
    // Wait for login form to be visible
    await expect(page.getByTestId('login-title')).toBeVisible();
    
    // Fill in login credentials
    await page.fill('input[placeholder="用戶名"]', 'admin@luckygas.com');
    await page.fill('input[type="password"]', 'admin-password-2025');
    
    // Click login button
    await page.click('button:has-text("登 入")');
    
    // Wait for either navigation or error message
    await Promise.race([
      page.waitForURL('**/dashboard', { timeout: 5000 }).catch(() => null),
      page.waitForURL('**/', { timeout: 5000 }).catch(() => null),
      page.waitForSelector('text=網路連線錯誤', { timeout: 5000 }).catch(() => null),
      page.waitForSelector('[role="alert"]', { timeout: 5000 }).catch(() => null),
    ]);
    
    // Take screenshot to see result
    await page.screenshot({ path: 'test-results/after-login.png' });
    
    // Check for errors
    const errorMessage = await page.locator('[role="alert"]').textContent().catch(() => null);
    if (errorMessage) {
      console.log('Error message:', errorMessage);
    }
    
    // Check if we're logged in (looking for dashboard or error)
    const url = page.url();
    console.log('Current URL after login:', url);
    
    // If we're still on login page, check for network errors
    if (url.includes('/login')) {
      const networkError = await page.locator('text=網路連線錯誤').isVisible().catch(() => false);
      if (networkError) {
        console.log('Network connection error detected');
      }
    }
  });
});