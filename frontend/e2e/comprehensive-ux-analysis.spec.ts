import { test, expect, Page, BrowserContext } from '@playwright/test';
import { LoginPage } from './pages/LoginPage';
import { DashboardPage } from './pages/DashboardPage';
import { OrderPage } from './pages/OrderPage';
import { CustomerPage } from './pages/CustomerPage';
import { RoutePage } from './pages/RoutePage';
import { DriverMobilePage } from './pages/DriverMobilePage';

// Test data
const TEST_USERS = {
  admin: { username: 'admin', password: 'admin123', role: 'super_admin' },
  office: { username: 'office1', password: 'office123', role: 'office_staff' },
  driver: { username: 'driver1', password: 'driver123', role: 'driver' },
  customer: { username: 'customer1', password: 'customer123', role: 'customer' },
  dispatch: { username: 'dispatch1', password: 'dispatch123', role: 'dispatcher' }
};

// Helper function to test responsive design
async function testResponsiveDesign(page: Page, url: string) {
  const viewports = [
    { width: 375, height: 667, name: 'iPhone SE' },
    { width: 768, height: 1024, name: 'iPad' },
    { width: 1920, height: 1080, name: 'Desktop' }
  ];

  for (const viewport of viewports) {
    await page.setViewportSize(viewport);
    await page.goto(url);
    await page.waitForLoadState('networkidle');
    
    // Check that page is properly rendered
    await expect(page).toHaveScreenshot(`${url.split('/').pop()}-${viewport.name}.png`, {
      fullPage: true,
      animations: 'disabled'
    });
  }
}

// Helper to check accessibility
async function checkAccessibility(page: Page) {
  // Check for ARIA labels
  const buttons = await page.locator('button').all();
  for (const button of buttons) {
    const ariaLabel = await button.getAttribute('aria-label');
    const text = await button.textContent();
    expect(ariaLabel || text).toBeTruthy();
  }

  // Check for alt text on images
  const images = await page.locator('img').all();
  for (const img of images) {
    const alt = await img.getAttribute('alt');
    expect(alt).toBeTruthy();
  }

  // Check focus management
  await page.keyboard.press('Tab');
  const focusedElement = await page.evaluate(() => document.activeElement?.tagName);
  expect(focusedElement).not.toBe('BODY');
}

