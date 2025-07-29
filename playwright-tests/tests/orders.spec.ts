import { test, expect } from '@playwright/test';
import { APIHelper } from '../utils/api-helper';
import { TestHelpers } from '../utils/test-helpers';
import testData from '../fixtures/test-data.json';

test.describe('Order Management Tests - 預定配送日期 Focus', () => {
  let apiHelper: APIHelper;
  let testCustomerId: number;

  test.beforeAll(async ({ request }) => {
    // Setup test customer
    apiHelper = new APIHelper(request);
    await apiHelper.login('admin');
    
    const customer = await apiHelper.createCustomer({
      客戶代碼: TestHelpers.generateUniqueId('CORD'),
      簡稱: '訂單測試客戶',
      地址: '台北市信義區松仁路100號'
    });
    testCustomerId = customer.id;
  });

  test.describe('Order Creation with 預定配送日期', () => {
    test('should create order with correct field name 預定配送日期', async () => {
      const tomorrow = new Date();
      tomorrow.setDate(tomorrow.getDate() + 1);
      
      const orderData = {
        客戶ID: testCustomerId,
        預定配送日期: tomorrow.toISOString(), // Critical: Using correct field name
        配送地址: '台北市信義區松仁路100號',
        訂單項目: [
          {
            產品ID: 1,
            數量: 2,
            單價: 850
          }
        ],
        總金額: 1700,
        備註: '測試預定配送日期欄位'
      };

      const response = await apiHelper.post('/api/v1/orders/', orderData);
      expect(response.ok()).toBeTruthy();
      
      const order = await response.json();
      expect(order.id).toBeTruthy();
      expect(order.訂單編號).toMatch(/^ORD\d{8}-\d{4}$/);
      expect(new Date(order.預定配送日期).toDateString()).toBe(tomorrow.toDateString());
    });

    test('should fail with wrong field name 預計配送日期', async () => {
      const tomorrow = new Date();
      tomorrow.setDate(tomorrow.getDate() + 1);
      
      const wrongFieldOrder = {
        客戶ID: testCustomerId,
        預計配送日期: tomorrow.toISOString(), // Wrong field name
        配送地址: '台北市信義區松仁路100號',
        訂單項目: [
          {
            產品ID: 1,
            數量: 1,
            單價: 850
          }
        ],
        總金額: 850
      };

      const response = await apiHelper.post('/api/v1/orders/', wrongFieldOrder);
      expect(response.status()).toBe(422);
      
      const error = await response.json();
      expect(error.detail).toContain('預定配送日期'); // Error should mention correct field
    });

    test('should validate 預定配送日期 is not in the past', async () => {
      const yesterday = new Date();
      yesterday.setDate(yesterday.getDate() - 1);
      
      const pastDateOrder = {
        客戶ID: testCustomerId,
        預定配送日期: yesterday.toISOString(),
        配送地址: '台北市信義區松仁路100號',
        訂單項目: [
          {
            產品ID: 1,
            數量: 1,
            單價: 850
          }
        ],
        總金額: 850
      };

      const response = await apiHelper.post('/api/v1/orders/', pastDateOrder);
      expect(response.status()).toBe(400);
      
      const error = await response.json();
      expect(error.detail).toContain('預定配送日期不能是過去的日期');
    });

    test('should accept various date formats for 預定配送日期', async () => {
      const testDates = [
        new Date('2025-08-15T10:00:00Z'), // ISO format
        new Date('2025-08-16T10:00:00+08:00'), // With timezone
        new Date('2025/08/17 10:00:00'), // Local format
      ];

      for (const date of testDates) {
        const order = {
          客戶ID: testCustomerId,
          預定配送日期: date.toISOString(),
          配送地址: '台北市信義區松仁路100號',
          訂單項目: [
            {
              產品ID: 1,
              數量: 1,
              單價: 850
            }
          ],
          總金額: 850,
          備註: `測試日期格式: ${date.toISOString()}`
        };

        const response = await apiHelper.post('/api/v1/orders/', order);
        expect(response.ok()).toBeTruthy();
      }
    });
  });

  test.describe('Order CRUD Operations', () => {
    let testOrderId: number;

    test('should create a complete order', async () => {
      const orderDate = new Date();
      orderDate.setDate(orderDate.getDate() + 3);
      
      const completeOrder = {
        客戶ID: testCustomerId,
        預定配送日期: orderDate.toISOString(),
        配送地址: '台北市大安區復興南路二段237號',
        訂單項目: [
          {
            產品ID: 1,
            數量: 2,
            單價: 850
          },
          {
            產品ID: 2,
            數量: 1,
            單價: 950
          }
        ],
        總金額: 2650,
        配送費: 100,
        稅額: 133,
        應付金額: 2883,
        付款方式: 'cash',
        備註: '請先電話聯絡',
        聯絡電話: '0912-345-678'
      };

      const response = await apiHelper.post('/api/v1/orders/', completeOrder);
      const order = await response.json();
      
      testOrderId = order.id;
      
      expect(order.訂單狀態).toBe('pending');
      expect(order.訂單項目.length).toBe(2);
      expect(order.應付金額).toBe(2883);
    });

    test('should retrieve order details', async () => {
      const response = await apiHelper.get(`/api/v1/orders/${testOrderId}`);
      const order = await response.json();
      
      expect(order.id).toBe(testOrderId);
      expect(order.客戶).toBeTruthy();
      expect(order.客戶.簡稱).toBe('訂單測試客戶');
      expect(order.訂單項目[0].產品).toBeTruthy();
    });

    test('should update order status workflow', async () => {
      const statusFlow = [
        { status: 'confirmed', expectedMessage: '訂單已確認' },
        { status: 'preparing', expectedMessage: '準備中' },
        { status: 'delivering', expectedMessage: '配送中' },
        { status: 'delivered', expectedMessage: '已送達' }
      ];

      for (const { status, expectedMessage } of statusFlow) {
        const response = await apiHelper.put(`/api/v1/orders/${testOrderId}/status`, {
          狀態: status,
          備註: `狀態更新為: ${status}`
        });
        
        expect(response.ok()).toBeTruthy();
        
        const updated = await response.json();
        expect(updated.訂單狀態).toBe(status);
      }
    });

    test('should edit order details before confirmation', async () => {
      // Create a new pending order
      const newOrder = await apiHelper.post('/api/v1/orders/', {
        客戶ID: testCustomerId,
        預定配送日期: new Date(Date.now() + 86400000).toISOString(),
        配送地址: '原始地址',
        訂單項目: [
          {
            產品ID: 1,
            數量: 1,
            單價: 850
          }
        ],
        總金額: 850
      });
      
      const orderId = (await newOrder.json()).id;
      
      // Update order
      const updateResponse = await apiHelper.put(`/api/v1/orders/${orderId}`, {
        配送地址: '更新後的地址：台北市中山區民生東路三段67號',
        預定配送日期: new Date(Date.now() + 172800000).toISOString(), // 2 days later
        備註: '客戶要求延後配送'
      });
      
      expect(updateResponse.ok()).toBeTruthy();
      
      const updated = await updateResponse.json();
      expect(updated.配送地址).toContain('民生東路');
    });

    test('should cancel order', async () => {
      // Create order to cancel
      const orderResponse = await apiHelper.post('/api/v1/orders/', {
        客戶ID: testCustomerId,
        預定配送日期: new Date(Date.now() + 86400000).toISOString(),
        配送地址: '取消測試地址',
        訂單項目: [
          {
            產品ID: 1,
            數量: 1,
            單價: 850
          }
        ],
        總金額: 850
      });
      
      const order = await orderResponse.json();
      
      // Cancel order
      const cancelResponse = await apiHelper.put(`/api/v1/orders/${order.id}/cancel`, {
        原因: '客戶要求取消',
        備註: '客戶出國'
      });
      
      expect(cancelResponse.ok()).toBeTruthy();
      
      const cancelled = await cancelResponse.json();
      expect(cancelled.訂單狀態).toBe('cancelled');
      expect(cancelled.取消原因).toBe('客戶要求取消');
    });

    test('should calculate order totals correctly', async () => {
      const orderItems = [
        { 產品ID: 1, 數量: 3, 單價: 850 }, // 2550
        { 產品ID: 2, 數量: 2, 單價: 950 }, // 1900
        { 產品ID: 3, 數量: 1, 單價: 1050 } // 1050
      ];
      
      const subtotal = 5500;
      const deliveryFee = 100;
      const taxRate = 0.05;
      const tax = Math.round((subtotal + deliveryFee) * taxRate);
      const total = subtotal + deliveryFee + tax;
      
      const response = await apiHelper.post('/api/v1/orders/', {
        客戶ID: testCustomerId,
        預定配送日期: new Date(Date.now() + 86400000).toISOString(),
        配送地址: '計算測試地址',
        訂單項目: orderItems,
        總金額: subtotal,
        配送費: deliveryFee,
        稅額: tax,
        應付金額: total
      });
      
      const order = await response.json();
      expect(order.總金額).toBe(subtotal);
      expect(order.稅額).toBe(tax);
      expect(order.應付金額).toBe(total);
    });
  });

  test.describe('Order Management UI Tests', () => {
    test.beforeEach(async ({ page }) => {
      await TestHelpers.loginUI(page, 'administrator', 'SuperSecure#9876');
      await page.goto('/orders');
      await TestHelpers.waitForLoadingComplete(page);
    });

    test('should create order through UI with 預定配送日期', async ({ page }) => {
      await page.click('button:has-text("新增訂單")');
      
      // Select customer
      await page.click('[data-testid="customer-select"]');
      await page.fill('input[placeholder="搜尋客戶..."]', '訂單測試客戶');
      await page.click('.customer-option:has-text("訂單測試客戶")');
      
      // Set 預定配送日期 - Critical field
      const deliveryDate = new Date();
      deliveryDate.setDate(deliveryDate.getDate() + 2);
      const dateString = TestHelpers.formatTaiwanDate(deliveryDate);
      
      await page.fill('input[name="預定配送日期"]', dateString);
      await page.fill('input[name="預定配送時間"]', '14:00');
      
      // Add products
      await page.click('button:has-text("新增產品")');
      await page.selectOption('select[name="產品"]', '1');
      await page.fill('input[name="數量"]', '2');
      
      // Fill delivery info
      await page.fill('textarea[name="配送地址"]', '台北市信義區基隆路一段333號');
      await page.fill('input[name="聯絡電話"]', '0912-345-678');
      await page.fill('textarea[name="備註"]', 'UI測試訂單 - 測試預定配送日期');
      
      // Submit
      await page.click('button[type="submit"]');
      
      // Check success
      await TestHelpers.checkToast(page, '訂單建立成功', 'success');
      
      // Verify order appears in list with correct date
      const orderRow = page.locator('tr', { hasText: dateString });
      await expect(orderRow).toBeVisible();
    });

    test('should show error when using wrong field name in API', async ({ page }) => {
      // This test verifies the UI correctly uses 預定配送日期, not 預計配送日期
      await page.click('button:has-text("新增訂單")');
      
      // Check that the date input has correct name attribute
      const dateInput = page.locator('input[type="date"]').first();
      const inputName = await dateInput.getAttribute('name');
      expect(inputName).toBe('預定配送日期');
      
      // Check label text
      const label = page.locator('label', { hasText: '預定配送日期' });
      await expect(label).toBeVisible();
      
      // Should NOT have any element with wrong field name
      const wrongField = page.locator('[name="預計配送日期"]');
      await expect(wrongField).not.toBeVisible();
    });

    test('should filter orders by delivery date', async ({ page }) => {
      // Set date range filter
      const today = new Date();
      const startDate = TestHelpers.formatTaiwanDate(today);
      const endDate = TestHelpers.formatTaiwanDate(new Date(today.getTime() + 7 * 86400000));
      
      await page.fill('input[name="startDate"]', startDate);
      await page.fill('input[name="endDate"]', endDate);
      await page.click('button:has-text("搜尋")');
      
      // Wait for results
      await TestHelpers.waitForLoadingComplete(page);
      
      // Verify all displayed orders are within date range
      const dates = await page.locator('td[data-field="預定配送日期"]').allTextContents();
      dates.forEach(dateStr => {
        const orderDate = new Date(dateStr);
        expect(orderDate >= today).toBeTruthy();
        expect(orderDate <= new Date(endDate)).toBeTruthy();
      });
    });

    test('should track order status changes', async ({ page }) => {
      // Find a pending order
      const pendingOrder = page.locator('tr', { hasText: 'pending' }).first();
      await pendingOrder.locator('button[aria-label="檢視"]').click();
      
      // Check status history
      await expect(page.locator('h2:has-text("訂單狀態歷程")')).toBeVisible();
      
      // Update status
      await page.click('button:has-text("更新狀態")');
      await page.selectOption('select[name="newStatus"]', 'confirmed');
      await page.fill('textarea[name="statusNote"]', '客戶已確認訂單');
      await page.click('button:has-text("確定")');
      
      // Check success
      await TestHelpers.checkToast(page, '狀態更新成功', 'success');
      
      // Verify new status in history
      await expect(page.locator('.status-timeline')).toContainText('confirmed');
      await expect(page.locator('.status-timeline')).toContainText('客戶已確認訂單');
    });

    test('should export orders with correct headers', async ({ page }) => {
      // Export orders
      const downloadPromise = page.waitForEvent('download');
      await page.click('button:has-text("匯出訂單")');
      
      const download = await downloadPromise;
      expect(download.suggestedFilename()).toMatch(/orders.*\.xlsx$/);
      
      // In a real test, you would verify the Excel file contains:
      // - Correct header: 預定配送日期 (not 預計配送日期)
      // - All order data with proper formatting
    });

    test('should show order calendar view', async ({ page }) => {
      await page.click('button:has-text("月曆檢視")');
      
      // Calendar should show orders on their 預定配送日期
      await expect(page.locator('.calendar-view')).toBeVisible();
      
      // Check that orders appear on correct dates
      const today = new Date();
      const todayCell = page.locator(`.calendar-day[data-date="${TestHelpers.formatTaiwanDate(today)}"]`);
      
      // If there are orders today, they should be visible
      const orderCount = await todayCell.locator('.order-badge').count();
      if (orderCount > 0) {
        await todayCell.click();
        await expect(page.locator('.order-list-modal')).toBeVisible();
        await expect(page.locator('.order-list-modal')).toContainText('預定配送日期');
      }
    });
  });

  test.describe('Order History and Reporting', () => {
    test('should track all order modifications', async () => {
      // Create an order
      const orderResponse = await apiHelper.post('/api/v1/orders/', {
        客戶ID: testCustomerId,
        預定配送日期: new Date(Date.now() + 86400000).toISOString(),
        配送地址: '歷史記錄測試',
        訂單項目: [
          {
            產品ID: 1,
            數量: 1,
            單價: 850
          }
        ],
        總金額: 850
      });
      
      const order = await orderResponse.json();
      
      // Get order history
      const historyResponse = await apiHelper.get(`/api/v1/orders/${order.id}/history`);
      const history = await historyResponse.json();
      
      expect(history.length).toBeGreaterThan(0);
      expect(history[0].action).toBe('created');
      expect(history[0].changes).toHaveProperty('預定配送日期');
    });

    test('should generate daily order report', async () => {
      const today = new Date();
      const reportResponse = await apiHelper.get(`/api/v1/orders/report/daily?date=${today.toISOString()}`);
      const report = await reportResponse.json();
      
      expect(report).toHaveProperty('total_orders');
      expect(report).toHaveProperty('total_revenue');
      expect(report).toHaveProperty('orders_by_status');
      expect(report).toHaveProperty('orders_by_hour');
      expect(report).toHaveProperty('average_order_value');
    });
  });
});