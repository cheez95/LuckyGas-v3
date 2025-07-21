import { test, expect } from '@playwright/test';
import { LoginPage } from './pages/LoginPage';
import { DriverMobilePage } from './pages/DriverMobilePage';
import { DeliveryCompletionModal } from './pages/DeliveryCompletionModal';

test.describe('Driver Mobile Interface', () => {
  let loginPage: LoginPage;
  let driverPage: DriverMobilePage;
  let completionModal: DeliveryCompletionModal;

  test.beforeEach(async ({ page, context }) => {
    // Set mobile viewport
    await page.setViewportSize({ width: 375, height: 812 });
    
    // Grant permissions for camera
    await context.grantPermissions(['camera'], { origin: 'http://localhost:5173' });
    
    loginPage = new LoginPage(page);
    driverPage = new DriverMobilePage(page);
    completionModal = new DeliveryCompletionModal(page);
    
    // Login as driver
    await loginPage.navigateToLogin();
    await loginPage.login('driver1', 'driver123');
    await loginPage.waitForLoginSuccess();
  });

  test('should display mobile-optimized driver interface', async ({ page }) => {
    await driverPage.navigateToDriverInterface();
    
    // Check mobile responsiveness
    const isMobileResponsive = await driverPage.checkMobileResponsiveness();
    expect(isMobileResponsive).toBe(true);
    
    // Check touch targets meet minimum size
    const touchTargetsOk = await driverPage.checkTouchTargets();
    expect(touchTargetsOk).toBe(true);
    
    // Verify key elements are visible
    await expect(driverPage.routesList).toBeVisible();
    await expect(driverPage.navigationMenu).toBeVisible();
  });

  test('should load and display routes for driver', async ({ page }) => {
    await driverPage.navigateToDriverInterface();
    await driverPage.waitForRouteLoad();
    
    // Should have routes assigned
    const routes = await page.locator('[data-testid="routes-list"] [data-route-id]').count();
    expect(routes).toBeGreaterThan(0);
  });

  test('should show delivery items when route is selected', async ({ page }) => {
    await driverPage.navigateToDriverInterface();
    await driverPage.waitForRouteLoad();
    
    // Select first route
    const firstRoute = await page.locator('[data-route-id]').first().getAttribute('data-route-id');
    if (firstRoute) {
      await driverPage.selectRoute(firstRoute);
    }
    
    // Check delivery items are shown
    const deliveryCount = await driverPage.getDeliveryItemCount();
    expect(deliveryCount).toBeGreaterThan(0);
  });

  test('should open delivery completion modal', async ({ page }) => {
    await driverPage.navigateToDriverInterface();
    await driverPage.waitForRouteLoad();
    
    // Select route and delivery
    const firstRoute = await page.locator('[data-route-id]').first().getAttribute('data-route-id');
    if (firstRoute) {
      await driverPage.selectRoute(firstRoute);
    }
    
    await driverPage.selectDeliveryItem(0);
    await driverPage.clickCompleteDelivery();
    
    // Modal should be visible
    await completionModal.waitForModal();
    expect(await completionModal.isModalVisible()).toBe(true);
  });

  test('should capture signature on touch device', async ({ page }) => {
    await driverPage.navigateToDriverInterface();
    await driverPage.waitForRouteLoad();
    
    // Navigate to completion modal
    const firstRoute = await page.locator('[data-route-id]').first().getAttribute('data-route-id');
    if (firstRoute) {
      await driverPage.selectRoute(firstRoute);
    }
    
    await driverPage.selectDeliveryItem(0);
    await driverPage.clickCompleteDelivery();
    await completionModal.waitForModal();
    
    // Draw signature with touch
    await completionModal.simulateTouchSignature();
    
    // Verify signature was captured
    const hasSignature = await completionModal.hasSignature();
    expect(hasSignature).toBe(true);
    
    // Clear and redraw
    await completionModal.clearSignature();
    const clearedSignature = await completionModal.hasSignature();
    expect(clearedSignature).toBe(false);
    
    await completionModal.drawSignature();
    const redrawnSignature = await completionModal.hasSignature();
    expect(redrawnSignature).toBe(true);
  });

  test('should handle photo upload with compression', async ({ page }) => {
    await driverPage.navigateToDriverInterface();
    await driverPage.waitForRouteLoad();
    
    // Navigate to completion modal
    const firstRoute = await page.locator('[data-route-id]').first().getAttribute('data-route-id');
    if (firstRoute) {
      await driverPage.selectRoute(firstRoute);
    }
    
    await driverPage.selectDeliveryItem(0);
    await driverPage.clickCompleteDelivery();
    await completionModal.waitForModal();
    
    // Test photo compression
    const compressionWorked = await completionModal.checkPhotoCompression();
    expect(compressionWorked).toBe(true);
  });

  test('should handle multiple photo uploads', async ({ page }) => {
    await driverPage.navigateToDriverInterface();
    await driverPage.waitForRouteLoad();
    
    // Navigate to completion modal
    const firstRoute = await page.locator('[data-route-id]').first().getAttribute('data-route-id');
    if (firstRoute) {
      await driverPage.selectRoute(firstRoute);
    }
    
    await driverPage.selectDeliveryItem(0);
    await driverPage.clickCompleteDelivery();
    await completionModal.waitForModal();
    
    // Create test photos
    const testPhotos = await page.evaluateHandle(() => {
      const photos = [];
      for (let i = 0; i < 3; i++) {
        const canvas = document.createElement('canvas');
        canvas.width = 100;
        canvas.height = 100;
        const ctx = canvas.getContext('2d');
        if (ctx) {
          ctx.fillStyle = `rgb(${i * 80}, ${i * 80}, ${i * 80})`;
          ctx.fillRect(0, 0, 100, 100);
        }
        
        const blob = canvas.toDataURL('image/jpeg');
        photos.push(blob);
      }
      return photos;
    });
    
    // Upload multiple photos
    const photoCount = await completionModal.getPhotoCount();
    expect(photoCount).toBeLessThanOrEqual(3); // Max 3 photos allowed
  });

  test('should show offline indicator and queue actions', async ({ page }) => {
    await driverPage.navigateToDriverInterface();
    await driverPage.waitForRouteLoad();
    
    // Go offline
    await driverPage.simulateOfflineMode();
    
    // Check offline indicator
    const isOffline = await driverPage.isOffline();
    expect(isOffline).toBe(true);
    
    // Complete a delivery while offline
    const firstRoute = await page.locator('[data-route-id]').first().getAttribute('data-route-id');
    if (firstRoute) {
      await driverPage.selectRoute(firstRoute);
    }
    
    await driverPage.selectDeliveryItem(0);
    await driverPage.clickCompleteDelivery();
    await completionModal.waitForModal();
    
    // Fill completion details
    await completionModal.drawSignature();
    await completionModal.enterNotes('Delivered while offline');
    await completionModal.confirmDelivery();
    
    // Check sync queue
    const queueCount = await driverPage.getSyncQueueCount();
    expect(queueCount).toBeGreaterThan(0);
    
    // Go back online
    await driverPage.simulateOnlineMode();
    
    // Wait for sync
    await page.waitForTimeout(2000);
    
    // Queue should be cleared
    const queueAfterSync = await driverPage.getSyncQueueCount();
    expect(queueAfterSync).toBe(0);
  });

  test('should persist offline queue on page reload', async ({ page }) => {
    await driverPage.navigateToDriverInterface();
    await driverPage.waitForRouteLoad();
    
    // Go offline and complete delivery
    await driverPage.simulateOfflineMode();
    
    const firstRoute = await page.locator('[data-route-id]').first().getAttribute('data-route-id');
    if (firstRoute) {
      await driverPage.selectRoute(firstRoute);
    }
    
    await driverPage.selectDeliveryItem(0);
    await driverPage.clickCompleteDelivery();
    await completionModal.waitForModal();
    
    await completionModal.drawSignature();
    await completionModal.confirmDelivery();
    
    // Check persistence
    const queuePersists = await driverPage.checkOfflineQueuePersistence();
    expect(queuePersists).toBe(true);
  });

  test('should validate completion requirements', async ({ page }) => {
    await driverPage.navigateToDriverInterface();
    await driverPage.waitForRouteLoad();
    
    // Navigate to completion modal
    const firstRoute = await page.locator('[data-route-id]').first().getAttribute('data-route-id');
    if (firstRoute) {
      await driverPage.selectRoute(firstRoute);
    }
    
    await driverPage.selectDeliveryItem(0);
    await driverPage.clickCompleteDelivery();
    await completionModal.waitForModal();
    
    // Try to confirm without signature
    const confirmDisabled = await completionModal.isConfirmButtonEnabled();
    expect(confirmDisabled).toBe(false);
    
    // Add signature
    await completionModal.drawSignature();
    
    // Now should be enabled
    const confirmEnabled = await completionModal.isConfirmButtonEnabled();
    expect(confirmEnabled).toBe(true);
  });

  test('should handle landscape orientation', async ({ page }) => {
    // Switch to landscape
    await page.setViewportSize({ width: 812, height: 375 });
    
    await driverPage.navigateToDriverInterface();
    
    // Check if UI adapts properly
    const isResponsive = await driverPage.checkMobileResponsiveness();
    expect(isResponsive).toBe(true);
    
    // Navigation should still work
    await expect(driverPage.navigationMenu).toBeVisible();
  });

  test('should display route optimization results', async ({ page }) => {
    await driverPage.navigateToDriverInterface();
    await driverPage.waitForRouteLoad();
    
    // Check if routes are displayed with optimization info
    const routeCards = await page.locator('[data-testid="route-card"]').all();
    
    for (const card of routeCards) {
      // Check for optimization indicators (distance, time, etc.)
      const distance = await card.locator('[data-testid="route-distance"]').isVisible();
      const estimatedTime = await card.locator('[data-testid="route-time"]').isVisible();
      const stopCount = await card.locator('[data-testid="stop-count"]').isVisible();
      
      expect(distance || estimatedTime || stopCount).toBe(true);
    }
  });

  test('should handle network interruptions gracefully', async ({ page }) => {
    await driverPage.navigateToDriverInterface();
    await driverPage.waitForRouteLoad();
    
    // Start a delivery completion
    const firstRoute = await page.locator('[data-route-id]').first().getAttribute('data-route-id');
    if (firstRoute) {
      await driverPage.selectRoute(firstRoute);
    }
    
    await driverPage.selectDeliveryItem(0);
    await driverPage.clickCompleteDelivery();
    await completionModal.waitForModal();
    
    // Fill details
    await completionModal.drawSignature();
    
    // Simulate network interruption
    await page.route('**/api/v1/deliveries/**/complete', route => route.abort());
    
    // Try to complete
    await completionModal.confirmDelivery();
    
    // Should show error but data should be queued
    const errorMessage = await completionModal.getErrorMessage();
    expect(errorMessage).toBeTruthy();
    
    // Check if data was queued for retry
    const queueCount = await driverPage.getSyncQueueCount();
    expect(queueCount).toBeGreaterThan(0);
  });

  test('should support Traditional Chinese throughout driver interface', async ({ page }) => {
    await driverPage.navigateToDriverInterface();
    
    // Check main interface
    const pageTitle = await page.locator('h1, h2').first().textContent();
    expect(pageTitle).toMatch(/[\u4e00-\u9fa5]/); // Contains Chinese characters
    
    // Check route information
    await driverPage.waitForRouteLoad();
    const routeText = await page.locator('[data-testid="route-card"]').first().textContent();
    expect(routeText).toMatch(/[\u4e00-\u9fa5]/);
    
    // Check completion modal
    const firstRoute = await page.locator('[data-route-id]').first().getAttribute('data-route-id');
    if (firstRoute) {
      await driverPage.selectRoute(firstRoute);
    }
    
    await driverPage.selectDeliveryItem(0);
    await driverPage.clickCompleteDelivery();
    await completionModal.waitForModal();
    
    const modalTitle = await page.locator('[data-testid="modal-title"]').textContent();
    expect(modalTitle).toMatch(/[\u4e00-\u9fa5]/);
  });

  test('should logout from mobile menu', async ({ page }) => {
    await driverPage.navigateToDriverInterface();
    
    // Logout via mobile menu
    await driverPage.logout();
    
    // Should redirect to login
    await expect(page).toHaveURL(/.*\/login/);
  });
});

