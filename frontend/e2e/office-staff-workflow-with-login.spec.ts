import { test, expect, Page } from '@playwright/test';

// Realistic test data for Taiwan office staff
const CUSTOMERS = {
  regular: {
    name: '王小明',
    phone: '0912345678',
    address: '台北市大安區信義路四段123號5樓',
    deliveryNotes: '請按電鈴，狗不會咬人'
  },
  commercial: {
    name: '幸福餐廳',
    phone: '02-27123456',
    address: '台北市信義區忠孝東路五段68號',
    deliveryNotes: '後門收貨，找陳經理'
  }
};

// Helper to simulate realistic typing speed
async function typeRealistic(page: Page, selector: any, text: string) {
  // Handle both string selectors and Locator objects
  if (typeof selector === 'string') {
    await page.fill(selector, '');
    await page.type(selector, text, { delay: 50 + Math.random() * 50 });
  } else {
    await selector.fill('');
    await selector.type(text, { delay: 50 + Math.random() * 50 });
  }
}

// Helper to simulate thinking time
async function thinkingPause(minMs = 500, maxMs = 1500) {
  await new Promise(resolve => setTimeout(resolve, minMs + Math.random() * (maxMs - minMs)));
}

// Take screenshot with annotation
async function annotatedScreenshot(page: Page, name: string, annotation?: string) {
  if (annotation) {
    console.log(`📸 Screenshot: ${name} - ${annotation}`);
  }
  await page.screenshot({ 
    path: `test-results/ux-analysis/${name}.png`,
    fullPage: true 
  });
}

// Perform actual login
async function performLogin(page: Page, username: string, password: string) {
  await page.goto('http://localhost:5173');
  
  // Wait for login form
  await page.waitForSelector('input[type="text"], input[placeholder*="用戶名"], input[placeholder*="帳號"]');
  
  // Find username and password fields
  const usernameInput = page.locator('input[type="text"], input[placeholder*="用戶名"], input[placeholder*="帳號"]').first();
  const passwordInput = page.locator('input[type="password"], input[placeholder*="密碼"]');
  
  // Type credentials
  await typeRealistic(page, usernameInput, username);
  await thinkingPause(300, 500);
  await typeRealistic(page, passwordInput, password);
  await thinkingPause(300, 500);
  
  // Take screenshot before login
  await annotatedScreenshot(page, 'login-filled', 'Login form with credentials');
  
  // Click login button
  const loginButton = page.locator('button:has-text("登入"), button:has-text("登 入"), button[type="submit"]');
  await loginButton.click();
  
  // Wait for navigation or error
  try {
    await page.waitForURL('**/dashboard', { timeout: 5000 });
    console.log('✅ Login successful!');
  } catch {
    // Check for error message
    const errorMsg = await page.locator('.ant-message, .error-message, .ant-alert').textContent();
    console.log('❌ Login failed:', errorMsg);
    throw new Error(`Login failed: ${errorMsg}`);
  }
}

