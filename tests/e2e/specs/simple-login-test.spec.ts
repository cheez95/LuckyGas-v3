import { test, expect } from '@playwright/test';

test('Login page loads correctly', async ({ page }) => {
  // Navigate to login page
  await page.goto('/login');
  
  // Wait for page to load
  await page.waitForLoadState('networkidle');
  
  // Check page title
  await expect(page.getByRole('heading', { name: '幸福氣管理系統' })).toBeVisible();
  
  // Check form fields are present
  await expect(page.getByLabel('用戶名')).toBeVisible();
  await expect(page.getByLabel('密碼')).toBeVisible();
  await expect(page.getByRole('button', { name: '登 入' })).toBeVisible();
  
  // Try to login with test credentials
  await page.getByLabel('用戶名').fill('staff@luckygas.com.tw');
  await page.getByLabel('密碼').fill('Staff123!');
  
  // Click login button
  await page.getByRole('button', { name: '登 入' }).click();
  
  // Wait for navigation or error
  await Promise.race([
    page.waitForURL((url) => !url.toString().includes('/login'), { timeout: 10000 }).catch(() => null),
    page.locator('[role="alert"]').waitFor({ timeout: 10000 }).catch(() => null)
  ]);
  
  // Log current state
  console.log('Current URL:', page.url());
  console.log('Has error alert:', await page.locator('[role="alert"]').isVisible().catch(() => false));
  
  // Check if token was stored
  const token = await page.evaluate(() => localStorage.getItem('access_token'));
  console.log('Auth token present:', !!token);
  
  // If we have an error, log it
  const errorText = await page.locator('[role="alert"]').textContent().catch(() => null);
  if (errorText) {
    console.log('Error message:', errorText);
  }
});