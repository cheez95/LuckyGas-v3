import { test, expect, Page } from '@playwright/test';
import { LoginPage } from './pages/LoginPage';

// WebSocket event types
enum WSEventType {
  ORDER_UPDATE = 'order_update',
  ROUTE_UPDATE = 'route_update',
  DELIVERY_UPDATE = 'delivery_update',
  NOTIFICATION = 'notification',
  DRIVER_LOCATION = 'driver_location',
  SYSTEM_ALERT = 'system_alert'
}

// Helper to wait for WebSocket message
async function waitForWSMessage(page: Page, eventType: WSEventType, timeout = 10000) {
  return page.evaluate((type) => {
    return new Promise((resolve) => {
      const originalSend = WebSocket.prototype.send;
      WebSocket.prototype.send = function(data) {
        const message = JSON.parse(data);
        if (message.type === type) {
          resolve(message);
        }
        return originalSend.call(this, data);
      };
    });
  }, eventType);
}

// Helper to simulate WebSocket message
async function simulateWSMessage(page: Page, message: any) {
  await page.evaluate((msg) => {
    // Find the WebSocket instance
    const ws = (window as any).__websocket;
    if (ws && ws.readyState === WebSocket.OPEN) {
      // Simulate receiving a message
      const event = new MessageEvent('message', {
        data: JSON.stringify(msg)
      });
      ws.dispatchEvent(event);
    }
  }, message);
}

