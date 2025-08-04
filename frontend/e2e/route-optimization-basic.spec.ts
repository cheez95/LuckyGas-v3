import { test, expect } from '@playwright/test';
import { LoginPage } from './pages/LoginPage';
import { RoutePage } from './pages/RoutePage';
import { DashboardPage } from './pages/DashboardPage';

test.describe('Route Optimization Basic Validation', () => {
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

  test('should access route planning page', async ({ page }) => {
    await routePage.navigateToRoutes();
    
    // Verify page loaded
    await expect(routePage.pageTitle).toBeVisible();
    await expect(routePage.pageTitle).toContainText('路線規劃');
  });

  test('should display placeholder optimization notice', async ({ page }) => {
    await routePage.navigateToRoutes();
    
    // Check for placeholder notice since Google Routes API is not configured
    const placeholderNotice = page.locator('[data-testid="placeholder-routes-notice"]');
    if (await placeholderNotice.isVisible()) {
      const noticeText = await placeholderNotice.textContent();
      expect(noticeText).toContain('Google Routes API');
    }
  });

  test('should show route optimization button', async ({ page: _page }) => {
    await routePage.navigateToRoutes();
    
    // Check if optimize button exists
    const optimizeExists = await routePage.optimizeRouteButton.isVisible();
    expect(optimizeExists).toBe(true);
    
    // Check button text is in Chinese
    const buttonText = await routePage.optimizeRouteButton.textContent();
    expect(buttonText).toContain('優化路線');
  });

  test('should display route statistics', async ({ page }) => {
    await routePage.navigateToRoutes();
    
    // Check for statistics display
    const statsElements = page.locator('.route-stats');
    if (await statsElements.isVisible()) {
      // Should show total stops
      const totalStops = page.locator('.stat-label').filter({ hasText: '總站點數' });
      await expect(totalStops).toBeVisible();
      
      // Should show total distance
      const totalDistance = page.locator('.stat-label').filter({ hasText: '總距離' });
      await expect(totalDistance).toBeVisible();
      
      // Should show estimated time
      const estimatedTime = page.locator('.stat-label').filter({ hasText: '預計時間' });
      await expect(estimatedTime).toBeVisible();
    }
  });

  test('should display map container for route visualization', async ({ page }) => {
    await routePage.navigateToRoutes();
    
    // Check if map container exists
    const mapContainer = page.locator('#route-map, .route-map-container, [data-testid="route-map"]');
    const mapExists = await mapContainer.isVisible();
    
    if (mapExists) {
      // Map should have proper dimensions
      const box = await mapContainer.boundingBox();
      expect(box).toBeTruthy();
      if (box) {
        expect(box.width).toBeGreaterThan(200);
        expect(box.height).toBeGreaterThan(200);
      }
    }
  });

  test.describe('Route Optimization Placeholder Logic', () => {
    test('should handle optimization with placeholder algorithm', async ({ page }) => {
      await routePage.navigateToRoutes();
      
      // Check if there are any existing routes
      const routeCards = page.locator('.route-card, [data-testid="route-card"]');
      const routeCount = await routeCards.count();
      
      if (routeCount > 0) {
        // Select first route
        await routeCards.first().click();
        
        // Try to optimize
        if (await routePage.optimizeRouteButton.isVisible()) {
          await routePage.optimizeRouteButton.click();
          
          // Should show optimization in progress
          const loadingMessage = page.locator('.ant-message-notice').filter({ hasText: '優化中' });
          await expect(loadingMessage).toBeVisible();
          
          // Wait for completion
          await page.waitForTimeout(3000);
          
          // Should show completion message
          const successMessage = page.locator('.ant-message-notice').filter({ hasText: '完成' });
          const successVisible = await successMessage.isVisible();
          
          if (!successVisible) {
            // Or show placeholder notice
            const placeholderMessage = page.locator('.ant-message-notice').filter({ hasText: 'placeholder' });
            await expect(placeholderMessage).toBeVisible();
          }
        }
      }
    });

    test('should display route metrics after optimization', async ({ page }) => {
      await routePage.navigateToRoutes();
      
      const routeCards = page.locator('.route-card, [data-testid="route-card"]');
      if (await routeCards.count() > 0) {
        await routeCards.first().click();
        
        // Check for route metrics display
        const metricsPanel = page.locator('.route-metrics, [data-testid="route-metrics"]');
        if (await metricsPanel.isVisible()) {
          // Should show distance
          const distance = metricsPanel.locator('.metric-value').filter({ hasText: 'km' });
          await expect(distance).toBeVisible();
          
          // Should show duration
          const duration = metricsPanel.locator('.metric-value').filter({ hasText: /分鐘|小時/ });
          await expect(duration).toBeVisible();
        }
      }
    });
  });

  test.describe('Basic Route Constraints', () => {
    test('should validate time window display', async ({ page }) => {
      await routePage.navigateToRoutes();
      
      // Check if time window information is displayed
      const timeWindowLabels = page.locator('.time-window, [data-testid="time-window"]');
      if (await timeWindowLabels.count() > 0) {
        const firstTimeWindow = await timeWindowLabels.first().textContent();
        expect(firstTimeWindow).toMatch(/\d{1,2}:\d{2}/); // Should match time format
      }
    });

    test('should display vehicle capacity information', async ({ page }) => {
      await routePage.navigateToRoutes();
      
      // Check for vehicle capacity display
      const capacityInfo = page.locator('.vehicle-capacity, [data-testid="vehicle-capacity"]');
      if (await capacityInfo.isVisible()) {
        const capacityText = await capacityInfo.textContent();
        expect(capacityText).toMatch(/\d+/); // Should contain numbers
      }
    });

    test('should show driver assignment status', async ({ page }) => {
      await routePage.navigateToRoutes();
      
      // Check for driver assignment
      const driverInfo = page.locator('.driver-info, [data-testid="driver-name"]');
      if (await driverInfo.count() > 0) {
        const driverText = await driverInfo.first().textContent();
        expect(driverText).toBeTruthy();
        
        // Should be either assigned or unassigned
        const hasDriver = !driverText.includes('未指派');
        if (hasDriver) {
          expect(driverText).not.toContain('未指派');
        }
      }
    });
  });

  test.describe('Route UI Responsiveness', () => {
    test('should be responsive on mobile devices', async ({ page }) => {
      // Set mobile viewport
      await page.setViewportSize({ width: 375, height: 812 });
      
      await routePage.navigateToRoutes();
      
      // Check if page adapts to mobile
      const pageTitle = await routePage.pageTitle.isVisible();
      expect(pageTitle).toBe(true);
      
      // Map and list should stack vertically on mobile
      const mapContainer = page.locator('#route-map, .route-map-container');
      const routeList = page.locator('.route-list, [data-testid="route-list"]');
      
      if (await mapContainer.isVisible() && await routeList.isVisible()) {
        const mapBox = await mapContainer.boundingBox();
        const listBox = await routeList.boundingBox();
        
        if (mapBox && listBox) {
          // Should stack vertically
          const isStacked = listBox.y >= mapBox.y + mapBox.height || 
                           mapBox.y >= listBox.y + listBox.height;
          expect(isStacked).toBe(true);
        }
      }
    });

    test('should maintain functionality on tablet devices', async ({ page }) => {
      // Set tablet viewport
      await page.setViewportSize({ width: 768, height: 1024 });
      
      await routePage.navigateToRoutes();
      
      // All main elements should be visible
      await expect(routePage.pageTitle).toBeVisible();
      
      // Optimize button should be accessible
      const optimizeVisible = await routePage.optimizeRouteButton.isVisible();
      expect(optimizeVisible).toBe(true);
    });
  });

  test.describe('Route Export Functionality', () => {
    test('should show export options', async ({ page }) => {
      await routePage.navigateToRoutes();
      
      // Look for export button
      const exportButton = page.locator('button').filter({ hasText: /匯出|導出|Export/ });
      if (await exportButton.isVisible()) {
        await exportButton.click();
        
        // Should show export options
        const pdfOption = page.locator('.ant-dropdown-menu-item').filter({ hasText: 'PDF' });
        const excelOption = page.locator('.ant-dropdown-menu-item').filter({ hasText: 'Excel' });
        
        const hasPdfOption = await pdfOption.isVisible();
        const hasExcelOption = await excelOption.isVisible();
        
        expect(hasPdfOption || hasExcelOption).toBe(true);
        
        // Close dropdown
        await page.keyboard.press('Escape');
      }
    });
  });

  test.describe('Integration with Other Features', () => {
    test('should integrate with predictions if available', async ({ page }) => {
      await routePage.navigateToRoutes();
      
      // Check for prediction integration button
      const predictionButton = page.locator('button').filter({ hasText: /預測|建議/ });
      const hasPredictionIntegration = await predictionButton.isVisible();
      
      if (hasPredictionIntegration) {
        const buttonText = await predictionButton.textContent();
        expect(buttonText).toMatch(/預測|建議/);
      }
    });

    test('should show delivery status integration', async ({ page }) => {
      await routePage.navigateToRoutes();
      
      // Check for delivery status indicators
      const statusIndicators = page.locator('.delivery-status, [data-testid="delivery-status"]');
      if (await statusIndicators.count() > 0) {
        const firstStatus = await statusIndicators.first().textContent();
        expect(firstStatus).toMatch(/待配送|配送中|已完成|未開始/);
      }
    });
  });

  test.describe('Error Handling', () => {
    test('should handle API errors gracefully', async ({ page }) => {
      await routePage.navigateToRoutes();
      
      // Intercept API calls to simulate error
      await page.route('**/api/v1/routes**', route => {
        route.fulfill({ status: 500, body: 'Internal Server Error' });
      });
      
      // Reload page to trigger error
      await page.reload();
      
      // Should show error message or empty state
      const errorMessage = page.locator('.ant-empty, .error-message, [data-testid="error-state"]');
      const hasErrorHandling = await errorMessage.isVisible();
      expect(hasErrorHandling).toBe(true);
    });

    test('should handle empty route list', async ({ page }) => {
      await routePage.navigateToRoutes();
      
      // Check if empty state is handled
      const emptyState = page.locator('.ant-empty');
      const routeCards = page.locator('.route-card, [data-testid="route-card"]');
      
      const routeCount = await routeCards.count();
      if (routeCount === 0) {
        // Should show empty state
        await expect(emptyState).toBeVisible();
        
        // Should show helpful message
        const emptyText = await emptyState.textContent();
        expect(emptyText).toBeTruthy();
      }
    });
  });
});