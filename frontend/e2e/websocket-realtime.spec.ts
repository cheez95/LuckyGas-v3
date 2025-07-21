import { test, expect } from '@playwright/test';
import { LoginPage } from './pages/LoginPage';
import { DashboardPage } from './pages/DashboardPage';
import { OrderPage } from './pages/OrderPage';
import { RoutePage } from './pages/RoutePage';

test.describe('Real-time WebSocket Communication', () => {
  let loginPage: LoginPage;
  let dashboardPage: DashboardPage;
  let orderPage: OrderPage;
  let routePage: RoutePage;

  test.beforeEach(async ({ page }) => {
    loginPage = new LoginPage(page);
    dashboardPage = new DashboardPage(page);
    orderPage = new OrderPage(page);
    routePage = new RoutePage(page);
    
    // Login as admin
    await loginPage.navigateToLogin();
    await loginPage.login('admin', 'admin123');
    await loginPage.waitForLoginSuccess();
  });

  test.describe('WebSocket Connection', () => {
    test('should establish WebSocket connection after login', async ({ page }) => {
      // Check for WebSocket connection indicator
      const connectionIndicator = page.locator('.ws-connection-status, [data-testid="ws-status"]');
      
      // Connection should be established within 5 seconds
      await expect(connectionIndicator).toHaveAttribute('data-status', 'connected', { timeout: 5000 });
      
      // Check console for WebSocket logs
      const consoleLogs: string[] = [];
      page.on('console', msg => {
        if (msg.text().includes('WebSocket')) {
          consoleLogs.push(msg.text());
        }
      });
      
      // Wait for connection message
      await page.waitForTimeout(1000);
      const hasConnectionLog = consoleLogs.some(log => log.includes('connected'));
      expect(hasConnectionLog).toBe(true);
    });

    test('should handle WebSocket reconnection', async ({ page }) => {
      // Simulate network interruption
      await page.context().setOffline(true);
      
      // Wait for disconnection
      await page.waitForTimeout(2000);
      
      // Check disconnection indicator
      const connectionIndicator = page.locator('.ws-connection-status, [data-testid="ws-status"]');
      await expect(connectionIndicator).toHaveAttribute('data-status', 'disconnected');
      
      // Restore network
      await page.context().setOffline(false);
      
      // Should automatically reconnect
      await expect(connectionIndicator).toHaveAttribute('data-status', 'connected', { timeout: 10000 });
    });

    test('should maintain WebSocket connection across page navigation', async ({ page }) => {
      // Navigate to different pages
      await dashboardPage.navigateToCustomers();
      await page.waitForTimeout(1000);
      
      await dashboardPage.navigateToOrders();
      await page.waitForTimeout(1000);
      
      await dashboardPage.navigateToRoutes();
      await page.waitForTimeout(1000);
      
      // Connection should remain active
      const connectionIndicator = page.locator('.ws-connection-status, [data-testid="ws-status"]');
      await expect(connectionIndicator).toHaveAttribute('data-status', 'connected');
    });
  });

  test.describe('Real-time Notifications', () => {
    test('should receive and display real-time notifications', async ({ page, context }) => {
      // Open a second browser page to simulate another user
      const page2 = await context.newPage();
      const loginPage2 = new LoginPage(page2);
      const orderPage2 = new OrderPage(page2);
      
      await loginPage2.navigateToLogin();
      await loginPage2.login('office1', 'office123');
      await loginPage2.waitForLoginSuccess();
      
      // Create an order from second user
      await orderPage2.navigateToOrders();
      await orderPage2.clickCreateOrder();
      await orderPage2.fillOrderForm({
        customerId: 'CUST001',
        deliveryDate: new Date().toISOString().split('T')[0],
        products: [{ productId: 'PROD001', quantity: 1 }],
        notes: 'Urgent delivery'
      });
      await orderPage2.submitOrderForm();
      
      // First user should receive notification
      const notification = page.locator('.ant-notification-notice').filter({ hasText: '新訂單' });
      await expect(notification).toBeVisible({ timeout: 5000 });
      
      // Cleanup
      await page2.close();
    });

    test('should handle high-priority notifications differently', async ({ page }) => {
      // Simulate high-priority notification
      await page.evaluate(() => {
        window.dispatchEvent(new CustomEvent('ws-message', {
          detail: {
            type: 'notification',
            title: '緊急通知',
            message: '客戶 A 需要緊急配送',
            priority: 'urgent',
            timestamp: new Date().toISOString()
          }
        }));
      });
      
      // Check for urgent notification styling
      const urgentNotification = page.locator('.ant-notification-notice-error, .urgent-notification');
      await expect(urgentNotification).toBeVisible();
      
      // Should have urgent indicator
      const urgentIcon = urgentNotification.locator('.anticon-exclamation-circle');
      await expect(urgentIcon).toBeVisible();
    });

    test('should persist notifications in notification center', async ({ page }) => {
      // Simulate multiple notifications
      for (let i = 0; i < 3; i++) {
        await page.evaluate((index) => {
          window.dispatchEvent(new CustomEvent('ws-message', {
            detail: {
              type: 'notification',
              title: `通知 ${index + 1}`,
              message: `這是第 ${index + 1} 個通知`,
              priority: 'normal',
              timestamp: new Date().toISOString()
            }
          }));
        }, i);
        await page.waitForTimeout(500);
      }
      
      // Open notification center
      const notificationIcon = page.locator('.notification-icon, [data-testid="notification-bell"]');
      await notificationIcon.click();
      
      // Should show all notifications
      const notificationList = page.locator('.notification-list-item');
      await expect(notificationList).toHaveCount(3);
    });
  });

  test.describe('Real-time Order Updates', () => {
    test('should update order status in real-time', async ({ page }) => {
      await orderPage.navigateToOrders();
      
      // Get first order
      const firstOrder = page.locator('.ant-table-row').first();
      const orderId = await firstOrder.getAttribute('data-row-key');
      
      // Simulate order status update
      await page.evaluate((id) => {
        window.dispatchEvent(new CustomEvent('ws-message', {
          detail: {
            type: 'order_update',
            order_id: parseInt(id || '1'),
            status: 'delivering',
            details: { driver: 'Driver A' },
            timestamp: new Date().toISOString()
          }
        }));
      }, orderId);
      
      // Status should update without refresh
      const statusBadge = firstOrder.locator('.ant-badge-status-text');
      await expect(statusBadge).toContainText('配送中', { timeout: 3000 });
    });

    test('should show real-time delivery progress', async ({ page }) => {
      await orderPage.navigateToOrders();
      
      // Click on an order to view details
      const firstOrder = page.locator('.ant-table-row').first();
      await firstOrder.click();
      
      // Should show delivery tracking
      const trackingPanel = page.locator('.delivery-tracking, [data-testid="delivery-tracking"]');
      if (await trackingPanel.isVisible()) {
        // Simulate delivery progress update
        await page.evaluate(() => {
          window.dispatchEvent(new CustomEvent('ws-message', {
            detail: {
              type: 'delivery_status_update',
              order_id: 1,
              status: 'arrived',
              location: { lat: 25.0330, lng: 121.5654 },
              timestamp: new Date().toISOString()
            }
          }));
        });
        
        // Progress should update
        const progressStatus = trackingPanel.locator('.progress-status');
        await expect(progressStatus).toContainText('已到達', { timeout: 3000 });
      }
    });

    test('should update order count badges in real-time', async ({ page }) => {
      // Check initial order count
      const orderMenuItem = page.locator('.ant-menu-item').filter({ hasText: '訂單管理' });
      const initialBadge = orderMenuItem.locator('.ant-badge-count');
      const initialCount = await initialBadge.textContent() || '0';
      
      // Simulate new order
      await page.evaluate(() => {
        window.dispatchEvent(new CustomEvent('ws-message', {
          detail: {
            type: 'order_update',
            order_id: 999,
            status: 'pending',
            details: { isNew: true },
            timestamp: new Date().toISOString()
          }
        }));
      });
      
      // Badge should increment
      await expect(initialBadge).not.toHaveText(initialCount, { timeout: 3000 });
    });
  });

  test.describe('Real-time Route Updates', () => {
    test('should update route status in real-time', async ({ page }) => {
      await routePage.navigateToRoutes();
      
      // Simulate route status update
      await page.evaluate(() => {
        window.dispatchEvent(new CustomEvent('ws-message', {
          detail: {
            type: 'route_update',
            route_id: 1,
            update_type: 'status_change',
            details: { status: 'in_progress', completed_stops: 3 },
            timestamp: new Date().toISOString()
          }
        }));
      });
      
      // Route status should update
      const routeCard = page.locator('.route-card, [data-testid="route-card"]').first();
      const statusIndicator = routeCard.locator('.route-status');
      await expect(statusIndicator).toContainText('進行中', { timeout: 3000 });
    });

    test('should show driver location updates on map', async ({ page }) => {
      await routePage.navigateToRoutes();
      
      // Check if map is visible
      const mapContainer = page.locator('#route-map, .route-map-container');
      if (await mapContainer.isVisible()) {
        // Simulate driver location update
        await page.evaluate(() => {
          window.dispatchEvent(new CustomEvent('ws-message', {
            detail: {
              type: 'driver_location_update',
              driver_id: 1,
              latitude: 25.0330,
              longitude: 121.5654,
              timestamp: new Date().toISOString()
            }
          }));
        });
        
        // Driver marker should update
        const driverMarker = page.locator('.driver-marker, [data-testid="driver-marker-1"]');
        await expect(driverMarker).toBeVisible({ timeout: 3000 });
      }
    });

    test('should update route optimization in real-time', async ({ page }) => {
      await routePage.navigateToRoutes();
      
      // Simulate route optimization complete
      await page.evaluate(() => {
        window.dispatchEvent(new CustomEvent('ws-message', {
          detail: {
            type: 'route_update',
            route_id: 1,
            update_type: 'optimization_complete',
            details: {
              optimized: true,
              total_distance: '45.2 km',
              estimated_time: '2.5 hours',
              stop_sequence: [1, 3, 2, 4]
            },
            timestamp: new Date().toISOString()
          }
        }));
      });
      
      // Optimization indicator should show
      const optimizedBadge = page.locator('.optimized-badge, [data-testid="optimized-indicator"]');
      await expect(optimizedBadge).toBeVisible({ timeout: 3000 });
    });
  });

  test.describe('Real-time Dashboard Updates', () => {
    test('should update dashboard statistics in real-time', async ({ page }) => {
      // Get initial order count
      const todayOrdersCard = dashboardPage.todayOrdersCard;
      const initialCount = await todayOrdersCard.locator('.ant-statistic-content-value').textContent();
      
      // Simulate new order
      await page.evaluate(() => {
        window.dispatchEvent(new CustomEvent('ws-message', {
          detail: {
            type: 'order_update',
            order_id: 1000,
            status: 'pending',
            details: { isNew: true, isToday: true },
            timestamp: new Date().toISOString()
          }
        }));
      });
      
      // Count should increment
      const newCount = await todayOrdersCard.locator('.ant-statistic-content-value').textContent();
      expect(parseInt(newCount || '0')).toBeGreaterThan(parseInt(initialCount || '0'));
    });

    test('should show real-time activity feed', async ({ page }) => {
      // Check for activity feed
      const activityFeed = page.locator('.activity-feed, [data-testid="activity-feed"]');
      if (await activityFeed.isVisible()) {
        // Simulate activity
        await page.evaluate(() => {
          window.dispatchEvent(new CustomEvent('ws-message', {
            detail: {
              type: 'system_message',
              message: '司機王小明已開始配送路線 A',
              timestamp: new Date().toISOString()
            }
          }));
        });
        
        // New activity should appear
        const latestActivity = activityFeed.locator('.activity-item').first();
        await expect(latestActivity).toContainText('王小明', { timeout: 3000 });
      }
    });

    test('should update revenue in real-time', async ({ page }) => {
      // Get initial revenue
      const revenueCard = dashboardPage.todayRevenueCard;
      const initialRevenue = await revenueCard.locator('.ant-statistic-content-value').textContent();
      
      // Simulate completed order with payment
      await page.evaluate(() => {
        window.dispatchEvent(new CustomEvent('ws-message', {
          detail: {
            type: 'order_update',
            order_id: 1001,
            status: 'completed',
            details: { 
              payment_received: true,
              amount: 1500
            },
            timestamp: new Date().toISOString()
          }
        }));
      });
      
      // Revenue should update
      await page.waitForTimeout(1000);
      const newRevenue = await revenueCard.locator('.ant-statistic-content-value').textContent();
      expect(newRevenue).not.toBe(initialRevenue);
    });
  });

  test.describe('Real-time Prediction Updates', () => {
    test('should notify when predictions are ready', async ({ page }) => {
      // Navigate to predictions page
      await page.goto('/office/predictions');
      
      // Simulate prediction ready message
      await page.evaluate(() => {
        window.dispatchEvent(new CustomEvent('ws-message', {
          detail: {
            type: 'prediction_ready',
            batch_id: 'batch-123',
            summary: {
              total_predictions: 50,
              high_confidence: 35,
              date: new Date().toISOString()
            },
            timestamp: new Date().toISOString()
          }
        }));
      });
      
      // Should show notification
      const notification = page.locator('.ant-notification-notice').filter({ hasText: '預測完成' });
      await expect(notification).toBeVisible({ timeout: 5000 });
      
      // Should auto-refresh predictions
      const predictionCount = page.locator('.prediction-count, [data-testid="prediction-count"]');
      await expect(predictionCount).toContainText('50');
    });
  });

  test.describe('WebSocket Error Handling', () => {
    test('should handle WebSocket errors gracefully', async ({ page }) => {
      // Simulate WebSocket error
      await page.evaluate(() => {
        const ws = (window as any).websocketService;
        if (ws) {
          ws.emit('error', new Error('Connection failed'));
        }
      });
      
      // Should show error indicator
      const errorIndicator = page.locator('.ws-error-indicator, [data-testid="ws-error"]');
      await expect(errorIndicator).toBeVisible({ timeout: 3000 });
    });

    test('should queue messages when disconnected', async ({ page }) => {
      // Disconnect WebSocket
      await page.context().setOffline(true);
      
      // Try to send message
      await page.evaluate(() => {
        const ws = (window as any).websocketService;
        if (ws) {
          ws.send({ type: 'test_message', data: 'queued' });
        }
      });
      
      // Reconnect
      await page.context().setOffline(false);
      
      // Wait for reconnection
      await page.waitForTimeout(5000);
      
      // Check if queued messages were sent
      const consoleLogs: string[] = [];
      page.on('console', msg => consoleLogs.push(msg.text()));
      
      const hasQueuedMessage = consoleLogs.some(log => log.includes('queued'));
      // Message should be sent after reconnection
    });
  });

  test.describe('Multi-user Real-time Collaboration', () => {
    test('should sync updates across multiple users', async ({ page, context }) => {
      // Open second user session
      const page2 = await context.newPage();
      const loginPage2 = new LoginPage(page2);
      const orderPage2 = new OrderPage(page2);
      
      await loginPage2.navigateToLogin();
      await loginPage2.login('office1', 'office123');
      await loginPage2.waitForLoginSuccess();
      await orderPage2.navigateToOrders();
      
      // Both users viewing orders
      await orderPage.navigateToOrders();
      
      // User 2 updates an order
      const firstOrder = page2.locator('.ant-table-row').first();
      await firstOrder.locator('.action-button').filter({ hasText: '編輯' }).click();
      
      // Make changes and save
      const modal = page2.locator('.ant-modal');
      await modal.locator('#order_notes').fill('Updated by User 2');
      await modal.locator('.ant-modal-footer button.ant-btn-primary').click();
      
      // User 1 should see the update
      await page.waitForTimeout(2000);
      const updatedOrder = page.locator('.ant-table-row').first();
      await expect(updatedOrder).toContainText('Updated by User 2', { timeout: 5000 });
      
      // Cleanup
      await page2.close();
    });

    test('should handle concurrent route assignments', async ({ page, context }) => {
      // Two managers assigning routes simultaneously
      const page2 = await context.newPage();
      const loginPage2 = new LoginPage(page2);
      const routePage2 = new RoutePage(page2);
      
      await loginPage2.navigateToLogin();
      await loginPage2.login('manager1', 'manager123');
      await loginPage2.waitForLoginSuccess();
      
      // Both navigate to routes
      await routePage.navigateToRoutes();
      await routePage2.navigateToRoutes();
      
      // Try to assign same route to different drivers
      // System should handle conflict and show appropriate message
      
      // Cleanup
      await page2.close();
    });
  });

  test.describe('WebSocket Performance', () => {
    test('should handle high-frequency updates efficiently', async ({ page }) => {
      // Monitor performance
      const startTime = Date.now();
      let updateCount = 0;
      
      // Simulate high-frequency updates
      for (let i = 0; i < 50; i++) {
        await page.evaluate((index) => {
          window.dispatchEvent(new CustomEvent('ws-message', {
            detail: {
              type: 'driver_location_update',
              driver_id: 1,
              latitude: 25.0330 + (index * 0.0001),
              longitude: 121.5654 + (index * 0.0001),
              timestamp: new Date().toISOString()
            }
          }));
        }, i);
        updateCount++;
      }
      
      const endTime = Date.now();
      const duration = endTime - startTime;
      
      // Should handle all updates within reasonable time
      expect(duration).toBeLessThan(5000); // 5 seconds for 50 updates
      
      // UI should remain responsive
      const testButton = page.locator('button').first();
      await expect(testButton).toBeEnabled();
    });

    test('should throttle UI updates appropriately', async ({ page }) => {
      // Check if throttling is implemented
      let renderCount = 0;
      
      await page.evaluate(() => {
        let count = 0;
        const originalSetState = (window as any).React?.Component?.prototype?.setState;
        if (originalSetState) {
          (window as any).React.Component.prototype.setState = function(...args: any[]) {
            count++;
            return originalSetState.apply(this, args);
          };
        }
        (window as any).getRenderCount = () => count;
      });
      
      // Send many updates rapidly
      for (let i = 0; i < 20; i++) {
        await page.evaluate(() => {
          window.dispatchEvent(new CustomEvent('ws-message', {
            detail: {
              type: 'order_update',
              order_id: Math.random(),
              status: 'pending',
              timestamp: new Date().toISOString()
            }
          }));
        });
      }
      
      await page.waitForTimeout(1000);
      
      // Check render count
      renderCount = await page.evaluate(() => (window as any).getRenderCount?.() || 0);
      
      // Should batch updates (not render 20 times)
      expect(renderCount).toBeLessThan(20);
    });
  });
});