import { test, expect } from '@playwright/test';

test.describe('Simple Login Test', () => {
  test.beforeEach(async ({ page }) => {
    // Start mock backend and frontend are assumed to be running
    // Set API URL for the page
    await page.addInitScript(() => {
      (window as any).VITE_API_URL = 'http://localhost:3001';
    });
  });

  test('should login and navigate to dashboard', async ({ page }) => {
    // Enable console logging
    page.on('console', msg => console.log('Browser console:', msg.type(), msg.text()));
    page.on('pageerror', error => console.log('Page error:', error));
    
    // Navigate to login page
    await page.goto('http://localhost:5173/login');
    
    // Wait for login form to be visible
    await expect(page.locator('[data-testid="username-input"]')).toBeVisible();
    
    // Fill in credentials
    await page.fill('[data-testid="username-input"]', 'admin');
    await page.fill('[data-testid="password-input"]', 'admin123');
    
    // Click login button
    await page.click('[data-testid="login-button"]');
    
    // Wait for navigation
    await page.waitForURL('**/dashboard', { timeout: 5000 });
    
    // Verify we're on the dashboard
    const url = page.url();
    console.log('Current URL after login:', url);
    
    // Wait for loading spinner to disappear (if any)
    const spinner = page.locator('.ant-spin');
    if (await spinner.isVisible({ timeout: 1000 }).catch(() => false)) {
      console.log('Waiting for spinner to disappear...');
      await spinner.waitFor({ state: 'hidden', timeout: 10000 });
    }
    
    // Check what content is on the page
    const pageContent = await page.locator('body').textContent();
    console.log('Page content:', pageContent?.substring(0, 200));
    
    // Check if dashboard title is visible
    const dashboardTitle = page.locator('[data-testid="page-title"]');
    await expect(dashboardTitle).toBeVisible({ timeout: 5000 });
    
    // Verify the title content
    const titleText = await dashboardTitle.textContent();
    console.log('Dashboard title:', titleText);
    expect(titleText).toContain('儀表板');
  });
});