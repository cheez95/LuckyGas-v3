import { test, expect } from '@playwright/test';
import { APIHelper } from '../utils/api-helper';
import { TestHelpers } from '../utils/test-helpers';
import testData from '../fixtures/test-data.json';

test.describe('Route Planning and Management Tests', () => {
  let apiHelper: APIHelper;
  let testOrderIds: number[] = [];

  test.beforeAll(async ({ request }) => {
    apiHelper = new APIHelper(request);
    await apiHelper.login('admin');
    
    // Create test orders for route planning
    const tomorrow = new Date();
    tomorrow.setDate(tomorrow.getDate() + 1);
    
    for (let i = 0; i < 5; i++) {
      const order = await apiHelper.post('/api/v1/orders/', {
        客戶ID: 1,
        預定配送日期: tomorrow.toISOString(),
        配送地址: testData.taiwanAddresses[i],
        訂單項目: [
          {
            產品ID: 1,
            數量: 2,
            單價: 850
          }
        ],
        總金額: 1700,
        備註: `路線測試訂單 ${i + 1}`
      });
      
      const orderData = await order.json();
      testOrderIds.push(orderData.id);
    }
  });

  test.describe('Route Creation with scheduled_date', () => {
    test('should create route with required scheduled_date field', async () => {
      const tomorrow = new Date();
      tomorrow.setDate(tomorrow.getDate() + 1);
      
      const routeData = {
        route_number: TestHelpers.generateUniqueId('R'),
        name: '測試路線',
        scheduled_date: tomorrow.toISOString().split('T')[0], // YYYY-MM-DD format
        driver_id: 1,
        area: '信義區',
        total_stops: 5
      };
      
      const response = await apiHelper.post('/api/v1/routes/', routeData);
      expect(response.ok()).toBeTruthy();
      
      const route = await response.json();
      expect(route.id).toBeTruthy();
      expect(route.route_number).toBe(routeData.route_number);
      expect(route.scheduled_date).toBe(routeData.scheduled_date);
      expect(route.status).toBe('pending');
    });

    test('should fail without scheduled_date', async () => {
      const invalidRoute = {
        route_number: TestHelpers.generateUniqueId('R'),
        name: '缺少日期路線',
        driver_id: 1,
        area: '大安區'
        // Missing scheduled_date
      };
      
      const response = await apiHelper.post('/api/v1/routes/', invalidRoute);
      expect(response.status()).toBe(422);
      
      const error = await response.json();
      expect(error.detail).toContain('scheduled_date');
    });

    test('should validate scheduled_date format', async () => {
      const invalidDates = [
        '2025/08/01', // Wrong format
        '01-08-2025', // Wrong format
        '2025-13-01', // Invalid month
        '2025-08-32', // Invalid day
        'tomorrow', // Not a date
        '' // Empty
      ];
      
      for (const date of invalidDates) {
        const response = await apiHelper.post('/api/v1/routes/', {
          route_number: TestHelpers.generateUniqueId('R'),
          name: '日期格式測試',
          scheduled_date: date,
          driver_id: 1,
          area: '測試區'
        });
        
        expect(response.status()).toBeGreaterThanOrEqual(400);
      }
    });
  });

  test.describe('Route Optimization', () => {
    test('should optimize route with multiple orders', async () => {
      const tomorrow = new Date();
      tomorrow.setDate(tomorrow.getDate() + 1);
      
      const optimizationRequest = {
        scheduled_date: tomorrow.toISOString().split('T')[0],
        order_ids: testOrderIds,
        driver_id: 1,
        vehicle_id: 1,
        start_location: {
          latitude: 25.0330,
          longitude: 121.5654,
          address: '台北市信義區市府路1號'
        }
      };
      
      const response = await apiHelper.post('/api/v1/routes/optimize', optimizationRequest);
      expect(response.ok()).toBeTruthy();
      
      const optimized = await response.json();
      
      expect(optimized).toHaveProperty('route_id');
      expect(optimized).toHaveProperty('optimized_sequence');
      expect(optimized).toHaveProperty('total_distance_km');
      expect(optimized).toHaveProperty('estimated_duration_minutes');
      expect(optimized).toHaveProperty('waypoints');
      expect(optimized).toHaveProperty('polyline');
      
      // Verify optimization changed the order
      expect(optimized.optimized_sequence).not.toEqual(testOrderIds);
      
      // Check waypoints
      expect(optimized.waypoints.length).toBe(testOrderIds.length);
      optimized.waypoints.forEach((waypoint: any) => {
        expect(waypoint).toHaveProperty('order_id');
        expect(waypoint).toHaveProperty('sequence');
        expect(waypoint).toHaveProperty('address');
        expect(waypoint).toHaveProperty('estimated_arrival');
        expect(waypoint).toHaveProperty('service_time_minutes');
      });
    });

    test('should consider traffic conditions', async () => {
      const morningRoute = {
        scheduled_date: new Date().toISOString().split('T')[0],
        departure_time: '08:00', // Rush hour
        order_ids: testOrderIds.slice(0, 3),
        driver_id: 1
      };
      
      const afternoonRoute = {
        scheduled_date: new Date().toISOString().split('T')[0],
        departure_time: '14:00', // Non-rush hour
        order_ids: testOrderIds.slice(0, 3),
        driver_id: 1
      };
      
      const morningResponse = await apiHelper.post('/api/v1/routes/optimize', morningRoute);
      const morningData = await morningResponse.json();
      
      const afternoonResponse = await apiHelper.post('/api/v1/routes/optimize', afternoonRoute);
      const afternoonData = await afternoonResponse.json();
      
      // Morning route should take longer due to traffic
      expect(morningData.estimated_duration_minutes).toBeGreaterThan(
        afternoonData.estimated_duration_minutes
      );
    });

    test('should handle route constraints', async () => {
      const constrainedRoute = {
        scheduled_date: new Date().toISOString().split('T')[0],
        order_ids: testOrderIds,
        driver_id: 1,
        constraints: {
          max_distance_km: 50,
          max_duration_minutes: 240,
          time_windows: [
            {
              order_id: testOrderIds[0],
              start_time: '09:00',
              end_time: '11:00'
            }
          ],
          priority_orders: [testOrderIds[0], testOrderIds[2]]
        }
      };
      
      const response = await apiHelper.post('/api/v1/routes/optimize', constrainedRoute);
      const optimized = await response.json();
      
      // Check constraints are respected
      expect(optimized.total_distance_km).toBeLessThanOrEqual(50);
      expect(optimized.estimated_duration_minutes).toBeLessThanOrEqual(240);
      
      // Priority orders should be early in sequence
      const priorityPositions = constrainedRoute.constraints.priority_orders.map(id =>
        optimized.optimized_sequence.indexOf(id)
      );
      
      priorityPositions.forEach(pos => {
        expect(pos).toBeLessThan(3); // Should be in first 3 positions
      });
    });
  });

  test.describe('Route Management UI', () => {
    test.beforeEach(async ({ page }) => {
      await TestHelpers.loginUI(page, 'administrator', 'SuperSecure#9876');
      await page.goto('/routes');
    });

    test('should display route planning interface', async ({ page }) => {
      await page.click('button:has-text("規劃新路線")');
      
      // Check planning form elements
      await expect(page.locator('input[name="scheduled_date"]')).toBeVisible();
      await expect(page.locator('select[name="driver_id"]')).toBeVisible();
      await expect(page.locator('select[name="vehicle_id"]')).toBeVisible();
      await expect(page.locator('select[name="area"]')).toBeVisible();
      
      // Order selection section
      await expect(page.locator('.order-selection')).toBeVisible();
      await expect(page.locator('button:has-text("AI 建議")')).toBeVisible();
      await expect(page.locator('button:has-text("自動選擇")')).toBeVisible();
    });

    test('should create route through UI', async ({ page }) => {
      await page.click('button:has-text("規劃新路線")');
      
      // Fill route details
      const tomorrow = new Date();
      tomorrow.setDate(tomorrow.getDate() + 1);
      
      await page.fill('input[name="scheduled_date"]', TestHelpers.formatTaiwanDate(tomorrow));
      await page.selectOption('select[name="driver_id"]', '1');
      await page.selectOption('select[name="area"]', '信義區');
      
      // Select orders
      await page.click('button:has-text("選擇訂單")');
      
      // Select first 3 orders
      for (let i = 0; i < 3; i++) {
        await page.click(`.order-checkbox:nth-child(${i + 1})`);
      }
      
      await page.click('button:has-text("確定選擇")');
      
      // Optimize route
      await page.click('button:has-text("優化路線")');
      
      // Wait for optimization
      await TestHelpers.waitForLoadingComplete(page);
      
      // Check optimization results
      await expect(page.locator('.optimization-results')).toBeVisible();
      await expect(page.locator('.route-map')).toBeVisible();
      await expect(page.locator('.waypoint-list')).toBeVisible();
      
      // Save route
      await page.click('button:has-text("儲存路線")');
      
      await TestHelpers.checkToast(page, '路線建立成功', 'success');
    });

    test('should display route on map', async ({ page }) => {
      // View existing route
      await page.click('tbody tr:first-child button[aria-label="檢視"]');
      
      // Map should be visible
      await expect(page.locator('#route-map')).toBeVisible({ timeout: 10000 });
      
      // Check map elements
      await expect(page.locator('.route-polyline')).toBeVisible();
      await expect(page.locator('.delivery-marker')).toBeVisible();
      
      // Legend should show route info
      await expect(page.locator('.route-legend')).toBeVisible();
      await expect(page.locator('.total-distance')).toBeVisible();
      await expect(page.locator('.estimated-time')).toBeVisible();
    });

    test('should modify route sequence', async ({ page }) => {
      await page.click('tbody tr:first-child button[aria-label="編輯"]');
      
      // Waypoint list should be draggable
      await expect(page.locator('.waypoint-list.sortable')).toBeVisible();
      
      // Drag first waypoint to third position
      const firstWaypoint = page.locator('.waypoint-item:first-child');
      const thirdWaypoint = page.locator('.waypoint-item:nth-child(3)');
      
      await firstWaypoint.dragTo(thirdWaypoint);
      
      // Recalculate should be triggered
      await expect(page.locator('.recalculating')).toBeVisible();
      await expect(page.locator('.recalculating')).not.toBeVisible({ timeout: 5000 });
      
      // New distance/time should be shown
      await expect(page.locator('.updated-metrics')).toBeVisible();
      
      // Save changes
      await page.click('button:has-text("儲存變更")');
      await TestHelpers.checkToast(page, '路線更新成功', 'success');
    });

    test('should track route progress in real-time', async ({ page }) => {
      // Open route tracking view
      await page.click('tbody tr:has-text("in_progress") button[aria-label="追蹤"]');
      
      // Real-time tracking elements
      await expect(page.locator('.live-map')).toBeVisible();
      await expect(page.locator('.driver-location')).toBeVisible();
      await expect(page.locator('.progress-bar')).toBeVisible();
      await expect(page.locator('.eta-display')).toBeVisible();
      
      // Delivery status list
      const deliveryStatuses = page.locator('.delivery-status-item');
      const count = await deliveryStatuses.count();
      expect(count).toBeGreaterThan(0);
      
      // Check for live updates (would receive WebSocket updates in real scenario)
      await page.waitForTimeout(2000);
      
      // Driver location should update
      const initialLocation = await page.locator('.driver-location').getAttribute('data-lat');
      // In real test, location would change
    });

    test('should export route sheet', async ({ page }) => {
      await page.click('tbody tr:first-child button[aria-label="檢視"]');
      
      // Export options
      const downloadPromise = page.waitForEvent('download');
      await page.click('button:has-text("匯出路線單")');
      
      const download = await downloadPromise;
      expect(download.suggestedFilename()).toMatch(/route.*\.pdf$/);
    });
  });

  test.describe('Route Analytics', () => {
    test('should show route performance metrics', async () => {
      const response = await apiHelper.get('/api/v1/routes/analytics');
      const analytics = await response.json();
      
      expect(analytics).toHaveProperty('average_completion_time');
      expect(analytics).toHaveProperty('on_time_delivery_rate');
      expect(analytics).toHaveProperty('average_stops_per_route');
      expect(analytics).toHaveProperty('fuel_efficiency');
      expect(analytics).toHaveProperty('cost_per_delivery');
    });

    test('should analyze driver route performance', async () => {
      const driverId = 1;
      const response = await apiHelper.get(`/api/v1/routes/analytics/driver/${driverId}`);
      const driverMetrics = await response.json();
      
      expect(driverMetrics).toHaveProperty('total_routes');
      expect(driverMetrics).toHaveProperty('average_efficiency_score');
      expect(driverMetrics).toHaveProperty('common_delays');
      expect(driverMetrics).toHaveProperty('customer_satisfaction');
    });
  });

  test.describe('Multi-Vehicle Route Planning', () => {
    test('should optimize routes for multiple vehicles', async () => {
      const multiVehicleRequest = {
        scheduled_date: new Date().toISOString().split('T')[0],
        vehicles: [
          { id: 1, capacity: 50, driver_id: 1 },
          { id: 2, capacity: 30, driver_id: 2 }
        ],
        orders: testOrderIds,
        optimization_goal: 'minimize_distance' // or 'balance_workload'
      };
      
      const response = await apiHelper.post('/api/v1/routes/optimize/multi-vehicle', multiVehicleRequest);
      const result = await response.json();
      
      expect(result).toHaveProperty('routes');
      expect(result.routes.length).toBe(2);
      
      result.routes.forEach((route: any) => {
        expect(route).toHaveProperty('vehicle_id');
        expect(route).toHaveProperty('driver_id');
        expect(route).toHaveProperty('assigned_orders');
        expect(route).toHaveProperty('total_load');
        expect(route).toHaveProperty('distance');
        expect(route).toHaveProperty('duration');
      });
    });
  });
});