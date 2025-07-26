import { Page, BrowserContext } from '@playwright/test';

/**
 * Set up request interception to add authentication headers
 */
export async function setupAuthInterceptor(page: Page) {
  // Intercept all API requests and add auth header
  await page.route('**/api/**', async (route, request) => {
    const token = await page.evaluate(() => localStorage.getItem('access_token'));
    
    const headers = {
      ...request.headers(),
    };
    
    if (token) {
      headers['Authorization'] = `Bearer ${token}`;
    }
    
    await route.continue({ headers });
  });
}

/**
 * Set up auth interceptor for entire context
 */
export async function setupContextAuthInterceptor(context: BrowserContext) {
  // Add auth header to all requests in this context
  await context.route('**/api/**', async (route, request) => {
    // Get the page that made the request
    const pages = context.pages();
    if (pages.length === 0) {
      await route.continue();
      return;
    }
    
    const page = pages[0]; // Use first page in context
    const token = await page.evaluate(() => localStorage.getItem('access_token')).catch(() => null);
    
    const headers = {
      ...request.headers(),
    };
    
    if (token) {
      headers['Authorization'] = `Bearer ${token}`;
    }
    
    await route.continue({ headers });
  });
}

/**
 * Set default headers for a page
 */
export async function setDefaultHeaders(page: Page) {
  // Get current token
  const token = await page.evaluate(() => localStorage.getItem('access_token'));
  
  if (token) {
    // Set extra HTTP headers
    await page.setExtraHTTPHeaders({
      'Authorization': `Bearer ${token}`,
    });
  }
}

/**
 * Ensure authentication state is properly loaded
 */
export async function ensureAuthState(page: Page, storageStatePath?: string) {
  if (storageStatePath) {
    // Storage state should already be loaded by Playwright
    // Just verify token exists
    const token = await page.evaluate(() => localStorage.getItem('access_token'));
    if (!token) {
      console.warn('⚠️ No auth token found after loading storage state');
    }
  }
  
  // Set up auth interceptor
  await setupAuthInterceptor(page);
}