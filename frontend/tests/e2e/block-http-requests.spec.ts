import { test, expect, Page } from '@playwright/test';

test.describe('Block HTTP Requests', () => {
  test('Verify no HTTP requests are made to backend', async ({ page }: { page: Page }) => {
    // Array to track blocked HTTP requests
    const blockedHttpRequests: string[] = [];
    
    // Intercept all network requests and block HTTP ones
    await page.route('**/*', async (route, request) => {
      const url = request.url();
      
      // Block ANY HTTP request to luckygas-backend
      if (url.includes('http://luckygas-backend')) {
        console.error(`❌ BLOCKED HTTP REQUEST: ${url}`);
        blockedHttpRequests.push(url);
        
        // Abort the HTTP request
        await route.abort('blockedbyclient');
        return;
      }
      
      // Allow HTTPS and other requests
      await route.continue();
    });
    
    // Navigate to the application
    console.log('🌐 Navigating to application...');
    await page.goto('https://vast-tributary-466619-m8.web.app', {
      waitUntil: 'domcontentloaded',
      timeout: 30000
    });
    
    // Wait for page to stabilize
    await page.waitForTimeout(3000);
    
    // Take screenshot of page
    await page.screenshot({ 
      path: 'screenshots/http-blocking-test.png',
      fullPage: true 
    });
    
    // Try to perform actions that would trigger API calls
    console.log('🔍 Attempting to trigger API calls...');
    
    // Check if login form is visible
    const emailInput = page.locator('input[type="email"], input[placeholder*="email" i], #email').first();
    const passwordInput = page.locator('input[type="password"], input[placeholder*="password" i], #password').first();
    
    if (await emailInput.isVisible() && await passwordInput.isVisible()) {
      console.log('📝 Filling login form...');
      await emailInput.fill('admin@luckygas.com');
      await passwordInput.fill('admin123');
      
      // Try to submit login (this should trigger API call)
      const loginButton = page.locator('button[type="submit"], button:has-text("登入"), button:has-text("Login")').first();
      if (await loginButton.isVisible()) {
        console.log('🔐 Attempting login...');
        await loginButton.click();
        await page.waitForTimeout(2000);
      }
    }
    
    // Check console for any errors
    page.on('console', msg => {
      if (msg.type() === 'error') {
        console.log(`📕 Console Error: ${msg.text()}`);
      }
    });
    
    // Wait a bit more for any delayed requests
    await page.waitForTimeout(3000);
    
    // Final verification
    console.log('\n📊 Test Results:');
    console.log(`Total HTTP requests blocked: ${blockedHttpRequests.length}`);
    
    if (blockedHttpRequests.length > 0) {
      console.error('\n❌ HTTP Requests were detected and blocked:');
      blockedHttpRequests.forEach(url => {
        console.error(`  - ${url}`);
      });
      
      // Take debug screenshot
      await page.screenshot({ 
        path: 'screenshots/http-requests-detected.png',
        fullPage: true 
      });
    } else {
      console.log('✅ No HTTP requests detected - all communication uses HTTPS');
    }
    
    // Assert that no HTTP requests were made
    expect(blockedHttpRequests.length).toBe(0);
  });
  
  test('Verify HTTPS override in main.tsx is working', async ({ page }: { page: Page }) => {
    let httpsOverrideDetected = false;
    
    // Listen for console messages
    page.on('console', msg => {
      const text = msg.text();
      if (text.includes('[HTTPS Override]') || text.includes('Global HTTP to HTTPS conversion enabled')) {
        httpsOverrideDetected = true;
        console.log(`✅ HTTPS Override detected: ${text}`);
      }
    });
    
    // Navigate to the application
    await page.goto('https://vast-tributary-466619-m8.web.app', {
      waitUntil: 'networkidle',
      timeout: 30000
    });
    
    // Wait for console messages
    await page.waitForTimeout(2000);
    
    // Check if override was detected
    expect(httpsOverrideDetected).toBe(true);
  });
});

// Set test timeout to 60 seconds
test.setTimeout(60000);