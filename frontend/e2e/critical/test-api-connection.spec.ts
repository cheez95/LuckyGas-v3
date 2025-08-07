import { test, expect } from '@playwright/test';

test.describe('API Connection Test', () => {
  test('Check API connection and login endpoint', async ({ page }) => {
    // Monitor network requests
    const apiRequests: string[] = [];
    page.on('request', request => {
      if (request.url().includes('localhost')) {
        apiRequests.push(`${request.method()} ${request.url()}`);
      }
    });
    
    page.on('requestfailed', request => {
      console.log(`Request failed: ${request.method()} ${request.url()}`);
      console.log(`Failure reason: ${request.failure()?.errorText}`);
    });
    
    // Navigate to the app
    await page.goto('http://localhost:5173');
    
    // Wait for page to load
    await page.waitForLoadState('networkidle');
    
    // Try to login
    await page.fill('input[placeholder="用戶名"]', 'admin@luckygas.com');
    await page.fill('input[type="password"]', 'admin-password-2025');
    await page.click('button:has-text("登 入")');
    
    // Wait a bit for requests
    await page.waitForTimeout(2000);
    
    // Log all API requests
    console.log('API requests made:');
    apiRequests.forEach(req => console.log(req));
    
    // Check if backend is accessible
    try {
      const response = await page.request.get('http://localhost:8000/api/v1/health');
      console.log('Backend health check status:', response.status());
      const data = await response.json();
      console.log('Backend response:', data);
    } catch (error) {
      console.log('Failed to connect to backend:', error);
    }
  });
});