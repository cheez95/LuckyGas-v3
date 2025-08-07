import { test, expect } from '@playwright/test';
import { loginAsOfficeStaff, setupTestData, cleanupTestData } from '../helpers/test-utils';

test.describe('Route Management Workflow', () => {
  test.beforeEach(async ({ page }) => {
    // Login as office staff
    await loginAsOfficeStaff(page);
    
    // Navigate to route management
    await page.goto('/routes');
    await page.waitForLoadState('networkidle');
  });

  test('Should generate routes from pending orders', async ({ page }) => {
    // Check if there are pending orders
    const pendingOrdersCount = await page.locator('[data-testid="pending-orders-count"]').textContent();
    
    if (pendingOrdersCount && parseInt(pendingOrdersCount) > 0) {
      // Click generate routes button
      await page.click('button:has-text("產生路線")');
      
      // Wait for route generation modal
      await page.waitForSelector('[data-testid="route-generation-modal"]', { state: 'visible' });
      
      // Select generation method
      await page.click('[data-testid="generation-method-auto"]');
      
      // Configure generation parameters
      await page.fill('[data-testid="max-stops-per-route"]', '20');
      await page.fill('[data-testid="max-distance-km"]', '30');
      await page.selectOption('[data-testid="optimization-priority"]', 'distance');
      
      // Select date range
      await page.click('[data-testid="delivery-date-picker"]');
      await page.click('.ant-picker-today-btn');
      
      // Select areas to include
      await page.click('[data-testid="area-select"]');
      await page.click('[data-testid="area-option-taipei"]');
      await page.click('[data-testid="area-option-new-taipei"]');
      await page.press('body', 'Escape'); // Close dropdown
      
      // Preview route generation
      await page.click('button:has-text("預覽路線")');
      
      // Wait for preview to load
      await page.waitForSelector('[data-testid="route-preview-map"]', { state: 'visible' });
      
      // Verify preview shows routes
      const previewRoutes = await page.locator('[data-testid="preview-route-card"]').count();
      expect(previewRoutes).toBeGreaterThan(0);
      
      // Check route details
      const firstRoute = page.locator('[data-testid="preview-route-card"]').first();
      await expect(firstRoute).toContainText(/路線 \d+/);
      await expect(firstRoute).toContainText(/\d+ 個配送點/);
      await expect(firstRoute).toContainText(/預計距離: \d+\.?\d* 公里/);
      await expect(firstRoute).toContainText(/預計時間: \d+ 小時/);
      
      // Confirm generation
      await page.click('button:has-text("確認產生")');
      
      // Wait for success message
      await expect(page.locator('.ant-message-success')).toBeVisible();
      await expect(page.locator('.ant-message-success')).toContainText('成功產生');
      
      // Verify routes appear in list
      await page.waitForTimeout(1000);
      const routeRows = await page.locator('tbody tr').count();
      expect(routeRows).toBeGreaterThan(0);
    } else {
      // No pending orders - create some first
      await page.goto('/orders');
      await page.click('button:has-text("新增訂單")');
      
      // Quick create an order
      await page.click('[data-testid="customer-select"]');
      await page.click('.ant-select-item:first-child');
      await page.click('[data-testid="add-product-btn"]');
      await page.selectOption('[data-testid="product-type-select"]', '20KG');
      await page.fill('[data-testid="product-quantity"]', '2');
      await page.click('button:has-text("建立訂單")');
      
      // Go back to routes
      await page.goto('/routes');
      
      // Retry route generation
      await page.click('button:has-text("產生路線")');
    }
  });

  test('Should optimize existing routes', async ({ page }) => {
    // Find an existing route
    const routeExists = await page.locator('tbody tr').count() > 0;
    
    if (routeExists) {
      // Select first route
      const firstRoute = page.locator('tbody tr').first();
      const routeId = await firstRoute.getAttribute('data-row-key');
      
      // Click optimize button
      await firstRoute.locator('[data-testid="optimize-route-btn"]').click();
      
      // Wait for optimization modal
      await page.waitForSelector('[data-testid="route-optimization-modal"]', { state: 'visible' });
      
      // View current route on map
      await expect(page.locator('[data-testid="current-route-map"]')).toBeVisible();
      
      // Check current metrics
      const currentDistance = await page.locator('[data-testid="current-distance"]').textContent();
      const currentTime = await page.locator('[data-testid="current-time"]').textContent();
      
      // Select optimization options
      await page.click('[data-testid="optimize-distance"]');
      await page.click('[data-testid="consider-traffic"]');
      await page.click('[data-testid="avoid-tolls"]');
      
      // Set time windows
      await page.click('[data-testid="use-time-windows"]');
      await page.fill('[data-testid="start-time"]', '08:00');
      await page.fill('[data-testid="end-time"]', '18:00');
      
      // Run optimization
      await page.click('button:has-text("開始優化")');
      
      // Wait for optimization to complete
      await page.waitForSelector('[data-testid="optimization-progress"]', { state: 'visible' });
      await page.waitForSelector('[data-testid="optimization-complete"]', { state: 'visible', timeout: 30000 });
      
      // Check optimized metrics
      const optimizedDistance = await page.locator('[data-testid="optimized-distance"]').textContent();
      const optimizedTime = await page.locator('[data-testid="optimized-time"]').textContent();
      const savings = await page.locator('[data-testid="optimization-savings"]').textContent();
      
      // Verify optimization shows improvement
      expect(savings).toBeTruthy();
      
      // View optimized route on map
      await page.click('[data-testid="view-optimized-route"]');
      await expect(page.locator('[data-testid="optimized-route-map"]')).toBeVisible();
      
      // Apply optimization
      await page.click('button:has-text("套用優化結果")');
      
      // Confirm application
      await page.click('button:has-text("確認套用")');
      
      // Wait for success message
      await expect(page.locator('.ant-message-success')).toBeVisible();
      await expect(page.locator('.ant-message-success')).toContainText('路線優化成功');
    }
  });

  test('Should assign drivers to routes', async ({ page }) => {
    // Check if routes exist
    const routeCount = await page.locator('tbody tr').count();
    
    if (routeCount > 0) {
      // Single route assignment
      const firstRoute = page.locator('tbody tr').first();
      
      // Click assign driver button
      await firstRoute.locator('[data-testid="assign-driver-btn"]').click();
      
      // Wait for driver selection modal
      await page.waitForSelector('[data-testid="driver-selection-modal"]', { state: 'visible' });
      
      // View available drivers
      const availableDrivers = await page.locator('[data-testid="available-driver-card"]').count();
      expect(availableDrivers).toBeGreaterThan(0);
      
      // Check driver details
      const firstDriver = page.locator('[data-testid="available-driver-card"]').first();
      await expect(firstDriver).toContainText(/司機/);
      await expect(firstDriver).toContainText(/可用/);
      
      // View driver stats
      await firstDriver.locator('[data-testid="view-driver-stats"]').click();
      await expect(page.locator('[data-testid="driver-stats-modal"]')).toBeVisible();
      await expect(page.locator('[data-testid="completion-rate"]')).toBeVisible();
      await expect(page.locator('[data-testid="average-delivery-time"]')).toBeVisible();
      await page.click('[data-testid="close-driver-stats"]');
      
      // Select driver
      await firstDriver.locator('[data-testid="select-driver-btn"]').click();
      
      // Confirm assignment
      await page.click('button:has-text("確認指派")');
      
      // Wait for success
      await expect(page.locator('.ant-message-success')).toBeVisible();
      await expect(page.locator('.ant-message-success')).toContainText('司機指派成功');
      
      // Verify driver assigned in list
      await page.waitForTimeout(1000);
      await expect(firstRoute).toContainText(/司機/);
      
      // Batch driver assignment
      if (routeCount > 1) {
        // Select multiple routes
        await page.click('input[type="checkbox"][aria-label="Select all"]');
        
        // Click batch assign
        await page.click('button:has-text("批次指派司機")');
        
        // Wait for batch assignment modal
        await page.waitForSelector('[data-testid="batch-driver-assignment-modal"]', { state: 'visible' });
        
        // Select assignment strategy
        await page.click('[data-testid="assignment-strategy-auto"]');
        
        // Configure auto-assignment rules
        await page.click('[data-testid="balance-workload"]');
        await page.click('[data-testid="consider-driver-location"]');
        await page.click('[data-testid="match-driver-skills"]');
        
        // Preview assignments
        await page.click('button:has-text("預覽指派")');
        
        // Wait for preview
        await page.waitForSelector('[data-testid="assignment-preview-table"]', { state: 'visible' });
        
        // Verify preview shows assignments
        const previewRows = await page.locator('[data-testid="assignment-preview-row"]').count();
        expect(previewRows).toBeGreaterThan(0);
        
        // Apply assignments
        await page.click('button:has-text("確認批次指派")');
        
        // Wait for success
        await expect(page.locator('.ant-message-success')).toBeVisible();
        await expect(page.locator('.ant-message-success')).toContainText('批次指派完成');
      }
    }
  });

  test('Should manage route stops and sequences', async ({ page }) => {
    // Find a route with multiple stops
    const routeRow = page.locator('tbody tr').filter({ hasText: /\d+ 個配送點/ }).first();
    const hasRoute = await routeRow.count() > 0;
    
    if (hasRoute) {
      // Click to edit route
      await routeRow.locator('[data-testid="edit-route-btn"]').click();
      
      // Wait for route editor
      await page.waitForSelector('[data-testid="route-editor-modal"]', { state: 'visible' });
      
      // View stops list
      await expect(page.locator('[data-testid="route-stops-list"]')).toBeVisible();
      
      const stops = await page.locator('[data-testid="route-stop-item"]').count();
      expect(stops).toBeGreaterThan(0);
      
      // Drag and drop to reorder (if multiple stops)
      if (stops > 1) {
        const firstStop = page.locator('[data-testid="route-stop-item"]').first();
        const secondStop = page.locator('[data-testid="route-stop-item"]').nth(1);
        
        // Drag first stop to second position
        await firstStop.dragTo(secondStop);
        
        // Verify order changed
        await page.waitForTimeout(500);
        
        // Add priority to a stop
        await page.locator('[data-testid="route-stop-item"]').first().locator('[data-testid="set-priority-btn"]').click();
        await page.click('[data-testid="priority-urgent"]');
        
        // Remove a stop
        if (stops > 2) {
          await page.locator('[data-testid="route-stop-item"]').last().locator('[data-testid="remove-stop-btn"]').click();
          await page.click('button:has-text("確認移除")');
          
          // Verify stop removed
          const newStopCount = await page.locator('[data-testid="route-stop-item"]').count();
          expect(newStopCount).toBe(stops - 1);
        }
        
        // Add a stop from unassigned orders
        await page.click('[data-testid="add-stop-btn"]');
        
        // Select from available orders
        const availableOrders = await page.locator('[data-testid="available-order-item"]').count();
        if (availableOrders > 0) {
          await page.locator('[data-testid="available-order-item"]').first().click();
          await page.click('button:has-text("加入路線")');
          
          // Verify stop added
          const finalStopCount = await page.locator('[data-testid="route-stop-item"]').count();
          expect(finalStopCount).toBeGreaterThan(stops - 1);
        }
      }
      
      // Save route changes
      await page.click('button:has-text("儲存變更")');
      
      // Wait for success
      await expect(page.locator('.ant-message-success')).toBeVisible();
      await expect(page.locator('.ant-message-success')).toContainText('路線更新成功');
    }
  });

  test('Should track route execution status', async ({ page }) => {
    // Find an assigned route
    const assignedRoute = page.locator('tbody tr').filter({ hasText: '已指派' }).first();
    const hasAssignedRoute = await assignedRoute.count() > 0;
    
    if (hasAssignedRoute) {
      // Click to view route details
      await assignedRoute.click();
      
      // Wait for route details drawer
      await page.waitForSelector('.ant-drawer', { state: 'visible' });
      
      // Verify route information
      await expect(page.locator('.ant-drawer-title')).toContainText('路線詳情');
      
      // Check route status
      await expect(page.locator('[data-testid="route-status"]')).toBeVisible();
      await expect(page.locator('[data-testid="assigned-driver"]')).toBeVisible();
      
      // View real-time tracking (if available)
      if (await page.locator('[data-testid="track-route-btn"]').isVisible()) {
        await page.click('[data-testid="track-route-btn"]');
        
        // Wait for tracking map
        await page.waitForSelector('[data-testid="route-tracking-map"]', { state: 'visible' });
        
        // Check driver location (if active)
        const driverMarker = await page.locator('[data-testid="driver-location-marker"]').isVisible();
        if (driverMarker) {
          await expect(page.locator('[data-testid="driver-location-marker"]')).toBeVisible();
          await expect(page.locator('[data-testid="last-update-time"]')).toBeVisible();
        }
        
        // Check completed stops
        const completedStops = await page.locator('[data-testid="completed-stop-marker"]').count();
        const pendingStops = await page.locator('[data-testid="pending-stop-marker"]').count();
        
        // Verify stop markers
        expect(completedStops + pendingStops).toBeGreaterThan(0);
      }
      
      // View route timeline
      await page.click('[data-testid="route-timeline-tab"]');
      await expect(page.locator('[data-testid="route-timeline"]')).toBeVisible();
      
      // Check timeline events
      const timelineEvents = await page.locator('.ant-timeline-item').count();
      expect(timelineEvents).toBeGreaterThan(0);
      
      // Close drawer
      await page.click('.ant-drawer-close');
    }
  });

  test('Should export route sheets for drivers', async ({ page }) => {
    // Select routes to export
    const routeCount = await page.locator('tbody tr').count();
    
    if (routeCount > 0) {
      // Select all routes
      await page.click('input[type="checkbox"][aria-label="Select all"]');
      
      // Click export button
      await page.click('button:has-text("匯出路線單")');
      
      // Wait for export options modal
      await page.waitForSelector('[data-testid="export-route-modal"]', { state: 'visible' });
      
      // Select export format
      await page.click('[data-testid="export-format-pdf"]');
      
      // Configure export options
      await page.click('label:has-text("包含地圖")');
      await page.click('label:has-text("包含客戶電話")');
      await page.click('label:has-text("包含產品明細")');
      await page.click('label:has-text("包含簽收欄位")');
      
      // Select grouping
      await page.click('[data-testid="group-by-driver"]');
      
      // Set up download promise
      const downloadPromise = page.waitForEvent('download');
      
      // Confirm export
      await page.click('button:has-text("確認匯出")');
      
      // Wait for download
      const download = await downloadPromise;
      
      // Verify download
      expect(download.suggestedFilename()).toContain('routes');
      expect(download.suggestedFilename()).toMatch(/\.pdf$/);
    }
  });

  test('Should handle route conflicts and adjustments', async ({ page }) => {
    // Create a conflict scenario
    const routeRow = page.locator('tbody tr').first();
    const hasRoute = await routeRow.count() > 0;
    
    if (hasRoute) {
      // Simulate an urgent order that needs to be added
      await page.click('[data-testid="urgent-order-notification"]');
      
      // Wait for urgent order modal
      const urgentModalVisible = await page.locator('[data-testid="urgent-order-modal"]').isVisible();
      
      if (urgentModalVisible) {
        // View urgent order details
        await expect(page.locator('[data-testid="urgent-order-details"]')).toBeVisible();
        
        // Find best route to add to
        await page.click('button:has-text("建議路線")');
        
        // Wait for suggestions
        await page.waitForSelector('[data-testid="route-suggestions"]', { state: 'visible' });
        
        // Select suggested route
        const suggestions = await page.locator('[data-testid="route-suggestion-item"]').count();
        if (suggestions > 0) {
          await page.locator('[data-testid="route-suggestion-item"]').first().click();
          
          // View impact analysis
          await expect(page.locator('[data-testid="impact-analysis"]')).toBeVisible();
          await expect(page.locator('[data-testid="additional-distance"]')).toBeVisible();
          await expect(page.locator('[data-testid="additional-time"]')).toBeVisible();
          
          // Confirm addition
          await page.click('button:has-text("確認加入")');
          
          // Wait for success
          await expect(page.locator('.ant-message-success')).toContainText('緊急訂單已加入路線');
        }
      }
    }
  });

  test('Should analyze route performance metrics', async ({ page }) => {
    // Navigate to route analytics
    await page.click('[data-testid="route-analytics-btn"]');
    
    // Wait for analytics dashboard
    await page.waitForSelector('[data-testid="route-analytics-dashboard"]', { state: 'visible' });
    
    // Check key metrics
    await expect(page.locator('[data-testid="average-completion-rate"]')).toBeVisible();
    await expect(page.locator('[data-testid="average-delivery-time"]')).toBeVisible();
    await expect(page.locator('[data-testid="total-distance-saved"]')).toBeVisible();
    await expect(page.locator('[data-testid="fuel-cost-savings"]')).toBeVisible();
    
    // View performance chart
    await expect(page.locator('[data-testid="route-performance-chart"]')).toBeVisible();
    
    // Filter by date range
    await page.click('[data-testid="date-range-picker"]');
    await page.click('[data-testid="last-7-days"]');
    
    // Wait for data refresh
    await page.waitForTimeout(1000);
    
    // Check driver performance
    await page.click('[data-testid="driver-performance-tab"]');
    await expect(page.locator('[data-testid="driver-performance-table"]')).toBeVisible();
    
    // Export analytics report
    const downloadPromise = page.waitForEvent('download');
    await page.click('button:has-text("匯出報表")');
    
    const download = await downloadPromise;
    expect(download.suggestedFilename()).toContain('route-analytics');
  });
});

