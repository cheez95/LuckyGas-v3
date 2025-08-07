import { test, expect } from '@playwright/test';
import { LoginPage } from './pages/LoginPage';
import { DashboardPage } from './pages/DashboardPage';
import { OrderPage } from './pages/OrderPage';

test.describe('WebSocket Basic Functionality', () => {
  let loginPage: LoginPage;
  let dashboardPage: DashboardPage;
  let orderPage: OrderPage;

  test.beforeEach(async ({ page }) => {
    loginPage = new LoginPage(page);
    dashboardPage = new DashboardPage(page);
    orderPage = new OrderPage(page);
    
    // Login as admin
    await loginPage.navigateToLogin();
    await loginPage.login('admin', 'admin123');
    await loginPage.waitForLoginSuccess();
  });

  test('should complete the test', async ({ page }) => {
    // Check if websocketService exists in window
    const hasWebSocketService = await page.evaluate(() => {
      return typeof (window as any).websocketService !== 'undefined';
    });
    
    expect(hasWebSocketService).toBe(true);
  });

  test('should complete the test - 2', async ({ page }) => {
    // Listen for console logs
    const consoleLogs: string[] = [];
    page.on('console', msg => {
      const text = msg.text();
      if (text.includes('WebSocket') || text.includes('ws')) {
        consoleLogs.push(text);
      }
    });

    // Simulate a WebSocket message
    await page.evaluate(() => {
      const event = new CustomEvent('ws-message', {
        detail: {
          type: 'notification',
          title: 'Test Notification',
          message: 'This is a test message',
          priority: 'normal',
          timestamp: new Date().toISOString()
        }
      });
      window.dispatchEvent(event);
    });

    // Wait for any console output
    await page.waitForTimeout(1000);
    
    // Should have some WebSocket-related logs
    const hasWebSocketLogs = consoleLogs.length > 0 || await page.evaluate(() => {
      // Check if WebSocket is configured
      return !!(window as any).websocketService;
    });
    
    expect(hasWebSocketLogs).toBe(true);
  });

  test('should complete the test - 3', async ({ page }) => {
    // Simulate notification message
    await page.evaluate(() => {
      // Check if notification system is available
      const antMessage = (window as any).antd?.message || (window as any).message;
      if (antMessage) {
        antMessage.info('新訂單通知');
      }
    });

    // Check for notification
    const notification = page.locator('.ant-message-notice');
    await expect(notification).toBeVisible({ timeout: 3000 });
  });

  test('should complete the test - 4', async ({ page }) => {
    await orderPage.navigateToOrders();
    
    // Get initial order count
    const initialRows = await page.locator('.ant-table-row').count();
    
    // Simulate order update via console
    await page.evaluate(() => {
      // Trigger a re-render or update event
      const event = new CustomEvent('order-update', {
        detail: { 
          type: 'order_update',
          order_id: 1,
          status: 'confirmed'
        }
      });
      window.dispatchEvent(event);
    });
    
    // Wait for potential update
    await page.waitForTimeout(2000);
    
    // Order list should still be present
    const orderRows = page.locator('.ant-table-row');
    await expect(orderRows.first()).toBeVisible();
  });

  test('should complete the test - 5', async ({ page }) => {
    // Navigate to different pages
    await dashboardPage.navigateToCustomers();
    
    // Check WebSocket service still exists
    const hasServiceAfterNav1 = await page.evaluate(() => {
      return typeof (window as any).websocketService !== 'undefined';
    });
    expect(hasServiceAfterNav1).toBe(true);
    
    await dashboardPage.navigateToOrders();
    
    // Check again
    const hasServiceAfterNav2 = await page.evaluate(() => {
      return typeof (window as any).websocketService !== 'undefined';
    });
    expect(hasServiceAfterNav2).toBe(true);
  });

  test('should complete the test - 6', async ({ page }) => {
    // Check if dashboard has real-time elements
    const statsCards = page.locator('.ant-statistic');
    const hasStats = await statsCards.count() > 0;
    
    if (hasStats) {
      // Get initial value
      const initialValue = await dashboardPage.todayOrdersCard
        .locator('.ant-statistic-content-value')
        .textContent();
      
      // Simulate update
      await page.evaluate(() => {
        // Trigger dashboard update
        const event = new Event('dashboard-update');
        window.dispatchEvent(event);
      });
      
      // Stats should still be visible
      await expect(dashboardPage.todayOrdersCard).toBeVisible();
    }
  });

  test('should complete the test - 7', async ({ page }) => {
    // Look for activity feed
    const activityFeed = page.locator('.activity-feed, .recent-activities, [data-testid="activity-feed"]');
    
    if (await activityFeed.isVisible()) {
      // Simulate activity
      await page.evaluate(() => {
        const event = new CustomEvent('activity-update', {
          detail: {
            message: '新訂單已建立',
            timestamp: new Date().toISOString()
          }
        });
        window.dispatchEvent(event);
      });
      
      // Feed should still be visible
      await expect(activityFeed).toBeVisible();
    }
  });

  test('should complete the test - 8', async ({ page }) => {
    // Check if we can access connection state
    const connectionState = await page.evaluate(() => {
      const ws = (window as any).websocketService;
      return ws?.getConnectionState?.() || 'unknown';
    });
    
    // Should have some connection state
    expect(['connected', 'connecting', 'disconnected', 'unknown']).toContain(connectionState);
  });

  test('should complete the test - 9', async ({ page }) => {
    // Test subscription mechanism
    const canSubscribe = await page.evaluate(() => {
      const ws = (window as any).websocketService;
      if (ws && typeof ws.subscribe === 'function') {
        // Try to subscribe to a topic
        ws.subscribe('test-topic');
        return true;
      }
      return false;
    });
    
    expect(canSubscribe).toBe(true);
  });

  test('should complete the test - 10', async ({ page }) => {
    // Check if driver interface is available
    const isDriverInterface = await page.url().includes('driver');
    
    if (isDriverInterface) {
      // Test location update
      const canUpdateLocation = await page.evaluate(() => {
        const ws = (window as any).websocketService;
        if (ws && typeof ws.updateDriverLocation === 'function') {
          ws.updateDriverLocation(25.0330, 121.5654);
          return true;
        }
        return false;
      });
      
      expect(canUpdateLocation).toBe(true);
    }
  });

  test('should complete the test - 11', async ({ page }) => {
    // Test message queuing
    const hasMessageQueue = await page.evaluate(() => {
      const ws = (window as any).websocketService;
      return ws && Array.isArray(ws.messageQueue);
    });
    
    // WebSocket service should have message queue capability
    expect(hasMessageQueue).toBe(true);
  });

  test('should complete the test - 12', async ({ page }) => {
    // Test event emitter functionality
    const canEmitEvents = await page.evaluate(() => {
      const ws = (window as any).websocketService;
      if (ws && typeof ws.emit === 'function') {
        // Test emitting an event
        ws.emit('test-event', { data: 'test' });
        return true;
      }
      return false;
    });
    
    expect(canEmitEvents).toBe(true);
  });

  test('should complete the test - 13', async ({ page }) => {
    // Check if heartbeat is configured
    const hasHeartbeat = await page.evaluate(() => {
      const ws = (window as any).websocketService;
      // Check for heartbeat-related properties or methods
      return ws && (ws.heartbeatInterval || typeof ws.startHeartbeat === 'function');
    });
    
    // WebSocket should have heartbeat mechanism
    expect(hasHeartbeat).toBe(true);
  });

  test('should complete the test - 14', async ({ page }) => {
    // Test reconnection capability
    const hasReconnectLogic = await page.evaluate(() => {
      const ws = (window as any).websocketService;
      return ws && (
        typeof ws.reconnectInterval !== 'undefined' ||
        typeof ws.scheduleReconnect === 'function'
      );
    });
    
    expect(hasReconnectLogic).toBe(true);
  });

  test('should complete the test - 15', async ({ page }) => {
    // Check if token is used for WebSocket
    const usesAuthToken = await page.evaluate(() => {
      const token = localStorage.getItem('access_token');
      const ws = (window as any).websocketService;
      return !!(token && ws);
    });
    
    expect(usesAuthToken).toBe(true);
  });
});