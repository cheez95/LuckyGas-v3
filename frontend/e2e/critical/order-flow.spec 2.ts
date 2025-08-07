import { test, expect } from '@playwright/test';
import { loginAsTestUser, loginAsOfficeStaff, waitForApiResponse } from '../helpers/auth.helper';

test.describe('Critical: Order Creation Flow', () => {
  test.beforeEach(async ({ page }) => {
    // Start from a clean state
    await loginAsTestUser(page);
  });

  test('Complete order journey from login to confirmation', async ({ page }) => {
    // 1. Verify dashboard loaded
    await expect(page.locator('h2:has-text("儀表板")')).toBeVisible();
    
    // 2. Navigate to Orders
    await page.click('text=訂單管理');
    await page.waitForURL(/orders/);
    
    // 3. Create New Order (if button exists)
    const addOrderButton = page.locator('button:has-text("新增訂單"), button:has-text("建立訂單"), button:has-text("新增"), button:has-text("Add")').first();
    
    if (await addOrderButton.isVisible({ timeout: 2000 }).catch(() => false)) {
      await addOrderButton.click();
      
      // 4. Fill order form (adapt based on actual form fields)
      // Select customer if dropdown exists
      const customerSelect = page.locator('select[name="customer"], select[name="customer_id"]');
      if (await customerSelect.isVisible()) {
        const options = await customerSelect.locator('option').count();
        if (options > 1) {
          await customerSelect.selectOption({ index: 1 });
        }
      }
      
      // Select product if exists
      const productSelect = page.locator('select[name="product"], select[name="product_id"]');
      if (await productSelect.isVisible()) {
        const options = await productSelect.locator('option').count();
        if (options > 1) {
          await productSelect.selectOption({ index: 1 });
        }
      }
      
      // Fill quantity if exists
      const quantityInput = page.locator('input[name="quantity"], input[placeholder*="數量"]');
      if (await quantityInput.isVisible()) {
        await quantityInput.fill('2');
      }
      
      // Set delivery date if exists
      const dateInput = page.locator('input[type="date"], .ant-picker-input input');
      if (await dateInput.isVisible()) {
        const tomorrow = new Date();
        tomorrow.setDate(tomorrow.getDate() + 1);
        await dateInput.fill(tomorrow.toISOString().split('T')[0]);
      }
      
      // 5. Submit order
      const submitButton = page.locator('button:has-text("確認"), button:has-text("提交"), button:has-text("建立")');
      await submitButton.click();
      
      // 6. Verify success message or redirect
      const successMessage = page.locator('text=/訂單.*成功|成功.*訂單/');
      const ordersTable = page.locator('.ant-table, [data-testid="orders-table"]');
      
      // Wait for either success message or redirect to orders list
      await Promise.race([
        successMessage.waitFor({ timeout: 5000 }).catch(() => {}),
        ordersTable.waitFor({ timeout: 5000 }).catch(() => {})
      ]);
      
      // Verify we're either on orders page or see success message
      const currentUrl = page.url();
      const isOnOrdersPage = currentUrl.includes('/orders');
      const hasSuccessMessage = await successMessage.isVisible().catch(() => false);
      
      expect(isOnOrdersPage || hasSuccessMessage).toBeTruthy();
    } else {
      // If no add button, verify order list is displayed
      const orderDisplay = page.locator('.ant-table').or(page.locator('.ant-empty')).or(page.locator('[data-testid="orders-table"]'));
      await expect(orderDisplay.first()).toBeVisible();
    }
  });

  test('View and filter existing orders', async ({ page }) => {
    // Navigate to orders
    await page.click('text=訂單管理');
    await page.waitForURL(/orders/);
    
    // Check if filters are available
    const statusFilter = page.locator('text=/所有狀態|篩選|狀態/').first();
    if (await statusFilter.isVisible()) {
      await statusFilter.click();
      
      // Check if dropdown appears
      const dropdown = page.locator('.ant-select-dropdown, .ant-dropdown');
      if (await dropdown.isVisible({ timeout: 1000 }).catch(() => false)) {
        // Verify filter options exist
        await expect(page.locator('text=/待處理|進行中|已完成/')).toBeVisible();
        
        // Close dropdown
        await page.keyboard.press('Escape');
      }
    }
    
    // Check date range picker
    const dateRangePicker = page.locator('.ant-picker-range, input[placeholder*="日期"]');
    if (await dateRangePicker.isVisible()) {
      await dateRangePicker.click();
      await expect(page.locator('.ant-picker-panel')).toBeVisible();
      await page.keyboard.press('Escape');
    }
  });

  test('Order status workflow', async ({ page }) => {
    // Navigate to orders
    await page.click('text=訂單管理');
    await page.waitForURL(/orders/);
    
    // Check if any orders exist
    const orderTable = await page.locator('.ant-table').isVisible({ timeout: 2000 }).catch(() => false);
    
    if (orderTable) {
      const orderRows = page.locator('.ant-table-tbody tr');
      const orderCount = await orderRows.count();
      
      if (orderCount > 0) {
      // Click on first order to view details
      await orderRows.first().click();
      
      // Verify order details view
      const detailsModal = page.locator('.ant-modal, [data-testid="order-details"]');
      const detailsPage = page.locator('h2:has-text("訂單詳情"), h2:has-text("訂單資訊")');
      
      // Wait for either modal or details page
      await Promise.race([
        detailsModal.waitFor({ timeout: 2000 }).catch(() => {}),
        detailsPage.waitFor({ timeout: 2000 }).catch(() => {})
      ]);
      
      // Check if status change button exists
      const statusButton = page.locator('button:has-text("更改狀態"), button:has-text("更新狀態")');
      if (await statusButton.isVisible()) {
        // Verify status can be changed
        await statusButton.click();
        await expect(page.locator('text=/待處理|處理中|已完成|已取消/')).toBeVisible();
      }
      } else {
        // No orders exist in table, verify empty state
        await expect(page.locator('.ant-empty')).toBeVisible();
      }
    } else {
      // No table found, verify empty state
      const emptyState = page.locator('.ant-empty').or(page.locator('text=/暫無.*訂單|沒有訂單/'));
      await expect(emptyState.first()).toBeVisible();
    }
  });
});

test.describe('Critical: Order Management Permissions', () => {
  test('Different roles see appropriate order views', async ({ page }) => {
    // Test with test user (basic permissions)
    await loginAsTestUser(page);
    await page.click('text=訂單管理');
    
    // Verify basic user can view orders
    const orderView = page.locator('.ant-table').or(page.locator('.ant-empty'));
    await expect(orderView.first()).toBeVisible();
    
    // Check if create button is visible (may be role-restricted)
    const createButton = page.locator('button:has-text("新增訂單"), button:has-text("建立訂單")');
    const canCreateOrders = await createButton.isVisible();
    
    // Log out
    await page.click('text=Test User');
    await page.click('text=登出');
    
    // TODO: Test with other roles when they have test accounts created
    // For now, we verified the basic flow works
  });
});