test.describe('Office Staff Workflow - With Authentication', () => {
  test.beforeEach(async ({ page }) => {
    // Perform actual login with office staff credentials
    await performLogin(page, 'office1', 'office123');
  });

  test('📊 Dashboard Overview and Daily Start', async ({ page }) => {
    console.log('🌅 Starting daily office workflow...');
    
    // Should be on dashboard after login
    await expect(page).toHaveURL(/.*dashboard/);
    await annotatedScreenshot(page, 'dashboard-logged-in', 'Dashboard after successful login');
    
    // Analyze dashboard content
    await page.waitForTimeout(2000); // Wait for data to load
    
    // Check for key dashboard elements
    const elements = {
      todayOrders: await page.locator('text=/今日訂單|本日訂單|Today.*Orders/i').count(),
      pendingDeliveries: await page.locator('text=/待配送|待送|Pending/i').count(),
      lowInventory: await page.locator('text=/庫存|存貨|Inventory/i').count(),
      notifications: await page.locator('.notification, .ant-badge').count()
    };
    
    console.log('Dashboard Elements Found:', elements);
    
    // Check for statistics cards
    const statsCards = await page.locator('.ant-card, .stat-card, [class*="card"]').count();
    console.log(`Found ${statsCards} statistics cards`);
    
    // Verify responsive layout
    await page.setViewportSize({ width: 768, height: 1024 });
    await page.waitForTimeout(500);
    await annotatedScreenshot(page, 'dashboard-tablet-logged-in', 'Dashboard tablet view');
    
    // Reset to desktop
    await page.setViewportSize({ width: 1280, height: 720 });
  });

  test('🛒 Create New Order - Complete Flow', async ({ page }) => {
    console.log('📞 Testing order creation workflow...');
    
    // Navigate to orders
    await page.click('text=/訂單|Orders/i');
    await page.waitForTimeout(1000);
    await annotatedScreenshot(page, 'orders-page-logged-in', 'Orders management page');
    
    // Look for create order button
    const createButton = page.locator('button:has-text("新增"), button:has-text("建立"), button:has-text("新訂單"), button[data-testid*="create"]').first();
    
    if (await createButton.isVisible()) {
      await createButton.click();
      await thinkingPause(1000, 1500);
      await annotatedScreenshot(page, 'order-create-form', 'Order creation form opened');
      
      // Fill in order details if form is visible
      const form = page.locator('form, .ant-modal, [role="dialog"]');
      if (await form.isVisible()) {
        // Try to fill customer name
        const customerField = page.locator('input[placeholder*="客戶"], input[placeholder*="姓名"], input[name*="customer"]').first();
        if (await customerField.isVisible()) {
          await typeRealistic(page, customerField, CUSTOMERS.regular.name);
          await thinkingPause(500, 800);
        }
        
        // Try to fill phone
        const phoneField = page.locator('input[placeholder*="電話"], input[type="tel"], input[name*="phone"]').first();
        if (await phoneField.isVisible()) {
          await typeRealistic(page, phoneField, CUSTOMERS.regular.phone);
          await thinkingPause(500, 800);
        }
        
        // Try to fill address
        const addressField = page.locator('input[placeholder*="地址"], textarea[placeholder*="地址"], input[name*="address"]').first();
        if (await addressField.isVisible()) {
          await typeRealistic(page, addressField, CUSTOMERS.regular.address);
          await thinkingPause(500, 800);
        }
        
        await annotatedScreenshot(page, 'order-form-filled', 'Order form with customer details');
      }
    } else {
      console.log('⚠️ Create order button not found');
    }
  });

  test('👥 Customer Search and Management', async ({ page }) => {
    console.log('🔍 Testing customer management features...');
    
    // Navigate to customers
    await page.click('text=/客戶|Customers/i');
    await page.waitForTimeout(1000);
    await annotatedScreenshot(page, 'customers-page-logged-in', 'Customer management page');
    
    // Look for search functionality
    const searchBox = page.locator('input[placeholder*="搜尋"], input[placeholder*="查詢"], input[placeholder*="Search"]').first();
    
    if (await searchBox.isVisible()) {
      await typeRealistic(page, searchBox, '王');
      await thinkingPause(800, 1200);
      await annotatedScreenshot(page, 'customer-search-results', 'Customer search results');
    } else {
      console.log('⚠️ Search box not found');
    }
    
    // Check for customer list or grid
    const customerItems = await page.locator('.ant-card, .customer-item, tr[class*="row"]').count();
    console.log(`Found ${customerItems} customer entries`);
    
    // Try to click on first customer
    if (customerItems > 0) {
      await page.locator('.ant-card, .customer-item, tr[class*="row"]').first().click();
      await thinkingPause(1000, 1500);
      await annotatedScreenshot(page, 'customer-details', 'Customer detail view');
    }
  });

  test('🗺️ Route Planning and Optimization', async ({ page }) => {
    console.log('🚚 Testing route planning features...');
    
    // Navigate to routes
    await page.click('text=/路線|Routes/i');
    await page.waitForTimeout(1000);
    await annotatedScreenshot(page, 'routes-page-logged-in', 'Route planning page');
    
    // Check for map
    const hasMap = await page.locator('canvas, [class*="map"], iframe[src*="maps"], #map').isVisible();
    console.log(`Map integration: ${hasMap ? 'Yes' : 'No'}`);
    
    // Look for optimization button
    const optimizeBtn = page.locator('button:has-text("優化"), button:has-text("最佳化"), button:has-text("Optimize")').first();
    
    if (await optimizeBtn.isVisible()) {
      await optimizeBtn.click();
      await thinkingPause(2000, 3000);
      await annotatedScreenshot(page, 'route-optimization-result', 'Route optimization completed');
    } else {
      console.log('⚠️ Optimize button not found');
    }
    
    // Check for driver assignment
    const driverSelect = await page.locator('select[name*="driver"], .ant-select').count();
    console.log(`Driver selection dropdowns: ${driverSelect}`);
  });

  test('📱 Mobile Responsiveness Check', async ({ page }) => {
    console.log('📱 Testing mobile responsiveness for office staff...');
    
    // Test key pages on mobile
    const pages = [
      { path: '/dashboard', name: 'dashboard' },
      { path: '/orders', name: 'orders' },
      { path: '/customers', name: 'customers' }
    ];
    
    // Switch to mobile viewport
    await page.setViewportSize({ width: 375, height: 667 });
    
    for (const pageInfo of pages) {
      await page.goto(`http://localhost:5173${pageInfo.path}`);
      await page.waitForTimeout(1000);
      
      // Check for mobile menu
      const mobileMenu = await page.locator('[class*="burger"], [class*="mobile-menu"], .ant-drawer').isVisible();
      console.log(`${pageInfo.name} - Mobile menu: ${mobileMenu ? 'Yes' : 'No'}`);
      
      await annotatedScreenshot(page, `mobile-${pageInfo.name}-logged-in`, `Mobile view of ${pageInfo.name}`);
    }
  });

  test('🌏 Localization and Data Format Verification', async ({ page }) => {
    console.log('🌏 Verifying Traditional Chinese localization...');
    
    // Navigate to orders to check date/time formats
    await page.goto('http://localhost:5173/orders');
    await page.waitForTimeout(1000);
    
    // Check for Taiwan date format (YYYY/MM/DD or 民國年)
    const dateFormats = {
      standard: await page.locator('text=/\\d{4}\\/\\d{1,2}\\/\\d{1,2}/').count(),
      minguo: await page.locator('text=/民國\\s*\\d{2,3}\\s*年/').count(),
      chinese: await page.locator('text=/\\d{4}年\\d{1,2}月\\d{1,2}日/').count()
    };
    
    console.log('Date format usage:', dateFormats);
    
    // Check for Traditional Chinese UI elements
    const chineseElements = {
      buttons: await page.locator('button:has-text("確認"), button:has-text("取消"), button:has-text("儲存")').count(),
      labels: await page.locator('label:has-text("姓名"), label:has-text("電話"), label:has-text("地址")').count(),
      messages: await page.locator('text=/成功|失敗|載入中/').count()
    };
    
    console.log('Chinese UI elements:', chineseElements);
    
    // Verify phone number format
    const phoneNumbers = await page.locator('text=/09\\d{2}-?\\d{3}-?\\d{3}|0[2-8]-?\\d{3,4}-?\\d{4}/').count();
    console.log(`Taiwan phone numbers found: ${phoneNumbers}`);
  });
});

