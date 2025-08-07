import { test, expect } from '@playwright/test';
import { loginAsOfficeStaff, setupTestData, cleanupTestData } from '../helpers/test-utils';

test.describe('Order Management Workflow', () => {
  test.beforeEach(async ({ page }) => {
    // Login as office staff
    await loginAsOfficeStaff(page);
    
    // Navigate to order management
    await page.goto('/orders');
    await page.waitForLoadState('networkidle');
  });

  test('Should create a new order successfully', async ({ page }) => {
    // Click create order button
    await page.click('button:has-text("新增訂單")');
    
    // Wait for modal to appear
    await page.waitForSelector('[role="dialog"]', { state: 'visible' });
    
    // Step 1: Select customer
    await page.click('[data-testid="customer-select"]');
    await page.type('[data-testid="customer-search"]', '王');
    await page.waitForTimeout(500); // Wait for search debounce
    
    // Select first customer from dropdown
    await page.click('.ant-select-item:first-child');
    
    // Step 2: Add products
    await page.click('[data-testid="add-product-btn"]');
    
    // Select product type
    await page.selectOption('[data-testid="product-type-select"]', '20KG');
    
    // Enter quantity
    await page.fill('[data-testid="product-quantity"]', '2');
    
    // Add another product
    await page.click('[data-testid="add-another-product"]');
    await page.selectOption('[data-testid="product-type-select-1"]', '50KG');
    await page.fill('[data-testid="product-quantity-1"]', '1');
    
    // Step 3: Set delivery details
    await page.selectOption('[data-testid="delivery-priority"]', 'urgent');
    
    // Add delivery notes
    await page.fill('[data-testid="delivery-notes"]', '請打電話確認');
    
    // Step 4: Submit order
    await page.click('button:has-text("建立訂單")');
    
    // Wait for success message
    await expect(page.locator('.ant-message-success')).toBeVisible();
    await expect(page.locator('.ant-message-success')).toContainText('訂單建立成功');
    
    // Verify order appears in list
    await page.waitForTimeout(1000);
    const orderRow = page.locator('tr').filter({ hasText: '王' }).first();
    await expect(orderRow).toBeVisible();
    
    // Verify order details
    await expect(orderRow).toContainText('20KG x 2');
    await expect(orderRow).toContainText('50KG x 1');
    await expect(orderRow).toContainText('緊急');
  });

  test('Should modify an existing order', async ({ page }) => {
    // Find an existing order
    const orderRow = page.locator('tr[data-row-key]').first();
    
    // Click edit button
    await orderRow.locator('button[aria-label="edit"]').click();
    
    // Wait for edit modal
    await page.waitForSelector('[role="dialog"]', { state: 'visible' });
    
    // Modify quantity
    const quantityInput = page.locator('[data-testid="product-quantity"]').first();
    await quantityInput.clear();
    await quantityInput.fill('3');
    
    // Change delivery priority
    await page.selectOption('[data-testid="delivery-priority"]', 'normal');
    
    // Update delivery notes
    const notesInput = page.locator('[data-testid="delivery-notes"]');
    await notesInput.clear();
    await notesInput.fill('已更新配送說明');
    
    // Save changes
    await page.click('button:has-text("儲存變更")');
    
    // Wait for success message
    await expect(page.locator('.ant-message-success')).toBeVisible();
    await expect(page.locator('.ant-message-success')).toContainText('訂單更新成功');
    
    // Verify changes in list
    await page.waitForTimeout(1000);
    await expect(orderRow).toContainText('3');
    await expect(orderRow).toContainText('一般');
  });

  test('Should cancel an order with reason', async ({ page }) => {
    // Find a pending order
    const orderRow = page.locator('tr[data-row-key]').filter({ hasText: '待處理' }).first();
    
    // Click more actions
    await orderRow.locator('button[aria-label="more"]').click();
    
    // Click cancel option
    await page.click('li:has-text("取消訂單")');
    
    // Wait for confirmation modal
    await page.waitForSelector('[role="dialog"]:has-text("取消訂單")', { state: 'visible' });
    
    // Select cancellation reason
    await page.selectOption('[data-testid="cancel-reason"]', 'customer_request');
    
    // Add additional notes
    await page.fill('[data-testid="cancel-notes"]', '客戶臨時取消');
    
    // Confirm cancellation
    await page.click('button:has-text("確認取消")');
    
    // Wait for success message
    await expect(page.locator('.ant-message-success')).toBeVisible();
    await expect(page.locator('.ant-message-success')).toContainText('訂單已取消');
    
    // Verify order status changed
    await page.waitForTimeout(1000);
    await expect(orderRow).toContainText('已取消');
    
    // Verify cancel reason is recorded
    await orderRow.locator('button[aria-label="info"]').click();
    await expect(page.locator('.ant-drawer')).toContainText('客戶要求');
    await expect(page.locator('.ant-drawer')).toContainText('客戶臨時取消');
  });

  test('Should handle bulk order operations', async ({ page }) => {
    // Select multiple orders
    await page.click('input[type="checkbox"][aria-label="Select all"]');
    
    // Verify selection count
    const selectedCount = await page.locator('.ant-alert').textContent();
    expect(selectedCount).toContain('已選擇');
    
    // Click bulk actions
    await page.click('button:has-text("批次操作")');
    
    // Select assign to route
    await page.click('li:has-text("指派路線")');
    
    // Wait for route assignment modal
    await page.waitForSelector('[role="dialog"]:has-text("指派路線")', { state: 'visible' });
    
    // Select route
    await page.selectOption('[data-testid="route-select"]', 'route-1');
    
    // Select driver
    await page.selectOption('[data-testid="driver-select"]', 'driver-1');
    
    // Confirm assignment
    await page.click('button:has-text("確認指派")');
    
    // Wait for success message
    await expect(page.locator('.ant-message-success')).toBeVisible();
    await expect(page.locator('.ant-message-success')).toContainText('批次指派成功');
    
    // Verify orders are assigned
    const assignedOrders = page.locator('tr:has-text("已指派")');
    const count = await assignedOrders.count();
    expect(count).toBeGreaterThan(0);
  });

  test('Should filter and search orders', async ({ page }) => {
    // Test status filter
    await page.click('[data-testid="status-filter"]');
    await page.click('label:has-text("待處理")');
    await page.click('button:has-text("確定")');
    
    // Verify filtered results
    await page.waitForTimeout(500);
    const pendingOrders = await page.locator('tr:has-text("待處理")').count();
    const totalOrders = await page.locator('tbody tr').count();
    expect(pendingOrders).toBe(totalOrders);
    
    // Clear filter
    await page.click('button[aria-label="close-circle"]');
    
    // Test date range filter
    await page.click('[data-testid="date-range-picker"]');
    await page.click('.ant-picker-today-btn');
    
    // Test customer search
    await page.fill('[placeholder="搜尋客戶名稱"]', '王');
    await page.press('[placeholder="搜尋客戶名稱"]', 'Enter');
    
    await page.waitForTimeout(500);
    const searchResults = await page.locator('tbody tr').count();
    expect(searchResults).toBeGreaterThan(0);
    
    // Verify all results contain search term
    const rows = await page.locator('tbody tr').all();
    for (const row of rows) {
      const text = await row.textContent();
      expect(text).toContain('王');
    }
  });

  test('Should export orders to Excel', async ({ page }) => {
    // Set up download promise before clicking
    const downloadPromise = page.waitForEvent('download');
    
    // Click export button
    await page.click('button:has-text("匯出")');
    
    // Select export options
    await page.click('label:has-text("包含客戶資訊")');
    await page.click('label:has-text("包含產品明細")');
    
    // Confirm export
    await page.click('button:has-text("確認匯出")');
    
    // Wait for download
    const download = await downloadPromise;
    
    // Verify download
    expect(download.suggestedFilename()).toContain('orders');
    expect(download.suggestedFilename()).toContain('.xlsx');
    
    // Save to temp location for verification
    const path = await download.path();
    expect(path).toBeTruthy();
  });

  test('Should handle order validation errors', async ({ page }) => {
    // Click create order
    await page.click('button:has-text("新增訂單")');
    
    // Try to submit without required fields
    await page.click('button:has-text("建立訂單")');
    
    // Verify validation messages
    await expect(page.locator('.ant-form-item-explain-error')).toContainText('請選擇客戶');
    
    // Select customer but no products
    await page.click('[data-testid="customer-select"]');
    await page.click('.ant-select-item:first-child');
    
    await page.click('button:has-text("建立訂單")');
    await expect(page.locator('.ant-message-error')).toContainText('請至少添加一項產品');
    
    // Add product with invalid quantity
    await page.click('[data-testid="add-product-btn"]');
    await page.selectOption('[data-testid="product-type-select"]', '20KG');
    await page.fill('[data-testid="product-quantity"]', '0');
    
    await page.click('button:has-text("建立訂單")');
    await expect(page.locator('.ant-form-item-explain-error')).toContainText('數量必須大於0');
    
    // Fix quantity to negative
    await page.fill('[data-testid="product-quantity"]', '-1');
    await expect(page.locator('.ant-form-item-explain-error')).toContainText('數量必須大於0');
    
    // Fix to valid quantity
    await page.fill('[data-testid="product-quantity"]', '2');
    await expect(page.locator('.ant-form-item-explain-error')).not.toBeVisible();
  });

  test('Should display order timeline and history', async ({ page }) => {
    // Click on an order to view details
    const orderRow = page.locator('tr[data-row-key]').first();
    await orderRow.click();
    
    // Wait for drawer to open
    await page.waitForSelector('.ant-drawer', { state: 'visible' });
    
    // Verify order details are displayed
    await expect(page.locator('.ant-drawer-title')).toContainText('訂單詳情');
    
    // Check timeline is visible
    await expect(page.locator('.ant-timeline')).toBeVisible();
    
    // Verify timeline items
    const timelineItems = page.locator('.ant-timeline-item');
    const itemCount = await timelineItems.count();
    expect(itemCount).toBeGreaterThan(0);
    
    // Verify first timeline item (order creation)
    const firstItem = timelineItems.first();
    await expect(firstItem).toContainText('訂單建立');
    
    // Check for status changes
    if (await page.locator('.ant-timeline-item:has-text("狀態變更")').count() > 0) {
      await expect(page.locator('.ant-timeline-item:has-text("狀態變更")')).toBeVisible();
    }
    
    // Close drawer
    await page.click('.ant-drawer-close');
    await page.waitForSelector('.ant-drawer', { state: 'hidden' });
  });
});

