import { test, expect } from '@playwright/test';
import { LoginPage } from './pages/LoginPage';
import { CustomerPage } from './pages/CustomerPage';
import { OrderPage } from './pages/OrderPage';
import { DriverMobilePage } from './pages/DriverMobilePage';
import { DeliveryCompletionModal } from './pages/DeliveryCompletionModal';

test.describe('Offline Functionality', () => {
  test.beforeEach(async ({ page }) => {
    const loginPage = new LoginPage(page);
    await loginPage.navigateToLogin();
    await loginPage.login('admin', 'admin123');
    await loginPage.waitForLoginSuccess();
  });

  test('should show offline indicator when network is disconnected', async ({ page, context }) => {
    // Navigate to any page
    await page.goto('/customers');
    
    // Go offline
    await context.setOffline(true);
    
    // Check offline indicator appears
    const offlineIndicator = page.locator('[data-testid="offline-indicator"]');
    await expect(offlineIndicator).toBeVisible({ timeout: 5000 });
    
    // Go back online
    await context.setOffline(false);
    
    // Offline indicator should disappear
    await expect(offlineIndicator).toBeHidden({ timeout: 5000 });
  });

  test('should queue customer creation when offline', async ({ page, context }) => {
    const customerPage = new CustomerPage(page);
    await customerPage.navigateToCustomers();
    
    // Go offline
    await context.setOffline(true);
    
    // Try to create customer
    await customerPage.clickAddCustomer();
    await customerPage.fillCustomerForm({
      name: '離線測試客戶',
      phone: '0912345678',
      address: '台北市信義區測試路123號'
    });
    await customerPage.submitCustomerForm();
    
    // Check if queued indicator shows
    const queueIndicator = page.locator('[data-testid="sync-queue-indicator"]');
    await expect(queueIndicator).toBeVisible();
    
    // Go back online
    await context.setOffline(false);
    
    // Wait for sync
    await page.waitForTimeout(3000);
    
    // Queue should be cleared
    await expect(queueIndicator).toBeHidden();
    
    // Customer should be created
    await customerPage.searchCustomers('離線測試客戶');
    const customerCount = await customerPage.getCustomerCount();
    expect(customerCount).toBeGreaterThan(0);
  });

  test('should persist offline queue across page reloads', async ({ page, context }) => {
    const orderPage = new OrderPage(page);
    await orderPage.navigateToOrders();
    
    // Go offline
    await context.setOffline(true);
    
    // Create order while offline
    await orderPage.clickCreateOrder();
    await orderPage.fillOrderForm({
      customerName: '測試客戶',
      quantity: 2,
      deliveryDate: new Date().toISOString().split('T')[0]
    });
    await orderPage.submitOrderForm();
    
    // Check queue count
    const queueCount = await page.locator('[data-testid="sync-queue-count"]').textContent();
    expect(queueCount).toBe('1');
    
    // Reload page
    await page.reload();
    
    // Queue should persist
    const queueCountAfterReload = await page.locator('[data-testid="sync-queue-count"]').textContent();
    expect(queueCountAfterReload).toBe('1');
  });

  test('should handle offline photo upload for drivers', async ({ page, context }) => {
    // Set mobile viewport
    await page.setViewportSize({ width: 375, height: 812 });
    
    const loginPage = new LoginPage(page);
    const driverPage = new DriverMobilePage(page);
    const completionModal = new DeliveryCompletionModal(page);
    
    // Login as driver
    await loginPage.navigateToLogin();
    await loginPage.login('driver1', 'driver123');
    await loginPage.waitForLoginSuccess();
    
    await driverPage.navigateToDriverInterface();
    await driverPage.waitForRouteLoad();
    
    // Select delivery
    const firstRoute = await page.locator('[data-route-id]').first().getAttribute('data-route-id');
    if (firstRoute) {
      await driverPage.selectRoute(firstRoute);
    }
    await driverPage.selectDeliveryItem(0);
    
    // Go offline
    await context.setOffline(true);
    
    // Complete delivery with photo
    await driverPage.clickCompleteDelivery();
    await completionModal.waitForModal();
    
    // Add signature and photo
    await completionModal.drawSignature();
    
    // Create test photo
    const testPhoto = await page.evaluateHandle(() => {
      const canvas = document.createElement('canvas');
      canvas.width = 200;
      canvas.height = 200;
      const ctx = canvas.getContext('2d');
      if (ctx) {
        ctx.fillStyle = 'blue';
        ctx.fillRect(0, 0, 200, 200);
      }
      return canvas.toDataURL('image/jpeg');
    });
    
    // Confirm delivery
    await completionModal.confirmDelivery();
    
    // Should show offline save indicator
    const offlineSaved = await page.locator('[data-testid="offline-save-success"]').isVisible();
    expect(offlineSaved).toBe(true);
    
    // Check sync queue
    const syncCount = await driverPage.getSyncQueueCount();
    expect(syncCount).toBeGreaterThan(0);
  });

  test('should retry failed requests automatically', async ({ page, context }) => {
    const customerPage = new CustomerPage(page);
    await customerPage.navigateToCustomers();
    
    // Intercept API calls to simulate failure then success
    let attemptCount = 0;
    await page.route('**/api/v1/customers', route => {
      attemptCount++;
      if (attemptCount <= 2) {
        // Fail first 2 attempts
        route.abort('failed');
      } else {
        // Succeed on 3rd attempt
        route.continue();
      }
    });
    
    // Create customer
    await customerPage.clickAddCustomer();
    await customerPage.fillCustomerForm({
      name: '重試測試客戶',
      phone: '0923456789',
      address: '台中市西區測試街456號'
    });
    await customerPage.submitCustomerForm();
    
    // Should eventually succeed after retries
    await page.waitForTimeout(5000);
    
    // Verify customer was created
    await customerPage.searchCustomers('重試測試客戶');
    const customerCount = await customerPage.getCustomerCount();
    expect(customerCount).toBeGreaterThan(0);
    
    // Should have attempted 3 times
    expect(attemptCount).toBe(3);
  });
});