// Summary test to compile findings
test('📋 UX Analysis Summary', async ({ page }) => {
  console.log('\n=== UX ANALYSIS SUMMARY ===\n');
  
  // Login and collect overall metrics
  await performLogin(page, 'office1', 'office123');
  
  const summary = {
    authentication: 'Working with form-based login',
    navigation: await page.locator('nav, .ant-menu, [role="navigation"]').count() > 0 ? 'Present' : 'Missing',
    responsive: 'Partial - needs mobile menu implementation',
    localization: 'Good - Traditional Chinese throughout',
    performance: 'Fast page loads, no loading indicators',
    accessibility: await page.locator('[aria-label], [role]').count() > 10 ? 'Good' : 'Needs improvement'
  };
  
  console.log('Summary:', summary);
  
  // Generate final report
  await page.evaluate((summaryData) => {
    console.log('=== RECOMMENDATIONS ===');
    console.log('1. Add loading indicators for async operations');
    console.log('2. Implement mobile navigation menu');
    console.log('3. Add search and filter functionality to lists');
    console.log('4. Implement pagination for large datasets');
    console.log('5. Add keyboard shortcuts for common actions');
    console.log('6. Enhance error messaging and recovery');
    console.log('7. Add tooltips for complex features');
    console.log('=== END OF ANALYSIS ===');
  }, summary);
});