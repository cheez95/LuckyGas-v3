import { test, expect } from '@playwright/test';

test.describe('Quick Smoke Test', () => {
  test('should load login page', async ({ page }) => {
    // Navigate to the app
    await page.goto('/');
    
    // Should redirect to login
    await expect(page).toHaveURL(/.*\/login/);
    
    // Check for key elements
    await expect(page.locator('h2.ant-typography')).toContainText('幸福氣瓦斯配送管理系統');
    await expect(page.locator('input#login_username')).toBeVisible();
    await expect(page.locator('input#login_password')).toBeVisible();
    await expect(page.locator('button[type="submit"]')).toBeVisible();
    
    // Take a screenshot
    await page.screenshot({ path: 'screenshots/login-page.png' });
  });
  
  test('should show error with invalid login', async ({ page }) => {
    await page.goto('/login');
    
    // Try to login with invalid credentials
    await page.fill('input#login_username', 'invalid');
    await page.fill('input#login_password', 'invalid');
    await page.click('button[type="submit"]');
    
    // Should show error (either network error or invalid credentials)
    await expect(page.locator('.ant-alert-error')).toBeVisible();
    const errorText = await page.locator('.ant-alert-error').textContent();
    expect(errorText).toMatch(/用戶名或密碼錯誤|網路連線失敗/);
  });
});