test.describe('WebSocket Real-time Features', () => {
  test.beforeEach(async ({ page }) => {
    // Setup WebSocket mock if needed
    await page.addInitScript(() => {
      // Store WebSocket reference for testing
      const OriginalWebSocket = window.WebSocket;
      window.WebSocket = function(...args) {
        const ws = new OriginalWebSocket(...args);
        (window as any).__websocket = ws;
        return ws;
      } as any;
      window.WebSocket.prototype = OriginalWebSocket.prototype;
    });

    const loginPage = new LoginPage(page);
    await loginPage.goto();
    await loginPage.login('office1', 'office123');
  });

  test('WebSocket connection lifecycle', async ({ page }) => {
    await page.goto('/dashboard');

    // Check initial connection
    await expect(page.locator('[data-testid="websocket-status"]')).toBeVisible();
    await expect(page.locator('[data-testid="websocket-status"]')).toHaveAttribute('data-status', 'connected');

    // Test reconnection on disconnect
    await page.evaluate(() => {
      const ws = (window as any).__websocket;
      if (ws) ws.close();
    });

    // Should show disconnected state
    await expect(page.locator('[data-testid="websocket-status"]')).toHaveAttribute('data-status', 'disconnected');

    // Should attempt reconnection
    await expect(page.locator('[data-testid="websocket-status"]')).toHaveAttribute('data-status', 'connecting', { timeout: 5000 });
    await expect(page.locator('[data-testid="websocket-status"]')).toHaveAttribute('data-status', 'connected', { timeout: 10000 });
  });

  test('Real-time order updates', async ({ page }) => {
    await page.goto('/orders');
    
    // Get initial order count
    const initialCount = await page.locator('.ant-table-row').count();

    // Simulate new order via WebSocket
    await simulateWSMessage(page, {
      type: WSEventType.ORDER_UPDATE,
      action: 'created',
      data: {
        id: 'test-order-1',
        orderNumber: 'ORD-2024-001',
        customerName: '測試客戶',
        status: 'pending',
        totalAmount: 1500,
        createdAt: new Date().toISOString()
      }
    });

    // Check if new order appears
    await expect(page.locator('.ant-table-row')).toHaveCount(initialCount + 1);
    await expect(page.locator('[data-testid="realtime-indicator"]')).toBeVisible();
    await expect(page.locator('text=ORD-2024-001')).toBeVisible();

    // Test order status update
    await simulateWSMessage(page, {
      type: WSEventType.ORDER_UPDATE,
      action: 'updated',
      data: {
        id: 'test-order-1',
        status: 'confirmed'
      }
    });

    // Check status updated
    await expect(page.locator('text=ORD-2024-001').locator('..').locator('[data-testid="order-status"]')).toContainText('已確認');
  });

  test('Real-time route tracking', async ({ page }) => {
    await page.goto('/routes');

    // Simulate driver location update
    await simulateWSMessage(page, {
      type: WSEventType.DRIVER_LOCATION,
      data: {
        driverId: 'driver-1',
        routeId: 'route-1',
        location: {
          latitude: 25.0330,
          longitude: 121.5654
        },
        speed: 45,
        heading: 90,
        timestamp: new Date().toISOString()
      }
    });

    // Check if driver marker updates on map
    await expect(page.locator('[data-testid="driver-marker-driver-1"]')).toBeVisible();
    await expect(page.locator('[data-testid="driver-speed"]')).toContainText('45');

    // Test route progress update
    await simulateWSMessage(page, {
      type: WSEventType.ROUTE_UPDATE,
      data: {
        routeId: 'route-1',
        completedStops: 5,
        totalStops: 10,
        estimatedCompletion: '14:30'
      }
    });

    await expect(page.locator('[data-testid="route-progress-route-1"]')).toContainText('50%');
  });

  test('Real-time notifications', async ({ page }) => {
    await page.goto('/dashboard');

    // Check notification bell
    const initialCount = await page.locator('[data-testid="notification-count"]').textContent() || '0';

    // Simulate urgent notification
    await simulateWSMessage(page, {
      type: WSEventType.NOTIFICATION,
      data: {
        id: 'notif-1',
        title: '緊急訂單',
        message: '客戶王小明急需瓦斯配送',
        type: 'urgent',
        timestamp: new Date().toISOString()
      }
    });

    // Check notification appears
    await expect(page.locator('[data-testid="notification-count"]')).toContainText(String(parseInt(initialCount) + 1));
    
    // Check notification toast
    await expect(page.locator('.ant-notification')).toBeVisible();
    await expect(page.locator('.ant-notification')).toContainText('緊急訂單');

    // Open notification panel
    await page.locator('[data-testid="notification-bell"]').click();
    await expect(page.locator('[data-testid="notification-item-notif-1"]')).toBeVisible();
  });

  test('Multi-user real-time collaboration', async ({ browser }) => {
    // Create two contexts for different users
    const context1 = await browser.newContext();
    const context2 = await browser.newContext();
    
    const page1 = await context1.newPage();
    const page2 = await context2.newPage();

    // Setup WebSocket tracking for both pages
    for (const page of [page1, page2]) {
      await page.addInitScript(() => {
        const OriginalWebSocket = window.WebSocket;
        window.WebSocket = function(...args) {
          const ws = new OriginalWebSocket(...args);
          (window as any).__websocket = ws;
          return ws;
        } as any;
        window.WebSocket.prototype = OriginalWebSocket.prototype;
      });
    }

    // Login both users
    const loginPage1 = new LoginPage(page1);
    const loginPage2 = new LoginPage(page2);
    
    await loginPage1.goto();
    await loginPage1.login('office1', 'office123');
    
    await loginPage2.goto();
    await loginPage2.login('dispatch1', 'dispatch123');

    // Both view same order
    await page1.goto('/orders');
    await page2.goto('/orders');

    // User 1 updates order status
    await page1.locator('[data-testid="order-actions"]').first().click();
    await page1.locator('[data-testid="update-status"]').click();
    await page1.locator('[data-value="confirmed"]').click();

    // User 2 should see the update immediately
    await expect(page2.locator('[data-testid="realtime-update-indicator"]')).toBeVisible();
    await expect(page2.locator('.ant-table-row').first().locator('[data-testid="order-status"]')).toContainText('已確認');

    await context1.close();
    await context2.close();
  });

  test('WebSocket message queuing during offline', async ({ page, context }) => {
    await page.goto('/driver/route/1');

    // Track outgoing messages
    const queuedMessages: any[] = [];
    await page.exposeFunction('trackMessage', (msg: any) => {
      queuedMessages.push(msg);
    });

    await page.evaluate(() => {
      const originalSend = WebSocket.prototype.send;
      WebSocket.prototype.send = function(data) {
        (window as any).trackMessage(JSON.parse(data));
        return originalSend.call(this, data);
      };
    });

    // Go offline
    await context.setOffline(true);

    // Perform actions that would send WebSocket messages
    await page.locator('[data-testid="update-delivery-status"]').click();
    await page.locator('[data-value="delivered"]').click();

    // Messages should be queued
    expect(queuedMessages.length).toBe(0); // No messages sent while offline

    // Go back online
    await context.setOffline(false);

    // Wait for queued messages to be sent
    await page.waitForTimeout(2000);
    
    // Check that messages were sent after reconnection
    expect(queuedMessages.length).toBeGreaterThan(0);
    expect(queuedMessages.some(msg => msg.type === 'delivery_update')).toBeTruthy();
  });

  test('WebSocket performance under load', async ({ page }) => {
    await page.goto('/dispatch-dashboard');

    const startTime = Date.now();
    const messageCount = 100;

    // Simulate rapid message updates
    for (let i = 0; i < messageCount; i++) {
      await simulateWSMessage(page, {
        type: WSEventType.DRIVER_LOCATION,
        data: {
          driverId: `driver-${i % 10}`,
          location: {
            latitude: 25.0330 + (Math.random() * 0.01),
            longitude: 121.5654 + (Math.random() * 0.01)
          },
          timestamp: new Date().toISOString()
        }
      });
    }

    const endTime = Date.now();
    const duration = endTime - startTime;

    // Check UI remains responsive
    await expect(page.locator('[data-testid="dispatch-map"]')).toBeVisible();
    
    // Performance assertion - should handle 100 messages in under 5 seconds
    expect(duration).toBeLessThan(5000);

    // Check no UI freezing
    await page.locator('[data-testid="menu-toggle"]').click();
    await expect(page.locator('.ant-menu')).toBeVisible();
  });

  test('WebSocket error handling and recovery', async ({ page }) => {
    await page.goto('/dashboard');

    // Simulate WebSocket error
    await page.evaluate(() => {
      const ws = (window as any).__websocket;
      if (ws) {
        const errorEvent = new Event('error');
        ws.dispatchEvent(errorEvent);
      }
    });

    // Should show error state
    await expect(page.locator('[data-testid="websocket-error"]')).toBeVisible();

    // Should attempt automatic reconnection
    await expect(page.locator('[data-testid="websocket-status"]')).toHaveAttribute('data-status', 'reconnecting', { timeout: 5000 });

    // Manual reconnection option
    await page.locator('[data-testid="manual-reconnect"]').click();
    await expect(page.locator('[data-testid="websocket-status"]')).toHaveAttribute('data-status', 'connected', { timeout: 10000 });
  });

  test('WebSocket authentication and session handling', async ({ page, context }) => {
    await page.goto('/dashboard');

    // Simulate session expiration
    await context.clearCookies();

    // Send authenticated message
    await simulateWSMessage(page, {
      type: WSEventType.SYSTEM_ALERT,
      data: {
        message: 'Session expired',
        code: 'AUTH_EXPIRED'
      }
    });

    // Should redirect to login
    await expect(page).toHaveURL(/login/, { timeout: 5000 });
    await expect(page.locator('[data-testid="session-expired-message"]')).toBeVisible();
  });

  test('WebSocket data synchronization', async ({ page }) => {
    await page.goto('/orders');

    // Get initial data
    const initialOrderCount = await page.locator('.ant-table-row').count();

    // Simulate batch update via WebSocket
    const batchUpdate = {
      type: 'batch_update',
      data: {
        orders: [
          { id: '1', status: 'delivered' },
          { id: '2', status: 'cancelled' },
          { id: '3', status: 'in_delivery' }
        ],
        timestamp: new Date().toISOString()
      }
    };

    await simulateWSMessage(page, batchUpdate);

    // Check all updates applied
    for (const order of batchUpdate.data.orders) {
      await expect(page.locator(`[data-order-id="${order.id}"] [data-testid="order-status"]`)).toContainText(order.status);
    }

    // Check data consistency indicator
    await expect(page.locator('[data-testid="sync-status"]')).toContainText('已同步');
  });
});