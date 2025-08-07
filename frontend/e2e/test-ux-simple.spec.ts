import { test, expect } from '@playwright/test';

test.describe('Simple UX Test', () => {
  test('should load login page', async ({ page }) => {
    await page.goto('/login');
    await expect(page).toHaveURL(/login/);
    
    // Check login form is visible
    await expect(page.locator('[data-testid="username-input"]')).toBeVisible();
    await expect(page.locator('[data-testid="password-input"]')).toBeVisible();
    await expect(page.locator('[data-testid="login-button"]')).toBeVisible();
    
    console.log('✅ Login page loaded successfully');
  });

  test('should login and navigate to dashboard', async ({ page }) => {
    await page.goto('/login');
    
    // Login
    await page.fill('[data-testid="username-input"]', 'office1');
    await page.fill('[data-testid="password-input"]', 'office123');
    await page.click('[data-testid="login-button"]');
    
    // Should redirect to dashboard
    await expect(page).toHaveURL(/dashboard/);
    await expect(page.locator('h2')).toContainText('儀表板');
    
    console.log('✅ Login successful, dashboard loaded');
  });
});