import { test, expect } from '@playwright/test';

test('Verify no HTTP URLs and customer data displays', async ({ page }) => {
  // Array to track all network requests
  const requests: { url: string; method: string; timestamp: string }[] = [];
  
  // Set up request interception to track all network requests
  page.on('request', request => {
    const url = request.url();
    const method = request.method();
    const timestamp = new Date().toISOString();
    
    requests.push({ url, method, timestamp });
    
    // Log HTTP requests immediately if found
    if (url.includes('http://luckygas-backend')) {
      console.error(`❌ HTTP Request detected: ${method} ${url}`);
    }
  });
  
  // Log responses for debugging
  page.on('response', response => {
    const url = response.url();
    const status = response.status();
    
    if (url.includes('luckygas-backend')) {
      console.log(`📡 Response: ${status} - ${url}`);
    }
  });
  
  // Navigate to the application
  console.log('🌐 Navigating to application...');
  await page.goto('https://vast-tributary-466619-m8.web.app', {
    waitUntil: 'networkidle',
    timeout: 30000
  });
  
  // Wait for the page to load and check what's on the page
  await page.waitForTimeout(3000);
  
  // Take screenshot of login page
  await page.screenshot({ 
    path: 'screenshots/01-login-page.png',
    fullPage: true 
  });
  console.log('📸 Screenshot saved: 01-login-page.png');
  
  // Check if we're already logged in or need to login
  const dashboardVisible = await page.locator('text=儀表板').isVisible().catch(() => false);
  const loginFormVisible = await page.locator('input[type="email"]').isVisible().catch(() => false);
  
  if (dashboardVisible) {
    console.log('✅ Already logged in, skipping login');
  } else if (loginFormVisible) {
    // Login with admin credentials
    console.log('🔐 Logging in as admin...');
    await page.fill('input[type="email"]', 'admin@luckygas.com');
    await page.fill('input[type="password"]', 'admin123');
    
    // Click login button
    await page.click('button[type="submit"]');
    
    // Wait for navigation after login
    await page.waitForTimeout(3000);
  } else {
    // Try alternative selectors
    console.log('⚠️ Login form not found with standard selectors, trying alternatives...');
    const emailInput = await page.locator('input[placeholder*="email" i], input[name*="email" i], #email').first();
    const passwordInput = await page.locator('input[type="password"], input[placeholder*="password" i], input[name*="password" i], #password').first();
    
    if (await emailInput.isVisible() && await passwordInput.isVisible()) {
      await emailInput.fill('admin@luckygas.com');
      await passwordInput.fill('admin123');
      
      // Find and click login button
      const loginButton = await page.locator('button:has-text("登入"), button:has-text("Login"), button[type="submit"]').first();
      await loginButton.click();
      
      // Wait for navigation after login
      await page.waitForTimeout(3000);
    } else {
      console.log('❌ Could not find login form elements');
      // Take debug screenshot
      await page.screenshot({ 
        path: 'screenshots/debug-no-login-form.png',
        fullPage: true 
      });
    }
  }
  
  // Take screenshot after login
  await page.screenshot({ 
    path: 'screenshots/02-after-login.png',
    fullPage: true 
  });
  console.log('📸 Screenshot saved: 02-after-login.png');
  
  // Navigate to customer management page
  console.log('📋 Navigating to customer management...');
  
  // Try multiple selectors for the customer menu item
  const customerMenuSelectors = [
    'text=客戶管理',
    'text=Customer Management',
    'text=Customers',
    '[href*="customers"]',
    'a:has-text("客戶")',
    'button:has-text("客戶")'
  ];
  
  let customerMenuClicked = false;
  for (const selector of customerMenuSelectors) {
    try {
      const element = await page.locator(selector).first();
      if (await element.isVisible()) {
        await element.click();
        customerMenuClicked = true;
        console.log(`✅ Clicked customer menu using selector: ${selector}`);
        break;
      }
    } catch (e) {
      // Try next selector
    }
  }
  
  if (!customerMenuClicked) {
    console.log('⚠️ Could not find customer menu item, trying direct navigation');
    await page.goto('https://vast-tributary-466619-m8.web.app/customers');
  }
  
  // Wait for customer data to load
  console.log('⏳ Waiting for customer data to load...');
  await page.waitForTimeout(5000);
  
  // Take screenshot of customer page
  await page.screenshot({ 
    path: 'screenshots/03-customer-page.png',
    fullPage: true 
  });
  console.log('📸 Screenshot saved: 03-customer-page.png');
  
  // Check for HTTP requests
  const httpRequests = requests.filter(r => r.url.includes('http://luckygas-backend'));
  
  console.log('\n📊 Request Analysis:');
  console.log(`Total requests: ${requests.length}`);
  console.log(`HTTP requests found: ${httpRequests.length}`);
  
  if (httpRequests.length > 0) {
    console.error('\n❌ HTTP Requests detected:');
    httpRequests.forEach(req => {
      console.error(`  - ${req.method} ${req.url} at ${req.timestamp}`);
    });
  } else {
    console.log('✅ No HTTP requests detected - all requests use HTTPS');
  }
  
  // Log all backend requests for debugging
  const backendRequests = requests.filter(r => r.url.includes('luckygas-backend'));
  console.log(`\n🔍 Backend requests (${backendRequests.length} total):`);
  backendRequests.slice(0, 10).forEach(req => {
    console.log(`  - ${req.method} ${req.url}`);
  });
  
  // Try to find customer data in different ways
  console.log('\n🔍 Checking for customer data display...');
  
  // Check for table rows
  const tableSelectors = [
    'table tbody tr',
    '.ant-table-tbody tr',
    '[role="table"] [role="row"]',
    '.customer-table tr',
    'div[class*="table"] tr'
  ];
  
  let tableRows = 0;
  for (const selector of tableSelectors) {
    try {
      const rows = await page.locator(selector);
      const count = await rows.count();
      if (count > 0) {
        tableRows = count;
        console.log(`✅ Found ${count} table rows using selector: ${selector}`);
        break;
      }
    } catch (e) {
      // Try next selector
    }
  }
  
  // Check for customer cards or list items
  if (tableRows === 0) {
    const cardSelectors = [
      '.customer-card',
      '.customer-item',
      '[class*="customer"]',
      '.list-item'
    ];
    
    for (const selector of cardSelectors) {
      try {
        const cards = await page.locator(selector);
        const count = await cards.count();
        if (count > 0) {
          tableRows = count;
          console.log(`✅ Found ${count} customer items using selector: ${selector}`);
          break;
        }
      } catch (e) {
        // Try next selector
      }
    }
  }
  
  // Check for any text content indicating customers
  const pageContent = await page.content();
  const hasCustomerCodes = pageContent.includes('1400103') || 
                           pageContent.includes('REST001') || 
                           pageContent.includes('IND001');
  const hasCustomerNames = pageContent.includes('幸福餐廳') || 
                           pageContent.includes('大同工廠') || 
                           pageContent.includes('台北辦公');
  
  console.log(`Customer codes found in page: ${hasCustomerCodes}`);
  console.log(`Customer names found in page: ${hasCustomerNames}`);
  
  // Final assertions
  console.log('\n📋 Test Results:');
  
  // Assert no HTTP requests
  try {
    expect(httpRequests).toHaveLength(0);
    console.log('✅ PASS: No HTTP requests detected');
  } catch (e) {
    console.error('❌ FAIL: HTTP requests were detected');
    throw e;
  }
  
  // Assert customer data is displayed
  const hasCustomerData = tableRows > 0 || hasCustomerCodes || hasCustomerNames;
  try {
    expect(hasCustomerData).toBeTruthy();
    console.log(`✅ PASS: Customer data is displayed (${tableRows} rows found)`);
  } catch (e) {
    console.error('❌ FAIL: No customer data found on the page');
    
    // Take debug screenshot
    await page.screenshot({ 
      path: 'screenshots/debug-no-data.png',
      fullPage: true 
    });
    console.log('📸 Debug screenshot saved: debug-no-data.png');
    
    throw e;
  }
  
  // Take final success screenshot
  await page.screenshot({ 
    path: 'screenshots/04-success-verification.png',
    fullPage: true 
  });
  console.log('📸 Final screenshot saved: 04-success-verification.png');
  
  console.log('\n✅ All verifications passed!');
  console.log('- No HTTP requests detected');
  console.log('- Customer data is displayed correctly');
  console.log('- HTTPS override is working properly');
});

// Set test timeout to 60 seconds
test.setTimeout(60000);