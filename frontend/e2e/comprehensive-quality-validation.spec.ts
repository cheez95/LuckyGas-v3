import { test, expect } from '@playwright/test';
import { LoginPage } from './pages/LoginPage';
import { DashboardPage } from './pages/DashboardPage';
import { CustomerPage } from './pages/CustomerPage';
import { OrderPage } from './pages/OrderPage';
import { RoutePage } from './pages/RoutePage';
import { DriverMobilePage } from './pages/DriverMobilePage';

test.describe('Comprehensive Quality Validation Suite', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/');
  });

  test.describe('Critical User Workflows', () => {
    test($1, async ({ page }) => {
      const loginPage = new LoginPage(page);
      const dashboardPage = new DashboardPage(page);
      const customerPage = new CustomerPage(page);
      const orderPage = new OrderPage(page);

      // Login as office staff
      await loginPage.login('office@luckygas.com', 'password123');
      await expect(dashboardPage.welcomeMessage).toBeVisible();

      // Create new customer
      await page.goto('/customers');
      await customerPage.createCustomer({
        code: `TEST${Date.now()}`,
        name: '測試客戶',
        phone: '0912345678',
        address: '台北市信義區信義路五段7號',
        area: '信義區'
      });

      // Create order for customer
      await page.goto('/orders');
      await orderPage.createOrder({
        customerCode: `TEST${Date.now()}`,
        productType: '20kg',
        quantity: 2,
        deliveryDate: new Date().toISOString().split('T')[0]
      });

      // Verify order created
      await expect(page.locator('text=訂單建立成功')).toBeVisible();
    });

    test($1, async ({ page, context }) => {
      // Set mobile viewport
      await page.setViewportSize({ width: 375, height: 812 });
      
      const loginPage = new LoginPage(page);
      const driverPage = new DriverMobilePage(page);

      // Login as driver
      await loginPage.login('driver@luckygas.com', 'password123');
      
      // Check mobile optimized interface
      await expect(driverPage.mobileHeader).toBeVisible();
      await expect(driverPage.routeList).toBeVisible();

      // Select first route
      await driverPage.selectRoute(0);
      
      // Complete delivery with photo
      await driverPage.completeDelivery({
        photoPath: './test-assets/delivery-proof.jpg',
        signature: true,
        notes: '已交付'
      });

      // Verify completion
      await expect(page.locator('text=交付完成')).toBeVisible();
    });

    test($1, async ({ page }) => {
      const loginPage = new LoginPage(page);
      const routePage = new RoutePage(page);

      // Login as manager
      await loginPage.login('manager@luckygas.com', 'password123');

      // Navigate to route planning
      await page.goto('/routes');
      
      // Select date and area
      await routePage.selectDate(new Date());
      await routePage.selectArea('信義區');

      // Optimize routes
      await routePage.optimizeRoutes();
      
      // Verify optimization results
      await expect(routePage.optimizationResults).toBeVisible();
      await expect(routePage.routeMap).toBeVisible();

      // Assign to driver
      await routePage.assignDriver('張三', 0);
      await expect(page.locator('text=路線已指派')).toBeVisible();
    });

    test($1, async ({ page, context }) => {
      const loginPage = new LoginPage(page);
      
      // Open customer view
      const customerPage = await context.newPage();
      await customerPage.goto('/track');
      
      // Enter order tracking number
      await customerPage.fill('[data-testid="tracking-number"]', 'ORD2024001');
      await customerPage.click('button:has-text("追蹤訂單")');

      // Verify real-time updates
      await expect(customerPage.locator('[data-testid="order-status"]')).toBeVisible();
      await expect(customerPage.locator('[data-testid="driver-location"]')).toBeVisible();

      // Simulate driver update
      const driverPage = await context.newPage();
      await driverPage.goto('/');
      await loginPage.login('driver@luckygas.com', 'password123');
      
      // Update delivery status
      await driverPage.goto('/driver/deliveries');
      await driverPage.click('[data-testid="delivery-ORD2024001"]');
      await driverPage.click('button:has-text("開始配送")');

      // Verify customer sees update
      await customerPage.waitForTimeout(1000);
      await expect(customerPage.locator('text=配送中')).toBeVisible();
    });
  });

  test.describe('Performance Benchmarks', () => {
    test($1, async ({ page }) => {
      const loginPage = new LoginPage(page);
      await loginPage.login('admin@luckygas.com', 'password123');

      // Measure API response times
      const responsePromise = page.waitForResponse(resp => 
        resp.url().includes('/api/v1/customers') && resp.status() === 200
      );
      
      await page.goto('/customers');
      const response = await responsePromise;
      
      const timing = response.timing();
      expect(timing.responseEnd - timing.requestStart).toBeLessThan(100); // < 100ms
    });

    test($1, async ({ page }) => {
      // Measure page load performance
      await page.goto('/');
      
      const metrics = await page.evaluate(() => {
        const navigation = performance.getEntriesByType('navigation')[0] as PerformanceNavigationTiming;
        return {
          domContentLoaded: navigation.domContentLoadedEventEnd - navigation.domContentLoadedEventStart,
          loadComplete: navigation.loadEventEnd - navigation.loadEventStart,
          firstPaint: performance.getEntriesByName('first-paint')[0]?.startTime || 0,
          firstContentfulPaint: performance.getEntriesByName('first-contentful-paint')[0]?.startTime || 0
        };
      });

      // Verify performance targets
      expect(metrics.domContentLoaded).toBeLessThan(1000); // < 1s
      expect(metrics.loadComplete).toBeLessThan(2000); // < 2s
      expect(metrics.firstContentfulPaint).toBeLessThan(1500); // < 1.5s
    });

    test($1, async ({ page }) => {
      // Simulate 3G network
      await page.route('**/*', async route => {
        await new Promise(resolve => setTimeout(resolve, 100)); // Simulate latency
        await route.continue();
      });

      const startTime = Date.now();
      await page.goto('/');
      const loadTime = Date.now() - startTime;

      expect(loadTime).toBeLessThan(3000); // < 3s on 3G
    });
  });

  test.describe('Error Recovery and Edge Cases', () => {
    test($1, async ({ page, context }) => {
      const loginPage = new LoginPage(page);
      await loginPage.login('office@luckygas.com', 'password123');

      // Simulate network failure
      await context.setOffline(true);
      
      // Try to create order
      await page.goto('/orders');
      await page.click('button:has-text("新增訂單")');
      
      // Verify offline message
      await expect(page.locator('text=網路連線中斷')).toBeVisible();

      // Restore network
      await context.setOffline(false);
      
      // Verify auto-recovery
      await page.waitForTimeout(2000);
      await expect(page.locator('text=網路已恢復')).toBeVisible();
    });

    test('Concurrent user operations', async ({ browser }) => {
      // Create multiple contexts for concurrent users
      const contexts = await Promise.all([
        browser.newContext(),
        browser.newContext(),
        browser.newContext()
      ]);

      const pages = await Promise.all(
        contexts.map(context => context.newPage())
      );

      // All users login simultaneously
      await Promise.all(pages.map(async (page, index) => {
        await page.goto('/');
        const loginPage = new LoginPage(page);
        await loginPage.login(`user${index}@luckygas.com`, 'password123');
      }));

      // All users perform operations
      await Promise.all(pages.map(async (page, index) => {
        await page.goto('/customers');
        await page.click('button:has-text("新增客戶")');
        await page.fill('[name="name"]', `並發測試客戶${index}`);
        await page.fill('[name="phone"]', `091234567${index}`);
        await page.click('button:has-text("儲存")');
      }));

      // Verify all operations succeeded
      for (const page of pages) {
        await expect(page.locator('text=客戶建立成功')).toBeVisible();
      }

      // Cleanup
      await Promise.all(contexts.map(context => context.close()));
    });

    test($1, async ({ page }) => {
      const loginPage = new LoginPage(page);
      const customerPage = new CustomerPage(page);

      await loginPage.login('office@luckygas.com', 'password123');
      await page.goto('/customers');

      // Test invalid data
      await customerPage.createCustomer({
        code: '', // Empty code
        name: 'A', // Too short
        phone: '123', // Invalid format
        address: '',
        area: ''
      });

      // Verify validation errors
      await expect(page.locator('text=客戶代碼為必填')).toBeVisible();
      await expect(page.locator('text=姓名至少需要2個字元')).toBeVisible();
      await expect(page.locator('text=電話號碼格式不正確')).toBeVisible();
    });
  });

  test.describe('Security Validation', () => {
    test($1, async ({ page }) => {
      const loginPage = new LoginPage(page);
      
      // Attempt SQL injection in login
      await loginPage.attemptLogin("admin' OR '1'='1", "' OR '1'='1");
      await expect(page.locator('text=帳號或密碼錯誤')).toBeVisible();

      // Attempt in search
      await loginPage.login('office@luckygas.com', 'password123');
      await page.goto('/customers');
      await page.fill('[data-testid="search-input"]', "'; DROP TABLE customers; --");
      await page.click('button:has-text("搜尋")');
      
      // Should return no results, not error
      await expect(page.locator('text=查無資料')).toBeVisible();
    });

    test($1, async ({ page }) => {
      const loginPage = new LoginPage(page);
      const customerPage = new CustomerPage(page);

      await loginPage.login('office@luckygas.com', 'password123');
      await page.goto('/customers');

      // Attempt XSS in customer name
      await customerPage.createCustomer({
        code: 'XSS001',
        name: '<script>alert("XSS")</script>',
        phone: '0912345678',
        address: '測試地址',
        area: '測試區'
      });

      // Verify script is escaped, not executed
      await page.goto('/customers');
      const alertPromise = page.waitForEvent('dialog', { timeout: 1000 }).catch(() => null);
      const alert = await alertPromise;
      expect(alert).toBeNull();
    });

    test($1, async ({ page }) => {
      const loginPage = new LoginPage(page);

      // Login as driver
      await loginPage.login('driver@luckygas.com', 'password123');

      // Try to access admin routes
      await page.goto('/admin/settings');
      await expect(page.locator('text=權限不足')).toBeVisible();

      // Try to access manager routes
      await page.goto('/routes/optimize');
      await expect(page.locator('text=權限不足')).toBeVisible();
    });
  });

  test.describe('Business Continuity', () => {
    test($1, async ({ page }) => {
      const loginPage = new LoginPage(page);
      
      await loginPage.login('admin@luckygas.com', 'password123');
      await page.goto('/admin/backup');

      // Trigger backup
      const downloadPromise = page.waitForEvent('download');
      await page.click('button:has-text("匯出資料")');
      const download = await downloadPromise;

      // Verify download
      expect(download.suggestedFilename()).toContain('luckygas-backup');
      expect(download.suggestedFilename()).toContain('.json');
    });

    test($1, async ({ page }) => {
      await page.goto('/api/health');
      
      const health = await page.evaluate(() => {
        return JSON.parse(document.body.innerText);
      });

      expect(health.status).toBe('healthy');
      expect(health.database).toBe('connected');
      expect(health.redis).toBe('connected');
      expect(health.services).toHaveProperty('websocket', 'running');
    });
  });
});