import { test as base, expect } from '@playwright/test';
import { WebSocketTestHelper } from './utils/WebSocketTestHelper';

// Extend the base test with custom fixtures
export const test = base.extend<{
  webSocketHelper: WebSocketTestHelper;
  authenticated: void;
}>({
  // WebSocket helper fixture
  webSocketHelper: async ({ page }, use) => {
    const helper = new WebSocketTestHelper(page);
    await helper.setupWebSocketInterception();
    await use(helper);
  },

  // Auto-authenticate fixture
  authenticated: [async ({ page }, use) => {
    // Navigate to login page
    await page.goto('/login');
    
    // Fill login form
    await page.fill('input[id="username"]', 'admin');
    await page.fill('input[id="password"]', 'admin123');
    
    // Submit form
    await page.click('button[type="submit"]');
    
    // Wait for navigation to dashboard
    await page.waitForURL('**/dashboard', { timeout: 10000 });
    
    // Verify authentication
    const token = await page.evaluate(() => {
      return localStorage.getItem('access_token');
    });
    
    expect(token).toBeTruthy();
    
    // Use the authenticated context
    await use();
  }, { auto: true }],
});

// Re-export expect for convenience
export { expect };

// Custom matchers
export const customExpect = {
  async toHaveChineseText(locator: unknown, expectedText: string) {
    const actualText = await locator.textContent();
    return {
      pass: actualText?.includes(expectedText) || false,
      message: () => `Expected to find Chinese text "${expectedText}" but got "${actualText}"`
    };
  },

  async toBeValidPhoneNumber(value: string, isLandline: boolean = false) {
    const mobileRegex = /^09\d{8}$/;
    const landlineRegex = /^0[2-8]\d{7,8}$/;
    const regex = isLandline ? landlineRegex : mobileRegex;
    
    return {
      pass: regex.test(value.replace(/[\s-]/g, '')),
      message: () => `Expected "${value}" to be a valid ${isLandline ? 'landline' : 'mobile'} number`
    };
  }
};

// Test data factories
export const testData = {
  generateCustomerCode: () => {
    const timestamp = Date.now();
    return `TEST${timestamp}`;
  },

  generatePhoneNumber: (isMobile: boolean = true) => {
    if (isMobile) {
      return `09${Math.floor(Math.random() * 100000000).toString().padStart(8, '0')}`;
    } else {
      const areaCode = Math.floor(Math.random() * 7) + 2;
      return `0${areaCode}-${Math.floor(Math.random() * 10000000).toString().padStart(7, '0')}`;
    }
  },

  generateAddress: () => {
    const streets = ['忠孝東路', '信義路', '仁愛路', '和平東路', '民生東路'];
    const districts = ['大安區', '信義區', '中正區', '松山區', '中山區'];
    const cities = ['台北市', '新北市', '台中市', '高雄市', '台南市'];
    
    const street = streets[Math.floor(Math.random() * streets.length)];
    const district = districts[Math.floor(Math.random() * districts.length)];
    const city = cities[Math.floor(Math.random() * cities.length)];
    const number = Math.floor(Math.random() * 500) + 1;
    const section = Math.floor(Math.random() * 5) + 1;
    
    return `${city}${district}${street}${section}段${number}號`;
  },

  generateTaxId: () => {
    // Generate valid Taiwan tax ID
    const digits = Array.from({ length: 7 }, () => Math.floor(Math.random() * 10));
    const weights = [1, 2, 1, 2, 1, 2, 4];
    
    let checksum = 0;
    for (let i = 0; i < 7; i++) {
      const product = digits[i] * weights[i];
      checksum += Math.floor(product / 10) + (product % 10);
    }
    
    const lastDigit = (10 - (checksum % 10)) % 10;
    digits.push(lastDigit);
    
    return digits.join('');
  }
};

// Common test helpers
export const helpers = {
  async waitForToast(page: unknown, message?: string, timeout: number = 5000) {
    const toastLocator = message 
      ? page.locator('.ant-message-notice').filter({ hasText: message })
      : page.locator('.ant-message-notice');
    
    await toastLocator.waitFor({ state: 'visible', timeout });
    await toastLocator.waitFor({ state: 'hidden', timeout: timeout + 5000 });
  },

  async waitForTableLoad(page: unknown) {
    // Wait for loading spinner to appear and disappear
    const spinner = page.locator('.ant-spin-spinning');
    if (await spinner.isVisible()) {
      await spinner.waitFor({ state: 'hidden', timeout: 10000 });
    }
    
    // Wait for table to have data
    await page.waitForSelector('.ant-table-tbody tr:not([aria-hidden="true"])', { 
      state: 'visible',
      timeout: 10000 
    });
  },

  async selectFromDropdown(page: unknown, triggerLocator: unknown, optionText: string) {
    await triggerLocator.click();
    await page.waitForSelector('.ant-select-dropdown', { state: 'visible' });
    await page.waitForTimeout(200); // Wait for animation
    
    const option = page.locator('.ant-select-dropdown .ant-select-item').filter({ hasText: optionText });
    await option.click();
    
    // Wait for dropdown to close
    await page.waitForSelector('.ant-select-dropdown', { state: 'hidden' });
  },

  async fillDatePicker(page: unknown, inputLocator: unknown, date: Date) {
    await inputLocator.click();
    await page.waitForSelector('.ant-picker-dropdown', { state: 'visible' });
    
    // Format date as YYYY-MM-DD
    const dateStr = date.toISOString().split('T')[0];
    
    await inputLocator.fill(dateStr);
    await page.keyboard.press('Enter');
    
    // Wait for picker to close
    await page.waitForSelector('.ant-picker-dropdown', { state: 'hidden' });
  },

  async fillTimeRangePicker(page: unknown, inputLocator: unknown, startTime: string, endTime: string) {
    await inputLocator.first().click();
    await page.waitForSelector('.ant-picker-dropdown', { state: 'visible' });
    
    // Clear and type start time
    await page.keyboard.press('Control+A');
    await page.keyboard.type(startTime);
    await page.keyboard.press('Tab');
    
    // Type end time
    await page.keyboard.type(endTime);
    await page.keyboard.press('Enter');
    
    // Wait for picker to close
    await page.waitForSelector('.ant-picker-dropdown', { state: 'hidden' });
  }
};

// API interceptors
export const apiInterceptors = {
  async mockApiResponse(page: unknown, pattern: string | RegExp, response: unknown) {
    await page.route(pattern, async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify(response)
      });
    });
  },

  async waitForApiCall(page: unknown, urlPattern: string, method: string = 'GET', timeout: number = 10000) {
    return await page.waitForResponse(
      (response) => {
        const url = response.url();
        const requestMethod = response.request().method();
        return url.includes(urlPattern) && requestMethod === method && response.ok();
      },
      { timeout }
    );
  },

  async interceptApiCalls(page: unknown, patterns: { url: string | RegExp; handler: (route: unknown) => void }[]) {
    for (const { url, handler } of patterns) {
      await page.route(url, handler);
    }
  }
};