import { test, expect } from '@playwright/test';

test.describe('Simple Customer Display Test', () => {
  test('Login and check customer list', async ({ page }) => {
    // Step 1: Navigate to the application
    console.log('🚀 Navigating to application...');
    await page.goto('http://localhost:5173');
    await page.waitForTimeout(2000);
    
    // Step 2: Login
    console.log('🔐 Attempting to login...');
    
    // Fill in login form
    await page.fill('input[type="email"], input[name="username"], input[name="email"]', 'admin@luckygas.com');
    await page.fill('input[type="password"], input[name="password"]', 'admin-password-2025');
    
    // Click login button
    const loginButton = page.locator('button:has-text("登入"), button:has-text("Login")');
    await loginButton.click();
    
    // Wait for navigation after login
    console.log('⏳ Waiting for login to complete...');
    await page.waitForTimeout(3000);
    
    // Step 3: Navigate to customers page
    console.log('📍 Navigating to customers page...');
    
    // Try clicking on the customers menu item
    const customerLink = page.locator('a:has-text("客戶"), a:has-text("Customers"), [href*="customers"]').first();
    if (await customerLink.isVisible()) {
      await customerLink.click();
    } else {
      // Navigate directly if link not found
      await page.goto('http://localhost:5173/customers');
    }
    
    // Wait for page to load
    await page.waitForTimeout(3000);
    
    // Step 4: Count customers
    console.log('🔍 Counting customers...');
    
    // Try various selectors to find customer rows
    const selectors = [
      'tbody tr',
      'tr[data-row]',
      '.customer-row',
      '.ant-table-row',
      '[role="row"]',
      '.customer-item',
    ];
    
    let customerCount = 0;
    let foundSelector = '';
    
    for (const selector of selectors) {
      const count = await page.locator(selector).count();
      if (count > customerCount) {
        customerCount = count;
        foundSelector = selector;
      }
    }
    
    console.log(`\n📊 Results:`);
    console.log(`   Found ${customerCount} customers using selector: ${foundSelector}`);
    console.log(`   Expected: 1257 active customers`);
    
    // Take screenshot
    await page.screenshot({ path: 'simple-test-screenshot.png', fullPage: true });
    console.log('📸 Screenshot saved as simple-test-screenshot.png');
    
    // Check if we have the expected number of customers
    expect(customerCount).toBeGreaterThan(0);
    expect(customerCount).toBeGreaterThanOrEqual(1257);
  });
});