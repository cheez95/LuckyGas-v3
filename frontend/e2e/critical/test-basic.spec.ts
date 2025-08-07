import { test, expect } from '@playwright/test';

test('basic test - homepage loads', async ({ page }) => {
  // Navigate to the app
  await page.goto('http://localhost:5173', { waitUntil: 'networkidle' });
  
  // Check if the page has loaded
  await expect(page).toHaveTitle(/幸福氣配送管理系統/);
  
  // Take a screenshot for debugging
  await page.screenshot({ path: 'test-results/homepage.png' });
});