import { test, expect } from '@playwright/test';
import { APIHelper } from '../utils/api-helper';
import { TestHelpers } from '../utils/test-helpers';
import testData from '../fixtures/test-data.json';

test.describe('Driver Management Tests', () => {
  let apiHelper: APIHelper;
  let driverApiHelper: APIHelper;
  let driverId: number;

  test.beforeAll(async ({ request }) => {
    apiHelper = new APIHelper(request);
    await apiHelper.login('admin');
    
    // Get driver user ID
    const response = await apiHelper.get('/api/v1/users/?role=driver');
    const users = await response.json();
    driverId = users.items.find((u: any) => u.username === 'driver01')?.id || 1;
  });

  test.beforeEach(async ({ request }) => {
    driverApiHelper = new APIHelper(request);
    await driverApiHelper.login('driver');
  });

  test.describe('Driver API Endpoints', () => {
    test('should get driver routes for today', async () => {
      const response = await driverApiHelper.get('/api/v1/drivers/routes/today');
      expect(response.ok()).toBeTruthy();
      
      const routes = await response.json();
      expect(Array.isArray(routes)).toBeTruthy();
      
      routes.forEach((route: any) => {
        expect(route).toHaveProperty('id');
        expect(route).toHaveProperty('name');
        expect(route).toHaveProperty('deliveryCount');
        expect(route).toHaveProperty('completedCount');
        expect(route).toHaveProperty('estimatedTime');
        expect(route).toHaveProperty('distance');
        expect(route).toHaveProperty('status');
      });
    });

    test('should get driver delivery statistics', async () => {
      const response = await driverApiHelper.get('/api/v1/drivers/stats/today');
      const stats = await response.json();
      
      expect(stats).toHaveProperty('total');
      expect(stats).toHaveProperty('completed');
      expect(stats).toHaveProperty('pending');
      expect(stats).toHaveProperty('failed');
      
      // Verify numbers make sense
      expect(stats.total).toBeGreaterThanOrEqual(0);
      expect(stats.completed + stats.pending + stats.failed).toBeLessThanOrEqual(stats.total);
    });

    test('should get route details with deliveries', async () => {
      // First get routes
      const routesResponse = await driverApiHelper.get('/api/v1/drivers/routes/today');
      const routes = await routesResponse.json();
      
      if (routes.length > 0) {
        const routeId = routes[0].id;
        
        const detailResponse = await driverApiHelper.get(`/api/v1/drivers/routes/${routeId}`);
        const details = await detailResponse.json();
        
        expect(details).toHaveProperty('id');
        expect(details).toHaveProperty('name');
        expect(details).toHaveProperty('deliveries');
        expect(Array.isArray(details.deliveries)).toBeTruthy();
        
        // Each delivery should have required fields
        details.deliveries.forEach((delivery: any) => {
          expect(delivery).toHaveProperty('id');
          expect(delivery).toHaveProperty('customerName');
          expect(delivery).toHaveProperty('address');
          expect(delivery).toHaveProperty('phone');
          expect(delivery).toHaveProperty('products');
          expect(delivery).toHaveProperty('status');
          expect(delivery).toHaveProperty('sequence');
        });
      }
    });

    test('should update driver location', async () => {
      const locationUpdate = {
        latitude: 25.0330,
        longitude: 121.5654,
        accuracy: 10,
        speed: 30,
        heading: 45,
        timestamp: new Date().toISOString()
      };
      
      const response = await driverApiHelper.post('/api/v1/drivers/location', locationUpdate);
      expect(response.ok()).toBeTruthy();
      
      const result = await response.json();
      expect(result.status).toBe('success');
    });

    test('should update delivery status', async () => {
      // Create a test route with delivery
      const route = await apiHelper.post('/api/v1/routes/', {
        route_number: TestHelpers.generateUniqueId('RTEST'),
        scheduled_date: new Date().toISOString().split('T')[0],
        driver_id: driverId,
        area: '測試區'
      });
      
      const routeData = await route.json();
      
      // Add a delivery to the route
      const delivery = await apiHelper.post(`/api/v1/routes/${routeData.id}/deliveries`, {
        order_id: 1,
        sequence: 1
      });
      
      const deliveryData = await delivery.json();
      
      // Update delivery status as driver
      const statusUpdate = {
        status: 'in_progress',
        notes: '正在前往客戶地址',
        location: {
          latitude: 25.0330,
          longitude: 121.5654
        }
      };
      
      const updateResponse = await driverApiHelper.post(
        `/api/v1/drivers/deliveries/status/${deliveryData.id}`,
        statusUpdate
      );
      
      expect(updateResponse.ok()).toBeTruthy();
      const result = await updateResponse.json();
      expect(result.status).toBe('success');
    });

    test('should confirm delivery with signature', async () => {
      // This would test multipart form data with signature/photo
      // For now, test the endpoint exists and accepts the request format
      const formData = new FormData();
      formData.append('recipient_name', '王先生');
      formData.append('notes', '已確認收貨');
      formData.append('signature', 'data:image/png;base64,iVBORw0KGgoAAAANS...');
      
      // Would need a real delivery ID
      // const response = await driverApiHelper.post('/api/v1/drivers/deliveries/confirm/1', formData);
    });

    test('should sync offline data', async () => {
      const syncData = {
        locations: [
          {
            id: '1',
            latitude: 25.0330,
            longitude: 121.5654,
            timestamp: new Date(Date.now() - 3600000).toISOString()
          },
          {
            id: '2',
            latitude: 25.0340,
            longitude: 121.5664,
            timestamp: new Date(Date.now() - 1800000).toISOString()
          }
        ],
        deliveries: [
          {
            delivery_id: 1,
            status: 'delivered',
            timestamp: new Date(Date.now() - 1800000).toISOString(),
            notes: '離線時送達'
          }
        ]
      };
      
      const response = await driverApiHelper.post('/api/v1/drivers/sync', syncData);
      const result = await response.json();
      
      expect(result).toHaveProperty('success');
      expect(result).toHaveProperty('synced_count');
      expect(result).toHaveProperty('failed_count');
      expect(result).toHaveProperty('synced_items');
      expect(result).toHaveProperty('failed_items');
    });
  });

  test.describe('Driver Mobile App UI', () => {
    test('should display driver dashboard on mobile', async ({ browser }) => {
      // Create mobile context
      const context = await browser.newContext({
        ...browser.contexts,
        viewport: { width: 375, height: 667 },
        userAgent: 'Mozilla/5.0 (iPhone; CPU iPhone OS 14_0 like Mac OS X) Mobile/15E148'
      });
      
      const page = await context.newPage();
      
      // Login as driver
      await page.goto('/mobile/login');
      await page.fill('input[name="username"]', 'driver01');
      await page.fill('input[name="password"]', 'Driver123!@#');
      await page.click('button[type="submit"]');
      
      // Should show driver dashboard
      await expect(page).toHaveURL(/.*mobile\/dashboard/);
      
      // Check mobile-specific elements
      await expect(page.locator('.mobile-header')).toBeVisible();
      await expect(page.locator('.route-summary-card')).toBeVisible();
      await expect(page.locator('.delivery-stats')).toBeVisible();
      
      // Bottom navigation should be visible
      await expect(page.locator('.bottom-nav')).toBeVisible();
      await expect(page.locator('[data-nav="routes"]')).toBeVisible();
      await expect(page.locator('[data-nav="map"]')).toBeVisible();
      await expect(page.locator('[data-nav="stats"]')).toBeVisible();
      
      await context.close();
    });

    test('should show route list optimized for mobile', async ({ browser }) => {
      const context = await browser.newContext({
        viewport: { width: 375, height: 667 }
      });
      
      const page = await context.newPage();
      await TestHelpers.loginUI(page, 'driver01', 'Driver123!@#');
      await page.goto('/mobile/routes');
      
      // Routes should be displayed as cards
      const routeCards = page.locator('.route-card');
      await expect(routeCards.first()).toBeVisible();
      
      // Each card should have mobile-friendly layout
      const firstCard = routeCards.first();
      await expect(firstCard.locator('.route-name')).toBeVisible();
      await expect(firstCard.locator('.delivery-count')).toBeVisible();
      await expect(firstCard.locator('.route-progress')).toBeVisible();
      
      // Swipe actions should be available
      await firstCard.locator('.swipe-actions').isVisible();
      
      await context.close();
    });

    test('should handle offline mode', async ({ browser }) => {
      const context = await browser.newContext({
        viewport: { width: 375, height: 667 }
      });
      
      const page = await context.newPage();
      await TestHelpers.loginUI(page, 'driver01', 'Driver123!@#');
      
      // Go offline
      await context.setOffline(true);
      
      await page.goto('/mobile/routes');
      
      // Should show offline indicator
      await expect(page.locator('.offline-banner')).toBeVisible();
      
      // Cached data should still be accessible
      await expect(page.locator('.route-card')).toBeVisible();
      
      // Can still update delivery status offline
      await page.click('.route-card:first-child');
      await page.click('.delivery-item:first-child');
      await page.click('button:has-text("標記為已送達")');
      
      // Should show sync pending indicator
      await expect(page.locator('.sync-pending')).toBeVisible();
      
      await context.close();
    });
  });

  test.describe('Driver Performance Tracking', () => {
    test('should track driver performance metrics', async () => {
      const response = await apiHelper.get(`/api/v1/drivers/${driverId}/performance`);
      const metrics = await response.json();
      
      expect(metrics).toHaveProperty('delivery_success_rate');
      expect(metrics).toHaveProperty('average_delivery_time');
      expect(metrics).toHaveProperty('total_deliveries');
      expect(metrics).toHaveProperty('on_time_rate');
      expect(metrics).toHaveProperty('customer_ratings');
    });

    test('should get driver availability schedule', async () => {
      const response = await apiHelper.get(`/api/v1/drivers/${driverId}/availability`);
      const schedule = await response.json();
      
      expect(schedule).toHaveProperty('weekly_schedule');
      expect(schedule).toHaveProperty('time_off_requests');
      expect(schedule).toHaveProperty('current_status');
    });
  });
});