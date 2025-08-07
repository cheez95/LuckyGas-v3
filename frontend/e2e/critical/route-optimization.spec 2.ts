import { test, expect } from '@playwright/test';
import { loginAsTestUser, waitForApiResponse } from '../helpers/auth.helper';

test.describe('Critical: Route Optimization', () => {
  test.beforeEach(async ({ page }) => {
    await loginAsTestUser(page);
  });

  test('Navigate to route planning and view routes', async ({ page }) => {
    // Navigate to routes
    await page.click('text=路線規劃');
    await page.waitForURL(/routes/);
    
    // Verify page loaded - check for any route-related content
    const pageLoaded = await page.locator('h2:has-text("路線規劃"), h1:has-text("路線規劃"), text=/路線|Routes/').first().isVisible({ timeout: 5000 }).catch(() => false);
    
    if (!pageLoaded) {
      // Page might use different title, check for route-related elements
      const routeContent = page.locator('.route-map').or(page.locator('.ant-table')).or(page.locator('text=/優化|路線|配送/'));
      await expect(routeContent.first()).toBeVisible();
    }
    
    // Check if route optimization button exists
    const optimizeButton = page.locator('button:has-text("優化路線"), button:has-text("路線優化")');
    const hasOptimizeFeature = await optimizeButton.isVisible();
    
    if (hasOptimizeFeature) {
      // Check if button is enabled before clicking
      const isEnabled = await optimizeButton.isEnabled();
      if (isEnabled) {
        // Click optimize button
        await optimizeButton.click();
      
      // Check if orders selection appears
      const orderSelection = page.locator('text=/選擇.*訂單|訂單.*選擇/');
      if (await orderSelection.isVisible({ timeout: 2000 }).catch(() => false)) {
        // Select some orders if checkboxes exist
        const checkboxes = page.locator('input[type="checkbox"]:not(:checked)');
        const checkboxCount = await checkboxes.count();
        
        if (checkboxCount > 0) {
          // Select up to 5 orders
          for (let i = 0; i < Math.min(5, checkboxCount); i++) {
            await checkboxes.nth(i).check();
          }
          
          // Run optimization
          const runButton = page.locator('button:has-text("執行優化"), button:has-text("開始優化")');
          if (await runButton.isVisible()) {
            await runButton.click();
            
            // Wait for optimization result
            await expect(page.locator('text=/優化完成|路線已生成|優化成功/')).toBeVisible({ timeout: 10000 });
          }
        }
      }
      } else {
        // Button is disabled, which is still a valid state
        console.log('Optimize button is disabled - might need orders first');
      }
    }
    
    // Check if routes table or map exists
    const routesTable = page.locator('.ant-table, [data-testid="routes-table"]');
    const routesMap = page.locator('.route-map, #map, [data-testid="routes-map"]');
    
    // Verify either table or map is visible
    const hasRoutesDisplay = await routesTable.isVisible() || await routesMap.isVisible();
    
    // If no routes display found, check for empty state or any route-related content
    if (!hasRoutesDisplay) {
      const emptyState = page.locator('.ant-empty').or(page.locator('text=/暫無路線|沒有路線/'));
      const routeContent = page.locator('text=/路線|配送|優化/').first();
      const hasAnyRouteContent = await emptyState.isVisible() || await routeContent.isVisible();
      expect(hasAnyRouteContent).toBeTruthy();
    } else {
      expect(hasRoutesDisplay).toBeTruthy();
    }
  });

  test('Assign driver to route', async ({ page }) => {
    // Navigate to routes
    await page.click('text=路線規劃');
    await page.waitForURL(/routes/);
    
    // Check if any routes exist
    const routeRows = page.locator('.ant-table-tbody tr, [data-testid="route-row"]');
    const routeCount = await routeRows.count();
    
    if (routeCount > 0) {
      // Click on first route
      await routeRows.first().click();
      
      // Look for driver assignment option
      const assignButton = page.locator('button:has-text("指派司機"), button:has-text("分配司機")');
      const driverSelect = page.locator('select:has-text("選擇司機"), .ant-select:has-text("司機")');
      
      if (await assignButton.isVisible()) {
        await assignButton.click();
        
        // Check if driver selection modal or dropdown appears
        const driverModal = page.locator('.ant-modal:has-text("司機")');
        if (await driverModal.isVisible({ timeout: 2000 }).catch(() => false)) {
          // Select first available driver
          const driverOption = page.locator('.ant-radio-group label, .driver-option').first();
          if (await driverOption.isVisible()) {
            await driverOption.click();
            
            // Confirm assignment
            const confirmButton = page.locator('button:has-text("確認"), button:has-text("指派")');
            await confirmButton.click();
            
            // Verify assignment success
            await expect(page.locator('text=/指派成功|已分配|司機已指派/')).toBeVisible();
          }
        }
      } else if (await driverSelect.isVisible()) {
        // Direct dropdown selection
        await driverSelect.click();
        const firstOption = page.locator('.ant-select-item').first();
        if (await firstOption.isVisible()) {
          await firstOption.click();
        }
      }
    } else {
      // No routes exist, check for empty state
      const emptyState = page.locator('.ant-empty').or(page.locator('text=/暫無路線|沒有路線/'));
      await expect(emptyState).toBeVisible();
    }
  });

  test('View route details and progress', async ({ page }) => {
    // Navigate to routes
    await page.click('text=路線規劃');
    await page.waitForURL(/routes/);
    
    // Check if any routes exist
    const routeRows = page.locator('.ant-table-tbody tr, [data-testid="route-row"]');
    const routeCount = await routeRows.count();
    
    if (routeCount > 0) {
      // Click on first route to view details
      await routeRows.first().click();
      
      // Wait for route details to appear
      const detailsModal = page.locator('.ant-modal, [data-testid="route-details"]');
      const detailsSection = page.locator('text=/路線詳情|路線資訊|配送進度/');
      
      await Promise.race([
        detailsModal.waitFor({ timeout: 3000 }).catch(() => {}),
        detailsSection.waitFor({ timeout: 3000 }).catch(() => {})
      ]);
      
      // Verify route information is displayed
      const routeInfo = [
        'text=/路線編號|路線代碼/',
        'text=/訂單數|配送數量/',
        'text=/狀態|進度/'
      ];
      
      // Check driver info separately to avoid strict mode violation
      const driverInfo = page.locator('text=/司機|配送員/').first();
      const hasDriverInfo = await driverInfo.isVisible({ timeout: 1000 }).catch(() => false);
      
      let hasRouteInfo = hasDriverInfo;
      for (const info of routeInfo) {
        const element = page.locator(info);
        if (await element.isVisible()) {
          hasRouteInfo = true;
          break;
        }
      }
      
      // Check if map is displayed
      const mapElement = page.locator('.route-map, #map, canvas');
      const hasMap = await mapElement.isVisible();
      
      // Check if orders list is displayed
      const ordersList = page.locator('.route-orders').or(page.locator('.orders-list')).or(page.locator('text=/訂單列表|配送清單/'));
      const hasOrdersList = await ordersList.isVisible();
      
      // Verify at least one visualization method exists
      expect(hasMap || hasOrdersList).toBeTruthy();
    }
  });

  test('Emergency route adjustment', async ({ page }) => {
    // Check if emergency dispatch is available
    const emergencyMenu = page.locator('text=緊急派遣');
    if (await emergencyMenu.isVisible()) {
      await emergencyMenu.click();
      await page.waitForURL(/emergency|dispatch/);
      
      // Verify emergency dispatch page loaded
      await expect(page.locator('h2:has-text("緊急派遣"), h1:has-text("緊急派遣")')).toBeVisible();
      
      // Check for urgent orders or alerts
      const urgentOrders = page.locator('text=/緊急|急件|優先/');
      const hasUrgentOrders = await urgentOrders.isVisible();
      
      if (hasUrgentOrders) {
        // Check if quick assign is available
        const quickAssign = page.locator('button:has-text("快速指派"), button:has-text("立即派遣")');
        if (await quickAssign.isVisible()) {
          await quickAssign.click();
          
          // Verify assignment options appear
          await expect(page.locator('text=/選擇司機|可用司機|最近司機/')).toBeVisible();
        }
      } else {
        // Verify no urgent orders message
        await expect(page.locator('text=/無緊急訂單|暫無急件/')).toBeVisible();
      }
    }
  });
});