import { test, expect } from '@playwright/test';
import { LoginPage } from './pages/LoginPage';
import { RoutePage } from './pages/RoutePage';
import { DashboardPage } from './pages/DashboardPage';

test.describe('Route Optimization Validation', () => {
  let loginPage: LoginPage;
  let routePage: RoutePage;
  let dashboardPage: DashboardPage;

  test.beforeEach(async ({ page }) => {
    loginPage = new LoginPage(page);
    routePage = new RoutePage(page);
    dashboardPage = new DashboardPage(page);
    
    // Login as admin
    await loginPage.navigateToLogin();
    await loginPage.login('admin', 'admin123');
    await loginPage.waitForLoginSuccess();
  });

  test.describe('Constraint Validation', () => {
    test('should optimize delivery routes', async ({ page }) => {
      await routePage.navigateToRoutes();
      
      // Create route with time-sensitive deliveries
      await routePage.clickCreateRoute();
      await routePage.fillRouteForm({
        name: 'Time Window Test Route',
        date: new Date().toISOString().split('T')[0],
        driverId: 'driver1',
        vehicleId: 'vehicle1',
        startTime: '08:00'
      });
      await routePage.submitRouteForm();
      
      // Add customers with different time windows
      const timeWindowCustomers = [
        { name: '早晨客戶', timeWindow: '08:00-10:00' },
        { name: '下午客戶', timeWindow: '14:00-16:00' },
        { name: '中午客戶', timeWindow: '11:00-13:00' }
      ];
      
      for (const customer of timeWindowCustomers) {
        await routePage.addStopToRoute(customer.name);
      }
      
      // Optimize route
      await routePage.clickOptimizeRoute();
      
      // Verify stop order respects time windows
      const stopItems = page.locator('.stop-item');
      const stopCount = await stopItems.count();
      
      const stopOrder = [];
      for (let i = 0; i < stopCount; i++) {
        const stopName = await stopItems.nth(i).locator('.stop-customer-name').textContent();
        stopOrder.push(stopName);
      }
      
      // Morning customer should be first
      expect(stopOrder[0]).toContain('早晨客戶');
      // Afternoon customer should be last
      expect(stopOrder[stopOrder.length - 1]).toContain('下午客戶');
    });

  test('should optimize delivery routes - 2', async ({ page }) => {
      await routePage.navigateToRoutes();
      
      // Create route
      await routePage.clickCreateRoute();
      await routePage.fillRouteForm({
        name: 'Capacity Test Route',
        date: new Date().toISOString().split('T')[0],
        driverId: 'driver1',
        vehicleId: 'small_truck', // Limited capacity
        startTime: '08:00'
      });
      await routePage.submitRouteForm();
      
      // Try to add more orders than vehicle capacity
      const largeOrders = 15; // Exceeds small truck capacity
      for (let i = 0; i < largeOrders; i++) {
        try {
          await routePage.addStopToRoute(`Customer ${i + 1}`);
        } catch (e) {
          // Expected to fail when capacity exceeded
          break;
        }
      }
      
      // Check capacity warning
      const capacityWarning = page.locator('.capacity-warning');
      if (await capacityWarning.isVisible()) {
        const warningText = await capacityWarning.textContent();
        expect(warningText).toContain('車輛容量');
      }
      
      // Verify stops don't exceed capacity
      const stopCount = await routePage.getStopCount();
      expect(stopCount).toBeLessThanOrEqual(12); // Small truck capacity
    });

  test('should optimize delivery routes - 3', async ({ page }) => {
      await routePage.navigateToRoutes();
      
      // Create route with many stops
      await routePage.clickCreateRoute();
      await routePage.fillRouteForm({
        name: 'Working Hours Test',
        date: new Date().toISOString().split('T')[0],
        driverId: 'driver1',
        vehicleId: 'vehicle1',
        startTime: '08:00'
      });
      await routePage.submitRouteForm();
      
      // Add many stops to exceed working hours
      for (let i = 0; i < 20; i++) {
        await routePage.addStopToRoute(`Customer ${i + 1}`);
      }
      
      // Optimize route
      await routePage.clickOptimizeRoute();
      
      // Check estimated duration
      const estimatedDuration = await routePage.getEstimatedDuration();
      const durationHours = parseInt(estimatedDuration.match(/\d+/)?.[0] || '0') / 60;
      
      // Should not exceed 8 hours
      expect(durationHours).toBeLessThanOrEqual(8);
      
      // Check if route was split or warning shown
      const workingHoursWarning = page.locator('.working-hours-warning');
      if (await workingHoursWarning.isVisible()) {
        const warningText = await workingHoursWarning.textContent();
        expect(warningText).toContain('工作時間');
      }
    });
  });

  test.describe('Optimization Algorithm Effectiveness', () => {
    test('should optimize delivery routes', async ({ page }) => {
      await routePage.navigateToRoutes();
      
      // Create unoptimized route
      await routePage.clickCreateRoute();
      await routePage.fillRouteForm({
        name: 'Distance Optimization Test',
        date: new Date().toISOString().split('T')[0],
        driverId: 'driver1',
        vehicleId: 'vehicle1'
      });
      await routePage.submitRouteForm();
      
      // Add stops in random order
      const customers = [
        '北區客戶 A', '南區客戶 B', '北區客戶 C', 
        '南區客戶 D', '中區客戶 E'
      ];
      
      for (const customer of customers) {
        await routePage.addStopToRoute(customer);
      }
      
      // Get initial distance
      const initialDistance = await routePage.getTotalDistance();
      const initialDistanceKm = parseFloat(initialDistance.match(/[\d.]+/)?.[0] || '0');
      
      // Optimize route
      await routePage.clickOptimizeRoute();
      
      // Get optimized distance
      const optimizedDistance = await routePage.getTotalDistance();
      const optimizedDistanceKm = parseFloat(optimizedDistance.match(/[\d.]+/)?.[0] || '0');
      
      // Distance should be reduced
      expect(optimizedDistanceKm).toBeLessThan(initialDistanceKm);
      
      // Check stop order is logical (grouped by area)
      const stopItems = page.locator('.stop-item');
      const stopOrder = [];
      for (let i = 0; i < await stopItems.count(); i++) {
        const stopName = await stopItems.nth(i).locator('.stop-customer-name').textContent();
        stopOrder.push(stopName || '');
      }
      
      // Verify area grouping (north stops together, south stops together)
      const northIndices = stopOrder
        .map((name, idx) => name.includes('北區') ? idx : -1)
        .filter(idx => idx !== -1);
      
      const southIndices = stopOrder
        .map((name, idx) => name.includes('南區') ? idx : -1)
        .filter(idx => idx !== -1);
      
      // Check if indices are consecutive (grouped)
      const isNorthGrouped = northIndices.every((val, idx, arr) => 
        idx === 0 || val === arr[idx - 1] + 1
      );
      const isSouthGrouped = southIndices.every((val, idx, arr) => 
        idx === 0 || val === arr[idx - 1] + 1
      );
      
      expect(isNorthGrouped || isSouthGrouped).toBe(true);
    });

  test('should optimize delivery routes - 2', async ({ page }) => {
      await routePage.navigateToRoutes();
      
      // Select date with many orders
      const tomorrow = new Date();
      tomorrow.setDate(tomorrow.getDate() + 1);
      await routePage.selectDate(tomorrow.toISOString().split('T')[0]);
      
      // Create routes from predictions (bulk operation)
      const createFromPredictionsBtn = page.locator('button').filter({ hasText: '從預測建立路線' });
      if (await createFromPredictionsBtn.isVisible()) {
        await createFromPredictionsBtn.click();
        await page.waitForTimeout(3000); // Wait for route creation
      }
      
      // Get all routes
      const routeCount = await routePage.getRouteCount();
      expect(routeCount).toBeGreaterThan(0);
      
      // Check route balance
      const routeStops = [];
      const routeDistances = [];
      
      for (let i = 0; i < routeCount; i++) {
        await routePage.selectRoute(i);
        const stops = await routePage.getStopCount();
        const distance = await routePage.getTotalDistance();
        
        routeStops.push(stops);
        routeDistances.push(parseFloat(distance.match(/[\d.]+/)?.[0] || '0'));
      }
      
      // Calculate variance
      const avgStops = routeStops.reduce((a, b) => a + b, 0) / routeStops.length;
      const stopVariance = routeStops.reduce((sum, stops) => 
        sum + Math.pow(stops - avgStops, 2), 0
      ) / routeStops.length;
      
      // Routes should be relatively balanced (low variance)
      expect(stopVariance).toBeLessThan(10); // Threshold for acceptable variance
    });

  test('should optimize delivery routes - 3', async ({ page }) => {
      await routePage.navigateToRoutes();
      
      // Create route
      await routePage.clickCreateRoute();
      await routePage.fillRouteForm({
        name: 'Priority Test Route',
        date: new Date().toISOString().split('T')[0],
        driverId: 'driver1',
        vehicleId: 'vehicle1'
      });
      await routePage.submitRouteForm();
      
      // Add mix of priority and regular orders
      const orders = [
        { name: '一般客戶 1', priority: 'normal' },
        { name: '緊急客戶 A', priority: 'urgent' },
        { name: '一般客戶 2', priority: 'normal' },
        { name: '優先客戶 B', priority: 'high' },
        { name: '一般客戶 3', priority: 'normal' }
      ];
      
      for (const order of orders) {
        await routePage.addStopToRoute(order.name);
        // Mark priority if applicable
        if (order.priority !== 'normal') {
          const lastStop = page.locator('.stop-item').last();
          const prioritySelect = lastStop.locator('.priority-select');
          if (await prioritySelect.isVisible()) {
            await prioritySelect.selectOption(order.priority);
          }
        }
      }
      
      // Optimize route
      await routePage.clickOptimizeRoute();
      
      // Verify priority orders are scheduled early
      const stopItems = page.locator('.stop-item');
      const firstStops = [];
      
      for (let i = 0; i < Math.min(2, await stopItems.count()); i++) {
        const stopName = await stopItems.nth(i).locator('.stop-customer-name').textContent();
        firstStops.push(stopName || '');
      }
      
      // Priority customers should be in first stops
      const hasPriorityFirst = firstStops.some(name => 
        name.includes('緊急') || name.includes('優先')
      );
      expect(hasPriorityFirst).toBe(true);
    });
  });

  test.describe('Edge Cases and Error Handling', () => {
    test('should optimize delivery routes', async ({ page }) => {
      await routePage.navigateToRoutes();
      
      // Create empty route
      await routePage.clickCreateRoute();
      await routePage.fillRouteForm({
        name: 'Empty Route Test',
        date: new Date().toISOString().split('T')[0],
        driverId: 'driver1',
        vehicleId: 'vehicle1'
      });
      await routePage.submitRouteForm();
      
      // Try to optimize empty route
      await routePage.clickOptimizeRoute();
      
      // Should show appropriate message
      const emptyRouteMessage = page.locator('.ant-message-notice');
      await expect(emptyRouteMessage).toContainText('沒有站點');
    });

  test('should optimize delivery routes - 2', async ({ page }) => {
      await routePage.navigateToRoutes();
      
      // Create route with single stop
      await routePage.clickCreateRoute();
      await routePage.fillRouteForm({
        name: 'Single Stop Test',
        date: new Date().toISOString().split('T')[0],
        driverId: 'driver1',
        vehicleId: 'vehicle1'
      });
      await routePage.submitRouteForm();
      
      // Add single stop
      await routePage.addStopToRoute('Single Customer');
      
      // Optimize route
      await routePage.clickOptimizeRoute();
      
      // Should complete without error
      const successMessage = page.locator('.ant-message-notice');
      await expect(successMessage).toContainText('路線優化完成');
      
      // Distance should be calculated
      const distance = await routePage.getTotalDistance();
      expect(distance).toMatch(/\d+\.?\d*\s*km/);
    });

  test('should optimize delivery routes - 3', async ({ page }) => {
      await routePage.navigateToRoutes();
      
      // Create route
      await routePage.clickCreateRoute();
      await routePage.fillRouteForm({
        name: 'Invalid Address Test',
        date: new Date().toISOString().split('T')[0],
        driverId: 'driver1',
        vehicleId: 'vehicle1'
      });
      await routePage.submitRouteForm();
      
      // Add stops including invalid addresses
      const customers = [
        '正常客戶 1',
        'Invalid Address 123xyz', // Invalid
        '正常客戶 2'
      ];
      
      for (const customer of customers) {
        try {
          await routePage.addStopToRoute(customer);
        } catch (e) {
          // Expected for invalid address
        }
      }
      
      // Optimize route
      await routePage.clickOptimizeRoute();
      
      // Check for geocoding warnings
      const warningMessage = page.locator('.geocoding-warning');
      if (await warningMessage.isVisible()) {
        const warningText = await warningMessage.textContent();
        expect(warningText).toContain('地址');
      }
      
      // Route should still optimize with valid stops
      const stopCount = await routePage.getStopCount();
      expect(stopCount).toBeGreaterThan(0);
    });

  test('should optimize delivery routes - 4', async ({ page }) => {
      await routePage.navigateToRoutes();
      
      // Create route with stops
      await routePage.clickCreateRoute();
      await routePage.fillRouteForm({
        name: 'Network Failure Test',
        date: new Date().toISOString().split('T')[0],
        driverId: 'driver1',
        vehicleId: 'vehicle1'
      });
      await routePage.submitRouteForm();
      
      // Add stops
      for (let i = 0; i < 3; i++) {
        await routePage.addStopToRoute(`Customer ${i + 1}`);
      }
      
      // Simulate network failure
      await page.route('**/api/v1/routes/optimize', route => route.abort());
      
      // Try to optimize
      await routePage.clickOptimizeRoute();
      
      // Should show error message
      const errorMessage = page.locator('.ant-message-error');
      await expect(errorMessage).toBeVisible();
      await expect(errorMessage).toContainText('網路');
      
      // Route should remain unchanged
      const stopCount = await routePage.getStopCount();
      expect(stopCount).toBe(3);
    });
  });

  test.describe('Business Rules Validation', () => {
    test('should optimize delivery routes', async ({ page }) => {
      await routePage.navigateToRoutes();
      
      // Create route
      await routePage.clickCreateRoute();
      await routePage.fillRouteForm({
        name: 'Delivery Interval Test',
        date: new Date().toISOString().split('T')[0],
        driverId: 'driver1',
        vehicleId: 'vehicle1'
      });
      await routePage.submitRouteForm();
      
      // Add multiple stops
      for (let i = 0; i < 5; i++) {
        await routePage.addStopToRoute(`Customer ${i + 1}`);
      }
      
      // Optimize route
      await routePage.clickOptimizeRoute();
      
      // Check estimated arrival times
      const stopItems = page.locator('.stop-item');
      const arrivalTimes = [];
      
      for (let i = 0; i < await stopItems.count(); i++) {
        const arrivalTime = await stopItems.nth(i).locator('.estimated-arrival').textContent();
        if (arrivalTime) {
          arrivalTimes.push(arrivalTime);
        }
      }
      
      // Verify minimum interval between stops (e.g., 15 minutes)
      for (let i = 1; i < arrivalTimes.length; i++) {
        const prevTime = new Date(`2024-01-01 ${arrivalTimes[i - 1]}`);
        const currTime = new Date(`2024-01-01 ${arrivalTimes[i]}`);
        const intervalMinutes = (currTime.getTime() - prevTime.getTime()) / (1000 * 60);
        
        expect(intervalMinutes).toBeGreaterThanOrEqual(15);
      }
    });

  test('should optimize delivery routes - 2', async ({ page }) => {
      await routePage.navigateToRoutes();
      
      // Create route
      await routePage.clickCreateRoute();
      await routePage.fillRouteForm({
        name: 'Customer Preference Test',
        date: new Date().toISOString().split('T')[0],
        driverId: 'driver1',
        vehicleId: 'vehicle1'
      });
      await routePage.submitRouteForm();
      
      // Add customers with preferences
      const customersWithPrefs = [
        { name: '避免尖峰時段客戶', avoidRushHour: true },
        { name: '指定司機客戶', preferredDriver: 'driver1' },
        { name: '一般客戶', noPreference: true }
      ];
      
      for (const customer of customersWithPrefs) {
        await routePage.addStopToRoute(customer.name);
      }
      
      // Optimize route
      await routePage.clickOptimizeRoute();
      
      // Verify preferences are respected
      const stopItems = page.locator('.stop-item');
      
      // Check avoid rush hour customer
      const rushHourStop = stopItems.filter({ hasText: '避免尖峰時段客戶' });
      if (await rushHourStop.count() > 0) {
        const arrivalTime = await rushHourStop.locator('.estimated-arrival').textContent();
        const hour = parseInt(arrivalTime?.split(':')[0] || '0');
        
        // Should not be during rush hours (7-9 AM or 5-7 PM)
        const isRushHour = (hour >= 7 && hour <= 9) || (hour >= 17 && hour <= 19);
        expect(isRushHour).toBe(false);
      }
    });

  test('should optimize delivery routes - 3', async ({ page }) => {
      await routePage.navigateToRoutes();
      
      // Select existing optimized route
      const routeCards = page.locator('.route-card');
      if (await routeCards.count() > 0) {
        await routeCards.first().click();
      } else {
        // Create and optimize a route first
        await routePage.clickCreateRoute();
        await routePage.fillRouteForm({
          name: 'Modification Test',
          date: new Date().toISOString().split('T')[0],
          driverId: 'driver1',
          vehicleId: 'vehicle1'
        });
        await routePage.submitRouteForm();
        
        for (let i = 0; i < 3; i++) {
          await routePage.addStopToRoute(`Customer ${i + 1}`);
        }
        
        await routePage.clickOptimizeRoute();
      }
      
      // Get initial metrics
      const initialDistance = await routePage.getTotalDistance();
      const initialDuration = await routePage.getEstimatedDuration();
      
      // Try to manually reorder stops
      await routePage.reorderStop(0, 2); // Move first stop to last
      
      // Check if reoptimization is suggested
      const reoptimizePrompt = page.locator('.reoptimize-prompt');
      if (await reoptimizePrompt.isVisible()) {
        expect(await reoptimizePrompt.textContent()).toContain('重新優化');
      }
      
      // Get new metrics
      const newDistance = await routePage.getTotalDistance();
      const newDuration = await routePage.getEstimatedDuration();
      
      // Manual changes might increase distance/duration
      const initialDistanceKm = parseFloat(initialDistance.match(/[\d.]+/)?.[0] || '0');
      const newDistanceKm = parseFloat(newDistance.match(/[\d.]+/)?.[0] || '0');
      
      // System should update metrics after manual changes
      expect(newDistanceKm).toBeGreaterThan(0);
    });
  });

  test.describe('Performance and Scalability', () => {
    test('should optimize delivery routes', async ({ page }) => {
      await routePage.navigateToRoutes();
      
      // Create route with many stops
      await routePage.clickCreateRoute();
      await routePage.fillRouteForm({
        name: 'Large Route Test',
        date: new Date().toISOString().split('T')[0],
        driverId: 'driver1',
        vehicleId: 'large_truck' // Higher capacity
      });
      await routePage.submitRouteForm();
      
      // Add 20+ stops
      const startTime = Date.now();
      for (let i = 0; i < 20; i++) {
        await routePage.addStopToRoute(`Customer ${i + 1}`);
      }
      
      // Optimize route
      await routePage.clickOptimizeRoute();
      const optimizationTime = Date.now() - startTime;
      
      // Should complete within reasonable time (< 30 seconds)
      expect(optimizationTime).toBeLessThan(30000);
      
      // All stops should be optimized
      const stopCount = await routePage.getStopCount();
      expect(stopCount).toBe(20);
      
      // Should have valid metrics
      const distance = await routePage.getTotalDistance();
      const duration = await routePage.getEstimatedDuration();
      
      expect(distance).toMatch(/\d+\.?\d*\s*km/);
      expect(duration).toMatch(/\d+/);
    });

    test('should respect time window constraints during optimization', async ({ page: _page, context }) => {
      await routePage.navigateToRoutes();
      
      // Create multiple routes
      const routeNames = ['Route A', 'Route B', 'Route C'];
      
      for (const routeName of routeNames) {
        await routePage.clickCreateRoute();
        await routePage.fillRouteForm({
          name: routeName,
          date: new Date().toISOString().split('T')[0],
          driverId: `driver${routeNames.indexOf(routeName) + 1}`,
          vehicleId: 'vehicle1'
        });
        await routePage.submitRouteForm();
        
        // Add stops
        for (let i = 0; i < 3; i++) {
          await routePage.addStopToRoute(`${routeName} Customer ${i + 1}`);
        }
      }
      
      // Open multiple tabs and optimize concurrently
      const pages = [page];
      for (let i = 1; i < routeNames.length; i++) {
        const newPage = await context.newPage();
        const newLoginPage = new LoginPage(newPage);
        const newRoutePage = new RoutePage(newPage);
        
        await newLoginPage.navigateToLogin();
        await newLoginPage.login('admin', 'admin123');
        await newLoginPage.waitForLoginSuccess();
        await newRoutePage.navigateToRoutes();
        
        pages.push(newPage);
      }
      
      // Start optimizations concurrently
      const optimizationPromises = pages.map(async (p, index) => {
        const pageRoutePage = new RoutePage(p);
        await pageRoutePage.selectRoute(index);
        await pageRoutePage.clickOptimizeRoute();
      });
      
      // Wait for all to complete
      await Promise.all(optimizationPromises);
      
      // Verify all routes were optimized
      for (let i = 0; i < pages.length; i++) {
        const pageRoutePage = new RoutePage(pages[i]);
        const distance = await pageRoutePage.getTotalDistance();
        expect(distance).toMatch(/\d+\.?\d*\s*km/);
      }
      
      // Cleanup
      for (let i = 1; i < pages.length; i++) {
        await pages[i].close();
      }
    });
  });
});