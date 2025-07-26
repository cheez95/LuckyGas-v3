import { test, expect } from '@playwright/test';

test('debug login page', async ({ page }) => {
  // Listen for console messages
  page.on('console', msg => {
    console.log(`Browser console [${msg.type()}]:`, msg.text());
  });
  
  // Listen for page errors
  page.on('pageerror', error => {
    console.log('Page error:', error.message);
  });
  
  await page.goto('http://localhost:5174/login');
  
  // Wait for any content
  await page.waitForTimeout(3000);
  
  // Take screenshot
  await page.screenshot({ path: 'debug-login.png', fullPage: true });
  
  // Log page content
  const title = await page.title();
  console.log('Page title:', title);
  
  const bodyText = await page.locator('body').textContent();
  console.log('Body text:', bodyText);
  
  // Check if React has rendered
  const rootDiv = await page.locator('#root').innerHTML();
  console.log('Root div content:', rootDiv?.substring(0, 200));
  
  // Look for any input fields
  const inputs = await page.locator('input').count();
  console.log('Number of input fields:', inputs);
  
  // Try to find any data-testid attributes
  const testIds = await page.locator('[data-testid]').count();
  console.log('Elements with data-testid:', testIds);
  
  // Get all data-testid values
  if (testIds > 0) {
    const elements = await page.locator('[data-testid]').all();
    for (const element of elements) {
      const testId = await element.getAttribute('data-testid');
      console.log('Found data-testid:', testId);
    }
  }
  
  // Check network requests
  const response = await page.goto('http://localhost:5174/login');
  console.log('Response status:', response?.status());
});