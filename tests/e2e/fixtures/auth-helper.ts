import { Page } from '@playwright/test';

/**
 * Inject auth header into all fetch requests
 */
export async function injectAuthHeader(page: Page) {
  await page.addInitScript(() => {
    // Store the original fetch
    const originalFetch = window.fetch;
    
    // Override fetch to add auth header
    window.fetch = async function(...args) {
      const [resource, config] = args;
      
      // Get the auth token
      const token = localStorage.getItem('access_token');
      
      // If we have a token and the request is to our API
      if (token && typeof resource === 'string' && resource.includes('/api/')) {
        // Ensure config exists
        const newConfig = config || {};
        
        // Ensure headers exist
        newConfig.headers = newConfig.headers || {};
        
        // Add auth header if not already present
        if (!newConfig.headers['Authorization'] && !newConfig.headers['authorization']) {
          newConfig.headers['Authorization'] = `Bearer ${token}`;
        }
        
        // Call original fetch with modified config
        return originalFetch(resource, newConfig);
      }
      
      // For non-API requests, call original fetch as-is
      return originalFetch(...args);
    };
  });
}

/**
 * Setup complete auth handling for a page
 */
export async function setupCompleteAuth(page: Page) {
  // Inject auth header into fetch requests
  await injectAuthHeader(page);
  
  // Also intercept navigation requests (for things like page navigation)
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