import { test, expect, webkit, Browser, BrowserContext, Page } from '@playwright/test';

test.describe('Safari HTTP Issue Reproduction', () => {
  test('Reproduce HTTP issue in Safari when clicking Customer Management', async () => {
    // Track all HTTP requests
    const httpRequests: string[] = [];
    const httpsRequests: string[] = [];
    const consoleErrors: string[] = [];
    
    // Launch webkit (Safari engine) with headless false for visibility
    const browser: Browser = await webkit.launch({ 
      headless: false,
      devtools: true 
    });
    
    const context: BrowserContext = await browser.newContext();
    const page: Page = await context.newPage();
    
    // Monitor console messages
    page.on('console', msg => {
      const text = msg.text();
      console.log(`[Safari Console ${msg.type()}]: ${text}`);
      
      // Check for HTTP URLs in console
      if (text.includes('http://')) {
        consoleErrors.push(`HTTP URL in console: ${text}`);
        console.error(`❌ HTTP URL DETECTED IN CONSOLE: ${text}`);
      }
      
      // Capture errors
      if (msg.type() === 'error') {
        consoleErrors.push(text);
        console.error(`❌ Console Error: ${text}`);
      }
    });
    
    // Monitor all network requests
    page.on('request', request => {
      const url = request.url();
      const method = request.method();
      
      console.log(`[Network ${method}]: ${url}`);
      
      // Check for HTTP vs HTTPS requests to luckygas-backend
      if (url.includes('luckygas-backend')) {
        if (url.startsWith('http://')) {
          httpRequests.push(`${method} ${url}`);
          console.error(`❌ HTTP REQUEST DETECTED: ${method} ${url}`);
        } else if (url.startsWith('https://')) {
          httpsRequests.push(`${method} ${url}`);
          console.log(`✅ HTTPS Request: ${method} ${url}`);
        }
      }
    });
    
    // Monitor responses for mixed content blocks
    page.on('response', response => {
      const url = response.url();
      const status = response.status();
      
      if (status === 0 && url.includes('http://')) {
        console.error(`❌ BLOCKED MIXED CONTENT: ${url}`);
        httpRequests.push(`BLOCKED: ${url}`);
      }
    });
    
    // Monitor request failures
    page.on('requestfailed', request => {
      const url = request.url();
      const failure = request.failure();
      console.error(`❌ Request Failed: ${url}`, failure?.errorText);
      
      if (url.includes('http://') && failure?.errorText?.includes('mixed')) {
        console.error(`❌ MIXED CONTENT FAILURE: ${url}`);
      }
    });
    
    try {
      console.log('\\n====================================');
      console.log('1. Opening frontend...');
      console.log('====================================');
      await page.goto('https://vast-tributary-466619-m8.web.app', {
        waitUntil: 'networkidle',
        timeout: 30000
      });
      
      // Wait for page to stabilize
      await page.waitForTimeout(2000);
      
      console.log('\\n====================================');
      console.log('2. Attempting login...');
      console.log('====================================');
      
      // Try to find and fill login form
      const emailInput = page.locator('input[name="email"], input[type="email"]').first();
      const passwordInput = page.locator('input[name="password"], input[type="password"]').first();
      
      if (await emailInput.isVisible() && await passwordInput.isVisible()) {
        await emailInput.fill('admin@luckygas.com');
        await passwordInput.fill('admin123');
        
        const submitButton = page.locator('button[type="submit"]').first();
        await submitButton.click();
        
        // Wait for navigation after login
        await page.waitForTimeout(3000);
        console.log('✅ Login completed');
      } else {
        console.log('ℹ️ Already logged in or login form not found');
      }
      
      console.log('\\n====================================');
      console.log('3. Clicking on Customer Management (客戶管理)...');
      console.log('====================================');
      
      // Clear previous request tracking for this specific action
      httpRequests.length = 0;
      
      // Click on Customer Management
      const customerManagementLink = page.locator('text=客戶管理').first();
      if (await customerManagementLink.isVisible()) {
        console.log('📍 Found Customer Management link, clicking...');
        await customerManagementLink.click();
        
        // Wait for potential HTTP requests
        await page.waitForTimeout(5000);
      } else {
        console.error('❌ Customer Management link not found');
      }
      
      console.log('\\n====================================');
      console.log('4. Taking screenshot of current state...');
      console.log('====================================');
      await page.screenshot({ 
        path: 'screenshots/safari-console-errors.png', 
        fullPage: true 
      });
      
      console.log('\\n====================================');
      console.log('5. Checking for errors on page...');
      console.log('====================================');
      
      // Check for error elements on the page
      const errors = await page.evaluate(() => {
        const errorElements = Array.from(document.querySelectorAll('.error, .ant-alert-error, [class*="error"]'));
        return errorElements.map(e => e.textContent || '');
      });
      
      if (errors.length > 0) {
        console.log('Page errors found:', errors);
      }
      
      // Check if there's a specific error message about mixed content
      const pageContent = await page.content();
      if (pageContent.includes('Mixed Content') || pageContent.includes('http://')) {
        console.error('❌ Page contains references to HTTP or Mixed Content');
      }
      
    } finally {
      console.log('\\n====================================');
      console.log('TEST RESULTS SUMMARY');
      console.log('====================================');
      
      console.log(`\\n📊 Network Requests:`);
      console.log(`  HTTPS Requests: ${httpsRequests.length}`);
      console.log(`  HTTP Requests: ${httpRequests.length}`);
      
      if (httpRequests.length > 0) {
        console.error('\\n❌ HTTP REQUESTS DETECTED:');
        httpRequests.forEach(req => console.error(`    ${req}`));
      } else {
        console.log('✅ No HTTP requests detected');
      }
      
      if (consoleErrors.length > 0) {
        console.error('\\n❌ CONSOLE ERRORS:');
        consoleErrors.forEach(err => console.error(`    ${err}`));
      }
      
      // Keep browser open for manual inspection
      console.log('\\n⏸️ Browser kept open for manual inspection. Press Ctrl+C to close.');
      await page.waitForTimeout(60000); // Keep open for 1 minute
      
      await browser.close();
    }
    
    // Assert no HTTP requests were made
    expect(httpRequests.length, `Found ${httpRequests.length} HTTP requests`).toBe(0);
  });
  
  test('Check if HTTP URLs are in the compiled JavaScript', async () => {
    const browser = await webkit.launch({ headless: true });
    const context = await browser.newContext();
    const page = await context.newPage();
    
    const jsFilesWithHttp: string[] = [];
    
    // Intercept all JS file responses
    page.on('response', async response => {
      const url = response.url();
      if (url.endsWith('.js') && response.status() === 200) {
        try {
          const text = await response.text();
          
          // Check for HTTP URLs to luckygas-backend
          if (text.includes('http://luckygas-backend')) {
            jsFilesWithHttp.push(url);
            console.error(`❌ HTTP URL found in JS: ${url}`);
            
            // Find specific occurrences
            const matches = text.match(/http:\/\/luckygas-backend[^'"\\s]*/g);
            if (matches) {
              matches.forEach(match => {
                console.error(`   Found: ${match}`);
              });
            }
          }
        } catch (e) {
          // Ignore read errors
        }
      }
    });
    
    await page.goto('https://vast-tributary-466619-m8.web.app', {
      waitUntil: 'networkidle',
      timeout: 30000
    });
    
    await page.waitForTimeout(5000);
    
    console.log(`\\n📦 Checked JavaScript files`);
    if (jsFilesWithHttp.length > 0) {
      console.error(`❌ Found HTTP URLs in ${jsFilesWithHttp.length} JS files`);
    } else {
      console.log('✅ No HTTP URLs in JavaScript files');
    }
    
    await browser.close();
    
    expect(jsFilesWithHttp.length).toBe(0);
  });
});

// Set test timeout
test.setTimeout(120000);