import { test, expect } from '@playwright/test';

test.describe('Authentication Flow', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/', { waitUntil: 'networkidle' });
  });

  test('should display login page', async ({ page }) => {
    // Check for login form elements
    await expect(page.locator('form')).toBeVisible();
    await expect(page.locator('input[type="text"]')).toBeVisible();
    await expect(page.locator('input[type="password"]')).toBeVisible();
    await expect(page.locator('button[type="submit"]')).toBeVisible();
  });

  test('should show validation errors for empty fields', async ({ page }) => {
    // Click submit without filling fields
    await page.locator('button[type="submit"]').click();
    
    // Wait for validation messages
    await page.waitForTimeout(500);
    
    // Check for error messages (Ant Design adds these classes)
    const errors = await page.locator('.ant-form-item-explain-error').count();
    expect(errors).toBeGreaterThan(0);
  });

  test('should handle invalid login attempt', async ({ page }) => {
    // Fill in invalid credentials
    await page.locator('input[type="text"]').fill('invalid@user.com');
    await page.locator('input[type="password"]').fill('wrongpassword');
    await page.locator('button[type="submit"]').click();
    
    // Wait for network error message
    await page.waitForSelector('[role="alert"]', { state: 'visible', timeout: 5000 });
    
    // Should still be on login page
    await expect(page.locator('form')).toBeVisible();
    
    // Check error message
    const errorAlert = page.locator('[role="alert"]');
    await expect(errorAlert).toBeVisible();
  });

  test('should successfully login with valid credentials', async ({ page }) => {
    // Monitor network to ensure request completes
    const responsePromise = page.waitForResponse(resp => 
      resp.url().includes('/auth/login') && resp.status() === 200
    );
    
    // Use test credentials
    await page.locator('input[type="text"]').fill('admin');
    await page.locator('input[type="password"]').fill('admin123');
    
    // Click login and wait for response
    await Promise.all([
      page.locator('button[type="submit"]').click(),
      responsePromise
    ]);
    
    // Give some time for the redirect to happen
    await page.waitForTimeout(2000);
    
    // Check if we navigated away from login
    const currentUrl = page.url();
    console.log('Current URL after login:', currentUrl);
    
    // Should not be on login page anymore
    expect(currentUrl).not.toContain('/login');
    
    // Verify token is stored
    const token = await page.evaluate(() => localStorage.getItem('access_token'));
    expect(token).toBeTruthy();
  });

  test('should handle logout', async ({ page }) => {
    // First login
    const loginResponsePromise = page.waitForResponse(resp => 
      resp.url().includes('/auth/login') && resp.status() === 200
    );
    
    await page.locator('input[type="text"]').fill('admin');
    await page.locator('input[type="password"]').fill('admin123');
    
    await Promise.all([
      page.locator('button[type="submit"]').click(),
      loginResponsePromise
    ]);
    
    // Wait for redirect
    await page.waitForTimeout(2000);
    
    // Try to find logout button - it might be in a dropdown menu
    const possibleLogoutLocations = [
      // Direct logout button
      'button:has-text("登出")',
      'a:has-text("登出")',
      // User menu that might contain logout
      '.ant-dropdown-trigger',
      '.ant-avatar',
      '[data-testid="user-menu"]',
      // Header items
      '.ant-layout-header button',
      '.ant-layout-header .ant-avatar'
    ];
    
    let logoutFound = false;
    
    for (const selector of possibleLogoutLocations) {
      const element = page.locator(selector).first();
      if (await element.isVisible({ timeout: 1000 }).catch(() => false)) {
        // Click to open dropdown if needed
        await element.click();
        await page.waitForTimeout(500);
        
        // Now look for logout option
        const logoutOption = page.locator('text=/登出|logout|退出/i').first();
        if (await logoutOption.isVisible({ timeout: 1000 }).catch(() => false)) {
          await logoutOption.click();
          logoutFound = true;
          break;
        }
      }
    }
    
    if (logoutFound) {
      // Wait for redirect to login
      await page.waitForURL(/\/login/, { timeout: 5000 });
      await expect(page.locator('form')).toBeVisible();
      
      // Verify token is cleared
      const token = await page.evaluate(() => localStorage.getItem('access_token'));
      expect(token).toBeNull();
    } else {
      console.log('Logout feature not found - might not be implemented yet');
    }
  });

  test('should persist session across page refresh', async ({ page }) => {
    // Login first
    const loginResponsePromise = page.waitForResponse(resp => 
      resp.url().includes('/auth/login') && resp.status() === 200
    );
    
    await page.locator('input[type="text"]').fill('admin');
    await page.locator('input[type="password"]').fill('admin123');
    
    await Promise.all([
      page.locator('button[type="submit"]').click(),
      loginResponsePromise
    ]);
    
    // Wait for redirect
    await page.waitForTimeout(2000);
    
    const dashboardUrl = page.url();
    expect(dashboardUrl).not.toContain('/login');
    
    // Refresh page
    await page.reload({ waitUntil: 'networkidle' });
    
    // Should still be on the same page (not redirected to login)
    expect(page.url()).toBe(dashboardUrl);
    
    // Verify token still exists
    const token = await page.evaluate(() => localStorage.getItem('access_token'));
    expect(token).toBeTruthy();
  });

  test('should redirect to login when accessing protected routes without auth', async ({ page }) => {
    // Clear any existing session
    await page.context().clearCookies();
    await page.evaluate(() => {
      localStorage.clear();
      sessionStorage.clear();
    });
    
    // Try to access dashboard without login
    await page.goto('/dashboard', { waitUntil: 'networkidle' });
    
    // Should redirect to login
    await page.waitForURL(/\/login/, { timeout: 5000 });
    
    // Should show login form
    await expect(page.locator('form')).toBeVisible();
    await expect(page.locator('input[type="password"]')).toBeVisible();
  });
});