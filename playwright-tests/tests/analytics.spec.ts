import { test, expect } from '@playwright/test';
import { APIHelper } from '../utils/api-helper';
import { TestHelpers } from '../utils/test-helpers';
import testData from '../fixtures/test-data.json';

test.describe('Analytics Dashboard Tests', () => {
  let apiHelper: APIHelper;
  let managerApiHelper: APIHelper;

  test.beforeEach(async ({ request }) => {
    apiHelper = new APIHelper(request);
    await apiHelper.login('admin');
    
    managerApiHelper = new APIHelper(request);
    await managerApiHelper.login('manager');
  });

  test.describe('Executive Dashboard API', () => {
    test('should get executive dashboard metrics', async () => {
      const endDate = new Date();
      const startDate = new Date();
      startDate.setDate(startDate.getDate() - 30);
      
      const response = await apiHelper.getAnalytics('executive', {
        start_date: startDate.toISOString(),
        end_date: endDate.toISOString()
      });
      
      expect(response).toHaveProperty('revenue');
      expect(response).toHaveProperty('orders');
      expect(response).toHaveProperty('customers');
      expect(response).toHaveProperty('cashFlow');
      expect(response).toHaveProperty('performance');
      expect(response).toHaveProperty('topMetrics');
      
      // Validate revenue metrics
      expect(response.revenue).toHaveProperty('total');
      expect(response.revenue).toHaveProperty('byProduct');
      expect(response.revenue).toHaveProperty('byCustomerType');
      expect(response.revenue).toHaveProperty('trend');
      expect(response.revenue).toHaveProperty('growth');
      
      // Validate order metrics
      expect(response.orders).toHaveProperty('total');
      expect(response.orders).toHaveProperty('completed');
      expect(response.orders).toHaveProperty('cancelled');
      expect(response.orders).toHaveProperty('averageValue');
      expect(response.orders).toHaveProperty('trend');
      
      // Validate customer metrics
      expect(response.customers).toHaveProperty('total');
      expect(response.customers).toHaveProperty('new');
      expect(response.customers).toHaveProperty('active');
      expect(response.customers).toHaveProperty('churnRate');
      expect(response.customers).toHaveProperty('lifetimeValue');
    });

    test('should respect date range filters', async () => {
      // Test different date ranges
      for (const range of testData.analyticsDateRanges) {
        const response = await apiHelper.getAnalytics('executive', {
          start_date: range.startDate,
          end_date: range.endDate
        });
        
        expect(response).toBeTruthy();
        
        // Data should be within date range
        if (response.orders.trend) {
          response.orders.trend.forEach((point: any) => {
            const date = new Date(point.date);
            expect(date >= new Date(range.startDate)).toBeTruthy();
            expect(date <= new Date(range.endDate)).toBeTruthy();
          });
        }
      }
    });

    test('should enforce role-based access', async () => {
      // Manager should have access
      const managerResponse = await managerApiHelper.get('/api/v1/analytics/executive');
      expect(managerResponse.ok()).toBeTruthy();
      
      // Office staff should not have access
      const staffApiHelper = new APIHelper(await managerApiHelper['request']);
      await staffApiHelper.login('officeStaff');
      
      const staffResponse = await staffApiHelper.get('/api/v1/analytics/executive');
      expect(staffResponse.status()).toBe(403);
    });
  });

  test.describe('Operations Dashboard API', () => {
    test('should get real-time operations metrics', async () => {
      const response = await apiHelper.getAnalytics('operations', {
        date: new Date().toISOString()
      });
      
      expect(response).toHaveProperty('realTimeOrders');
      expect(response).toHaveProperty('driverUtilization');
      expect(response).toHaveProperty('routeEfficiency');
      expect(response).toHaveProperty('deliveryMetrics');
      expect(response).toHaveProperty('inventory');
      expect(response).toHaveProperty('alerts');
      
      // Validate real-time order status
      expect(response.realTimeOrders).toHaveProperty('pending');
      expect(response.realTimeOrders).toHaveProperty('confirmed');
      expect(response.realTimeOrders).toHaveProperty('preparing');
      expect(response.realTimeOrders).toHaveProperty('delivering');
      expect(response.realTimeOrders).toHaveProperty('delivered');
      expect(response.realTimeOrders).toHaveProperty('total');
      
      // Validate driver utilization
      expect(response.driverUtilization).toHaveProperty('activeDrivers');
      expect(response.driverUtilization).toHaveProperty('totalDrivers');
      expect(response.driverUtilization).toHaveProperty('utilizationRate');
      expect(response.driverUtilization).toHaveProperty('driverStatus');
      
      // Validate delivery metrics
      expect(response.deliveryMetrics).toHaveProperty('onTimeRate');
      expect(response.deliveryMetrics).toHaveProperty('averageDeliveryTime');
      expect(response.deliveryMetrics).toHaveProperty('delayedDeliveries');
      expect(response.deliveryMetrics).toHaveProperty('failureRate');
    });

    test('should show operational alerts', async () => {
      const response = await apiHelper.getAnalytics('operations');
      
      expect(Array.isArray(response.alerts)).toBeTruthy();
      
      response.alerts.forEach((alert: any) => {
        expect(alert).toHaveProperty('id');
        expect(alert).toHaveProperty('type');
        expect(alert).toHaveProperty('severity');
        expect(alert).toHaveProperty('message');
        expect(alert).toHaveProperty('timestamp');
        expect(['low', 'medium', 'high', 'critical']).toContain(alert.severity);
      });
    });

    test('should update in near real-time', async () => {
      // Get initial metrics
      const response1 = await apiHelper.getAnalytics('operations');
      const timestamp1 = new Date(response1.timestamp);
      
      // Wait a bit
      await new Promise(resolve => setTimeout(resolve, 2000));
      
      // Get updated metrics
      const response2 = await apiHelper.getAnalytics('operations');
      const timestamp2 = new Date(response2.timestamp);
      
      // Timestamps should be different
      expect(timestamp2 > timestamp1).toBeTruthy();
    });
  });

  test.describe('Financial Dashboard API', () => {
    test('should get financial metrics', async () => {
      const endDate = new Date();
      const startDate = new Date(endDate.getFullYear(), endDate.getMonth(), 1);
      
      const response = await apiHelper.getAnalytics('financial', {
        start_date: startDate.toISOString(),
        end_date: endDate.toISOString()
      });
      
      expect(response).toHaveProperty('receivables');
      expect(response).toHaveProperty('collections');
      expect(response).toHaveProperty('outstandingInvoices');
      expect(response).toHaveProperty('revenueBySegment');
      expect(response).toHaveProperty('profitMargins');
      expect(response).toHaveProperty('cashPosition');
      
      // Validate accounts receivable aging
      expect(response.receivables).toHaveProperty('current');
      expect(response.receivables).toHaveProperty('overdue30');
      expect(response.receivables).toHaveProperty('overdue60');
      expect(response.receivables).toHaveProperty('overdue90');
      expect(response.receivables).toHaveProperty('total');
      
      // Validate revenue by segment
      expect(response.revenueBySegment).toHaveProperty('residential');
      expect(response.revenueBySegment).toHaveProperty('commercial');
      expect(response.revenueBySegment).toHaveProperty('industrial');
      
      // Validate profit margins
      expect(response.profitMargins).toHaveProperty('gross');
      expect(response.profitMargins).toHaveProperty('operating');
      expect(response.profitMargins).toHaveProperty('net');
    });

    test('should calculate outstanding invoices correctly', async () => {
      const response = await apiHelper.getAnalytics('financial');
      
      expect(Array.isArray(response.outstandingInvoices)).toBeTruthy();
      
      let totalOutstanding = 0;
      response.outstandingInvoices.forEach((invoice: any) => {
        expect(invoice).toHaveProperty('invoiceNumber');
        expect(invoice).toHaveProperty('customerName');
        expect(invoice).toHaveProperty('amount');
        expect(invoice).toHaveProperty('dueDate');
        expect(invoice).toHaveProperty('daysOverdue');
        
        totalOutstanding += invoice.amount;
      });
      
      // Total should match summary
      if (response.receivables && response.receivables.total) {
        expect(totalOutstanding).toBeCloseTo(response.receivables.total, 2);
      }
    });

    test('should require appropriate permissions', async () => {
      // Super admin and manager should have access
      const adminResponse = await apiHelper.get('/api/v1/analytics/financial');
      expect(adminResponse.ok()).toBeTruthy();
      
      const managerResponse = await managerApiHelper.get('/api/v1/analytics/financial');
      expect(managerResponse.ok()).toBeTruthy();
      
      // Driver should not have access
      const driverApiHelper = new APIHelper(await apiHelper['request']);
      await driverApiHelper.login('driver');
      
      const driverResponse = await driverApiHelper.get('/api/v1/analytics/financial');
      expect(driverResponse.status()).toBe(403);
    });
  });

  test.describe('Performance Analytics API', () => {
    test('should get system performance metrics', async () => {
      const timeRanges = ['1h', '6h', '24h', '7d', '30d'];
      
      for (const range of timeRanges) {
        const response = await apiHelper.getAnalytics('performance', {
          time_range: range
        });
        
        expect(response).toHaveProperty('systemMetrics');
        expect(response).toHaveProperty('apiUsage');
        expect(response).toHaveProperty('errorAnalysis');
        expect(response).toHaveProperty('userActivity');
        expect(response).toHaveProperty('resourceUtilization');
        
        // Validate system metrics
        expect(response.systemMetrics).toHaveProperty('uptime');
        expect(response.systemMetrics).toHaveProperty('responseTime');
        expect(response.systemMetrics).toHaveProperty('throughput');
        expect(response.systemMetrics).toHaveProperty('errorRate');
        
        // Validate API usage
        expect(response.apiUsage).toHaveProperty('totalRequests');
        expect(response.apiUsage).toHaveProperty('byEndpoint');
        expect(response.apiUsage).toHaveProperty('byMethod');
        expect(response.apiUsage).toHaveProperty('averageResponseTime');
        
        // Validate resource utilization
        expect(response.resourceUtilization).toHaveProperty('cpu');
        expect(response.resourceUtilization).toHaveProperty('memory');
        expect(response.resourceUtilization).toHaveProperty('database');
        expect(response.resourceUtilization).toHaveProperty('storage');
      }
    });

    test('should track error patterns', async () => {
      const response = await apiHelper.getAnalytics('performance', {
        time_range: '24h'
      });
      
      expect(response.errorAnalysis).toHaveProperty('byType');
      expect(response.errorAnalysis).toHaveProperty('byEndpoint');
      expect(response.errorAnalysis).toHaveProperty('trends');
      expect(response.errorAnalysis).toHaveProperty('topErrors');
      
      // Validate error categorization
      const errorTypes = Object.keys(response.errorAnalysis.byType);
      errorTypes.forEach(type => {
        expect(['4xx', '5xx', 'timeout', 'validation']).toContain(type);
      });
    });

    test('should only be accessible to super admin', async () => {
      // Super admin should have access
      const adminResponse = await apiHelper.get('/api/v1/analytics/performance');
      expect(adminResponse.ok()).toBeTruthy();
      
      // Manager should NOT have access
      const managerResponse = await managerApiHelper.get('/api/v1/analytics/performance');
      expect(managerResponse.status()).toBe(403);
    });
  });

  test.describe('Analytics Dashboard UI', () => {
    test('should display executive dashboard', async ({ page }) => {
      await TestHelpers.loginUI(page, 'administrator', 'SuperSecure#9876');
      await page.goto('/analytics/executive');
      
      // Wait for data to load
      await TestHelpers.waitForLoadingComplete(page);
      
      // Check key metric cards
      await expect(page.locator('[data-metric="revenue"]')).toBeVisible();
      await expect(page.locator('[data-metric="orders"]')).toBeVisible();
      await expect(page.locator('[data-metric="customers"]')).toBeVisible();
      await expect(page.locator('[data-metric="growth"]')).toBeVisible();
      
      // Check charts
      await expect(page.locator('#revenue-chart')).toBeVisible();
      await expect(page.locator('#orders-trend-chart')).toBeVisible();
      await expect(page.locator('#customer-segment-chart')).toBeVisible();
      
      // Date range selector
      await expect(page.locator('.date-range-selector')).toBeVisible();
      await page.click('[data-range="本月"]');
      await TestHelpers.waitForLoadingComplete(page);
      
      // Data should update
      const revenueValue = await page.locator('[data-metric="revenue"] .value').textContent();
      expect(revenueValue).toBeTruthy();
    });

    test('should display operations dashboard with real-time updates', async ({ page }) => {
      await TestHelpers.loginUI(page, 'administrator', 'SuperSecure#9876');
      await page.goto('/analytics/operations');
      
      // Real-time indicators
      await expect(page.locator('.real-time-indicator')).toBeVisible();
      await expect(page.locator('.real-time-indicator')).toHaveClass(/active/);
      
      // Order status widgets
      await expect(page.locator('.order-status-grid')).toBeVisible();
      const statusCards = page.locator('.status-card');
      expect(await statusCards.count()).toBeGreaterThan(0);
      
      // Driver utilization chart
      await expect(page.locator('#driver-utilization-chart')).toBeVisible();
      
      // Alerts panel
      await expect(page.locator('.alerts-panel')).toBeVisible();
      
      // Check for WebSocket connection (real-time updates)
      await page.waitForTimeout(2000);
      const updateTimestamp = await page.locator('.last-update').textContent();
      expect(updateTimestamp).toContain('秒前');
    });

    test('should display financial dashboard with filters', async ({ page }) => {
      await TestHelpers.loginUI(page, 'administrator', 'SuperSecure#9876');
      await page.goto('/analytics/financial');
      
      // Financial metrics
      await expect(page.locator('.receivables-summary')).toBeVisible();
      await expect(page.locator('.cash-flow-chart')).toBeVisible();
      await expect(page.locator('.profit-margin-gauges')).toBeVisible();
      
      // Outstanding invoices table
      await expect(page.locator('.outstanding-invoices-table')).toBeVisible();
      const invoiceRows = page.locator('.invoice-row');
      
      // Filter by overdue
      await page.click('input[name="showOverdueOnly"]');
      await TestHelpers.waitForLoadingComplete(page);
      
      // Check filtered results
      const overdueRows = await page.locator('.invoice-row.overdue').count();
      const totalRows = await invoiceRows.count();
      expect(overdueRows).toBe(totalRows);
    });

    test('should export analytics reports', async ({ page }) => {
      await TestHelpers.loginUI(page, 'administrator', 'SuperSecure#9876');
      await page.goto('/analytics/executive');
      
      // Open export dialog
      await page.click('button:has-text("匯出報表")');
      
      // Select options
      await page.selectOption('select[name="reportType"]', 'executive');
      await page.selectOption('select[name="format"]', 'excel');
      
      // Set date range
      const startDate = new Date();
      startDate.setMonth(startDate.getMonth() - 1);
      await page.fill('input[name="startDate"]', TestHelpers.formatTaiwanDate(startDate));
      await page.fill('input[name="endDate"]', TestHelpers.formatTaiwanDate(new Date()));
      
      // Export
      const downloadPromise = page.waitForEvent('download');
      await page.click('button:has-text("匯出")');
      
      const download = await downloadPromise;
      expect(download.suggestedFilename()).toMatch(/executive.*\.xlsx$/);
    });

    test('should handle data refresh', async ({ page }) => {
      await TestHelpers.loginUI(page, 'administrator', 'SuperSecure#9876');
      await page.goto('/analytics/operations');
      
      // Get initial data
      const initialValue = await page.locator('[data-metric="activeOrders"] .value').textContent();
      
      // Click refresh
      await page.click('button[aria-label="重新整理"]');
      await TestHelpers.waitForLoadingComplete(page);
      
      // Check timestamp updated
      const updateTime = await page.locator('.last-update').textContent();
      expect(updateTime).toContain('剛剛');
    });
  });

  test.describe('Custom Analytics', () => {
    test('should create custom analytics query', async () => {
      const customQuery = {
        metrics: ['revenue', 'orders', 'customers'],
        start_date: new Date(Date.now() - 30 * 24 * 60 * 60 * 1000).toISOString(),
        end_date: new Date().toISOString(),
        group_by: 'day',
        filters: JSON.stringify({
          customer_type: 'commercial',
          area: '信義區'
        })
      };
      
      const response = await apiHelper.get('/api/v1/analytics/custom', customQuery);
      const data = await response.json();
      
      expect(data).toHaveProperty('results');
      expect(data).toHaveProperty('query');
      expect(data).toHaveProperty('execution_time');
      
      // Results should be grouped by day
      expect(Array.isArray(data.results)).toBeTruthy();
      data.results.forEach((row: any) => {
        expect(row).toHaveProperty('date');
        expect(row).toHaveProperty('revenue');
        expect(row).toHaveProperty('orders');
        expect(row).toHaveProperty('customers');
      });
    });
  });

  test.describe('Real-time Analytics Updates', () => {
    test('should receive real-time order updates', async ({ page }) => {
      await TestHelpers.loginUI(page, 'administrator', 'SuperSecure#9876');
      await page.goto('/analytics/operations');
      
      // Wait for WebSocket connection
      await page.waitForTimeout(1000);
      
      // Create a new order in another context to trigger update
      const newOrder = await apiHelper.post('/api/v1/orders/', {
        客戶ID: 1,
        預定配送日期: new Date().toISOString(),
        配送地址: '即時更新測試',
        訂單項目: [
          {
            產品ID: 1,
            數量: 1,
            單價: 850
          }
        ],
        總金額: 850
      });
      
      // Should see real-time update notification
      await expect(page.locator('.real-time-notification')).toBeVisible({ timeout: 5000 });
      
      // Metrics should update
      await expect(page.locator('[data-metric="pendingOrders"]')).toContainText(/\d+/);
    });
  });
});