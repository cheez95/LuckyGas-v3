import { test, expect, Page } from '@playwright/test';

test.describe('Verify HTTPS Only - No HTTP Requests', () => {
  test('Monitor console and network for HTTP requests', async ({ page }: { page: Page }) => {
    // Track all console messages
    const consoleMessages: string[] = [];
    const consoleErrors: string[] = [];
    const httpRequests: string[] = [];
    const httpsRequests: string[] = [];
    
    // Monitor console messages
    page.on('console', msg => {
      const text = msg.text();
      consoleMessages.push(`[${msg.type()}] ${text}`);
      
      // Log all console output for debugging
      console.log(`[Browser Console ${msg.type()}]: ${text}`);
      
      // Check for HTTP URLs in console
      if (text.includes('http://luckygas-backend')) {
        consoleErrors.push(`HTTP URL in console: ${text}`);
        console.error(`❌ HTTP URL detected in console: ${text}`);
      }
      
      // Capture errors specifically
      if (msg.type() === 'error') {
        consoleErrors.push(text);
        console.error(`❌ Console Error: ${text}`);
      }
    });
    
    // Monitor network requests
    page.on('request', request => {
      const url = request.url();
      console.log(`[Network Request]: ${request.method()} ${url}`);
      
      // Check for HTTP requests to luckygas-backend
      if (url.includes('luckygas-backend')) {
        if (url.startsWith('http://')) {
          httpRequests.push(url);
          console.error(`❌ HTTP Request detected: ${url}`);
        } else if (url.startsWith('https://')) {
          httpsRequests.push(url);
          console.log(`✅ HTTPS Request: ${url}`);
        }
      }
    });
    
    // Monitor network responses
    page.on('response', response => {
      const url = response.url();
      const status = response.status();
      console.log(`[Network Response]: ${status} ${url}`);
      
      // Check for mixed content warnings
      if (status === 0 && url.includes('http://')) {
        console.error(`❌ Blocked mixed content: ${url}`);
      }
    });
    
    // Navigate to the application
    console.log('\\n🌐 Navigating to application...');
    await page.goto('https://vast-tributary-466619-m8.web.app', {
      waitUntil: 'networkidle',
      timeout: 30000
    });
    
    // Wait for initial page load
    await page.waitForTimeout(3000);
    
    // Take screenshot of initial page
    await page.screenshot({ 
      path: 'screenshots/https-verification-initial.png',
      fullPage: true 
    });
    
    // Try to trigger API calls by attempting login
    console.log('\\n🔍 Attempting to trigger API calls...');
    
    // Check if login form is visible
    const emailInput = page.locator('input[type="email"], input[placeholder*="email" i], #email').first();
    const passwordInput = page.locator('input[type="password"], input[placeholder*="password" i], #password').first();
    
    if (await emailInput.isVisible() && await passwordInput.isVisible()) {
      console.log('📝 Filling login form...');
      await emailInput.fill('admin@luckygas.com');
      await passwordInput.fill('admin123');
      
      // Try to submit login
      const loginButton = page.locator('button[type="submit"], button:has-text("登入"), button:has-text("Login")').first();
      if (await loginButton.isVisible()) {
        console.log('🔐 Attempting login to trigger API calls...');
        await loginButton.click();
        await page.waitForTimeout(3000);
      }
    } else {
      console.log('ℹ️ Login form not found, app might be already logged in');
      
      // Try to navigate to customers page to trigger API calls
      const customersLink = page.locator('a[href*="customers"], a:has-text("客戶"), a:has-text("Customers")').first();
      if (await customersLink.isVisible()) {
        console.log('📋 Navigating to customers page...');
        await customersLink.click();
        await page.waitForTimeout(3000);
      }
    }
    
    // Take screenshot after actions
    await page.screenshot({ 
      path: 'screenshots/https-verification-after-actions.png',
      fullPage: true 
    });
    
    // Open browser console and take screenshot
    console.log('\\n📸 Opening DevTools console...');
    await page.keyboard.press('F12');
    await page.waitForTimeout(1000);
    
    // Take screenshot with console open
    await page.screenshot({ 
      path: 'screenshots/https-verification-with-console.png',
      fullPage: true 
    });
    
    // Final analysis
    console.log('\\n' + '='.repeat(80));
    console.log('📊 TEST RESULTS SUMMARY');
    console.log('='.repeat(80));
    
    console.log(`\\n📝 Console Messages: ${consoleMessages.length} total`);
    if (consoleMessages.length > 0) {
      console.log('Recent console messages:');
      consoleMessages.slice(-10).forEach(msg => console.log(`  ${msg}`));
    }
    
    console.log(`\\n❌ Console Errors: ${consoleErrors.length} total`);
    if (consoleErrors.length > 0) {
      consoleErrors.forEach(err => console.error(`  ${err}`));
    }
    
    console.log(`\\n🔒 HTTPS Requests: ${httpsRequests.length} total`);
    if (httpsRequests.length > 0) {
      httpsRequests.forEach(url => console.log(`  ✅ ${url}`));
    }
    
    console.log(`\\n⚠️ HTTP Requests: ${httpRequests.length} total`);
    if (httpRequests.length > 0) {
      console.error('\\n❌ FAILURE: HTTP requests were detected!');
      httpRequests.forEach(url => console.error(`  ❌ ${url}`));
    } else {
      console.log('✅ SUCCESS: No HTTP requests detected!');
    }
    
    console.log('\\n' + '='.repeat(80));
    
    // Assert no HTTP requests were made
    expect(httpRequests.length, `Found ${httpRequests.length} HTTP requests: ${httpRequests.join(', ')}`).toBe(0);
    
    // Assert no HTTP URLs in console
    const httpUrlsInConsole = consoleMessages.filter(msg => msg.includes('http://luckygas-backend'));
    expect(httpUrlsInConsole.length, `Found HTTP URLs in console: ${httpUrlsInConsole.join(', ')}`).toBe(0);
  });
  
  test('Check compiled JavaScript for HTTP URLs', async ({ page }: { page: Page }) => {
    console.log('\\n🔍 Checking compiled JavaScript for HTTP URLs...');
    
    const jsFiles: string[] = [];
    const httpUrls: string[] = [];
    
    // Intercept responses to check JS files
    page.on('response', async response => {
      const url = response.url();
      if (url.endsWith('.js') && response.status() === 200) {
        jsFiles.push(url);
        try {
          const text = await response.text();
          
          // Check for HTTP URLs in the JavaScript
          if (text.includes('http://luckygas-backend')) {
            httpUrls.push(url);
            console.error(`❌ HTTP URL found in JS file: ${url}`);
            
            // Find the specific occurrences
            const matches = text.match(/http:\/\/luckygas-backend[^'"\\s]*/g);
            if (matches) {
              matches.forEach(match => {
                console.error(`   Found: ${match}`);
              });
            }
          }
        } catch (e) {
          // Ignore errors reading response
        }
      }
    });
    
    // Navigate to the application
    await page.goto('https://vast-tributary-466619-m8.web.app', {
      waitUntil: 'networkidle',
      timeout: 30000
    });
    
    // Wait for all JS to load
    await page.waitForTimeout(5000);
    
    console.log(`\\n📦 Checked ${jsFiles.length} JavaScript files`);
    if (httpUrls.length > 0) {
      console.error(`\\n❌ Found HTTP URLs in ${httpUrls.length} files:`);
      httpUrls.forEach(url => console.error(`  ${url}`));
    } else {
      console.log('✅ No HTTP URLs found in JavaScript files');
    }
    
    // Assert no HTTP URLs in JS files
    expect(httpUrls.length, `Found HTTP URLs in ${httpUrls.length} JS files`).toBe(0);
  });
});

// Set test timeout to 60 seconds
test.setTimeout(60000);