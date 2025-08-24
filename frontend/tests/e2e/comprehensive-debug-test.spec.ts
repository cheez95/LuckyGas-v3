import { test, expect, Page, ConsoleMessage } from '@playwright/test';

test.describe('Lucky Gas Comprehensive Debug Test', () => {
  test('Debug customer data display issue', async ({ page }) => {
    // Enhanced console monitoring
    const consoleLogs: string[] = [];
    const consoleErrors: string[] = [];
    const consoleWarnings: string[] = [];
    const networkRequests: any[] = [];
    const networkResponses: any[] = [];
    
    // Monitor ALL console messages
    page.on('console', (msg: ConsoleMessage) => {
      const type = msg.type();
      const text = msg.text();
      const location = msg.location();
      
      const logEntry = `[${type.toUpperCase()}] ${text} (${location.url}:${location.lineNumber})`;
      
      if (type === 'error') {
        consoleErrors.push(logEntry);
        console.error('🔴 Console Error:', logEntry);
      } else if (type === 'warning') {
        consoleWarnings.push(logEntry);
        console.warn('🟡 Console Warning:', logEntry);
      } else {
        consoleLogs.push(logEntry);
        console.log('🔵 Console Log:', logEntry);
      }
    });
    
    // Monitor page errors
    page.on('pageerror', (error) => {
      console.error('🔴 Page Error:', error.message);
      consoleErrors.push(`Page Error: ${error.message}`);
    });
    
    // Monitor all network requests
    page.on('request', (request) => {
      const url = request.url();
      const method = request.method();
      const headers = request.headers();
      
      if (url.includes('/api/')) {
        console.log(`📤 API Request: ${method} ${url}`);
        console.log('   Headers:', headers);
        networkRequests.push({
          url,
          method,
          headers,
          timestamp: new Date().toISOString()
        });
      }
    });
    
    // Monitor all network responses
    page.on('response', async (response) => {
      const url = response.url();
      const status = response.status();
      
      if (url.includes('/api/')) {
        console.log(`📥 API Response: ${status} ${url}`);
        
        let body = null;
        try {
          if (response.headers()['content-type']?.includes('application/json')) {
            body = await response.json();
            console.log('   Response Body:', JSON.stringify(body, null, 2));
          }
        } catch (e) {
          console.log('   Could not parse response body');
        }
        
        networkResponses.push({
          url,
          status,
          body,
          headers: response.headers(),
          timestamp: new Date().toISOString()
        });
      }
    });
    
    // Monitor failed requests
    page.on('requestfailed', (request) => {
      console.error('🔴 Request Failed:', request.url(), request.failure()?.errorText);
      consoleErrors.push(`Request Failed: ${request.url()} - ${request.failure()?.errorText}`);
    });
    
    console.log('\n🚀 Starting comprehensive debug test...\n');
    
    // Step 1: Navigate to the application
    console.log('📍 Step 1: Navigating to application...');
    await page.goto('http://localhost:5173', { waitUntil: 'networkidle' });
    await page.waitForTimeout(2000);
    
    // Check localStorage and sessionStorage
    const localStorage = await page.evaluate(() => {
      const items: any = {};
      for (let i = 0; i < window.localStorage.length; i++) {
        const key = window.localStorage.key(i);
        if (key) {
          items[key] = window.localStorage.getItem(key);
        }
      }
      return items;
    });
    console.log('📦 LocalStorage:', localStorage);
    
    // Step 2: Check if we need to login
    console.log('\n📍 Step 2: Checking authentication status...');
    const loginButton = page.locator('button:has-text("登入"), button:has-text("Login")');
    const isLoginPage = await loginButton.isVisible();
    
    if (isLoginPage) {
      console.log('🔐 Login required, attempting to authenticate...');
      
      // Clear any existing auth data
      await page.evaluate(() => {
        window.localStorage.clear();
        window.sessionStorage.clear();
      });
      
      // Fill login form
      await page.fill('input[type="email"], input[name="username"], input[name="email"]', 'admin@luckygas.com');
      await page.fill('input[type="password"], input[name="password"]', 'admin-password-2025');
      
      // Click login and wait for navigation
      await loginButton.click();
      await page.waitForLoadState('networkidle');
      await page.waitForTimeout(3000);
      
      // Check if login was successful
      const afterLoginStorage = await page.evaluate(() => {
        const items: any = {};
        for (let i = 0; i < window.localStorage.length; i++) {
          const key = window.localStorage.key(i);
          if (key) {
            items[key] = window.localStorage.getItem(key);
          }
        }
        return items;
      });
      console.log('📦 Storage after login:', afterLoginStorage);
    }
    
    // Step 3: Navigate to customers page
    console.log('\n📍 Step 3: Navigating to customers page...');
    
    // Try different navigation methods
    const navSelectors = [
      'a:has-text("客戶")',
      'a:has-text("Customers")',
      '[href*="customers"]',
      'nav a:has-text("客戶")',
      '.menu-item:has-text("客戶")',
      'button:has-text("客戶")'
    ];
    
    let navFound = false;
    for (const selector of navSelectors) {
      const element = page.locator(selector).first();
      if (await element.isVisible()) {
        console.log(`✅ Found navigation element: ${selector}`);
        await element.click();
        navFound = true;
        break;
      }
    }
    
    if (!navFound) {
      console.log('⚠️ Navigation element not found, trying direct URL...');
      await page.goto('http://localhost:5173/customers');
    }
    
    await page.waitForLoadState('networkidle');
    await page.waitForTimeout(3000);
    
    // Step 4: Check what's on the page
    console.log('\n📍 Step 4: Analyzing page content...');
    
    // Get page URL and title
    const currentUrl = page.url();
    const pageTitle = await page.title();
    console.log(`📄 Current URL: ${currentUrl}`);
    console.log(`📄 Page Title: ${pageTitle}`);
    
    // Check for loading indicators
    const loadingSelectors = [
      '.loading',
      '.spinner',
      '[data-loading="true"]',
      '.ant-spin',
      '.MuiCircularProgress-root'
    ];
    
    for (const selector of loadingSelectors) {
      const isLoading = await page.locator(selector).isVisible();
      if (isLoading) {
        console.log(`⏳ Loading indicator found: ${selector}`);
      }
    }
    
    // Step 5: Count customers in various possible containers
    console.log('\n📍 Step 5: Searching for customer data...');
    
    const customerSelectors = [
      'tbody tr',                    // Standard table rows
      'tr[data-row]',               // Data-attributed rows
      '.customer-row',              // Custom class
      '.ant-table-row',            // Ant Design
      '.MuiTableRow-root',         // Material UI
      '[role="row"]',              // Accessible rows
      '.customer-item',            // List items
      '.card.customer',            // Card layout
      'table tbody tr',            // More specific table
      '.customer-list-item',       // List view
    ];
    
    let maxCustomerCount = 0;
    let bestSelector = '';
    
    for (const selector of customerSelectors) {
      try {
        const count = await page.locator(selector).count();
        if (count > 0) {
          console.log(`📊 Selector "${selector}": ${count} items found`);
          if (count > maxCustomerCount) {
            maxCustomerCount = count;
            bestSelector = selector;
          }
        }
      } catch (e) {
        // Selector might be invalid, skip
      }
    }
    
    console.log(`\n🎯 Best selector: "${bestSelector}" with ${maxCustomerCount} customers`);
    
    // Step 6: Check for API calls to customers endpoint
    console.log('\n📍 Step 6: Analyzing API calls...');
    
    const customerApiCalls = networkRequests.filter(req => 
      req.url.includes('/customers') || req.url.includes('/api/v1/customers')
    );
    
    console.log(`📡 Found ${customerApiCalls.length} customer API calls:`);
    customerApiCalls.forEach((call, index) => {
      console.log(`   ${index + 1}. ${call.method} ${call.url}`);
      if (call.headers['authorization']) {
        console.log(`      Auth: ${call.headers['authorization'].substring(0, 50)}...`);
      }
    });
    
    const customerApiResponses = networkResponses.filter(res => 
      res.url.includes('/customers') || res.url.includes('/api/v1/customers')
    );
    
    console.log(`\n📡 Customer API responses:`);
    customerApiResponses.forEach((response, index) => {
      console.log(`   ${index + 1}. Status ${response.status}: ${response.url}`);
      if (response.body) {
        if (Array.isArray(response.body)) {
          console.log(`      Data: Array with ${response.body.length} items`);
        } else if (response.body.data && Array.isArray(response.body.data)) {
          console.log(`      Data: Object with data array of ${response.body.data.length} items`);
        } else {
          console.log(`      Data:`, JSON.stringify(response.body).substring(0, 200));
        }
      }
    });
    
    // Step 7: Try to trigger a customer data load
    console.log('\n📍 Step 7: Attempting to trigger data load...');
    
    // Look for refresh buttons
    const refreshSelectors = [
      'button:has-text("刷新")',
      'button:has-text("Refresh")',
      'button[aria-label*="refresh"]',
      '.refresh-button',
      '[data-action="refresh"]'
    ];
    
    for (const selector of refreshSelectors) {
      const button = page.locator(selector).first();
      if (await button.isVisible()) {
        console.log(`🔄 Found refresh button: ${selector}`);
        await button.click();
        await page.waitForTimeout(2000);
        break;
      }
    }
    
    // Step 8: Check page source for clues
    console.log('\n📍 Step 8: Examining page source...');
    
    const pageContent = await page.content();
    
    // Check for common error messages
    const errorPatterns = [
      /error/i,
      /failed/i,
      /unauthorized/i,
      /403/,
      /401/,
      /500/,
      /no.*data/i,
      /empty/i,
      /找不到/,
      /沒有資料/
    ];
    
    errorPatterns.forEach(pattern => {
      const matches = pageContent.match(pattern);
      if (matches) {
        console.log(`⚠️ Found potential error pattern: ${matches[0]}`);
      }
    });
    
    // Step 9: Execute JavaScript to check React/Vue state
    console.log('\n📍 Step 9: Checking JavaScript framework state...');
    
    const frameworkState = await page.evaluate(() => {
      const result: any = {};
      
      // Check for React
      const reactRoot = document.querySelector('#root') || document.querySelector('#app');
      if (reactRoot && (window as any).React) {
        result.framework = 'React detected';
      }
      
      // Check for Vue
      if ((window as any).Vue || document.querySelector('[data-v-]')) {
        result.framework = 'Vue detected';
      }
      
      // Try to find customer data in window object
      if ((window as any).customers) {
        result.windowCustomers = (window as any).customers;
      }
      
      // Check for common state management
      if ((window as any).__REDUX_DEVTOOLS_EXTENSION__) {
        result.redux = 'Redux detected';
      }
      
      return result;
    });
    
    console.log('🎭 Framework state:', frameworkState);
    
    // Step 10: Take screenshots for analysis
    console.log('\n📍 Step 10: Capturing screenshots...');
    
    await page.screenshot({ 
      path: 'debug-full-page.png',
      fullPage: true 
    });
    console.log('📸 Full page screenshot saved: debug-full-page.png');
    
    await page.screenshot({ 
      path: 'debug-viewport.png'
    });
    console.log('📸 Viewport screenshot saved: debug-viewport.png');
    
    // Step 11: Summary
    console.log('\n' + '='.repeat(80));
    console.log('📊 TEST SUMMARY');
    console.log('='.repeat(80));
    console.log(`\n🔵 Console Logs: ${consoleLogs.length}`);
    console.log(`🟡 Console Warnings: ${consoleWarnings.length}`);
    console.log(`🔴 Console Errors: ${consoleErrors.length}`);
    console.log(`📤 API Requests: ${networkRequests.length}`);
    console.log(`📥 API Responses: ${networkResponses.length}`);
    console.log(`👥 Customers Displayed: ${maxCustomerCount}`);
    
    if (consoleErrors.length > 0) {
      console.log('\n❌ Console Errors Found:');
      consoleErrors.forEach((error, index) => {
        console.log(`   ${index + 1}. ${error}`);
      });
    }
    
    // Assertion
    expect(maxCustomerCount, 'Expected to find customers in the UI').toBeGreaterThan(0);
    
    // Additional detailed logging for debugging
    if (maxCustomerCount === 0) {
      console.log('\n🚨 CRITICAL: No customers found in UI!');
      console.log('\nDiagnostic Information:');
      console.log('1. Check if authentication token is being sent');
      console.log('2. Verify API endpoint is correct');
      console.log('3. Check response parsing in frontend');
      console.log('4. Verify component is receiving data');
      console.log('5. Check for pagination limits');
    }
  });
});