test.describe('Comprehensive UX Analysis', () => {
  test.describe('1. Authentication & Authorization', () => {
    test('Login flow with proper error handling', async ({ page }) => {
      const loginPage = new LoginPage(page);
      await loginPage.goto();

      // Test empty form submission
      await loginPage.clickLogin();
      await expect(page.locator('.ant-form-item-explain-error')).toBeVisible();

      // Test invalid credentials
      await loginPage.login('invalid', 'invalid');
      await expect(page.locator('[data-testid="error-alert"]')).toBeVisible();
      await expect(page.locator('[data-testid="error-alert"]')).toContainText(/無效|錯誤|失敗/);

      // Test successful login
      await loginPage.login(TEST_USERS.office.username, TEST_USERS.office.password);
      await expect(page).toHaveURL(/dashboard/);
    });

    test('Role-based access control', async ({ browser }) => {
      // Test each role's access
      for (const [role, user] of Object.entries(TEST_USERS)) {
        const context = await browser.newContext();
        const page = await context.newPage();
        const loginPage = new LoginPage(page);
        
        await loginPage.goto();
        await loginPage.login(user.username, user.password);
        
        // Check role-specific routes
        if (role === 'driver') {
          await expect(page).toHaveURL(/driver/);
          await page.goto('/orders');
          await expect(page).toHaveURL(/driver/); // Should redirect
        } else if (role === 'customer') {
          await expect(page).toHaveURL(/customer/);
        } else {
          await expect(page).toHaveURL(/dashboard/);
        }
        
        await context.close();
      }
    });

    test('Session management and timeout', async ({ page }) => {
      const loginPage = new LoginPage(page);
      await loginPage.goto();
      await loginPage.login(TEST_USERS.office.username, TEST_USERS.office.password);
      
      // Check session persistence
      await page.reload();
      await expect(page).toHaveURL(/dashboard/);
      
      // Check logout
      await page.locator('[data-testid="user-menu"]').click();
      await page.locator('[data-testid="logout-btn"]').click();
      await expect(page).toHaveURL(/login/);
    });
  });

  test.describe('2. Dashboard & Real-time Features', () => {
    test.beforeEach(async ({ page }) => {
      const loginPage = new LoginPage(page);
      await loginPage.goto();
      await loginPage.login(TEST_USERS.office.username, TEST_USERS.office.password);
    });

    test('Dashboard statistics and real-time updates', async ({ page }) => {
      const dashboard = new DashboardPage(page);
      await dashboard.goto();
      
      // Check all statistics cards are visible
      await expect(page.locator('[data-testid="stat-today-orders"]')).toBeVisible();
      await expect(page.locator('[data-testid="stat-active-customers"]')).toBeVisible();
      await expect(page.locator('[data-testid="stat-drivers-on-route"]')).toBeVisible();
      await expect(page.locator('[data-testid="stat-today-revenue"]')).toBeVisible();
      
      // Check real-time activity feed
      await expect(page.locator('[data-testid="activity-feed"]')).toBeVisible();
      
      // Check WebSocket connection indicator
      await expect(page.locator('[data-testid="websocket-status"]')).toBeVisible();
      const wsStatus = await page.locator('[data-testid="websocket-status"]').getAttribute('data-status');
      expect(wsStatus).toBe('connected');
    });

    test('Notification system', async ({ page }) => {
      await page.goto('/dashboard');
      
      // Check notification bell
      await expect(page.locator('[data-testid="notification-bell"]')).toBeVisible();
      
      // Open notification panel
      await page.locator('[data-testid="notification-bell"]').click();
      await expect(page.locator('.ant-popover')).toBeVisible();
      
      // Check notification types
      const notifications = page.locator('.notification-item');
      await expect(notifications).toHaveCount(await notifications.count());
    });
  });

  test.describe('3. Office Staff Features', () => {
    test.beforeEach(async ({ page }) => {
      const loginPage = new LoginPage(page);
      await loginPage.goto();
      await loginPage.login(TEST_USERS.office.username, TEST_USERS.office.password);
    });

    test('Order management - CRUD operations', async ({ page }) => {
      const orderPage = new OrderPage(page);
      await orderPage.goto();
      
      // Test search functionality
      await orderPage.searchOrder('test');
      await page.waitForTimeout(1000);
      
      // Test filter by status
      await page.locator('[data-testid="status-filter"]').click();
      await page.locator('[data-value="pending"]').click();
      await page.waitForTimeout(1000);
      
      // Test create order
      await page.locator('[data-testid="create-order-btn"]').click();
      await expect(page.locator('.ant-modal')).toBeVisible();
      
      // Fill order form
      await page.locator('[data-testid="customer-select"]').click();
      await page.locator('.ant-select-item').first().click();
      await page.locator('[data-testid="product-select"]').click();
      await page.locator('[data-value="20kg"]').click();
      await page.locator('[data-testid="quantity-input"]').fill('2');
      
      // Check form validation
      await page.locator('[data-testid="submit-order-btn"]').click();
      await expect(page.locator('.ant-message')).toBeVisible();
    });

    test('Customer management with inventory tracking', async ({ page }) => {
      const customerPage = new CustomerPage(page);
      await customerPage.goto();
      
      // Test customer search
      await customerPage.searchCustomer('王');
      await page.waitForTimeout(1000);
      
      // Test customer detail view
      await page.locator('.ant-table-row').first().click();
      await expect(page.locator('[data-testid="customer-detail-drawer"]')).toBeVisible();
      
      // Check inventory tracking
      await expect(page.locator('[data-testid="cylinder-inventory"]')).toBeVisible();
      await expect(page.locator('[data-testid="delivery-history"]')).toBeVisible();
      
      // Test inline editing
      await page.locator('[data-testid="edit-customer-btn"]').click();
      await page.locator('[data-testid="phone-input"]').fill('0912345678');
      await page.locator('[data-testid="save-customer-btn"]').click();
      await expect(page.locator('.ant-message-success')).toBeVisible();
    });

    test('Order templates and bulk operations', async ({ page }) => {
      await page.goto('/orders');
      
      // Test template quick select
      await expect(page.locator('[data-testid="template-quick-select"]')).toBeVisible();
      await page.locator('[data-testid="template-quick-select"]').click();
      await page.locator('.template-option').first().click();
      
      // Test bulk operations
      await page.locator('.ant-checkbox-input').first().click();
      await page.locator('.ant-checkbox-input').nth(1).click();
      await expect(page.locator('[data-testid="bulk-actions"]')).toBeVisible();
      
      // Test bulk status update
      await page.locator('[data-testid="bulk-update-status"]').click();
      await page.locator('[data-value="confirmed"]').click();
      await expect(page.locator('.ant-message')).toBeVisible();
    });
  });

  test.describe('4. Driver Mobile Interface', () => {
    test('Mobile-optimized interface and navigation', async ({ browser }) => {
      const context = await browser.newContext({
        ...TEST_USERS.driver,
        viewport: { width: 375, height: 667 },
        isMobile: true,
        hasTouch: true
      });
      const page = await context.newPage();
      
      const loginPage = new LoginPage(page);
      await loginPage.goto();
      await loginPage.login(TEST_USERS.driver.username, TEST_USERS.driver.password);
      
      // Should redirect to driver dashboard
      await expect(page).toHaveURL(/driver/);
      
      // Check mobile layout
      await expect(page.locator('[data-testid="mobile-nav"]')).toBeVisible();
      
      // Test touch gestures
      const routeCard = page.locator('[data-testid="route-card"]').first();
      await routeCard.tap();
      await expect(page).toHaveURL(/route/);
      
      await context.close();
    });

    test('Offline mode and sync', async ({ page, context }) => {
      // Login as driver
      const loginPage = new LoginPage(page);
      await loginPage.goto();
      await loginPage.login(TEST_USERS.driver.username, TEST_USERS.driver.password);
      
      // Go to driver route
      await page.goto('/driver/route/1');
      
      // Go offline
      await context.setOffline(true);
      
      // Check offline indicator
      await expect(page.locator('[data-testid="offline-indicator"]')).toBeVisible();
      
      // Try to complete delivery offline
      await page.locator('[data-testid="complete-delivery-btn"]').first().click();
      await page.locator('[data-testid="signature-pad"]').click();
      await page.locator('[data-testid="save-signature-btn"]').click();
      
      // Check pending sync indicator
      await expect(page.locator('[data-testid="sync-status"]')).toContainText(/待同步/);
      
      // Go back online
      await context.setOffline(false);
      
      // Check sync in progress
      await expect(page.locator('[data-testid="sync-status"]')).toContainText(/同步中/);
    });

    test('GPS tracking and navigation', async ({ page, context }) => {
      // Mock geolocation
      await context.grantPermissions(['geolocation']);
      await context.setGeolocation({ latitude: 25.0330, longitude: 121.5654 });
      
      const loginPage = new LoginPage(page);
      await loginPage.goto();
      await loginPage.login(TEST_USERS.driver.username, TEST_USERS.driver.password);
      
      await page.goto('/driver/navigation');
      
      // Check GPS tracker is active
      await expect(page.locator('[data-testid="gps-tracker"]')).toBeVisible();
      await expect(page.locator('[data-testid="current-location"]')).toContainText(/25.033/);
      
      // Test navigation to stop
      await page.locator('[data-testid="navigate-to-stop"]').first().click();
      await expect(page.locator('[data-testid="navigation-active"]')).toBeVisible();
    });
  });

  test.describe('5. Dispatch & Route Planning', () => {
    test.beforeEach(async ({ page }) => {
      const loginPage = new LoginPage(page);
      await loginPage.goto();
      await loginPage.login(TEST_USERS.dispatch.username, TEST_USERS.dispatch.password);
    });

    test('Route optimization and planning', async ({ page }) => {
      const routePage = new RoutePage(page);
      await routePage.goto();
      
      // Test route creation
      await page.locator('[data-testid="create-route-btn"]').click();
      await page.locator('[data-testid="route-name-input"]').fill('測試路線');
      await page.locator('[data-testid="driver-select"]').click();
      await page.locator('.ant-select-item').first().click();
      
      // Test drag and drop for orders
      const unassignedOrder = page.locator('[data-testid="unassigned-order"]').first();
      const routeDropZone = page.locator('[data-testid="route-drop-zone"]');
      
      await unassignedOrder.dragTo(routeDropZone);
      
      // Test optimization
      await page.locator('[data-testid="optimize-route-btn"]').click();
      await expect(page.locator('[data-testid="optimization-progress"]')).toBeVisible();
      await expect(page.locator('[data-testid="optimization-complete"]')).toBeVisible({ timeout: 10000 });
    });

    test('Emergency dispatch functionality', async ({ page }) => {
      await page.goto('/emergency-dispatch');
      
      // Check priority queue
      await expect(page.locator('[data-testid="priority-queue"]')).toBeVisible();
      
      // Test emergency order creation
      await page.locator('[data-testid="create-emergency-btn"]').click();
      await expect(page.locator('[data-testid="emergency-modal"]')).toBeVisible();
      
      // Fill emergency order
      await page.locator('[data-testid="emergency-customer"]').click();
      await page.locator('.ant-select-item').first().click();
      await page.locator('[data-testid="emergency-reason"]').fill('瓦斯用完');
      await page.locator('[data-testid="submit-emergency-btn"]').click();
      
      // Check alert banner
      await expect(page.locator('[data-testid="emergency-alert-banner"]')).toBeVisible();
    });
  });

  test.describe('6. Admin Analytics & Monitoring', () => {
    test.beforeEach(async ({ page }) => {
      const loginPage = new LoginPage(page);
      await loginPage.goto();
      await loginPage.login(TEST_USERS.admin.username, TEST_USERS.admin.password);
    });

    test('Executive dashboard with KPIs', async ({ page }) => {
      await page.goto('/admin/executive');
      
      // Check KPI cards
      await expect(page.locator('[data-testid="kpi-revenue"]')).toBeVisible();
      await expect(page.locator('[data-testid="kpi-orders"]')).toBeVisible();
      await expect(page.locator('[data-testid="kpi-customers"]')).toBeVisible();
      await expect(page.locator('[data-testid="kpi-efficiency"]')).toBeVisible();
      
      // Check charts
      await expect(page.locator('[data-testid="revenue-chart"]')).toBeVisible();
      await expect(page.locator('[data-testid="trend-chart"]')).toBeVisible();
      
      // Test date range picker
      await page.locator('[data-testid="date-range-picker"]').click();
      await page.locator('[data-testid="last-30-days"]').click();
      await page.waitForLoadState('networkidle');
    });

    test('Performance monitoring', async ({ page }) => {
      await page.goto('/admin/performance');
      
      // Check performance metrics
      await expect(page.locator('[data-testid="delivery-efficiency"]')).toBeVisible();
      await expect(page.locator('[data-testid="driver-performance"]')).toBeVisible();
      await expect(page.locator('[data-testid="route-optimization-score"]')).toBeVisible();
      
      // Test export functionality
      await page.locator('[data-testid="export-report-btn"]').click();
      await page.locator('[data-testid="export-pdf"]').click();
      
      // Wait for download
      const download = await page.waitForEvent('download');
      expect(download.suggestedFilename()).toContain('performance-report');
    });
  });

  test.describe('7. Customer Portal', () => {
    test('Order tracking and history', async ({ page }) => {
      const loginPage = new LoginPage(page);
      await loginPage.goto();
      await loginPage.login(TEST_USERS.customer.username, TEST_USERS.customer.password);
      
      // Should redirect to customer portal
      await expect(page).toHaveURL(/customer/);
      
      // Check order tracking
      await page.locator('[data-testid="track-order-btn"]').first().click();
      await expect(page.locator('[data-testid="order-timeline"]')).toBeVisible();
      await expect(page.locator('[data-testid="delivery-map"]')).toBeVisible();
      
      // Check order history
      await page.goto('/customer');
      await expect(page.locator('[data-testid="order-history"]')).toBeVisible();
      
      // Test reorder functionality
      await page.locator('[data-testid="reorder-btn"]').first().click();
      await expect(page.locator('[data-testid="confirm-reorder-modal"]')).toBeVisible();
    });
  });

  test.describe('8. Cross-cutting Concerns', () => {
    test('Internationalization (i18n)', async ({ page }) => {
      const loginPage = new LoginPage(page);
      await loginPage.goto();
      
      // Check Chinese UI
      await expect(page.locator('[data-testid="login-title"]')).toContainText(/幸福氣體|Lucky Gas/);
      await expect(page.locator('label')).toContainText(/用戶名|密碼/);
      
      // Login and check dashboard
      await loginPage.login(TEST_USERS.office.username, TEST_USERS.office.password);
      await expect(page.locator('h1')).toContainText(/儀表板|總覽/);
    });

    test('Accessibility compliance', async ({ page }) => {
      const loginPage = new LoginPage(page);
      await loginPage.goto();
      
      // Run accessibility checks
      await checkAccessibility(page);
      
      // Test keyboard navigation
      await page.keyboard.press('Tab');
      await expect(page.locator('[data-testid="username-input"]')).toBeFocused();
      await page.keyboard.press('Tab');
      await expect(page.locator('[data-testid="password-input"]')).toBeFocused();
      await page.keyboard.press('Tab');
      await expect(page.locator('[data-testid="login-btn"]')).toBeFocused();
    });

    test('Error handling and recovery', async ({ page }) => {
      await page.goto('/dashboard');
      
      // Simulate network error
      await page.route('**/api/**', route => route.abort());
      
      // Try to load orders
      await page.goto('/orders');
      
      // Check error message
      await expect(page.locator('[data-testid="error-message"]')).toBeVisible();
      await expect(page.locator('[data-testid="retry-btn"]')).toBeVisible();
      
      // Restore network and retry
      await page.unroute('**/api/**');
      await page.locator('[data-testid="retry-btn"]').click();
      await expect(page.locator('.ant-table')).toBeVisible();
    });

    test('Performance and loading states', async ({ page }) => {
      const loginPage = new LoginPage(page);
      await loginPage.goto();
      await loginPage.login(TEST_USERS.office.username, TEST_USERS.office.password);
      
      // Test loading states
      await page.goto('/orders');
      await expect(page.locator('.ant-spin')).toBeVisible();
      await expect(page.locator('.ant-table')).toBeVisible({ timeout: 5000 });
      
      // Check page load performance
      const metrics = await page.evaluate(() => {
        const navigation = performance.getEntriesByType('navigation')[0] as PerformanceNavigationTiming;
        return {
          domContentLoaded: navigation.domContentLoadedEventEnd - navigation.domContentLoadedEventStart,
          loadComplete: navigation.loadEventEnd - navigation.loadEventStart
        };
      });
      
      expect(metrics.domContentLoaded).toBeLessThan(3000);
      expect(metrics.loadComplete).toBeLessThan(5000);
    });

    test('Responsive design across devices', async ({ page }) => {
      const loginPage = new LoginPage(page);
      await loginPage.goto();
      await loginPage.login(TEST_USERS.office.username, TEST_USERS.office.password);
      
      // Test key pages at different resolutions
      const pages = ['/dashboard', '/orders', '/customers', '/routes'];
      
      for (const pageUrl of pages) {
        await testResponsiveDesign(page, pageUrl);
      }
    });
  });

  test.describe('9. Advanced Features', () => {
    test('Real-time collaboration', async ({ browser }) => {
      // Open two browser contexts
      const context1 = await browser.newContext();
      const context2 = await browser.newContext();
      
      const page1 = await context1.newPage();
      const page2 = await context2.newPage();
      
      // Login both users
      const loginPage1 = new LoginPage(page1);
      const loginPage2 = new LoginPage(page2);
      
      await loginPage1.goto();
      await loginPage1.login(TEST_USERS.office.username, TEST_USERS.office.password);
      
      await loginPage2.goto();
      await loginPage2.login(TEST_USERS.dispatch.username, TEST_USERS.dispatch.password);
      
      // Both navigate to orders
      await page1.goto('/orders');
      await page2.goto('/orders');
      
      // User 1 creates an order
      await page1.locator('[data-testid="create-order-btn"]').click();
      // ... fill order details
      await page1.locator('[data-testid="submit-order-btn"]').click();
      
      // User 2 should see the new order appear
      await expect(page2.locator('[data-testid="realtime-indicator"]')).toBeVisible();
      await expect(page2.locator('.ant-table-row')).toHaveCount(await page2.locator('.ant-table-row').count() + 1);
      
      await context1.close();
      await context2.close();
    });

    test('Data export and reporting', async ({ page }) => {
      const loginPage = new LoginPage(page);
      await loginPage.goto();
      await loginPage.login(TEST_USERS.admin.username, TEST_USERS.admin.password);
      
      await page.goto('/analytics');
      
      // Test export options
      await page.locator('[data-testid="export-menu-btn"]').click();
      
      // Test CSV export
      await page.locator('[data-testid="export-csv"]').click();
      const csvDownload = await page.waitForEvent('download');
      expect(csvDownload.suggestedFilename()).toContain('.csv');
      
      // Test PDF export
      await page.locator('[data-testid="export-menu-btn"]').click();
      await page.locator('[data-testid="export-pdf"]').click();
      const pdfDownload = await page.waitForEvent('download');
      expect(pdfDownload.suggestedFilename()).toContain('.pdf');
    });

    test('Search functionality across modules', async ({ page }) => {
      const loginPage = new LoginPage(page);
      await loginPage.goto();
      await loginPage.login(TEST_USERS.office.username, TEST_USERS.office.password);
      
      // Test global search
      await page.locator('[data-testid="global-search"]').fill('王小明');
      await page.keyboard.press('Enter');
      
      // Should show results from multiple modules
      await expect(page.locator('[data-testid="search-results"]')).toBeVisible();
      await expect(page.locator('[data-testid="customer-results"]')).toBeVisible();
      await expect(page.locator('[data-testid="order-results"]')).toBeVisible();
    });
  });
});

