import { test, expect, testData, helpers } from '../playwright-helpers';
import { LoginPage } from '../pages/LoginPage';
import { DashboardPage } from '../pages/DashboardPage';
import { CustomerPage } from '../pages/CustomerPage';

test.describe('Customer Management with WebSocket', () => {
  let loginPage: LoginPage;
  let dashboardPage: DashboardPage;
  let customerPage: CustomerPage;

  test.beforeEach(async ({ page, webSocketHelper }) => {
    loginPage = new LoginPage(page);
    dashboardPage = new DashboardPage(page);
    customerPage = new CustomerPage(page);
    
    // Login first
    await loginPage.navigateToLogin();
    await loginPage.login('admin', 'admin123');
    await loginPage.waitForLoginSuccess();
    
    // Wait for WebSocket connection
    const connected = await webSocketHelper.waitForConnection();
    expect(connected).toBe(true);
    
    // Verify WebSocket authentication
    const token = await page.evaluate(() => localStorage.getItem('access_token'));
    const authenticated = await webSocketHelper.verifyAuthentication(token!);
    expect(authenticated).toBe(true);
    
    // Navigate to customers
    await dashboardPage.navigateToCustomers();
  });

  test('should receive real-time notifications for new customers', async ({ page, webSocketHelper }) => {
    // Start monitoring for notifications
    const notificationPromise = webSocketHelper.waitForMessage(
      (msg) => msg.parsedData?.type === 'notification' && msg.parsedData?.title === '新客戶'
    );
    
    // Create a new customer
    const customerData = {
      customerCode: testData.generateCustomerCode(),
      shortName: '測試客戶',
      invoiceTitle: '測試客戶有限公司',
      phone: testData.generatePhoneNumber(false),
      mobile: testData.generatePhoneNumber(true),
      address: testData.generateAddress(),
      area: 'A-瑞光',
      deliveryTimeStart: '09:00',
      deliveryTimeEnd: '18:00',
      avgDailyUsage: 20,
      paymentMethod: '月結'
    };
    
    await customerPage.clickAddCustomer();
    await customerPage.fillCustomerForm(customerData);
    await customerPage.submitCustomerForm();
    
    // Wait for notification
    const notification = await notificationPromise;
    expect(notification.parsedData.title).toBe('新客戶');
    expect(notification.parsedData.message).toContain(customerData.shortName);
  });

  test('should handle WebSocket disconnection gracefully', async ({ page, webSocketHelper }) => {
    // Simulate disconnection
    await webSocketHelper.simulateDisconnect();
    
    // Verify disconnection indicator appears
    await expect(page.locator('.connection-status.offline')).toBeVisible({ timeout: 5000 });
    
    // Try to create a customer (should queue the request)
    const customerData = {
      customerCode: testData.generateCustomerCode(),
      shortName: '離線測試客戶',
      invoiceTitle: '離線測試公司',
      address: testData.generateAddress()
    };
    
    await customerPage.clickAddCustomer();
    await customerPage.fillCustomerForm(customerData);
    await customerPage.submitCustomerForm();
    
    // Should show offline message
    await helpers.waitForToast(page, '離線模式');
    
    // Simulate reconnection
    await webSocketHelper.simulateReconnect();
    
    // Verify reconnection
    await expect(page.locator('.connection-status.online')).toBeVisible({ timeout: 10000 });
    
    // Verify queued request was processed
    await customerPage.searchCustomer(customerData.customerCode);
    await helpers.waitForTableLoad(page);
    
    const customerCount = await customerPage.getCustomerCount();
    expect(customerCount).toBeGreaterThan(0);
  });

  test('should update customer list in real-time when another user adds a customer', async ({ page, webSocketHelper }) => {
    // Get initial customer count
    const initialCount = await customerPage.getTotalCustomerCount();
    
    // Simulate another user adding a customer via WebSocket
    const newCustomer = {
      id: Date.now(),
      customer_code: testData.generateCustomerCode(),
      short_name: '即時更新測試',
      invoice_title: '即時更新測試公司',
      address: testData.generateAddress(),
      area: 'B-四維',
      created_at: new Date().toISOString()
    };
    
    // Emit customer-added event
    await page.evaluate((customer) => {
      window.dispatchEvent(new CustomEvent('ws-customer-added', {
        detail: customer
      }));
    }, newCustomer);
    
    // Wait for the table to update
    await page.waitForTimeout(1000);
    
    // Refresh the count
    await page.reload();
    await helpers.waitForTableLoad(page);
    
    const newCount = await customerPage.getTotalCustomerCount();
    expect(newCount).toBe(initialCount + 1);
    
    // Search for the new customer
    await customerPage.searchCustomer(newCustomer.customer_code);
    await helpers.waitForTableLoad(page);
    
    const searchCount = await customerPage.getCustomerCount();
    expect(searchCount).toBe(1);
  });

  test('should receive route assignment notifications for customers', async ({ page, webSocketHelper }) => {
    // Join customer updates room
    await webSocketHelper.joinRoom('customer-updates');
    
    // Monitor for route assignment notifications
    const routeNotificationPromise = webSocketHelper.waitForMessage(
      (msg) => msg.parsedData?.type === 'route-assigned'
    );
    
    // Select a customer
    await customerPage.clickCustomerRow(0);
    const customerData = await customerPage.getCustomerData(0);
    
    // Simulate route assignment via WebSocket
    await page.evaluate((data) => {
      window.dispatchEvent(new CustomEvent('ws-route-assigned', {
        detail: {
          customer_id: 1,
          customer_name: data.shortName,
          route_id: 1,
          route_name: '北區路線A',
          delivery_date: new Date().toISOString()
        }
      }));
    }, customerData);
    
    // Wait for notification
    const notification = await routeNotificationPromise;
    expect(notification.parsedData.customer_name).toBe(customerData.shortName);
  });

  test('should sync customer data across multiple tabs', async ({ browser, page, webSocketHelper }) => {
    // Create a second context (simulating another tab)
    const context2 = await browser.newContext();
    const page2 = await context2.newPage();
    
    // Login in second tab
    const loginPage2 = new LoginPage(page2);
    await loginPage2.navigateToLogin();
    await loginPage2.login('office1', 'office123');
    await loginPage2.waitForLoginSuccess();
    
    // Navigate to customers in second tab
    const dashboardPage2 = new DashboardPage(page2);
    const customerPage2 = new CustomerPage(page2);
    await dashboardPage2.navigateToCustomers();
    
    // Create customer in first tab
    const customerData = {
      customerCode: testData.generateCustomerCode(),
      shortName: '多分頁同步測試',
      invoiceTitle: '同步測試公司',
      address: testData.generateAddress()
    };
    
    await customerPage.clickAddCustomer();
    await customerPage.fillCustomerForm(customerData);
    await customerPage.submitCustomerForm();
    
    // Wait for sync
    await page2.waitForTimeout(2000);
    
    // Search for the customer in second tab
    await customerPage2.searchCustomer(customerData.customerCode);
    await helpers.waitForTableLoad(page2);
    
    const count = await customerPage2.getCustomerCount();
    expect(count).toBeGreaterThan(0);
    
    // Clean up
    await context2.close();
  });

  test('should handle batch updates via WebSocket', async ({ page, webSocketHelper }) => {
    // Monitor for batch update completion
    const batchUpdatePromise = webSocketHelper.waitForMessage(
      (msg) => msg.parsedData?.type === 'batch-update-complete'
    );
    
    // Select multiple customers
    await customerPage.selectCustomersByCheckbox([0, 1, 2]);
    
    // Trigger batch update (e.g., change area)
    const batchUpdateButton = page.locator('button').filter({ hasText: '批量更新' });
    await batchUpdateButton.click();
    
    // Select new area in modal
    const areaSelect = page.locator('.ant-modal input[id="batch_area"]');
    await helpers.selectFromDropdown(page, areaSelect, 'C-漢中');
    
    // Confirm batch update
    const confirmButton = page.locator('.ant-modal-footer button.ant-btn-primary');
    await confirmButton.click();
    
    // Wait for WebSocket confirmation
    const batchResult = await batchUpdatePromise;
    expect(batchResult.parsedData.updated_count).toBe(3);
    
    // Verify updates in UI
    await page.reload();
    await helpers.waitForTableLoad(page);
    
    // Check that all selected customers now have the new area
    for (let i = 0; i < 3; i++) {
      const customerData = await customerPage.getCustomerData(i);
      expect(customerData.area).toBe('C-漢中');
    }
  });

  test('should display real-time delivery status updates', async ({ page, webSocketHelper }) => {
    // Navigate to a customer with active delivery
    await customerPage.searchCustomer('王大明');
    await helpers.waitForTableLoad(page);
    await customerPage.clickCustomerRow(0);
    
    // Monitor for delivery status updates
    const deliveryUpdatePromise = webSocketHelper.waitForMessage(
      (msg) => msg.parsedData?.type === 'delivery-status-update'
    );
    
    // Simulate delivery completion via WebSocket
    await webSocketHelper.mockOrderUpdate({
      order_id: 1,
      customer_id: 1,
      status: 'delivered',
      delivered_at: new Date().toISOString(),
      signature_url: 'mock://signature.png'
    });
    
    // Wait for update
    const update = await deliveryUpdatePromise;
    expect(update.parsedData.status).toBe('delivered');
    
    // Verify UI updates
    const statusBadge = page.locator('.delivery-status-badge');
    await expect(statusBadge).toHaveText('已送達');
  });

  test('should handle concurrent edits with conflict resolution', async ({ page, webSocketHelper }) => {
    // Search for a specific customer
    await customerPage.searchCustomer('李小華');
    await helpers.waitForTableLoad(page);
    
    // Start editing
    await customerPage.editCustomer(0);
    
    // Simulate another user editing the same customer
    await webSocketHelper.mockNotification({
      type: 'customer-locked',
      customer_id: 2,
      locked_by: 'office1',
      locked_at: new Date().toISOString()
    });
    
    // Should show warning
    await expect(page.locator('.ant-alert-warning')).toContainText('另一位用戶正在編輯');
    
    // Try to save changes
    await customerPage.fillCustomerForm({
      customerCode: '', // Keep existing
      avgDailyUsage: 25
    });
    
    await customerPage.submitCustomerForm(true);
    
    // Should show conflict resolution dialog
    await expect(page.locator('.conflict-resolution-modal')).toBeVisible();
    
    // Choose to merge changes
    const mergeButton = page.locator('button').filter({ hasText: '合併變更' });
    await mergeButton.click();
    
    // Verify success
    await helpers.waitForToast(page, '更新成功');
  });
});