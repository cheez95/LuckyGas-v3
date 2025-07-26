import { test, expect } from '@playwright/test';

test.describe('Smoke Tests', () => {
  test('should load login page', async ({ page }) => {
    // Try to load the login page
    await page.goto('http://localhost:3000/login');
    
    // Check that we reached a page (not connection refused)
    const title = await page.title();
    expect(title).toBeTruthy();
    
    // Check for any content on the page
    const content = await page.textContent('body');
    expect(content).toBeTruthy();
  });

  test('should connect to backend API', async ({ request }) => {
    // Try to hit the backend health endpoint
    const response = await request.get('http://localhost:8000/api/v1/health', {
      failOnStatusCode: false
    });
    
    // We should get some response (even if 404)
    expect(response.status()).toBeLessThan(600);
  });
});