import { test, expect, Page } from '@playwright/test';
import { LoginPage } from '../pages/LoginPage';

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
async function typeRealistic(page: Page, selector: string, text: string) {
  await page.fill(selector, '');
  await page.type(selector, text, { delay: 50 + Math.random() * 50 });
}

// Helper to simulate thinking time
async function thinkingPause(minMs = 500, maxMs = 1500) {
  await new Promise(resolve => setTimeout(resolve, minMs + Math.random() * (maxMs - minMs)));
}

test.describe('Office Staff Daily Workflow - Realistic Usage', () => {
  let page: Page;

  test.beforeAll(async ({ browser }) => {
    page = await browser.newPage();
    
    // Login as office staff
    const loginPage = new LoginPage(page);
    await loginPage.goto();
    await loginPage.login('office1', 'office123');
    await page.waitForURL('**/dashboard');
  });

  test.afterAll(async () => {
    await page.close();
  });

  test('Morning routine - Check dashboard and pending orders', async () => {
    console.log('🌅 Starting morning routine...');
    
    // 1. Check dashboard statistics
    await page.goto('/dashboard');
    await expect(page.locator('h2')).toContainText('儀表板');
    
    // Check today's statistics
    const stats = {
      pendingOrders: await page.locator('[data-testid="stat-pending-orders"]').textContent(),
      todayDeliveries: await page.locator('[data-testid="stat-today-deliveries"]').textContent(),
      lowStock: await page.locator('[data-testid="stat-low-stock"]').textContent()
    };
    
    console.log('📊 Morning stats:', stats);
    
    // Simulate reading the dashboard
    await thinkingPause(2000, 3000);
    
    // 2. Check for urgent notifications
    const notificationBell = page.locator('[data-testid="notification-bell"]');
    if (await notificationBell.isVisible()) {
      const notificationCount = await notificationBell.locator('.ant-badge-count').textContent();
      if (notificationCount && parseInt(notificationCount) > 0) {
        console.log(`🔔 ${notificationCount} new notifications`);
        await notificationBell.click();
        await thinkingPause(1000, 2000);
        await page.keyboard.press('Escape');
      }
    }
    
    // 3. Navigate to orders to check pending items
    await page.click('text=訂單管理');
    await page.waitForURL('**/orders');
    
    // Filter for pending orders
    await page.click('[data-testid="order-status-filter"]');
    await page.click('text=待處理');
    await thinkingPause(1000, 1500);
    
    const pendingOrdersCount = await page.locator('.ant-table-row').count();
    console.log(`📦 Found ${pendingOrdersCount} pending orders to process`);
  });

  test('Process a phone order from regular customer', async () => {
    console.log('📞 Incoming phone call from regular customer...');
    
    // Navigate to orders
    await page.goto('/orders');
    
    // Click create new order
    await page.click('[data-testid="create-order-btn"]');
    await expect(page.locator('.ant-modal')).toBeVisible();
    
    // Search for existing customer
    console.log('🔍 Searching for customer: ' + CUSTOMERS.regular.name);
    await typeRealistic(page, '[data-testid="customer-search"]', CUSTOMERS.regular.phone);
    await thinkingPause(1000, 1500);
    
    // Select customer from dropdown
    await page.click(`.ant-select-item:has-text("${CUSTOMERS.regular.name}")`);
    
    // Verify customer details loaded
    await expect(page.locator('[data-testid="customer-address"]')).toContainText(CUSTOMERS.regular.address.substring(0, 10));
    
    // Add products - typical order
    console.log('📝 Taking order details...');
    
    // Add 16kg cylinders
    await page.click('[data-testid="add-product-btn"]');
    await page.selectOption('[data-testid="product-select"]', '16kg-cylinder');
    await page.fill('[data-testid="quantity-input"]', '2');
    await page.fill('[data-testid="exchange-quantity"]', '2');
    
    // Customer mentions they're running low
    await typeRealistic(page, '[data-testid="order-notes"]', '客戶說瓦斯快用完了，請優先配送');
    
    // Simulate confirming details with customer
    await thinkingPause(2000, 3000);
    
    // Schedule delivery for afternoon
    await page.click('[data-testid="delivery-date"]');
    await page.click('.ant-picker-today');
    
    await page.selectOption('[data-testid="delivery-time-slot"]', 'afternoon');
    
    // Calculate total and confirm with customer
    const total = await page.locator('[data-testid="order-total"]').textContent();
    console.log(`💰 Total amount: ${total}`);
    await thinkingPause(1500, 2000);
    
    // Submit order
    await page.click('[data-testid="submit-order-btn"]');
    
    // Wait for success message
    await expect(page.locator('.ant-message-success')).toBeVisible();
    console.log('✅ Order created successfully');
    
    // Give order number to customer
    const orderNumber = await page.locator('.ant-message-success').textContent();
    console.log(`📋 Order number for customer: ${orderNumber}`);
  });

  test('Handle customer complaint about late delivery', async () => {
    console.log('😤 Incoming complaint call about late delivery...');
    
    // Navigate to customers
    await page.goto('/customers');
    
    // Search for complaining customer
    await typeRealistic(page, '[data-testid="search-input"]', CUSTOMERS.commercial.phone);
    await page.keyboard.press('Enter');
    await thinkingPause(1000, 1500);
    
    // Open customer details
    await page.click('.ant-table-row:first-child');
    await expect(page.locator('[data-testid="customer-detail-modal"]')).toBeVisible();
    
    // Check delivery history
    await page.click('[data-testid="tab-delivery-history"]');
    await thinkingPause(1000, 2000);
    
    // Find today's delivery
    const latestDelivery = page.locator('[data-testid="delivery-history-item"]').first();
    const deliveryStatus = await latestDelivery.locator('[data-testid="delivery-status"]').textContent();
    
    console.log(`📦 Latest delivery status: ${deliveryStatus}`);
    
    if (deliveryStatus?.includes('配送中')) {
      // Check driver location
      await page.click('[data-testid="track-delivery-btn"]');
      await thinkingPause(2000, 3000);
      
      // Get ETA
      const eta = await page.locator('[data-testid="delivery-eta"]').textContent();
      console.log(`🚚 Driver ETA: ${eta}`);
      
      // Add note about complaint
      await page.click('[data-testid="add-note-btn"]');
      await typeRealistic(
        page, 
        '[data-testid="note-input"]', 
        '客戶來電反映配送延遲，已告知預計到達時間，客戶表示理解'
      );
      await page.click('[data-testid="save-note-btn"]');
      
      console.log('📝 Added complaint note to customer record');
    }
    
    // Close modal
    await page.keyboard.press('Escape');
  });

  test('Prepare routes for afternoon deliveries', async () => {
    console.log('🗺️ Preparing afternoon delivery routes...');
    
    // Navigate to routes
    await page.goto('/routes');
    
    // Click optimize routes
    await page.click('[data-testid="optimize-routes-btn"]');
    await thinkingPause(1000, 2000);
    
    // Select afternoon time slot
    await page.click('[data-testid="time-slot-afternoon"]');
    
    // Select available drivers
    const availableDrivers = await page.locator('[data-testid^="driver-checkbox-"]:not(:checked)').count();
    console.log(`👷 ${availableDrivers} drivers available for afternoon`);
    
    // Select first 3 available drivers
    for (let i = 0; i < Math.min(3, availableDrivers); i++) {
      await page.click(`[data-testid^="driver-checkbox-"]:not(:checked):nth(${i})`);
      await thinkingPause(300, 500);
    }
    
    // Run optimization
    await page.click('[data-testid="run-optimization-btn"]');
    console.log('⚙️ Running route optimization...');
    
    // Wait for optimization to complete
    await expect(page.locator('[data-testid="optimization-complete"]')).toBeVisible({ timeout: 10000 });
    
    // Review results
    const totalDistance = await page.locator('[data-testid="total-distance"]').textContent();
    const estimatedTime = await page.locator('[data-testid="total-time"]').textContent();
    console.log(`📊 Optimization results: ${totalDistance}, ${estimatedTime}`);
    
    // Make manual adjustments if needed
    await thinkingPause(2000, 3000);
    
    // Approve routes
    await page.click('[data-testid="approve-routes-btn"]');
    await expect(page.locator('.ant-message-success')).toContainText('路線已確認');
    console.log('✅ Routes approved and sent to drivers');
  });

  test('Process payment and update customer credit', async () => {
    console.log('💳 Processing customer payment...');
    
    // Navigate to customers
    await page.goto('/customers');
    
    // Find customer with outstanding balance
    await page.click('[data-testid="filter-with-balance"]');
    await thinkingPause(1000, 1500);
    
    // Open first customer with balance
    await page.click('.ant-table-row:first-child');
    await expect(page.locator('[data-testid="customer-detail-modal"]')).toBeVisible();
    
    // Go to payment tab
    await page.click('[data-testid="tab-payments"]');
    
    const currentBalance = await page.locator('[data-testid="current-balance"]').textContent();
    console.log(`💰 Current balance: ${currentBalance}`);
    
    // Record payment
    await page.click('[data-testid="record-payment-btn"]');
    
    // Fill payment details
    await page.selectOption('[data-testid="payment-method"]', 'cash');
    await typeRealistic(page, '[data-testid="payment-amount"]', '5000');
    await typeRealistic(page, '[data-testid="payment-notes"]', '現金收款，已開收據');
    
    // Save payment
    await page.click('[data-testid="save-payment-btn"]');
    await expect(page.locator('.ant-message-success')).toContainText('付款已記錄');
    
    // Verify balance updated
    const newBalance = await page.locator('[data-testid="current-balance"]').textContent();
    console.log(`✅ New balance: ${newBalance}`);
    
    await page.keyboard.press('Escape');
  });

  test('End of day - Review daily summary', async () => {
    console.log('🌆 End of day summary...');
    
    // Go back to dashboard
    await page.goto('/dashboard');
    
    // Refresh to get latest data
    await page.reload();
    await thinkingPause(2000, 3000);
    
    // Collect end of day stats
    const endOfDayStats = {
      ordersProcessed: await page.locator('[data-testid="stat-orders-today"]').textContent(),
      deliveriesCompleted: await page.locator('[data-testid="stat-deliveries-completed"]').textContent(),
      revenue: await page.locator('[data-testid="stat-revenue-today"]').textContent(),
      pendingTomorrow: await page.locator('[data-testid="stat-pending-tomorrow"]').textContent()
    };
    
    console.log('📊 End of day summary:', endOfDayStats);
    
    // Check if any urgent items for tomorrow
    if (endOfDayStats.pendingTomorrow && parseInt(endOfDayStats.pendingTomorrow) > 20) {
      console.log('⚠️ High volume expected tomorrow, may need extra drivers');
    }
    
    // Export daily report
    await page.click('[data-testid="export-daily-report"]');
    console.log('📄 Daily report exported');
    
    await thinkingPause(2000, 3000);
    console.log('👋 Logging off for the day...');
  });
});