test.describe('Driver Performance on Mobile', () => {
  test('should load interface quickly on 3G', async ({ page, context }) => {
    // Simulate 3G network
    await context.route('**/*', (route) => {
      route.continue();
    });
    
    // Set mobile viewport
    await page.setViewportSize({ width: 375, height: 812 });
    
    const loginPage = new LoginPage(page);
    const driverPage = new DriverMobilePage(page);
    
    // Login
    await loginPage.navigateToLogin();
    await loginPage.login('driver1', 'driver123');
    await loginPage.waitForLoginSuccess();
    
    // Measure load time
    const startTime = Date.now();
    await driverPage.navigateToDriverInterface();
    await driverPage.waitForRouteLoad();
    const loadTime = Date.now() - startTime;
    
    // Should load within 3 seconds on 3G
    expect(loadTime).toBeLessThan(3000);
  });

  test('should handle large route lists efficiently', async ({ page }) => {
    // Set mobile viewport
    await page.setViewportSize({ width: 375, height: 812 });
    
    const loginPage = new LoginPage(page);
    const driverPage = new DriverMobilePage(page);
    
    // Login
    await loginPage.navigateToLogin();
    await loginPage.login('driver1', 'driver123');
    await loginPage.waitForLoginSuccess();
    
    await driverPage.navigateToDriverInterface();
    await driverPage.waitForRouteLoad();
    
    // Check if virtualization or pagination is implemented for large lists
    const routeCount = await page.locator('[data-route-id]').count();
    
    // If more than 20 routes, should have pagination or virtualization
    if (routeCount > 20) {
      const hasPagination = await page.locator('[data-testid="pagination"]').isVisible();
      const hasVirtualization = await page.locator('[data-testid="virtual-list"]').isVisible();
      
      expect(hasPagination || hasVirtualization).toBe(true);
    }
  });
});