test.describe('Order Management - Offline Mode', () => {
  test('Should queue orders when offline', async ({ page, context }) => {
    // Login first
    await loginAsOfficeStaff(page);
    await page.goto('/orders');
    
    // Go offline
    await context.setOffline(true);
    
    // Try to create an order
    await page.click('button:has-text("新增訂單")');
    
    // Fill order details
    await page.click('[data-testid="customer-select"]');
    await page.click('.ant-select-item:first-child');
    
    await page.click('[data-testid="add-product-btn"]');
    await page.selectOption('[data-testid="product-type-select"]', '20KG');
    await page.fill('[data-testid="product-quantity"]', '2');
    
    // Submit order
    await page.click('button:has-text("建立訂單")');
    
    // Verify offline message
    await expect(page.locator('.ant-message-info')).toBeVisible();
    await expect(page.locator('.ant-message-info')).toContainText('離線模式');
    
    // Check that order is queued
    const queueIndicator = page.locator('[data-testid="offline-queue-indicator"]');
    await expect(queueIndicator).toBeVisible();
    await expect(queueIndicator).toContainText('1');
    
    // Go back online
    await context.setOffline(false);
    
    // Wait for sync
    await page.waitForTimeout(3000);
    
    // Verify sync success message
    await expect(page.locator('.ant-message-success')).toContainText('同步完成');
    
    // Verify queue is cleared
    await expect(queueIndicator).not.toBeVisible();
  });
});