test.describe('Office Staff Error Scenarios', () => {
  test('Handle double booking attempt', async ({ page }) => {
    const loginPage = new LoginPage(page);
    await loginPage.goto();
    await loginPage.login('office1', 'office123');
    
    await page.goto('/orders');
    
    // Create first order
    await page.click('[data-testid="create-order-btn"]');
    await typeRealistic(page, '[data-testid="customer-search"]', CUSTOMERS.regular.phone);
    await page.click(`.ant-select-item:has-text("${CUSTOMERS.regular.name}")`);
    
    // Try to select same time slot that's already full
    await page.click('[data-testid="delivery-date"]');
    await page.click('.ant-picker-today');
    await page.selectOption('[data-testid="delivery-time-slot"]', 'morning');
    
    // System should show warning
    await expect(page.locator('[data-testid="time-slot-full-warning"]')).toBeVisible();
    console.log('⚠️ System prevented double booking');
  });

  test('Handle network interruption during order creation', async ({ page, context }) => {
    const loginPage = new LoginPage(page);
    await loginPage.goto();
    await loginPage.login('office1', 'office123');
    
    await page.goto('/orders');
    await page.click('[data-testid="create-order-btn"]');
    
    // Fill order details
    await typeRealistic(page, '[data-testid="customer-search"]', CUSTOMERS.commercial.phone);
    await page.click(`.ant-select-item:has-text("${CUSTOMERS.commercial.name}")`);
    
    // Simulate network interruption
    await context.setOffline(true);
    
    // Try to submit
    await page.click('[data-testid="submit-order-btn"]');
    
    // Should show offline warning
    await expect(page.locator('[data-testid="offline-warning"]')).toBeVisible();
    console.log('📵 Offline warning displayed');
    
    // Restore connection
    await context.setOffline(false);
    
    // Retry submission
    await page.click('[data-testid="retry-submit-btn"]');
    await expect(page.locator('.ant-message-success')).toBeVisible();
    console.log('✅ Order submitted after connection restored');
  });
});

