import { test, expect, Page } from '@playwright/test';

test.describe('Offline Mode Functionality', () => {
  let page: Page;

  test.beforeEach(async ({ page: p }) => {
    page = p;
    // Navigate to driver interface
    await page.goto('/driver');
  });

  test('should show offline indicator when network is disconnected', async () => {
    // Go offline
    await page.context().setOffline(true);
    
    // Wait for offline indicator to appear
    await expect(page.locator('[data-testid="offline-indicator"]')).toBeVisible();
    
    // Check if the indicator shows offline status
    await expect(page.locator('[data-testid="offline-indicator"]')).toContainText('離線模式');
  });

  test('should save delivery completion while offline', async () => {
    // Setup: Navigate to a delivery
    await page.click('[data-testid="delivery-item"]:first-child');
    
    // Go offline
    await page.context().setOffline(true);
    
    // Complete delivery
    await page.click('[data-testid="complete-delivery-btn"]');
    
    // Fill completion form
    await page.fill('[data-testid="delivery-notes"]', 'Delivered to customer');
    
    // Draw signature (simulate)
    const canvas = await page.locator('[data-testid="signature-canvas"]');
    const box = await canvas.boundingBox();
    if (box) {
      await page.mouse.move(box.x + box.width / 2, box.y + box.height / 2);
      await page.mouse.down();
      await page.mouse.move(box.x + box.width / 2 + 50, box.y + box.height / 2 + 50);
      await page.mouse.up();
    }
    
    // Submit
    await page.click('[data-testid="submit-delivery"]');
    
    // Check for offline success message
    await expect(page.locator('.ant-message')).toContainText('離線模式');
    
    // Verify local state updated
    await expect(page.locator('[data-testid="delivery-item"]:first-child')).toHaveClass(/completed/);
  });

  test('should show sync progress when coming back online', async () => {
    // Start offline
    await page.context().setOffline(true);
    
    // Perform some offline actions
    await page.click('[data-testid="delivery-item"]:first-child');
    await page.click('[data-testid="complete-delivery-btn"]');
    await page.fill('[data-testid="delivery-notes"]', 'Test delivery');
    await page.click('[data-testid="submit-delivery"]');
    
    // Go back online
    await page.context().setOffline(false);
    
    // Wait for sync to start
    await expect(page.locator('[data-testid="sync-progress"]')).toBeVisible();
    
    // Wait for sync to complete
    await expect(page.locator('[data-testid="sync-status"]')).toContainText('已同步', { timeout: 10000 });
  });

  test('should cache route data for offline use', async () => {
    // Load route data while online
    await page.waitForSelector('[data-testid="route-data"]');
    
    // Go offline
    await page.context().setOffline(true);
    
    // Refresh page
    await page.reload();
    
    // Route data should still be visible
    await expect(page.locator('[data-testid="route-data"]')).toBeVisible();
    await expect(page.locator('[data-testid="offline-indicator"]')).toBeVisible();
  });

  test('should track location while offline', async () => {
    // Grant location permission
    await page.context().grantPermissions(['geolocation']);
    await page.context().setGeolocation({ latitude: 25.0330, longitude: 121.5654 });
    
    // Start tracking
    await page.click('[data-testid="start-tracking"]');
    
    // Go offline
    await page.context().setOffline(true);
    
    // Update location
    await page.context().setGeolocation({ latitude: 25.0340, longitude: 121.5664 });
    
    // Wait a bit for location to be saved
    await page.waitForTimeout(2000);
    
    // Check if location is being tracked (visual indicator)
    await expect(page.locator('[data-testid="location-tracking"]')).toBeVisible();
  });

  test('should handle photo uploads while offline', async () => {
    // Navigate to delivery completion
    await page.click('[data-testid="delivery-item"]:first-child');
    await page.click('[data-testid="complete-delivery-btn"]');
    
    // Go offline
    await page.context().setOffline(true);
    
    // Upload photo
    const fileInput = await page.locator('input[type="file"]');
    await fileInput.setInputFiles({
      name: 'delivery-photo.jpg',
      mimeType: 'image/jpeg',
      buffer: Buffer.from('fake-image-data'),
    });
    
    // Submit delivery
    await page.click('[data-testid="submit-delivery"]');
    
    // Check for success message
    await expect(page.locator('.ant-message')).toContainText('離線模式');
  });

  test('should display storage quota warning', async () => {
    // This test would simulate low storage conditions
    // In a real scenario, you'd need to fill up storage to trigger the warning
    
    // Navigate to settings or a page that shows storage info
    await page.goto('/driver/settings');
    
    // Check if storage indicator is visible
    await expect(page.locator('[data-testid="storage-status"]')).toBeVisible();
  });

  test('should handle conflict resolution after sync', async () => {
    // This test simulates a conflict scenario
    // 1. Go offline and make changes
    await page.context().setOffline(true);
    await page.click('[data-testid="delivery-item"]:first-child');
    await page.click('[data-testid="complete-delivery-btn"]');
    await page.fill('[data-testid="delivery-notes"]', 'Offline delivery');
    await page.click('[data-testid="submit-delivery"]');
    
    // 2. Simulate server-side change (would need API mock)
    // This would typically be done through API mocking
    
    // 3. Go back online
    await page.context().setOffline(false);
    
    // 4. Wait for conflict dialog
    await expect(page.locator('[data-testid="conflict-dialog"]')).toBeVisible({ timeout: 10000 });
    
    // 5. Choose resolution
    await page.click('[data-testid="use-local-version"]');
    
    // 6. Verify resolution
    await expect(page.locator('[data-testid="conflict-resolved"]')).toBeVisible();
  });

  test('should work with service worker for true offline experience', async ({ browser }) => {
    // Create a new context with service worker enabled
    const context = await browser.newContext({
      serviceWorkers: 'allow',
    });
    const page = await context.newPage();
    
    // Navigate to the app
    await page.goto('/');
    
    // Wait for service worker to be ready
    await page.waitForTimeout(3000);
    
    // Go offline
    await context.setOffline(true);
    
    // Navigate to driver page - should work offline
    await page.goto('/driver');
    
    // Page should load from service worker cache
    await expect(page.locator('body')).toBeVisible();
    
    // Clean up
    await context.close();
  });
});

test.describe('Background Sync', () => {
  test('should trigger background sync when coming online', async ({ page }) => {
    // Monitor network requests
    const syncRequests: string[] = [];
    page.on('request', (request) => {
      if (request.url().includes('/api/v1/sync')) {
        syncRequests.push(request.url());
      }
    });
    
    // Start offline
    await page.context().setOffline(true);
    
    // Perform offline actions
    await page.goto('/driver');
    await page.click('[data-testid="delivery-item"]:first-child');
    await page.click('[data-testid="complete-delivery-btn"]');
    await page.fill('[data-testid="delivery-notes"]', 'Test');
    await page.click('[data-testid="submit-delivery"]');
    
    // Go online
    await page.context().setOffline(false);
    
    // Wait for sync
    await page.waitForTimeout(5000);
    
    // Verify sync requests were made
    expect(syncRequests.length).toBeGreaterThan(0);
  });
});