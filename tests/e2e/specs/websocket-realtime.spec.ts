import { test, expect, Browser, BrowserContext, Page } from '@playwright/test';
import { test as customTest, interceptWebSocketMessages, waitForWebSocket } from '../fixtures/test-helpers';
import { LoginPage } from '../pages/LoginPage';
import { DashboardPage } from '../pages/DashboardPage';
import { TestUsers, TestOrders } from '../fixtures/test-data';

test.describe('WebSocket Real-time Updates', () => {
  let officeContext: BrowserContext;
  let driverContext: BrowserContext;
  let managerContext: BrowserContext;
  
  let officePage: Page;
  let driverPage: Page;
  let managerPage: Page;

  test.beforeAll(async ({ browser }) => {
    // Create contexts for different users
    officeContext = await browser.newContext();
    driverContext = await browser.newContext({
      ...browser._options,
      viewport: { width: 390, height: 844 }, // iPhone 12 size
    });
    managerContext = await browser.newContext();

    // Create pages
    officePage = await officeContext.newPage();
    driverPage = await driverContext.newPage();
    managerPage = await managerContext.newPage();

    // Login all users
    const officeLogin = new LoginPage(officePage);
    await officeLogin.goto();
    await officeLogin.login(TestUsers.officeStaff.email, TestUsers.officeStaff.password);

    const driverLogin = new LoginPage(driverPage);
    await driverLogin.goto();
    await driverLogin.login(TestUsers.driver.email, TestUsers.driver.password);

    const managerLogin = new LoginPage(managerPage);
    await managerLogin.goto();
    await managerLogin.login(TestUsers.manager.email, TestUsers.manager.password);

    // Wait for WebSocket connections
    await waitForWebSocket(officePage);
    await waitForWebSocket(driverPage);
    await waitForWebSocket(managerPage);
  });

  test.afterAll(async () => {
    await officeContext.close();
    await driverContext.close();
    await managerContext.close();
  });

  test('should broadcast new order to all connected users', async () => {
    const orderData = {
      customer: '測試客戶_' + Date.now(),
      product: '20kg 家用桶裝瓦斯',
      quantity: 1,
    };

    // Set up WebSocket message listeners
    const officeMessages: any[] = [];
    const driverMessages: any[] = [];
    const managerMessages: any[] = [];

    await interceptWebSocketMessages(officePage, (data) => {
      if (data.type === 'order_created') officeMessages.push(data);
    });

    await interceptWebSocketMessages(driverPage, (data) => {
      if (data.type === 'order_created') driverMessages.push(data);
    });

    await interceptWebSocketMessages(managerPage, (data) => {
      if (data.type === 'order_created') managerMessages.push(data);
    });

    // Office staff creates new order
    await officePage.goto('/orders');
    await officePage.click('[data-testid="create-order-button"]');
    
    // Quick order creation
    await officePage.fill('[data-testid="customer-name-quick"]', orderData.customer);
    await officePage.fill('[data-testid="customer-phone-quick"]', '0912-345-678');
    await officePage.selectOption('[data-testid="product-select"]', orderData.product);
    await officePage.fill('[data-testid="quantity-input"]', orderData.quantity.toString());
    await officePage.click('[data-testid="submit-order-button"]');

    // Wait for WebSocket broadcasts
    await officePage.waitForTimeout(2000);

    // Verify all users received the update
    expect(officeMessages.length).toBeGreaterThan(0);
    expect(driverMessages.length).toBeGreaterThan(0);
    expect(managerMessages.length).toBeGreaterThan(0);

    // Verify order appears in real-time on manager dashboard
    const managerDashboard = new DashboardPage(managerPage);
    await managerDashboard.verifyRealTimeUpdate('order');
  });

  test('should update delivery status in real-time', async () => {
    // Driver starts a delivery
    await driverPage.goto('/driver');
    await driverPage.click('[data-testid="route-item"]:first-child');
    await driverPage.click('[data-testid="start-route-button"]');
    
    // Get current delivery order number
    const orderNumber = await driverPage.locator('[data-testid="order-number"]').textContent();

    // Office staff views the order
    await officePage.goto('/orders');
    await officePage.fill('[data-testid="order-search"]', orderNumber || '');
    await officePage.press('[data-testid="order-search"]', 'Enter');
    await officePage.click(`[data-testid="order-row"]:has-text("${orderNumber}")`);

    // Initial status should be "assigned"
    await expect(officePage.locator('[data-testid="order-status"]')).toContainText('已指派');

    // Driver updates status to "in transit"
    await driverPage.click('[data-testid="start-delivery-button"]');

    // Office should see real-time update
    await expect(officePage.locator('[data-testid="order-status"]')).toContainText('配送中', { timeout: 5000 });
    
    // Status change notification should appear
    await expect(officePage.locator('[data-testid="status-update-notification"]')).toBeVisible();
  });

  test('should sync route optimization across devices', async () => {
    // Manager triggers route optimization
    await managerPage.goto('/routes');
    await managerPage.click('[data-testid="optimize-routes-button"]');
    
    // Select optimization parameters
    await managerPage.selectOption('[data-testid="optimization-method"]', 'distance');
    await managerPage.click('[data-testid="include-traffic"]');
    await managerPage.click('[data-testid="run-optimization"]');

    // Wait for optimization to complete
    await expect(managerPage.locator('[data-testid="optimization-complete"]')).toBeVisible({ timeout: 30000 });

    // Driver should receive updated route
    await expect(driverPage.locator('[data-testid="route-updated-notification"]')).toBeVisible({ timeout: 5000 });
    
    // Verify driver sees new route order
    await driverPage.click('[data-testid="view-updated-route"]');
    await expect(driverPage.locator('[data-testid="optimized-badge"]')).toBeVisible();
  });

  test('should handle connection loss and reconnection', async () => {
    // Monitor connection status
    await expect(officePage.locator('[data-testid="websocket-status"]')).toHaveAttribute('data-status', 'connected');

    // Simulate connection loss
    await officePage.evaluate(() => {
      const ws = (window as any).websocket;
      if (ws) ws.close();
    });

    // Should show disconnected status
    await expect(officePage.locator('[data-testid="websocket-status"]')).toHaveAttribute('data-status', 'disconnected', { timeout: 5000 });
    await expect(officePage.locator('[data-testid="connection-lost-banner"]')).toBeVisible();

    // Should attempt reconnection
    await expect(officePage.locator('[data-testid="websocket-status"]')).toHaveAttribute('data-status', 'connecting', { timeout: 5000 });

    // Should reconnect successfully
    await expect(officePage.locator('[data-testid="websocket-status"]')).toHaveAttribute('data-status', 'connected', { timeout: 10000 });
    await expect(officePage.locator('[data-testid="connection-restored-toast"]')).toBeVisible();
  });

  test('should queue messages during offline period', async () => {
    // Create order while online
    const orderNumber = 'TEST_' + Date.now();
    
    // Go offline
    await officeContext.setOffline(true);
    
    // Try to update order (should queue)
    await officePage.goto('/orders');
    await officePage.click('[data-testid="order-row"]:first-child');
    await officePage.click('[data-testid="edit-order-button"]');
    await officePage.fill('[data-testid="order-notes"]', 'Updated while offline');
    await officePage.click('[data-testid="save-order-button"]');

    // Should show queued indicator
    await expect(officePage.locator('[data-testid="offline-queue-badge"]')).toBeVisible();
    await expect(officePage.locator('[data-testid="offline-queue-count"]')).toContainText('1');

    // Go back online
    await officeContext.setOffline(false);

    // Should sync queued changes
    await expect(officePage.locator('[data-testid="syncing-indicator"]')).toBeVisible();
    await expect(officePage.locator('[data-testid="sync-complete-toast"]')).toBeVisible({ timeout: 5000 });
    await expect(officePage.locator('[data-testid="offline-queue-badge"]')).not.toBeVisible();
  });

  test('should handle high-frequency updates', async () => {
    // Simulate multiple drivers updating simultaneously
    const updatePromises = [];
    
    // Create 10 rapid updates
    for (let i = 0; i < 10; i++) {
      updatePromises.push(
        driverPage.evaluate((index) => {
          fetch('/api/v1/deliveries/update', {
            method: 'POST',
            headers: {
              'Content-Type': 'application/json',
              'Authorization': `Bearer ${localStorage.getItem('access_token')}`,
            },
            body: JSON.stringify({
              orderId: `TEST_ORDER_${index}`,
              status: 'delivered',
              timestamp: new Date().toISOString(),
            }),
          });
        }, i)
      );
    }

    await Promise.all(updatePromises);

    // Manager dashboard should handle all updates without freezing
    const fps = await managerPage.evaluate(() => {
      let lastTime = performance.now();
      let frames = 0;
      
      return new Promise<number>((resolve) => {
        function measureFPS() {
          frames++;
          const currentTime = performance.now();
          
          if (currentTime >= lastTime + 1000) {
            resolve(frames);
          } else {
            requestAnimationFrame(measureFPS);
          }
        }
        
        requestAnimationFrame(measureFPS);
      });
    });

    // Should maintain reasonable FPS during updates
    expect(fps).toBeGreaterThan(30);
  });

  test('should broadcast system notifications', async () => {
    // Admin sends system-wide notification
    const adminContext = await test.browser!.newContext();
    const adminPage = await adminContext.newPage();
    
    const adminLogin = new LoginPage(adminPage);
    await adminLogin.goto();
    await adminLogin.login(TestUsers.superAdmin.email, TestUsers.superAdmin.password);
    
    await adminPage.goto('/admin/notifications');
    await adminPage.click('[data-testid="send-broadcast-button"]');
    
    // Compose notification
    await adminPage.fill('[data-testid="notification-title"]', '系統維護通知');
    await adminPage.fill('[data-testid="notification-message"]', '系統將於今晚 10:00 進行維護，預計 30 分鐘');
    await adminPage.selectOption('[data-testid="notification-priority"]', 'high');
    await adminPage.click('[data-testid="send-notification-button"]');

    // All users should receive notification
    await expect(officePage.locator('[data-testid="system-notification-popup"]')).toBeVisible({ timeout: 5000 });
    await expect(driverPage.locator('[data-testid="system-notification-popup"]')).toBeVisible({ timeout: 5000 });
    await expect(managerPage.locator('[data-testid="system-notification-popup"]')).toBeVisible({ timeout: 5000 });

    // Verify notification content
    await expect(officePage.locator('[data-testid="notification-title"]')).toContainText('系統維護通知');
    
    await adminContext.close();
  });

  test('should update inventory levels in real-time', async () => {
    // Office updates inventory
    await officePage.goto('/inventory');
    
    const initialCount = await officePage.locator('[data-testid="20kg-stock-count"]').textContent();
    
    // Reduce inventory
    await officePage.click('[data-testid="adjust-inventory-button"]');
    await officePage.selectOption('[data-testid="product-type"]', '20kg');
    await officePage.selectOption('[data-testid="adjustment-type"]', 'remove');
    await officePage.fill('[data-testid="adjustment-quantity"]', '5');
    await officePage.fill('[data-testid="adjustment-reason"]', '配送出貨');
    await officePage.click('[data-testid="confirm-adjustment"]');

    // Manager should see updated inventory
    await managerPage.goto('/dashboard');
    const newCount = parseInt(initialCount || '0') - 5;
    await expect(managerPage.locator('[data-testid="20kg-inventory-widget"]')).toContainText(newCount.toString(), { timeout: 5000 });
    
    // Low stock alert if applicable
    if (newCount < 50) {
      await expect(managerPage.locator('[data-testid="low-stock-alert"]')).toBeVisible();
    }
  });

  test('should handle role-based WebSocket channels', async () => {
    // Create driver-specific update
    const driverOnlyMessage = {
      type: 'route_traffic_update',
      data: { severity: 'high', location: '信義路', delay: 15 }
    };

    // Simulate traffic update that only drivers should receive
    await driverPage.evaluate((msg) => {
      // Trigger API call that would send driver-only WebSocket message
      fetch('/api/v1/routes/traffic-alert', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${localStorage.getItem('access_token')}`,
        },
        body: JSON.stringify(msg),
      });
    }, driverOnlyMessage);

    // Driver should receive traffic update
    await expect(driverPage.locator('[data-testid="traffic-alert"]')).toBeVisible({ timeout: 5000 });
    
    // Office and Manager should NOT receive this update
    await officePage.waitForTimeout(2000);
    await expect(officePage.locator('[data-testid="traffic-alert"]')).not.toBeVisible();
    await expect(managerPage.locator('[data-testid="traffic-alert"]')).not.toBeVisible();
  });
});