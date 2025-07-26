import { test, expect } from '@playwright/test';
import { TestUsers } from '../fixtures/test-data';
import { setupAuthInterceptor } from '../fixtures/auth-interceptor';
import path from 'path';

test.describe('Auth Interceptor Verification', () => {
  // Test for each user role
  const roles = [
    { name: 'Office Staff', user: TestUsers.officeStaff, authFile: '.auth/officeStaff.json' },
    { name: 'Manager', user: TestUsers.manager, authFile: '.auth/manager.json' },
    { name: 'Driver', user: TestUsers.driver, authFile: '.auth/driver.json' },
    { name: 'Customer', user: TestUsers.customer, authFile: '.auth/customer.json' },
  ];

  for (const { name, user, authFile } of roles) {
    test(`${name} - should authenticate with interceptor`, async ({ browser }) => {
      // Create a new context with saved auth state
      const context = await browser.newContext({
        storageState: authFile,
      });
      const page = await context.newPage();
      
      // Set up auth interceptor
      await setupAuthInterceptor(page);
      
      // Navigate directly to a protected route
      await page.goto('/dashboard');
      
      // Wait for page to load
      await page.waitForLoadState('networkidle');
      
      // Verify we're not redirected to login
      const currentUrl = page.url();
      expect(currentUrl).not.toContain('/login');
      
      // Verify auth token exists
      const token = await page.evaluate(() => localStorage.getItem('access_token'));
      expect(token).toBeTruthy();
      
      // Get the auth token to add to request
      const authToken = await page.evaluate(() => localStorage.getItem('access_token'));
      
      // Make an API request with auth header
      const response = await page.request.get('/api/v1/orders', {
        failOnStatusCode: false,
        headers: authToken ? {
          'Authorization': `Bearer ${authToken}`
        } : {},
      });
      
      // Should not get 401 if auth header is included
      expect(response.status()).not.toBe(401);
      
      // Verify the response is successful or a redirect (307)
      expect([200, 307]).toContain(response.status());
      
      // Log the response for debugging
      console.log(`${name} API response status: ${response.status()}`);
      
      // Also test that browser requests work with the interceptor
      const browserApiResult = await page.evaluate(async () => {
        try {
          const response = await fetch('/api/v1/orders');
          return {
            status: response.status,
            ok: response.ok
          };
        } catch (error) {
          return { error: error.message };
        }
      });
      
      console.log(`${name} browser fetch result:`, browserApiResult);
      
      await context.close();
    });
  }

  test('Direct API test with auth interceptor', async ({ page }) => {
    // Use pre-authenticated state
    await page.goto('/login');
    await page.getByLabel('用戶名').fill(TestUsers.officeStaff.email);
    await page.getByLabel('密碼').fill(TestUsers.officeStaff.password);
    await page.getByRole('button', { name: '登 入' }).click();
    
    // Wait for navigation
    await page.waitForURL(/\/dashboard|\/home/, { timeout: 10000 });
    
    // Set up auth interceptor
    await setupAuthInterceptor(page);
    
    // Test API endpoint directly through browser
    const ordersResponse = await page.evaluate(async () => {
      const token = localStorage.getItem('access_token');
      try {
        const response = await fetch('/api/v1/orders', {
          headers: {
            'Authorization': `Bearer ${token}`,
          },
        });
        return {
          status: response.status,
          hasToken: !!token,
          ok: response.ok,
        };
      } catch (error) {
        return {
          error: error.message,
          hasToken: !!token,
        };
      }
    });
    
    console.log('Direct API response:', ordersResponse);
    
    expect(ordersResponse.hasToken).toBe(true);
    expect(ordersResponse.error).toBeUndefined();
    if (ordersResponse.status) {
      expect([200, 307]).toContain(ordersResponse.status);
    }
  });
});