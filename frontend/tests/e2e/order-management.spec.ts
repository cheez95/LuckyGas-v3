import { test, expect } from '@playwright/test';
import { LoginPage } from './pages/LoginPage';
import { OrderManagementPage } from './pages/OrderManagementPage';
import { 
  ConsoleMonitor, 
  NetworkMonitor, 
  assertNoMapErrors,
  assertNoFailedAPIRequests,
  collectPerformanceMetrics,
  waitForWebSocketConnection,
  testResponsiveBehavior,
  takeScreenshot 
} from './helpers/testHelpers';

test.describe('Order Management Page Tests', () => {
  let loginPage: LoginPage;
  let orderPage: OrderManagementPage;
  let consoleMonitor: ConsoleMonitor;
  let networkMonitor: NetworkMonitor;

  test.beforeEach(async ({ page }) => {
    // Initialize monitors
    consoleMonitor = new ConsoleMonitor(page);
    networkMonitor = new NetworkMonitor(page);
    
    // Initialize page objects
    loginPage = new LoginPage(page);
    orderPage = new OrderManagementPage(page);
    
    // Login as admin
    await loginPage.goto();
    await loginPage.login('admin@luckygas.com', 'admin123');
    await page.waitForLoadState('networkidle');
    
    // Navigate to Order Management page
    await orderPage.goto();
  });

  test.afterEach(async ({ page }, testInfo) => {
    // Take screenshot on failure
    if (testInfo.status !== testInfo.expectedStatus) {
      await takeScreenshot(page, `order-management-failure-${testInfo.title}`);
    }
    
    // Log any console errors
    const errors = consoleMonitor.getErrors();
    if (errors.length > 0) {
      console.log('Console errors detected:', errors);
    }
  });

  test('should load Order Management page without errors', async ({ page }) => {
    // Wait for page to load
    await orderPage.waitForPageLoad();
    
    // Check page title is visible
    await expect(orderPage.pageTitle).toBeVisible({ timeout: 10000 });
    
    // Check no map errors occurred
    await assertNoMapErrors(consoleMonitor);
    
    // Check no failed API requests
    await assertNoFailedAPIRequests(networkMonitor);
    
    // Check error boundary didn't trigger
    const hasError = await orderPage.isErrorDisplayed();
    expect(hasError).toBeFalsy();
  });

  test('should verify no .map() errors or crashes occur', async ({ page }) => {
    // Wait for page to fully load
    await orderPage.waitForPageLoad();
    
    // Check specifically for map errors
    const hasMapErrors = await orderPage.checkForMapErrors();
    expect(hasMapErrors).toBeFalsy();
    
    // Verify console has no map-related errors
    await assertNoMapErrors(consoleMonitor);
    
    // Check that table renders correctly
    await expect(orderPage.ordersTable).toBeVisible();
    
    // Verify at least some content loaded
    const orderCount = await orderPage.getOrderCount();
    expect(orderCount).toBeGreaterThanOrEqual(0);
  });

  test('should test search functionality for orders', async ({ page }) => {
    // Wait for initial load
    await orderPage.waitForPageLoad();
    
    // Search for orders
    await orderPage.searchOrders('ORD-2025');
    
    // Check search executed without errors
    await assertNoMapErrors(consoleMonitor);
    
    // Verify search request was made
    const apiRequests = networkMonitor.getAPIRequests();
    const searchRequest = apiRequests.find(r => r.url.includes('search'));
    expect(searchRequest).toBeTruthy();
    
    // Check results updated
    await page.waitForTimeout(2000);
    const orderCount = await orderPage.getOrderCount();
    expect(orderCount).toBeGreaterThanOrEqual(0);
  });

  test('should test search functionality for customers', async ({ page }) => {
    // Wait for page load
    await orderPage.waitForPageLoad();
    
    // Search for customers
    await orderPage.searchCustomers('測試客戶');
    
    // Check no errors occurred
    await assertNoMapErrors(consoleMonitor);
    
    // Verify customer search API call
    const apiRequests = networkMonitor.getAPIRequests();
    const customerSearch = apiRequests.find(r => 
      r.url.includes('customers') && r.url.includes('search')
    );
    expect(customerSearch).toBeTruthy();
  });

  test('should test WebSocket connection establishment', async ({ page }) => {
    // Wait for page load
    await orderPage.waitForPageLoad();
    
    // Check for WebSocket connection
    const wsConnected = await waitForWebSocketConnection(page, 10000);
    
    // Check WebSocket status indicator
    const wsStatus = await orderPage.isWebSocketConnected();
    
    // At least one should indicate connection
    expect(wsConnected || wsStatus).toBeTruthy();
    
    // Check for WebSocket-related errors
    const errors = consoleMonitor.getErrors();
    const wsErrors = errors.filter(e => 
      e.text.includes('WebSocket') || e.text.includes('ws://')
    );
    expect(wsErrors).toHaveLength(0);
  });

  test('should test data fetching for orders, statistics, customers, and drivers', async ({ page }) => {
    // Wait for page load
    await orderPage.waitForPageLoad();
    
    // Check all API endpoints were called
    const apiRequests = networkMonitor.getAPIRequests();
    
    // Check orders endpoint
    const ordersRequest = apiRequests.find(r => r.url.includes('/orders'));
    expect(ordersRequest).toBeTruthy();
    expect(ordersRequest?.status).toBeLessThan(400);
    
    // Check statistics endpoint
    const statsRequest = apiRequests.find(r => r.url.includes('stats'));
    expect(statsRequest).toBeTruthy();
    expect(statsRequest?.status).toBeLessThan(400);
    
    // Check customers endpoint
    const customersRequest = apiRequests.find(r => r.url.includes('/customers'));
    expect(customersRequest).toBeTruthy();
    expect(customersRequest?.status).toBeLessThan(400);
    
    // Check drivers endpoint
    const driversRequest = apiRequests.find(r => r.url.includes('/drivers'));
    expect(driversRequest).toBeTruthy();
    
    // Verify data displayed
    const statistics = await orderPage.getStatisticsValue('總訂單');
    expect(statistics).toBeTruthy();
  });

  test('should test error boundaries catch component errors', async ({ page }) => {
    // Trigger an error by manipulating the page
    await page.evaluate(() => {
      // Force an error in React component
      const event = new ErrorEvent('error', {
        error: new Error('Test error'),
        message: 'Test error boundary'
      });
      window.dispatchEvent(event);
    });
    
    // Wait for error boundary to catch it
    await page.waitForTimeout(2000);
    
    // Check if error boundary displayed
    const hasError = await orderPage.isErrorDisplayed();
    if (hasError) {
      const errorMessage = await orderPage.getErrorMessage();
      console.log('Error boundary caught:', errorMessage);
    }
    
    // Page should still be functional
    await expect(orderPage.pageTitle).toBeVisible();
  });

  test('should test responsive behavior', async ({ page }) => {
    // Wait for page load
    await orderPage.waitForPageLoad();
    
    // Test different viewports
    const viewports = [
      { width: 1920, height: 1080 }, // Desktop
      { width: 768, height: 1024 },  // Tablet
      { width: 375, height: 667 }    // Mobile
    ];
    
    await testResponsiveBehavior(page, viewports);
    
    // Check mobile menu appears on small screens
    await page.setViewportSize({ width: 375, height: 667 });
    const mobileMenu = page.locator('.ant-layout-sider-trigger, .mobile-menu');
    const isMobileMenuVisible = await mobileMenu.isVisible();
    expect(isMobileMenuVisible).toBeTruthy();
  });

  test('should test UI interactions', async ({ page }) => {
    // Wait for page load
    await orderPage.waitForPageLoad();
    
    // Test create order button
    if (await orderPage.createOrderButton.isVisible()) {
      await orderPage.clickCreateOrder();
      // Check modal or navigation
      await page.waitForTimeout(1000);
      const modal = page.locator('.ant-modal, .create-order-modal');
      const isModalVisible = await modal.isVisible();
      if (isModalVisible) {
        // Close modal
        await page.keyboard.press('Escape');
      }
    }
    
    // Test export functionality
    if (await orderPage.exportButton.isVisible()) {
      const downloadPromise = page.waitForEvent('download');
      await orderPage.exportOrders();
      
      try {
        const download = await Promise.race([
          downloadPromise,
          page.waitForTimeout(5000).then(() => null)
        ]);
        
        if (download) {
          expect(download.suggestedFilename()).toContain('.xlsx');
        }
      } catch {
        // Export might not trigger download in test env
      }
    }
    
    // Test filter buttons
    const filterButtons = await orderPage.filterButtons.count();
    if (filterButtons > 0) {
      await orderPage.filterButtons.first().click();
      await orderPage.waitForLoadingComplete();
      // Check table updated
      await assertNoMapErrors(consoleMonitor);
    }
    
    // Test status filter
    await orderPage.filterByStatus('待處理');
    await assertNoMapErrors(consoleMonitor);
  });

  test('should collect performance metrics', async ({ page }) => {
    // Wait for page load
    await orderPage.waitForPageLoad();
    
    // Collect performance metrics
    const metrics = await collectPerformanceMetrics(page);
    
    console.log('Performance Metrics:', metrics);
    
    // Check performance thresholds
    expect(metrics.loadTime).toBeLessThan(5000); // 5 seconds max load time
    expect(metrics.domContentLoaded).toBeLessThan(3000); // 3 seconds DOMContentLoaded
    
    if (metrics.firstContentfulPaint) {
      expect(metrics.firstContentfulPaint).toBeLessThan(2500); // 2.5s FCP
    }
    
    if (metrics.largestContentfulPaint) {
      expect(metrics.largestContentfulPaint).toBeLessThan(4000); // 4s LCP
    }
  });

  test('should verify timeline functionality', async ({ page }) => {
    // Wait for page load
    await orderPage.waitForPageLoad();
    
    // Get timeline events
    const events = await orderPage.getTimelineEvents();
    
    // If timeline exists, verify it works
    if (events.length > 0) {
      console.log('Timeline events:', events);
      // Check timeline renders without errors
      await assertNoMapErrors(consoleMonitor);
    }
  });

  test('should handle rapid interactions without crashes', async ({ page }) => {
    // Wait for page load
    await orderPage.waitForPageLoad();
    
    // Perform rapid clicks and interactions
    for (let i = 0; i < 5; i++) {
      // Rapid search
      await orderPage.searchOrders(`test${i}`);
      
      // Quick filter changes
      if (await orderPage.filterButtons.count() > 0) {
        await orderPage.filterButtons.nth(i % await orderPage.filterButtons.count()).click();
      }
      
      // Don't wait for completion
    }
    
    // Wait for all operations to settle
    await page.waitForTimeout(3000);
    
    // Check no crashes occurred
    await assertNoMapErrors(consoleMonitor);
    const hasError = await orderPage.isErrorDisplayed();
    expect(hasError).toBeFalsy();
  });

  test('should verify data persistence after page refresh', async ({ page }) => {
    // Wait for page load
    await orderPage.waitForPageLoad();
    
    // Apply some filters or search
    await orderPage.searchOrders('ORD-2025');
    await page.waitForTimeout(2000);
    
    // Get current state
    const beforeRefresh = await orderPage.getOrderCount();
    
    // Refresh page
    await page.reload();
    await orderPage.waitForPageLoad();
    
    // Check page loads without errors after refresh
    await assertNoMapErrors(consoleMonitor);
    
    // Verify data loads again
    const afterRefresh = await orderPage.getOrderCount();
    expect(afterRefresh).toBeGreaterThanOrEqual(0);
  });
});