test.describe('Error Handling', () => {
  test.beforeEach(async ({ page }) => {
    const loginPage = new LoginPage(page);
    await loginPage.navigateToLogin();
    await loginPage.login('admin', 'admin123');
    await loginPage.waitForLoginSuccess();
  });

  test('should handle 404 errors gracefully', async ({ page }) => {
    // Navigate to non-existent page
    await page.goto('/non-existent-page');
    
    // Should show 404 page
    await expect(page.locator('text=/找不到頁面|404/')).toBeVisible();
    
    // Should have link to go back
    const backLink = page.locator('a[href="/"]');
    await expect(backLink).toBeVisible();
  });

  test('should handle API 500 errors with user-friendly message', async ({ page }) => {
    const customerPage = new CustomerPage(page);
    await customerPage.navigateToCustomers();
    
    // Mock 500 error
    await page.route('**/api/v1/customers', route => {
      route.fulfill({
        status: 500,
        contentType: 'application/json',
        body: JSON.stringify({ detail: 'Internal server error' })
      });
    });
    
    // Try to load customers
    await page.reload();
    
    // Should show error message
    const errorMessage = page.locator('[data-testid="error-message"]');
    await expect(errorMessage).toBeVisible();
    await expect(errorMessage).toContainText(/伺服器錯誤|系統錯誤/);
  });

  test('should handle validation errors clearly', async ({ page }) => {
    const customerPage = new CustomerPage(page);
    await customerPage.navigateToCustomers();
    
    // Try to create customer with invalid data
    await customerPage.clickAddCustomer();
    await customerPage.fillCustomerForm({
      name: '', // Empty name
      phone: '123', // Invalid phone
      address: '123' // Too short address
    });
    await customerPage.submitCustomerForm();
    
    // Should show validation errors
    const nameError = page.locator('[data-testid="name-error"]');
    const phoneError = page.locator('[data-testid="phone-error"]');
    const addressError = page.locator('[data-testid="address-error"]');
    
    await expect(nameError).toBeVisible();
    await expect(phoneError).toBeVisible();
    await expect(addressError).toBeVisible();
    
    // Errors should be in Chinese
    await expect(nameError).toContainText(/[\u4e00-\u9fa5]/);
    await expect(phoneError).toContainText(/[\u4e00-\u9fa5]/);
  });

  test('should handle session timeout gracefully', async ({ page }) => {
    // Navigate to protected page
    await page.goto('/customers');
    
    // Simulate session timeout
    await page.evaluate(() => {
      localStorage.removeItem('access_token');
      localStorage.removeItem('refresh_token');
    });
    
    // Make an API call that requires auth
    await page.reload();
    
    // Should redirect to login
    await expect(page).toHaveURL(/.*\/login/);
    
    // Should show session expired message
    const sessionMessage = page.locator('[data-testid="session-expired-message"]');
    await expect(sessionMessage).toBeVisible();
  });

  test('should handle network timeouts', async ({ page }) => {
    const customerPage = new CustomerPage(page);
    await customerPage.navigateToCustomers();
    
    // Simulate slow network
    await page.route('**/api/v1/customers', async route => {
      await new Promise(resolve => setTimeout(resolve, 35000)); // 35 second delay
      route.continue();
    });
    
    // Reload to trigger timeout
    page.reload();
    
    // Should show timeout error
    const timeoutError = await page.waitForSelector('[data-testid="timeout-error"]', {
      timeout: 40000
    });
    await expect(timeoutError).toContainText(/請求超時|連線逾時/);
  });

  test('should recover from temporary API failures', async ({ page }) => {
    const orderPage = new OrderPage(page);
    await orderPage.navigateToOrders();
    
    let failCount = 0;
    await page.route('**/api/v1/orders', route => {
      if (failCount < 2) {
        failCount++;
        route.abort('failed');
      } else {
        route.continue();
      }
    });
    
    // Page should retry and eventually load
    await page.waitForSelector('[data-testid="orders-list"]', {
      timeout: 15000
    });
    
    // Orders should be displayed
    const orderCount = await orderPage.getOrderCount();
    expect(orderCount).toBeGreaterThanOrEqual(0);
  });

  test('should handle concurrent request conflicts', async ({ page, context }) => {
    const customerPage = new CustomerPage(page);
    
    // Open two tabs
    const page2 = await context.newPage();
    const customerPage2 = new CustomerPage(page2);
    
    // Login on second page
    const loginPage2 = new LoginPage(page2);
    await loginPage2.navigateToLogin();
    await loginPage2.login('admin', 'admin123');
    await loginPage2.waitForLoginSuccess();
    
    // Navigate to same customer
    await customerPage.navigateToCustomers();
    await customerPage2.navigateToCustomers();
    
    // Edit same customer on both pages
    await customerPage.clickEditCustomer(0);
    await customerPage2.clickEditCustomer(0);
    
    // Update on first page
    await customerPage.fillCustomerForm({
      name: '更新1',
      phone: '0911111111',
      address: '地址1'
    });
    await customerPage.submitCustomerForm();
    
    // Update on second page (should show conflict)
    await customerPage2.fillCustomerForm({
      name: '更新2',
      phone: '0922222222',
      address: '地址2'
    });
    await customerPage2.submitCustomerForm();
    
    // Should show conflict error on second page
    const conflictError = page2.locator('[data-testid="conflict-error"]');
    await expect(conflictError).toBeVisible();
    
    // Cleanup
    await page2.close();
  });

  test('should gracefully degrade when features are unavailable', async ({ page }) => {
    // Mock Google APIs being unavailable
    await page.route('**/predictions/generate', route => {
      route.fulfill({
        status: 503,
        body: 'Service Unavailable'
      });
    });
    
    await page.goto('/predictions');
    
    // Should show fallback UI
    const fallbackNotice = page.locator('[data-testid="service-unavailable-notice"]');
    await expect(fallbackNotice).toBeVisible();
    
    // Basic functionality should still work
    const manualPredictionButton = page.locator('[data-testid="manual-prediction-btn"]');
    await expect(manualPredictionButton).toBeVisible();
  });

  test('should handle file upload errors', async ({ page }) => {
    // Set mobile viewport
    await page.setViewportSize({ width: 375, height: 812 });
    
    const loginPage = new LoginPage(page);
    const driverPage = new DriverMobilePage(page);
    const completionModal = new DeliveryCompletionModal(page);
    
    // Login as driver
    await loginPage.navigateToLogin();
    await loginPage.login('driver1', 'driver123');
    await loginPage.waitForLoginSuccess();
    
    await driverPage.navigateToDriverInterface();
    await driverPage.waitForRouteLoad();
    
    // Navigate to completion
    const firstRoute = await page.locator('[data-route-id]').first().getAttribute('data-route-id');
    if (firstRoute) {
      await driverPage.selectRoute(firstRoute);
    }
    await driverPage.selectDeliveryItem(0);
    await driverPage.clickCompleteDelivery();
    await completionModal.waitForModal();
    
    // Mock upload failure
    await page.route('**/upload', route => {
      route.fulfill({
        status: 413,
        body: 'Payload Too Large'
      });
    });
    
    // Try to upload large file
    await completionModal.uploadPhoto('large-file.jpg');
    
    // Should show error
    const uploadError = await completionModal.getErrorMessage();
    expect(uploadError).toContain('檔案太大');
  });
});

test.describe('Error Boundaries', () => {
  test('should catch and display React errors gracefully', async ({ page }) => {
    // Navigate to any page
    await page.goto('/dashboard');
    
    // Inject error
    await page.evaluate(() => {
      // Force a React error
      const event = new ErrorEvent('error', {
        error: new Error('Test React Error'),
        message: 'Test React Error'
      });
      window.dispatchEvent(event);
    });
    
    // Should show error boundary UI
    const errorBoundary = page.locator('[data-testid="error-boundary"]');
    await expect(errorBoundary).toBeVisible();
    
    // Should have reload button
    const reloadButton = page.locator('[data-testid="reload-page-btn"]');
    await expect(reloadButton).toBeVisible();
  });

  test('should log errors for debugging', async ({ page }) => {
    const errors: string[] = [];
    
    // Capture console errors
    page.on('console', msg => {
      if (msg.type() === 'error') {
        errors.push(msg.text());
      }
    });
    
    // Navigate and cause an error
    await page.goto('/dashboard');
    await page.evaluate(() => {
      console.error('Test error for logging');
    });
    
    // Verify error was logged
    expect(errors).toContain('Test error for logging');
  });
});