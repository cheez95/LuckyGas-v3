import { test as base, expect, Page, BrowserContext } from '@playwright/test';
import { TestUsers } from './test-data';
import { setupAuthInterceptor } from './auth-interceptor';

/**
 * Extended test fixtures with common utilities
 */
export const test = base.extend<{
  authenticatedPage: Page;
  authenticatedContext: BrowserContext;
  testUser: typeof TestUsers[keyof typeof TestUsers];
  userRole: 'officeStaff' | 'manager' | 'superAdmin' | 'driver' | 'customer';
}>({
  // Provide authenticated page for different user roles
  authenticatedPage: async ({ page, testUser }, use) => {
    await login(page, testUser.email, testUser.password);
    await use(page);
  },

  // Provide authenticated browser context
  authenticatedContext: async ({ browser, testUser }, use) => {
    const context = await browser.newContext({
      storageState: undefined,
    });
    const page = await context.newPage();
    await login(page, testUser.email, testUser.password);
    
    // Save authentication state
    const storageState = await context.storageState();
    await context.close();

    // Create new context with saved auth
    const authenticatedContext = await browser.newContext({ storageState });
    await use(authenticatedContext);
    await authenticatedContext.close();
  },

  // Default test user (can be overridden in tests)
  testUser: TestUsers.officeStaff,
  
  // Default user role
  userRole: 'officeStaff',
});

/**
 * Test with pre-authenticated state
 */
export const authenticatedTest = base.extend<{
  userRole: 'officeStaff' | 'manager' | 'superAdmin' | 'driver' | 'customer';
}>({
  // Default role
  userRole: 'officeStaff',
  
  // Use saved authentication state
  storageState: async ({ userRole }, use) => {
    const authFile = `./fixtures/.auth/${userRole}.json`;
    await use(authFile);
  },
});

/**
 * Login helper function
 */
export async function login(page: Page, email: string, password: string) {
  await page.goto('/login');
  
  // Use the actual UI elements with Chinese labels
  await page.getByLabel('用戶名').fill(email);
  await page.getByLabel('密碼').fill(password);
  await page.getByRole('button', { name: '登 入' }).click();
  
  // Wait for successful login - different roles redirect to different pages
  await expect(page).toHaveURL(/\/dashboard|\/home|\/driver|\/customer|\/customer-portal/, { timeout: 10000 });
  
  // Verify JWT token is stored
  const token = await page.evaluate(() => localStorage.getItem('access_token'));
  expect(token).toBeTruthy();
  
  // Set up auth interceptor for API requests
  await setupAuthInterceptor(page);
}

/**
 * Logout helper function
 */
export async function logout(page: Page) {
  await page.click('[data-testid="user-menu"]');
  await page.click('[data-testid="logout-button"]');
  await expect(page).toHaveURL('/login');
}

/**
 * Wait for API response helper
 */
export async function waitForApiResponse(
  page: Page,
  urlPattern: string | RegExp,
  method: string = 'GET'
) {
  return page.waitForResponse(
    response => {
      const url = response.url();
      const matchesUrl = typeof urlPattern === 'string' 
        ? url.includes(urlPattern)
        : urlPattern.test(url);
      return matchesUrl && response.request().method() === method;
    },
    { timeout: 30000 }
  );
}

/**
 * Mock API response helper
 */
export async function mockApiResponse(
  page: Page,
  urlPattern: string | RegExp,
  response: any,
  status: number = 200
) {
  await page.route(urlPattern, async route => {
    await route.fulfill({
      status,
      contentType: 'application/json',
      body: JSON.stringify(response),
    });
  });
}

/**
 * Take screenshot with timestamp
 */
export async function takeScreenshot(page: Page, name: string) {
  const timestamp = new Date().toISOString().replace(/[:.]/g, '-');
  await page.screenshot({
    path: `test-results/screenshots/${name}-${timestamp}.png`,
    fullPage: true,
  });
}

/**
 * Fill Taiwan address autocomplete
 */
export async function fillTaiwanAddress(
  page: Page,
  address: string,
  fieldSelector: string = '[data-testid="address-input"]'
) {
  await page.fill(fieldSelector, address);
  
  // Wait for autocomplete suggestions
  await page.waitForSelector('[data-testid="address-suggestions"]', { timeout: 5000 }).catch(() => {});
  
  // Select first suggestion if available
  const firstSuggestion = await page.$('[data-testid="address-suggestion-0"]');
  if (firstSuggestion) {
    await firstSuggestion.click();
  }
}

/**
 * Fill Taiwan phone number with validation
 */
export async function fillPhoneNumber(
  page: Page,
  phone: string,
  fieldSelector: string = '[data-testid="phone-input"]'
) {
  // Clear field first
  await page.fill(fieldSelector, '');
  
  // Type phone number character by character to trigger formatting
  for (const char of phone) {
    await page.type(fieldSelector, char, { delay: 50 });
  }
  
  // Verify formatting
  const value = await page.inputValue(fieldSelector);
  expect(value).toMatch(/^0[2-9]-?\d{3,4}-?\d{4}$|^09\d{2}-?\d{3}-?\d{3}$/);
}

