import { test, expect } from '@playwright/test';

test.describe('Debug Login', () => {
  test('debug login request', async ({ page }) => {
    // Monitor network requests
    const requests: any[] = [];
    page.on('request', request => {
      if (request.url().includes('auth/login')) {
        console.log('Login request:', {
          url: request.url(),
          method: request.method(),
          headers: request.headers(),
          postData: request.postData()
        });
        requests.push(request);
      }
    });

    page.on('response', response => {
      if (response.url().includes('auth/login')) {
        console.log('Login response:', {
          url: response.url(),
          status: response.status(),
          statusText: response.statusText()
        });
      }
    });

    // Navigate to login page
    await page.goto('/');
    await page.waitForLoadState('networkidle');
    
    // Fill login form
    await page.locator('input[type="text"]').fill('admin');
    await page.locator('input[type="password"]').fill('admin123');
    
    // Click login button
    await page.locator('button[type="submit"]').click();
    
    // Wait a bit to see what happens
    await page.waitForTimeout(2000);
    
    // Check if we made a request
    console.log('Total login requests:', requests.length);
    
    // Check current URL
    console.log('Current URL:', page.url());
    
    // Check for any errors
    const errorAlert = page.locator('[role="alert"]');
    if (await errorAlert.isVisible()) {
      console.log('Error message:', await errorAlert.textContent());
    }
    
    // Check localStorage
    const token = await page.evaluate(() => localStorage.getItem('access_token'));
    console.log('Access token in localStorage:', token);
  });
});