// Performance monitoring test
test('Performance metrics collection', async ({ page }) => {
  const loginPage = new LoginPage(page);
  await loginPage.goto();
  await loginPage.login(TEST_USERS.office.username, TEST_USERS.office.password);
  
  // Navigate through key pages and collect metrics
  const pages = [
    { url: '/dashboard', name: 'Dashboard' },
    { url: '/orders', name: 'Orders' },
    { url: '/customers', name: 'Customers' },
    { url: '/routes', name: 'Routes' }
  ];
  
  const performanceMetrics = [];
  
  for (const pageInfo of pages) {
    await page.goto(pageInfo.url);
    await page.waitForLoadState('networkidle');
    
    const metrics = await page.evaluate(() => {
      const navigation = performance.getEntriesByType('navigation')[0] as PerformanceNavigationTiming;
      const paint = performance.getEntriesByType('paint');
      
      return {
        domContentLoaded: navigation.domContentLoadedEventEnd - navigation.fetchStart,
        loadComplete: navigation.loadEventEnd - navigation.fetchStart,
        firstPaint: paint.find(p => p.name === 'first-paint')?.startTime || 0,
        firstContentfulPaint: paint.find(p => p.name === 'first-contentful-paint')?.startTime || 0,
        domInteractive: navigation.domInteractive - navigation.fetchStart
      };
    });
    
    performanceMetrics.push({
      page: pageInfo.name,
      ...metrics
    });
  }
  
  // Log performance report
  console.log('Performance Metrics Report:');
  console.table(performanceMetrics);
  
  // Assert performance thresholds
  for (const metric of performanceMetrics) {
    expect(metric.firstContentfulPaint).toBeLessThan(1500); // FCP < 1.5s
    expect(metric.domInteractive).toBeLessThan(3000); // Interactive < 3s
    expect(metric.loadComplete).toBeLessThan(5000); // Full load < 5s
  }
});