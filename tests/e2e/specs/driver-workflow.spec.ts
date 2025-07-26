import { test, expect, devices } from '@playwright/test';
import { test as customTest } from '../fixtures/test-helpers';
import { LoginPage } from '../pages/LoginPage';
import { TestUsers, TestRoutes, SuccessMessages } from '../fixtures/test-data';

// Use mobile viewport for driver tests
test.use({
  ...devices['Pixel 5'],
  locale: 'zh-TW',
  timezoneId: 'Asia/Taipei',
});

test.describe('Driver Workflow Tests', () => {
  let loginPage: LoginPage;

  test.beforeEach(async ({ page }) => {
    loginPage = new LoginPage(page);
    await loginPage.goto();
    await loginPage.login(TestUsers.driver.email, TestUsers.driver.password);
    
    // Should redirect to driver dashboard
    await expect(page).toHaveURL(/\/driver/);
  });

  test.describe('Driver Dashboard', () => {
    test('should display driver dashboard optimized for mobile', async ({ page }) => {
      // Verify mobile-optimized layout
      await expect(page.locator('[data-testid="driver-mobile-header"]')).toBeVisible();
      await expect(page.locator('[data-testid="today-routes"]')).toBeVisible();
      await expect(page.locator('[data-testid="delivery-summary"]')).toBeVisible();
      
      // Check touch-friendly buttons
      const startButton = page.locator('[data-testid="start-route-button"]');
      const buttonSize = await startButton.boundingBox();
      expect(buttonSize?.height).toBeGreaterThanOrEqual(44); // Min touch target size
    });

    test('should show assigned routes for the day', async ({ page }) => {
      // Verify route list
      const routes = await page.locator('[data-testid="route-item"]').count();
      expect(routes).toBeGreaterThan(0);
      
      // Check route details
      const firstRoute = page.locator('[data-testid="route-item"]:first-child');
      await expect(firstRoute.locator('[data-testid="route-name"]')).toBeVisible();
      await expect(firstRoute.locator('[data-testid="delivery-count"]')).toBeVisible();
      await expect(firstRoute.locator('[data-testid="estimated-time"]')).toBeVisible();
    });

    test('should display delivery statistics', async ({ page }) => {
      const stats = {
        total: await page.locator('[data-testid="total-deliveries"]').textContent(),
        completed: await page.locator('[data-testid="completed-deliveries"]').textContent(),
        pending: await page.locator('[data-testid="pending-deliveries"]').textContent(),
      };
      
      expect(parseInt(stats.total || '0')).toBeGreaterThan(0);
      expect(parseInt(stats.completed || '0')).toBeGreaterThanOrEqual(0);
      expect(parseInt(stats.pending || '0')).toBeGreaterThanOrEqual(0);
    });
  });

  test.describe('Route Navigation', () => {
    test('should start route and show first delivery', async ({ page }) => {
      // Select a route
      await page.click('[data-testid="route-item"]:first-child');
      
      // Start route
      await page.click('[data-testid="start-route-button"]');
      
      // Should show first delivery
      await expect(page.locator('[data-testid="current-delivery"]')).toBeVisible();
      await expect(page.locator('[data-testid="customer-name"]')).toBeVisible();
      await expect(page.locator('[data-testid="delivery-address"]')).toBeVisible();
      await expect(page.locator('[data-testid="delivery-products"]')).toBeVisible();
    });

    test('should show optimized route on map', async ({ page }) => {
      await page.click('[data-testid="route-item"]:first-child');
      await page.click('[data-testid="view-map-button"]');
      
      // Verify map is displayed
      await expect(page.locator('[data-testid="route-map-container"]')).toBeVisible();
      
      // Check route markers
      await expect(page.locator('[data-testid="current-location-marker"]')).toBeVisible();
      await expect(page.locator('[data-testid="delivery-marker"]')).toHaveCount(5); // Based on test data
      
      // Verify route line
      await expect(page.locator('[data-testid="route-polyline"]')).toBeVisible();
    });

    test('should provide turn-by-turn navigation', async ({ page }) => {
      await page.click('[data-testid="route-item"]:first-child');
      await page.click('[data-testid="start-route-button"]');
      
      // Start navigation
      await page.click('[data-testid="start-navigation-button"]');
      
      // Check navigation instructions
      await expect(page.locator('[data-testid="navigation-instruction"]')).toBeVisible();
      await expect(page.locator('[data-testid="distance-to-turn"]')).toBeVisible();
      await expect(page.locator('[data-testid="eta"]')).toBeVisible();
      
      // Verify voice navigation toggle
      await page.click('[data-testid="voice-navigation-toggle"]');
      await expect(page.locator('[data-testid="voice-enabled-indicator"]')).toBeVisible();
    });

    test('should handle offline navigation', async ({ page, context }) => {
      // Load route first
      await page.click('[data-testid="route-item"]:first-child');
      await page.click('[data-testid="download-offline-button"]');
      
      // Wait for download
      await expect(page.locator('[data-testid="offline-ready-badge"]')).toBeVisible();
      
      // Go offline
      await context.setOffline(true);
      
      // Should still show route
      await page.click('[data-testid="start-route-button"]');
      await expect(page.locator('[data-testid="offline-mode-banner"]')).toBeVisible();
      await expect(page.locator('[data-testid="current-delivery"]')).toBeVisible();
      
      // Go back online
      await context.setOffline(false);
    });
  });

  test.describe('Delivery Completion', () => {
    test('should complete delivery with signature', async ({ page }) => {
      // Navigate to a delivery
      await page.click('[data-testid="route-item"]:first-child');
      await page.click('[data-testid="start-route-button"]');
      
      // Arrive at delivery location
      await page.click('[data-testid="arrived-button"]');
      
      // Complete delivery steps
      await page.click('[data-testid="delivered-button"]');
      
      // Should show completion modal
      await expect(page.locator('[data-testid="delivery-completion-modal"]')).toBeVisible();
      
      // Add signature
      const canvas = page.locator('[data-testid="signature-canvas"]');
      const box = await canvas.boundingBox();
      if (box) {
        // Draw signature
        await page.mouse.move(box.x + 50, box.y + 50);
        await page.mouse.down();
        await page.mouse.move(box.x + 150, box.y + 50);
        await page.mouse.move(box.x + 150, box.y + 100);
        await page.mouse.up();
      }
      
      // Add notes
      await page.fill('[data-testid="delivery-notes"]', '已交付給警衛室');
      
      // Submit
      await page.click('[data-testid="confirm-delivery-button"]');
      
      // Should show success and move to next delivery
      await expect(page.locator('[data-testid="success-toast"]')).toBeVisible();
      await expect(page.locator('[data-testid="current-delivery"]')).toContainText(/2 \/ 5/); // Next delivery
    });

    test('should complete delivery with photo proof', async ({ page }) => {
      await page.click('[data-testid="route-item"]:first-child');
      await page.click('[data-testid="start-route-button"]');
      await page.click('[data-testid="arrived-button"]');
      await page.click('[data-testid="delivered-button"]');
      
      // Take photo
      await page.click('[data-testid="take-photo-button"]');
      
      // Mock camera permission and capture
      await page.locator('[data-testid="camera-preview"]').waitFor();
      await page.click('[data-testid="capture-button"]');
      
      // Should show photo preview
      await expect(page.locator('[data-testid="photo-preview"]')).toBeVisible();
      
      // Can retake if needed
      await page.click('[data-testid="retake-button"]');
      await page.click('[data-testid="capture-button"]');
      
      // Confirm photo
      await page.click('[data-testid="use-photo-button"]');
      
      // Complete delivery
      await page.click('[data-testid="confirm-delivery-button"]');
      await expect(page.locator('[data-testid="success-toast"]')).toBeVisible();
    });

    test('should handle delivery issues', async ({ page }) => {
      await page.click('[data-testid="route-item"]:first-child');
      await page.click('[data-testid="start-route-button"]');
      await page.click('[data-testid="arrived-button"]');
      
      // Report issue
      await page.click('[data-testid="report-issue-button"]');
      
      // Select issue type
      await page.click('[data-testid="issue-type-absent"]');
      
      // Add details
      await page.fill('[data-testid="issue-notes"]', '客戶不在家，已聯絡但無回應');
      
      // Submit issue
      await page.click('[data-testid="submit-issue-button"]');
      
      // Should update order status
      await expect(page.locator('[data-testid="delivery-status"]')).toContainText('無法配送');
      
      // Should move to next delivery
      await page.click('[data-testid="next-delivery-button"]');
      await expect(page.locator('[data-testid="current-delivery"]')).toContainText(/2 \/ 5/);
    });

    test('should handle customer rejection', async ({ page }) => {
      await page.click('[data-testid="route-item"]:first-child');
      await page.click('[data-testid="start-route-button"]');
      await page.click('[data-testid="arrived-button"]');
      
      // Customer rejects delivery
      await page.click('[data-testid="report-issue-button"]');
      await page.click('[data-testid="issue-type-rejected"]');
      
      // Select reason
      await page.selectOption('[data-testid="rejection-reason"]', 'wrong_product');
      await page.fill('[data-testid="issue-notes"]', '客戶訂購20kg但送成50kg');
      
      // Submit
      await page.click('[data-testid="submit-issue-button"]');
      
      // Should notify office
      await expect(page.locator('[data-testid="office-notified-badge"]')).toBeVisible();
    });
  });

  test.describe('Communication Features', () => {
    test('should call customer from app', async ({ page }) => {
      await page.click('[data-testid="route-item"]:first-child');
      await page.click('[data-testid="start-route-button"]');
      
      // Click call button
      await page.click('[data-testid="call-customer-button"]');
      
      // Should show call dialog with customer info
      await expect(page.locator('[data-testid="call-dialog"]')).toBeVisible();
      await expect(page.locator('[data-testid="customer-phone"]')).toContainText(/09\d{2}-?\d{3}-?\d{3}/);
      
      // Initiate call (will open phone app on real device)
      await page.click('[data-testid="confirm-call-button"]');
    });

    test('should send SMS to customer', async ({ page }) => {
      await page.click('[data-testid="route-item"]:first-child');
      await page.click('[data-testid="start-route-button"]');
      
      // Open SMS options
      await page.click('[data-testid="sms-customer-button"]');
      
      // Select template
      await page.click('[data-testid="sms-template-arriving"]');
      
      // Should pre-fill message
      const message = await page.locator('[data-testid="sms-message"]').inputValue();
      expect(message).toContain('即將到達');
      expect(message).toContain('幸福氣');
      
      // Send SMS
      await page.click('[data-testid="send-sms-button"]');
      await expect(page.locator('[data-testid="sms-sent-indicator"]')).toBeVisible();
    });

    test('should communicate with office via chat', async ({ page }) => {
      // Open chat
      await page.click('[data-testid="office-chat-button"]');
      
      // Should show chat interface
      await expect(page.locator('[data-testid="chat-window"]')).toBeVisible();
      
      // Send message
      await page.fill('[data-testid="chat-input"]', '客戶要求改期，請協助處理');
      await page.press('[data-testid="chat-input"]', 'Enter');
      
      // Should show sent message
      await expect(page.locator('[data-testid="chat-message-sent"]')).toContainText('客戶要求改期');
      
      // Simulate office response
      await page.waitForTimeout(1000);
      await expect(page.locator('[data-testid="chat-message-received"]')).toBeVisible();
    });
  });

  test.describe('End of Day Operations', () => {
    test('should complete route summary', async ({ page }) => {
      // Navigate to completed route
      await page.goto('/driver/routes/completed');
      
      // Select today's route
      await page.click('[data-testid="completed-route"]:first-child');
      
      // View summary
      await expect(page.locator('[data-testid="route-summary"]')).toBeVisible();
      
      const summary = {
        totalDeliveries: await page.locator('[data-testid="total-deliveries"]').textContent(),
        completed: await page.locator('[data-testid="completed-count"]').textContent(),
        failed: await page.locator('[data-testid="failed-count"]').textContent(),
        totalDistance: await page.locator('[data-testid="total-distance"]').textContent(),
        totalTime: await page.locator('[data-testid="total-time"]').textContent(),
      };
      
      expect(parseInt(summary.totalDeliveries || '0')).toBeGreaterThan(0);
    });

    test('should submit cylinder return report', async ({ page }) => {
      await page.goto('/driver/cylinder-return');
      
      // Add returned cylinders
      await page.click('[data-testid="add-cylinder-button"]');
      await page.selectOption('[data-testid="cylinder-type"]', '20kg');
      await page.fill('[data-testid="cylinder-count"]', '5');
      await page.fill('[data-testid="cylinder-condition"]', 'good');
      
      // Add another type
      await page.click('[data-testid="add-cylinder-button"]');
      await page.selectOption('[data-testid="cylinder-type"]:last-child', '50kg');
      await page.fill('[data-testid="cylinder-count"]:last-child', '3');
      
      // Submit report
      await page.click('[data-testid="submit-return-report"]');
      
      await expect(page.locator('[data-testid="success-message"]')).toContainText('回收報告已提交');
    });

    test('should clock out at end of day', async ({ page }) => {
      await page.goto('/driver');
      
      // Click clock out
      await page.click('[data-testid="clock-out-button"]');
      
      // Confirm dialog
      await page.click('[data-testid="confirm-clock-out"]');
      
      // Should show summary
      await expect(page.locator('[data-testid="day-summary-modal"]')).toBeVisible();
      
      // Verify working hours
      const workingHours = await page.locator('[data-testid="working-hours"]').textContent();
      expect(workingHours).toMatch(/\d+小時\d+分/);
      
      // Close summary
      await page.click('[data-testid="close-summary-button"]');
      
      // Should redirect to login
      await expect(page).toHaveURL('/login');
    });
  });

  test.describe('Performance and Reliability', () => {
    test('should work on slow network', async ({ page, context }) => {
      // Simulate slow 3G
      const client = await context.newCDPSession(page);
      await client.send('Network.emulateNetworkConditions', {
        offline: false,
        downloadThroughput: 50 * 1024 / 8,
        uploadThroughput: 50 * 1024 / 8,
        latency: 400,
      });
      
      // Load route
      await page.click('[data-testid="route-item"]:first-child');
      
      // Should show loading indicator
      await expect(page.locator('[data-testid="loading-indicator"]')).toBeVisible();
      
      // But should eventually load
      await expect(page.locator('[data-testid="route-details"]')).toBeVisible({ timeout: 10000 });
    });

    test('should handle GPS errors gracefully', async ({ page, context }) => {
      // Mock GPS error
      await context.grantPermissions(['geolocation']);
      await page.addInitScript(() => {
        navigator.geolocation.getCurrentPosition = (success, error) => {
          error({ code: 1, message: 'User denied Geolocation' });
        };
      });
      
      await page.click('[data-testid="route-item"]:first-child');
      await page.click('[data-testid="start-route-button"]');
      
      // Should show GPS error but allow manual progress
      await expect(page.locator('[data-testid="gps-error-banner"]')).toBeVisible();
      await expect(page.locator('[data-testid="manual-navigation-button"]')).toBeVisible();
    });

    test('should sync data when connection restored', async ({ page, context }) => {
      await page.click('[data-testid="route-item"]:first-child');
      await page.click('[data-testid="start-route-button"]');
      
      // Go offline
      await context.setOffline(true);
      
      // Complete a delivery offline
      await page.click('[data-testid="arrived-button"]');
      await page.click('[data-testid="delivered-button"]');
      await page.click('[data-testid="skip-signature-button"]'); // Simplified for offline
      await page.click('[data-testid="confirm-delivery-button"]');
      
      // Should queue for sync
      await expect(page.locator('[data-testid="pending-sync-badge"]')).toBeVisible();
      
      // Go back online
      await context.setOffline(false);
      
      // Should sync automatically
      await expect(page.locator('[data-testid="sync-complete-indicator"]')).toBeVisible({ timeout: 5000 });
      await expect(page.locator('[data-testid="pending-sync-badge"]')).not.toBeVisible();
    });
  });
});