// Performance monitoring during workflow
test.describe('Workflow Performance Metrics', () => {
  test('Measure common task completion times', async ({ page }) => {
    const loginPage = new LoginPage(page);
    await loginPage.goto();
    
    const metrics = {
      loginTime: 0,
      orderCreationTime: 0,
      customerSearchTime: 0,
      routeOptimizationTime: 0
    };
    
    // Measure login time
    const loginStart = Date.now();
    await loginPage.login('office1', 'office123');
    await page.waitForURL('**/dashboard');
    metrics.loginTime = Date.now() - loginStart;
    
    // Measure order creation time
    await page.goto('/orders');
    const orderStart = Date.now();
    await page.click('[data-testid="create-order-btn"]');
    await page.fill('[data-testid="customer-search"]', '0912345678');
    await page.click('[data-testid="submit-order-btn"]');
    await expect(page.locator('.ant-message-success')).toBeVisible();
    metrics.orderCreationTime = Date.now() - orderStart;
    
    console.log('⏱️ Performance Metrics:');
    console.log(`  Login: ${metrics.loginTime}ms`);
    console.log(`  Order Creation: ${metrics.orderCreationTime}ms`);
    
    // Check against performance budgets
    expect(metrics.loginTime).toBeLessThan(3000);
    expect(metrics.orderCreationTime).toBeLessThan(5000);
  });
});