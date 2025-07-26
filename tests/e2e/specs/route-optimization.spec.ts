import { test, expect } from '../fixtures/test-helpers';
import { LoginPage } from '../pages/LoginPage';
import { DashboardPage } from '../pages/DashboardPage';
import { RoutePage } from '../pages/RoutePage';
import { TestUsers, TestRoutes, TestOrders } from '../fixtures/test-data';

test.describe('Route Optimization E2E Tests', () => {
  let loginPage: LoginPage;
  let dashboardPage: DashboardPage;
  let routePage: RoutePage;

  test.beforeEach(async ({ page }) => {
    loginPage = new LoginPage(page);
    dashboardPage = new DashboardPage(page);
    routePage = new RoutePage(page);
    
    // Login as manager who has route planning permissions
    await loginPage.goto();
    await loginPage.login(TestUsers.manager.email, TestUsers.manager.password);
    await dashboardPage.waitForPageLoad();
  });

  test.describe('AI-Powered Route Generation', () => {
    test('should generate optimized routes for daily deliveries', async ({ page }) => {
      await dashboardPage.navigateTo('routes');
      await routePage.waitForPageLoad();
      
      // Select date for route planning
      const tomorrow = new Date(Date.now() + 24 * 60 * 60 * 1000);
      await routePage.selectPlanningDate(tomorrow);
      
      // Check unassigned orders
      const unassignedCount = await routePage.getUnassignedOrderCount();
      expect(unassignedCount).toBeGreaterThan(0);
      
      // Configure optimization parameters
      await routePage.configureOptimization({
        maxDeliveriesPerRoute: 25,
        maxDistancePerRoute: 50, // km
        maxDurationPerRoute: 8 * 60, // 8 hours in minutes
        prioritizeUrgent: true,
        balanceWorkload: true,
        vehicleTypes: ['motorcycle', 'truck'],
        startTime: '08:00',
        endTime: '17:00'
      });
      
      // Generate routes using AI
      await routePage.generateOptimizedRoutes();
      
      // Wait for optimization to complete
      await routePage.waitForOptimizationComplete();
      
      // Verify routes generated
      const generatedRoutes = await routePage.getGeneratedRouteCount();
      expect(generatedRoutes).toBeGreaterThan(0);
      
      // Check optimization metrics
      const metrics = await routePage.getOptimizationMetrics();
      expect(metrics.totalDistance).toBeGreaterThan(0);
      expect(metrics.totalDuration).toBeGreaterThan(0);
      expect(metrics.averageUtilization).toBeGreaterThan(70); // 70% vehicle utilization
      expect(metrics.unassignedOrders).toBe(0); // All orders should be assigned
    });

    test('should respect delivery time windows', async ({ page }) => {
      await dashboardPage.navigateTo('routes');
      
      // Create orders with specific time windows
      const ordersWithTimeWindows = [
        { customer: '早餐店', timeWindow: '06:00-08:00' },
        { customer: '餐廳午餐', timeWindow: '11:00-13:00' },
        { customer: '晚餐餐廳', timeWindow: '17:00-19:00' }
      ];
      
      // Add test orders
      for (const order of ordersWithTimeWindows) {
        await routePage.addTestOrder({
          customerName: order.customer,
          deliveryTimeWindow: order.timeWindow,
          priority: 'high'
        });
      }
      
      // Generate routes
      await routePage.generateOptimizedRoutes();
      await routePage.waitForOptimizationComplete();
      
      // Verify time windows are respected
      const routes = await routePage.getGeneratedRoutes();
      
      for (const route of routes) {
        const stops = await routePage.getRouteStops(route.id);
        
        for (const stop of stops) {
          if (stop.customerName.includes('早餐店')) {
            expect(stop.estimatedArrival).toMatch(/0[67]:\d{2}/);
          } else if (stop.customerName.includes('午餐')) {
            expect(stop.estimatedArrival).toMatch(/1[12]:\d{2}/);
          } else if (stop.customerName.includes('晚餐')) {
            expect(stop.estimatedArrival).toMatch(/1[78]:\d{2}/);
          }
        }
      }
    });

    test('should optimize for different vehicle types', async ({ page }) => {
      await dashboardPage.navigateTo('routes');
      
      // Add mixed orders
      await routePage.addBulkTestOrders([
        { type: 'residential', cylinderSize: '16kg', quantity: 1 },
        { type: 'residential', cylinderSize: '20kg', quantity: 2 },
        { type: 'commercial', cylinderSize: '50kg', quantity: 3 },
        { type: 'industrial', cylinderSize: '50kg', quantity: 5 }
      ]);
      
      // Configure vehicles
      await routePage.configureVehicles([
        { type: 'motorcycle', capacity: 4, maxWeight: 100 },
        { type: 'small_truck', capacity: 20, maxWeight: 500 },
        { type: 'large_truck', capacity: 50, maxWeight: 1500 }
      ]);
      
      // Generate optimized routes
      await routePage.generateOptimizedRoutes();
      await routePage.waitForOptimizationComplete();
      
      // Verify vehicle assignments
      const routes = await routePage.getGeneratedRoutes();
      
      routes.forEach(route => {
        if (route.vehicleType === 'motorcycle') {
          expect(route.totalWeight).toBeLessThanOrEqual(100);
          expect(route.stopCount).toBeLessThanOrEqual(4);
        } else if (route.vehicleType === 'small_truck') {
          expect(route.totalWeight).toBeLessThanOrEqual(500);
        } else if (route.vehicleType === 'large_truck') {
          // Large orders should be on large truck
          expect(route.hasIndustrialOrders).toBe(true);
        }
      });
    });

    test('should handle traffic and road conditions', async ({ page }) => {
      await dashboardPage.navigateTo('routes');
      
      // Enable real-time traffic
      await routePage.enableTrafficConsideration({
        provider: 'google',
        updateFrequency: 'realtime',
        avoidHighways: false,
        avoidTolls: true
      });
      
      // Add traffic incident
      await routePage.addTrafficIncident({
        location: '台北市信義區市府路',
        severity: 'high',
        estimatedDelay: 30 // minutes
      });
      
      // Generate routes
      await routePage.generateOptimizedRoutes();
      await routePage.waitForOptimizationComplete();
      
      // Verify routes avoid incident area
      const routes = await routePage.getGeneratedRoutes();
      const affectedRoute = routes.find(r => r.includesArea('信義區'));
      
      if (affectedRoute) {
        // Route should have alternative path
        expect(affectedRoute.hasAlternativeRoute).toBe(true);
        expect(affectedRoute.estimatedDelay).toBeLessThan(15); // Should minimize delay
      }
    });
  });

  test.describe('Manual Route Adjustments', () => {
    test('should allow drag-and-drop route modification', async ({ page }) => {
      await dashboardPage.navigateTo('routes');
      
      // Generate initial routes
      await routePage.generateOptimizedRoutes();
      await routePage.waitForOptimizationComplete();
      
      // Select a route to modify
      const firstRoute = await routePage.selectRoute(0);
      await routePage.openRouteEditor(firstRoute.id);
      
      // Get initial stop order
      const initialStops = await routePage.getRouteStopOrder(firstRoute.id);
      
      // Drag stop from position 3 to position 1
      await routePage.dragStopToPosition(3, 1);
      
      // Verify order changed
      const updatedStops = await routePage.getRouteStopOrder(firstRoute.id);
      expect(updatedStops[1]).toBe(initialStops[3]);
      
      // Check route metrics updated
      const metrics = await routePage.getRouteMetrics(firstRoute.id);
      expect(metrics.distance).toBeGreaterThan(0);
      expect(metrics.duration).toBeGreaterThan(0);
      expect(metrics.efficiency).toBeLessThanOrEqual(100);
    });

    test('should move deliveries between routes', async ({ page }) => {
      await dashboardPage.navigateTo('routes');
      
      // Generate routes with multiple drivers
      await routePage.generateOptimizedRoutes();
      await routePage.waitForOptimizationComplete();
      
      // Get two routes
      const routes = await routePage.getGeneratedRoutes();
      expect(routes.length).toBeGreaterThanOrEqual(2);
      
      const sourceRoute = routes[0];
      const targetRoute = routes[1];
      
      // Move delivery from one route to another
      await routePage.openMultiRouteView();
      const deliveryToMove = await routePage.getFirstDelivery(sourceRoute.id);
      
      await routePage.moveDeliveryBetweenRoutes({
        deliveryId: deliveryToMove.id,
        fromRouteId: sourceRoute.id,
        toRouteId: targetRoute.id,
        position: 5
      });
      
      // Verify delivery moved
      const sourceStops = await routePage.getRouteStops(sourceRoute.id);
      const targetStops = await routePage.getRouteStops(targetRoute.id);
      
      expect(sourceStops.find(s => s.id === deliveryToMove.id)).toBeUndefined();
      expect(targetStops.find(s => s.id === deliveryToMove.id)).toBeDefined();
      
      // Check workload rebalanced
      const workloadDiff = Math.abs(sourceStops.length - targetStops.length);
      expect(workloadDiff).toBeLessThanOrEqual(3); // Reasonably balanced
    });

    test('should add new urgent delivery to existing route', async ({ page }) => {
      await dashboardPage.navigateTo('routes');
      
      // Generate and lock routes
      await routePage.generateOptimizedRoutes();
      await routePage.waitForOptimizationComplete();
      await routePage.lockRoutes();
      
      // Simulate urgent order coming in
      await routePage.createUrgentOrder({
        customerName: '緊急客戶',
        address: '台北市大安區和平東路100號',
        cylinderType: '20kg',
        quantity: 2,
        timeWindow: 'ASAP'
      });
      
      // Find best route for insertion
      await routePage.findBestRouteForUrgentDelivery();
      
      // Verify suggestion
      const suggestion = await routePage.getUrgentDeliverySuggestion();
      expect(suggestion.routeId).toBeTruthy();
      expect(suggestion.insertPosition).toBeGreaterThan(0);
      expect(suggestion.estimatedDelay).toBeLessThan(30); // Minutes
      
      // Accept suggestion
      await routePage.acceptUrgentDeliverySuggestion();
      
      // Verify delivery added
      const updatedRoute = await routePage.getRoute(suggestion.routeId);
      expect(updatedRoute.hasUrgentDelivery).toBe(true);
      expect(updatedRoute.stopCount).toBe(suggestion.originalStopCount + 1);
    });
  });

  test.describe('Driver Assignment', () => {
    test('should assign drivers based on availability and skills', async ({ page }) => {
      await dashboardPage.navigateTo('routes');
      
      // Set up driver availability
      await routePage.configureDriverAvailability([
        { name: '王師傅', available: true, vehicleType: 'truck', maxHours: 8 },
        { name: '李師傅', available: true, vehicleType: 'motorcycle', maxHours: 6 },
        { name: '陳師傅', available: false, reason: '請假' },
        { name: '張師傅', available: true, vehicleType: 'truck', maxHours: 8, skills: ['heavy_lifting'] }
      ]);
      
      // Generate routes
      await routePage.generateOptimizedRoutes();
      await routePage.waitForOptimizationComplete();
      
      // Auto-assign drivers
      await routePage.autoAssignDrivers();
      
      // Verify assignments
      const routes = await routePage.getGeneratedRoutes();
      
      routes.forEach(route => {
        if (route.vehicleType === 'truck') {
          expect(['王師傅', '張師傅']).toContain(route.assignedDriver);
        } else if (route.vehicleType === 'motorcycle') {
          expect(route.assignedDriver).toBe('李師傅');
        }
        
        // Check heavy lifting assignments
        if (route.hasHeavyDeliveries) {
          expect(route.assignedDriver).toBe('張師傅');
        }
      });
      
      // Verify 陳師傅 not assigned (on leave)
      const chenRoutes = routes.filter(r => r.assignedDriver === '陳師傅');
      expect(chenRoutes.length).toBe(0);
    });

    test('should handle driver substitution', async ({ page }) => {
      await dashboardPage.navigateTo('routes');
      
      // Create route with assigned driver
      await routePage.generateOptimizedRoutes();
      await routePage.waitForOptimizationComplete();
      
      const route = (await routePage.getGeneratedRoutes())[0];
      await routePage.assignDriver(route.id, '王師傅');
      
      // Simulate driver calling in sick
      await routePage.markDriverUnavailable('王師傅', 'sick');
      
      // Find substitute
      await routePage.findSubstituteDriver(route.id);
      
      // Verify substitute suggestions
      const substitutes = await routePage.getSubstituteSuggestions();
      expect(substitutes.length).toBeGreaterThan(0);
      
      substitutes.forEach(sub => {
        expect(sub.available).toBe(true);
        expect(sub.vehicleType).toBe(route.vehicleType);
        expect(sub.currentWorkload).toBeLessThan(8); // Hours
      });
      
      // Assign substitute
      await routePage.assignSubstitute(route.id, substitutes[0].name);
      
      // Verify assignment updated
      const updatedRoute = await routePage.getRoute(route.id);
      expect(updatedRoute.assignedDriver).toBe(substitutes[0].name);
      expect(updatedRoute.originalDriver).toBe('王師傅');
      expect(updatedRoute.substitutionReason).toBe('sick');
    });
  });

  test.describe('Route Monitoring and Tracking', () => {
    test('should show real-time route progress', async ({ page }) => {
      await dashboardPage.navigateTo('routes');
      
      // Select active route
      await routePage.filterByStatus('in_progress');
      const activeRoute = await routePage.getFirstActiveRoute();
      
      if (!activeRoute) {
        test.skip();
        return;
      }
      
      // Open tracking view
      await routePage.openRouteTracking(activeRoute.id);
      
      // Verify tracking elements
      await expect(page.locator('[data-testid="route-map"]')).toBeVisible();
      await expect(page.locator('[data-testid="driver-location"]')).toBeVisible();
      await expect(page.locator('[data-testid="completed-stops"]')).toBeVisible();
      await expect(page.locator('[data-testid="remaining-stops"]')).toBeVisible();
      
      // Check progress metrics
      const progress = await routePage.getRouteProgress();
      expect(progress.completed).toBeGreaterThanOrEqual(0);
      expect(progress.total).toBeGreaterThan(0);
      expect(progress.percentage).toBeGreaterThanOrEqual(0);
      expect(progress.percentage).toBeLessThanOrEqual(100);
      
      // Verify ETA updates
      const eta = await routePage.getRouteETA();
      expect(eta).toMatch(/\d{2}:\d{2}/);
    });

    test('should alert on route delays', async ({ page }) => {
      await dashboardPage.navigateTo('routes');
      
      // Monitor active routes
      await routePage.enableDelayMonitoring({
        threshold: 15, // minutes
        notificationMethod: 'both' // dashboard + SMS
      });
      
      // Simulate delay on a route
      const activeRoute = await routePage.getFirstActiveRoute();
      if (activeRoute) {
        await routePage.simulateDelay(activeRoute.id, 20); // 20 minutes delay
        
        // Check for delay alert
        await expect(page.locator('[data-testid="delay-alert"]')).toBeVisible();
        const alert = await routePage.getDelayAlert();
        
        expect(alert.routeId).toBe(activeRoute.id);
        expect(alert.delayMinutes).toBe(20);
        expect(alert.impactedCustomers).toBeGreaterThan(0);
        
        // Verify notification sent
        const notifications = await routePage.getNotificationLog();
        const delayNotification = notifications.find(n => 
          n.type === 'delay' && n.routeId === activeRoute.id
        );
        expect(delayNotification).toBeDefined();
      }
    });
  });

  test.describe('Route Performance Analytics', () => {
    test('should analyze route efficiency', async ({ page }) => {
      await dashboardPage.navigateTo('routes');
      await routePage.navigateToAnalytics();
      
      // Select date range
      await routePage.selectAnalyticsPeriod('last_7_days');
      
      // Get efficiency metrics
      const metrics = await routePage.getEfficiencyMetrics();
      
      expect(metrics.averageCompletionRate).toBeGreaterThan(0);
      expect(metrics.averageDeliveryTime).toBeGreaterThan(0);
      expect(metrics.fuelEfficiency).toBeGreaterThan(0);
      expect(metrics.customerSatisfaction).toBeGreaterThan(0);
      
      // Check route optimization savings
      const savings = await routePage.getOptimizationSavings();
      expect(savings.distanceReduction).toBeGreaterThan(0);
      expect(savings.timeReduction).toBeGreaterThan(0);
      expect(savings.fuelSavings).toBeGreaterThan(0);
    });

    test('should identify optimization opportunities', async ({ page }) => {
      await dashboardPage.navigateTo('routes');
      await routePage.navigateToAnalytics();
      
      // Run optimization analysis
      await routePage.runOptimizationAnalysis();
      
      // Get recommendations
      const recommendations = await routePage.getOptimizationRecommendations();
      
      expect(recommendations.length).toBeGreaterThan(0);
      
      recommendations.forEach(rec => {
        expect(rec).toHaveProperty('type');
        expect(rec).toHaveProperty('description');
        expect(rec).toHaveProperty('potentialSavings');
        expect(rec).toHaveProperty('priority');
        
        // Verify recommendation types
        expect(['route_consolidation', 'time_window_adjustment', 
                'vehicle_reallocation', 'driver_training']).toContain(rec.type);
      });
      
      // Apply a recommendation
      if (recommendations.length > 0) {
        await routePage.applyRecommendation(recommendations[0].id);
        
        // Verify applied
        await expect(page.locator('[data-testid="recommendation-applied"]')).toBeVisible();
      }
    });

    test('should export route data for analysis', async ({ page }) => {
      await dashboardPage.navigateTo('routes');
      await routePage.navigateToAnalytics();
      
      // Configure export
      await routePage.configureDataExport({
        period: 'last_month',
        includeMetrics: ['distance', 'duration', 'stops', 'efficiency'],
        format: 'excel',
        groupBy: 'driver'
      });
      
      // Export data
      await routePage.exportRouteData();
      
      // Verify download
      const download = await page.waitForEvent('download');
      expect(download.suggestedFilename()).toMatch(/^route_analysis_\d{6}\.xlsx$/);
      
      // Also test CSV export for integration
      await routePage.configureDataExport({
        period: 'last_month',
        format: 'csv'
      });
      
      await routePage.exportRouteData();
      
      const csvDownload = await page.waitForEvent('download');
      expect(csvDownload.suggestedFilename()).toMatch(/^route_data_\d{6}\.csv$/);
    });
  });
});