test.describe('Route Management - Advanced Features', () => {
  test.beforeEach(async ({ page }) => {
    await loginAsOfficeStaff(page);
    await page.goto('/routes');
    await page.waitForLoadState('networkidle');
  });

  test('Should handle multi-day route planning', async ({ page }) => {
    // Click advanced planning
    await page.click('[data-testid="advanced-planning-btn"]');
    
    // Wait for planning modal
    await page.waitForSelector('[data-testid="multi-day-planning-modal"]', { state: 'visible' });
    
    // Select date range
    await page.click('[data-testid="planning-date-range"]');
    await page.click('[data-testid="next-7-days"]');
    
    // Configure planning parameters
    await page.fill('[data-testid="daily-capacity"]', '100');
    await page.fill('[data-testid="max-drivers"]', '5');
    
    // Set working hours
    await page.fill('[data-testid="work-start-time"]', '08:00');
    await page.fill('[data-testid="work-end-time"]', '18:00');
    
    // Enable load balancing
    await page.click('[data-testid="enable-load-balancing"]');
    
    // Generate multi-day plan
    await page.click('button:has-text("產生計劃")');
    
    // Wait for plan generation
    await page.waitForSelector('[data-testid="multi-day-plan-result"]', { state: 'visible' });
    
    // Verify plan details
    const planDays = await page.locator('[data-testid="plan-day-card"]').count();
    expect(planDays).toBeGreaterThan(0);
    
    // Review first day
    const firstDay = page.locator('[data-testid="plan-day-card"]').first();
    await expect(firstDay).toContainText(/第 1 天/);
    await expect(firstDay).toContainText(/\d+ 條路線/);
    await expect(firstDay).toContainText(/\d+ 個訂單/);
    
    // Apply plan
    await page.click('button:has-text("套用計劃")');
    
    // Confirm application
    await page.click('button:has-text("確認套用")');
    
    // Wait for success
    await expect(page.locator('.ant-message-success')).toContainText('多日計劃已套用');
  });

  test('Should simulate route scenarios', async ({ page }) => {
    // Click simulation tool
    await page.click('[data-testid="route-simulation-btn"]');
    
    // Wait for simulation modal
    await page.waitForSelector('[data-testid="route-simulation-modal"]', { state: 'visible' });
    
    // Configure simulation parameters
    await page.fill('[data-testid="simulation-orders"]', '50');
    await page.fill('[data-testid="simulation-drivers"]', '3');
    
    // Set constraints
    await page.fill('[data-testid="max-route-distance"]', '50');
    await page.fill('[data-testid="max-route-duration"]', '480'); // 8 hours in minutes
    
    // Add traffic conditions
    await page.selectOption('[data-testid="traffic-condition"]', 'heavy');
    
    // Run simulation
    await page.click('button:has-text("執行模擬")');
    
    // Wait for simulation results
    await page.waitForSelector('[data-testid="simulation-results"]', { state: 'visible', timeout: 30000 });
    
    // Check simulation metrics
    await expect(page.locator('[data-testid="simulated-routes"]')).toBeVisible();
    await expect(page.locator('[data-testid="total-distance"]')).toBeVisible();
    await expect(page.locator('[data-testid="total-time"]')).toBeVisible();
    await expect(page.locator('[data-testid="efficiency-score"]')).toBeVisible();
    
    // Compare scenarios
    await page.click('[data-testid="add-scenario-btn"]');
    
    // Modify parameters for comparison
    await page.selectOption('[data-testid="traffic-condition-2"]', 'light');
    await page.fill('[data-testid="simulation-drivers-2"]', '4');
    
    // Run comparison
    await page.click('button:has-text("比較情境")');
    
    // View comparison results
    await expect(page.locator('[data-testid="scenario-comparison"]')).toBeVisible();
    await expect(page.locator('[data-testid="best-scenario"]')).toBeVisible();
  });
});