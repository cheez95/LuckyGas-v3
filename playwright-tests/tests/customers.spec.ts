import { test, expect } from '@playwright/test';
import { APIHelper } from '../utils/api-helper';
import { TestHelpers } from '../utils/test-helpers';
import testData from '../fixtures/test-data.json';

test.describe('Customer Management Tests', () => {
  let apiHelper: APIHelper;

  test.beforeEach(async ({ request, page }) => {
    apiHelper = new APIHelper(request);
    await apiHelper.login('admin');
  });

  test.describe('Customer CRUD Operations - API', () => {
    test('should create a new customer with all fields', async () => {
      const newCustomer = {
        客戶代碼: TestHelpers.generateUniqueId('CTEST'),
        簡稱: '測試客戶',
        全名: '測試客戶有限公司',
        地址: '台北市松山區南京東路三段248號',
        電話: '0912-888-999',
        類型: 'commercial',
        聯絡人: '王經理',
        Email: 'test@example.com',
        備註: 'E2E測試建立的客戶'
      };

      const response = await apiHelper.createCustomer(newCustomer);
      
      expect(response.id).toBeTruthy();
      expect(response.客戶代碼).toBe(newCustomer.客戶代碼);
      expect(response.簡稱).toBe(newCustomer.簡稱);
      expect(response.地址).toBe(newCustomer.地址);
    });

    test('should fail to create duplicate customer', async () => {
      const duplicateCustomer = {
        客戶代碼: testData.customers[0].客戶代碼,
        簡稱: '重複客戶',
        地址: '台北市測試區'
      };

      const response = await apiHelper.post('/api/v1/customers/', duplicateCustomer);
      expect(response.status()).toBe(400);
      
      const error = await response.json();
      expect(error.detail).toContain('客戶代碼已存在');
    });

    test('should retrieve customer list with pagination', async () => {
      const response = await apiHelper.get('/api/v1/customers/?skip=0&limit=10');
      const data = await response.json();
      
      expect(data).toHaveProperty('items');
      expect(data).toHaveProperty('total');
      expect(data).toHaveProperty('skip');
      expect(data).toHaveProperty('limit');
      expect(data.items.length).toBeLessThanOrEqual(10);
    });

    test('should search customers by name', async () => {
      const searchTerm = '王';
      const response = await apiHelper.get(`/api/v1/customers/?search=${encodeURIComponent(searchTerm)}`);
      const data = await response.json();
      
      expect(data.items.length).toBeGreaterThan(0);
      data.items.forEach((customer: any) => {
        expect(
          customer.簡稱.includes(searchTerm) || 
          customer.全名?.includes(searchTerm)
        ).toBeTruthy();
      });
    });

    test('should update customer information', async () => {
      // First create a customer
      const customerId = TestHelpers.generateUniqueId('CUPD');
      const createResponse = await apiHelper.createCustomer({
        客戶代碼: customerId,
        簡稱: '更新前',
        地址: '原始地址'
      });
      
      const id = createResponse.id;
      
      // Update the customer
      const updateData = {
        簡稱: '更新後',
        地址: '新地址：台北市大同區重慶北路一段1號',
        電話: '02-2555-6666'
      };
      
      const updateResponse = await apiHelper.put(`/api/v1/customers/${id}`, updateData);
      expect(updateResponse.ok()).toBeTruthy();
      
      const updated = await updateResponse.json();
      expect(updated.簡稱).toBe(updateData.簡稱);
      expect(updated.地址).toBe(updateData.地址);
      expect(updated.電話).toBe(updateData.電話);
    });

    test('should soft delete customer', async () => {
      // Create a customer to delete
      const customerId = TestHelpers.generateUniqueId('CDEL');
      const createResponse = await apiHelper.createCustomer({
        客戶代碼: customerId,
        簡稱: '待刪除客戶',
        地址: '刪除測試地址'
      });
      
      const id = createResponse.id;
      
      // Delete the customer
      const deleteResponse = await apiHelper.delete(`/api/v1/customers/${id}`);
      expect(deleteResponse.ok()).toBeTruthy();
      
      // Try to retrieve deleted customer
      const getResponse = await apiHelper.get(`/api/v1/customers/${id}`);
      expect(getResponse.status()).toBe(404);
    });

    test('should validate required fields', async () => {
      const invalidCustomers = [
        { 簡稱: '缺少代碼', 地址: '測試地址' }, // Missing 客戶代碼
        { 客戶代碼: 'TEST001', 地址: '測試地址' }, // Missing 簡稱
        { 客戶代碼: 'TEST002', 簡稱: '缺少地址' } // Missing 地址
      ];

      for (const customer of invalidCustomers) {
        const response = await apiHelper.post('/api/v1/customers/', customer);
        expect(response.status()).toBe(422);
      }
    });
  });

  test.describe('Customer Management - UI', () => {
    test.beforeEach(async ({ page }) => {
      await TestHelpers.loginUI(page, 'administrator', 'SuperSecure#9876');
      await page.goto('/customers');
      await TestHelpers.waitForLoadingComplete(page);
    });

    test('should display customer list page', async ({ page }) => {
      // Check page title
      await expect(page.locator('h1')).toContainText('客戶管理');
      
      // Check table headers
      const headers = ['客戶代碼', '簡稱', '地址', '電話', '類型', '操作'];
      for (const header of headers) {
        await expect(page.locator('th', { hasText: header })).toBeVisible();
      }
      
      // Check add button
      await expect(page.locator('button', { hasText: '新增客戶' })).toBeVisible();
    });

    test('should create customer through UI', async ({ page }) => {
      // Click add button
      await page.click('button:has-text("新增客戶")');
      
      // Fill form
      const newCustomer = {
        'input[name="客戶代碼"]': TestHelpers.generateUniqueId('CUI'),
        'input[name="簡稱"]': 'UI測試客戶',
        'input[name="全名"]': 'UI測試客戶股份有限公司',
        'input[name="地址"]': '台北市內湖區瑞光路583巷21號',
        'input[name="電話"]': '02-8797-8888',
        'select[name="類型"]': 'commercial',
        'input[name="聯絡人"]': '李經理',
        'input[name="Email"]': 'uitest@example.com',
        'textarea[name="備註"]': '透過UI建立的測試客戶'
      };
      
      await TestHelpers.fillForm(page, newCustomer);
      
      // Submit form
      await page.click('button[type="submit"]');
      
      // Check success message
      await TestHelpers.checkToast(page, '客戶建立成功', 'success');
      
      // Verify customer appears in list
      await expect(page.locator('td', { hasText: 'UI測試客戶' })).toBeVisible();
    });

    test('should edit customer through UI', async ({ page }) => {
      // Find and click edit button for first customer
      await page.click('tbody tr:first-child button[aria-label="編輯"]');
      
      // Update fields
      await page.fill('input[name="簡稱"]', 'UI更新客戶');
      await page.fill('input[name="電話"]', '02-2222-3333');
      
      // Save changes
      await page.click('button[type="submit"]');
      
      // Check success message
      await TestHelpers.checkToast(page, '客戶更新成功', 'success');
      
      // Verify changes in list
      await expect(page.locator('td', { hasText: 'UI更新客戶' })).toBeVisible();
    });

    test('should search customers', async ({ page }) => {
      // Type in search box
      await page.fill('input[placeholder="搜尋客戶..."]', '王');
      
      // Wait for search results
      await page.waitForTimeout(500); // Debounce delay
      
      // Check that results are filtered
      const rows = await page.locator('tbody tr').count();
      expect(rows).toBeGreaterThan(0);
      
      // Verify all results contain search term
      const customerNames = await page.locator('tbody tr td:nth-child(2)').allTextContents();
      customerNames.forEach(name => {
        expect(name).toContain('王');
      });
    });

    test('should handle pagination', async ({ page }) => {
      // Check pagination controls
      await expect(page.locator('.pagination')).toBeVisible();
      
      // Get total pages
      const totalText = await page.locator('.pagination-info').textContent();
      const match = totalText?.match(/共 (\d+) 筆/);
      const total = match ? parseInt(match[1]) : 0;
      
      if (total > 10) {
        // Click next page
        await page.click('button[aria-label="下一頁"]');
        
        // URL should update
        await expect(page).toHaveURL(/.*page=2/);
        
        // Different data should be shown
        const firstRowText = await page.locator('tbody tr:first-child').textContent();
        
        // Go back to first page
        await page.click('button[aria-label="上一頁"]');
        
        const newFirstRowText = await page.locator('tbody tr:first-child').textContent();
        expect(firstRowText).not.toBe(newFirstRowText);
      }
    });

    test('should delete customer with confirmation', async ({ page }) => {
      // Create a customer to delete
      const deleteCustomer = {
        客戶代碼: TestHelpers.generateUniqueId('CDUI'),
        簡稱: 'UI刪除測試',
        地址: '刪除測試地址'
      };
      
      await apiHelper.createCustomer(deleteCustomer);
      await page.reload();
      
      // Find the customer row
      const row = page.locator('tr', { hasText: deleteCustomer.簡稱 });
      
      // Click delete button
      await row.locator('button[aria-label="刪除"]').click();
      
      // Confirm deletion
      await page.click('button:has-text("確定")');
      
      // Check success message
      await TestHelpers.checkToast(page, '客戶刪除成功', 'success');
      
      // Customer should be removed from list
      await expect(page.locator('td', { hasText: deleteCustomer.簡稱 })).not.toBeVisible();
    });

    test('should show validation errors', async ({ page }) => {
      // Click add button
      await page.click('button:has-text("新增客戶")');
      
      // Try to submit empty form
      await page.click('button[type="submit"]');
      
      // Check validation messages
      await expect(page.locator('.error-message:has-text("客戶代碼為必填")')).toBeVisible();
      await expect(page.locator('.error-message:has-text("簡稱為必填")')).toBeVisible();
      await expect(page.locator('.error-message:has-text("地址為必填")')).toBeVisible();
    });

    test('should export customer list', async ({ page }) => {
      // Click export button
      const downloadPromise = page.waitForEvent('download');
      await page.click('button:has-text("匯出")');
      
      const download = await downloadPromise;
      
      // Verify download
      expect(download.suggestedFilename()).toMatch(/customers.*\.xlsx$/);
    });

    test('should filter by customer type', async ({ page }) => {
      // Select commercial type
      await page.selectOption('select[name="typeFilter"]', 'commercial');
      
      // Wait for filter to apply
      await page.waitForTimeout(500);
      
      // Check all displayed customers are commercial
      const types = await page.locator('tbody tr td:nth-child(5)').allTextContents();
      types.forEach(type => {
        expect(type).toBe('商業');
      });
      
      // Select residential type
      await page.selectOption('select[name="typeFilter"]', 'residential');
      
      // Check all displayed customers are residential
      const residentialTypes = await page.locator('tbody tr td:nth-child(5)').allTextContents();
      residentialTypes.forEach(type => {
        expect(type).toBe('住宅');
      });
    });
  });

  test.describe('Customer Import/Export', () => {
    test('should import customers from Excel', async ({ page }) => {
      await TestHelpers.loginUI(page, 'administrator', 'SuperSecure#9876');
      await page.goto('/customers');
      
      // Click import button
      await page.click('button:has-text("匯入")');
      
      // Upload file
      const fileInput = page.locator('input[type="file"]');
      await fileInput.setInputFiles('./fixtures/sample-customers.xlsx');
      
      // Confirm import
      await page.click('button:has-text("開始匯入")');
      
      // Check progress
      await expect(page.locator('.import-progress')).toBeVisible();
      
      // Wait for completion
      await expect(page.locator('.import-success')).toBeVisible({ timeout: 30000 });
      
      // Check success message
      const successText = await page.locator('.import-success').textContent();
      expect(successText).toContain('成功匯入');
    });
  });
});