/**
 * Wait for WebSocket connection
 */
export async function waitForWebSocket(page: Page, timeout: number = 10000) {
  await page.waitForFunction(
    () => {
      const ws = (window as any).websocket;
      return ws && ws.readyState === WebSocket.OPEN;
    },
    { timeout }
  );
}

/**
 * Intercept and verify WebSocket messages
 */
export async function interceptWebSocketMessages(
  page: Page,
  messageHandler: (data: any) => void
) {
  await page.evaluateOnNewDocument(() => {
    const originalWebSocket = window.WebSocket;
    
    window.WebSocket = new Proxy(originalWebSocket, {
      construct(target, args) {
        const ws = new target(...args);
        
        ws.addEventListener('message', event => {
          window.postMessage(
            { type: 'websocket-message', data: event.data },
            '*'
          );
        });
        
        return ws;
      },
    });
  });

  page.on('console', msg => {
    if (msg.type() === 'log' && msg.text().includes('websocket-message')) {
      try {
        const data = JSON.parse(msg.text().replace('websocket-message:', ''));
        messageHandler(data);
      } catch (e) {
        // Ignore parsing errors
      }
    }
  });
}

/**
 * Performance measurement helper
 */
export async function measurePerformance(
  page: Page,
  operation: () => Promise<void>
): Promise<{ duration: number; metrics: any }> {
  // Clear performance entries
  await page.evaluate(() => performance.clearMarks());
  
  const startTime = Date.now();
  await operation();
  const duration = Date.now() - startTime;
  
  // Get performance metrics
  const metrics = await page.evaluate(() => {
    const navigation = performance.getEntriesByType('navigation')[0] as PerformanceNavigationTiming;
    return {
      domContentLoaded: navigation.domContentLoadedEventEnd - navigation.domContentLoadedEventStart,
      loadComplete: navigation.loadEventEnd - navigation.loadEventStart,
      firstPaint: performance.getEntriesByName('first-paint')[0]?.startTime || 0,
      firstContentfulPaint: performance.getEntriesByName('first-contentful-paint')[0]?.startTime || 0,
    };
  });
  
  return { duration, metrics };
}

/**
 * Check element visibility and content in Traditional Chinese
 */
export async function expectChineseText(
  page: Page,
  selector: string,
  expectedText: string | RegExp
) {
  await expect(page.locator(selector)).toBeVisible();
  await expect(page.locator(selector)).toContainText(expectedText);
}

/**
 * Network condition simulation
 */
export async function simulateNetworkCondition(
  page: Page,
  condition: 'offline' | 'slow-3g' | 'fast-3g' | '4g' | 'wifi'
) {
  const conditions = {
    'offline': { offline: true },
    'slow-3g': {
      offline: false,
      downloadThroughput: 50 * 1024 / 8, // 50kb/s
      uploadThroughput: 50 * 1024 / 8,
      latency: 400,
    },
    'fast-3g': {
      offline: false,
      downloadThroughput: 1.6 * 1024 * 1024 / 8, // 1.6Mb/s
      uploadThroughput: 750 * 1024 / 8,
      latency: 150,
    },
    '4g': {
      offline: false,
      downloadThroughput: 4 * 1024 * 1024 / 8, // 4Mb/s
      uploadThroughput: 3 * 1024 * 1024 / 8,
      latency: 50,
    },
    'wifi': {
      offline: false,
      downloadThroughput: 30 * 1024 * 1024 / 8, // 30Mb/s
      uploadThroughput: 15 * 1024 * 1024 / 8,
      latency: 2,
    },
  };

  await page.context().setOffline(conditions[condition].offline || false);
  if (!conditions[condition].offline) {
    // Note: Playwright doesn't support throttling directly, 
    // but we can use Chrome DevTools Protocol for Chromium
    const client = await page.context().newCDPSession(page);
    await client.send('Network.emulateNetworkConditions', conditions[condition]);
  }
}

/**
 * Database cleanup helper for test isolation
 */
export async function cleanupTestData(page: Page, testPrefix: string) {
  try {
    // Get auth token
    const token = await page.evaluate(() => localStorage.getItem('access_token'));
    if (!token) {
      console.log('⚠️ No auth token found, skipping cleanup');
      return;
    }
    
    // Call backend cleanup endpoint
    const response = await page.request.delete(`/api/v1/test/cleanup`, {
      headers: {
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json',
      },
      data: { 
        prefix: testPrefix,
        cleanup_orphans: true 
      },
    });
    
    if (response.ok()) {
      const result = await response.json();
      console.log(`✅ Test data cleanup successful: ${JSON.stringify(result.deleted_counts)}`);
    } else {
      console.log(`⚠️ Test data cleanup failed: ${response.status()}`);
    }
  } catch (error) {
    console.log('⚠️ Error during test data cleanup:', error);
  }
}

export { expect } from '@playwright/test';