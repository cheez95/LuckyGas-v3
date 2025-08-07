import { test, expect } from '@playwright/test';
import { loginAsOfficeStaff, setupTestData, cleanupTestData } from '../helpers/test-utils';

test.describe('Customer Management Workflow', () => {
  test.beforeEach(async ({ page }) => {
    // Login as office staff
    await loginAsOfficeStaff(page);
    
    // Navigate to customer management
    await page.goto('/customers');
    await page.waitForLoadState('networkidle');
  });

  test('Should search for customers effectively', async ({ page }) => {
    // Test basic text search
    await page.fill('[placeholder="搜尋客戶"]', '王');
    await page.press('[placeholder="搜尋客戶"]', 'Enter');
    
    // Wait for search results
    await page.waitForTimeout(500);
    
    // Verify search results
    const results = await page.locator('tbody tr').count();
    expect(results).toBeGreaterThan(0);
    
    // Verify all results contain search term
    const rows = await page.locator('tbody tr').all();
    for (const row of rows) {
      const text = await row.textContent();
      expect(text?.toLowerCase()).toContain('王');
    }
    
    // Clear search
    await page.click('[aria-label="close-circle"]');
    await page.waitForTimeout(500);
    
    // Test phone number search
    await page.fill('[placeholder="搜尋客戶"]', '0912');
    await page.press('[placeholder="搜尋客戶"]', 'Enter');
    
    await page.waitForTimeout(500);
    const phoneResults = await page.locator('tbody tr').count();
    expect(phoneResults).toBeGreaterThan(0);
    
    // Test address search
    await page.click('[aria-label="close-circle"]');
    await page.fill('[placeholder="搜尋客戶"]', '台北市');
    await page.press('[placeholder="搜尋客戶"]', 'Enter');
    
    await page.waitForTimeout(500);
    const addressResults = await page.locator('tbody tr').count();
    expect(addressResults).toBeGreaterThan(0);
  });

  test('Should filter customers by various criteria', async ({ page }) => {
    // Filter by customer type
    await page.click('[data-testid="customer-type-filter"]');
    await page.click('label:has-text("商業客戶")');
    await page.click('button:has-text("確定")');
    
    await page.waitForTimeout(500);
    
    // Verify filtered results
    const commercialCustomers = await page.locator('tr:has-text("商業")').count();
    const totalCustomers = await page.locator('tbody tr').count();
    expect(commercialCustomers).toBe(totalCustomers);
    
    // Clear filter
    await page.click('[data-testid="clear-filters"]');
    
    // Filter by area
    await page.click('[data-testid="area-filter"]');
    await page.click('label:has-text("大安區")');
    await page.click('button:has-text("確定")');
    
    await page.waitForTimeout(500);
    const areaResults = await page.locator('tbody tr').count();
    expect(areaResults).toBeGreaterThan(0);
    
    // Filter by status
    await page.click('[data-testid="status-filter"]');
    await page.click('label:has-text("活躍")');
    await page.click('button:has-text("確定")');
    
    await page.waitForTimeout(500);
    const activeCustomers = await page.locator('tr:has-text("活躍")').count();
    expect(activeCustomers).toBeGreaterThan(0);
    
    // Combine multiple filters
    await page.click('[data-testid="customer-type-filter"]');
    await page.click('label:has-text("家庭客戶")');
    await page.click('button:has-text("確定")');
    
    await page.waitForTimeout(500);
    const combinedResults = await page.locator('tbody tr').count();
    expect(combinedResults).toBeGreaterThanOrEqual(0);
  });

  test('Should create a new customer with complete information', async ({ page }) => {
    // Click create customer button
    await page.click('button:has-text("新增客戶")');
    
    // Wait for modal
    await page.waitForSelector('[role="dialog"]', { state: 'visible' });
    
    // Fill basic information
    await page.fill('[data-testid="customer-name"]', '測試客戶有限公司');
    await page.fill('[data-testid="customer-contact"]', '張經理');
    await page.fill('[data-testid="customer-phone"]', '0912345678');
    await page.fill('[data-testid="customer-alt-phone"]', '02-23456789');
    
    // Select customer type
    await page.selectOption('[data-testid="customer-type"]', 'commercial');
    
    // Fill address information
    await page.fill('[data-testid="customer-postal-code"]', '106');
    await page.selectOption('[data-testid="customer-city"]', '台北市');
    await page.selectOption('[data-testid="customer-district"]', '大安區');
    await page.fill('[data-testid="customer-street"]', '和平東路二段123號');
    await page.fill('[data-testid="customer-floor"]', '5樓');
    
    // Add delivery preferences
    await page.click('[data-testid="delivery-preferences-tab"]');
    await page.selectOption('[data-testid="preferred-time"]', 'morning');
    await page.click('[data-testid="delivery-day-mon"]');
    await page.click('[data-testid="delivery-day-wed"]');
    await page.click('[data-testid="delivery-day-fri"]');
    
    // Add special instructions
    await page.fill('[data-testid="delivery-notes"]', '請先打電話確認，需要開發票');
    
    // Set credit terms (if not disabled)
    const creditTab = await page.locator('[data-testid="credit-terms-tab"]').isVisible();
    if (creditTab) {
      await page.click('[data-testid="credit-terms-tab"]');
      await page.selectOption('[data-testid="payment-terms"]', 'net30');
      await page.fill('[data-testid="credit-limit"]', '50000');
    }
    
    // Add contact persons
    await page.click('[data-testid="contacts-tab"]');
    await page.click('[data-testid="add-contact"]');
    await page.fill('[data-testid="contact-name-0"]', '李小姐');
    await page.fill('[data-testid="contact-phone-0"]', '0923456789');
    await page.fill('[data-testid="contact-email-0"]', 'lee@example.com');
    await page.selectOption('[data-testid="contact-role-0"]', 'purchasing');
    
    // Submit form
    await page.click('button:has-text("建立客戶")');
    
    // Wait for success message
    await expect(page.locator('.ant-message-success')).toBeVisible();
    await expect(page.locator('.ant-message-success')).toContainText('客戶建立成功');
    
    // Verify customer appears in list
    await page.waitForTimeout(1000);
    const newCustomer = page.locator('tr').filter({ hasText: '測試客戶有限公司' });
    await expect(newCustomer).toBeVisible();
  });

  test('Should update existing customer information', async ({ page }) => {
    // Find an existing customer
    const customerRow = page.locator('tr[data-row-key]').first();
    const customerName = await customerRow.locator('td:nth-child(2)').textContent();
    
    // Click edit button
    await customerRow.locator('button[aria-label="edit"]').click();
    
    // Wait for edit modal
    await page.waitForSelector('[role="dialog"]', { state: 'visible' });
    
    // Update contact information
    const phoneInput = page.locator('[data-testid="customer-phone"]');
    await phoneInput.clear();
    await phoneInput.fill('0987654321');
    
    // Update address
    await page.fill('[data-testid="customer-street"]', '更新後的地址123號');
    
    // Update delivery preferences
    await page.click('[data-testid="delivery-preferences-tab"]');
    await page.selectOption('[data-testid="preferred-time"]', 'afternoon');
    
    // Add a note about the update
    const notesInput = page.locator('[data-testid="delivery-notes"]');
    const existingNotes = await notesInput.inputValue();
    await notesInput.clear();
    await notesInput.fill(existingNotes + ' [已更新聯絡資訊]');
    
    // Save changes
    await page.click('button:has-text("儲存變更")');
    
    // Wait for success message
    await expect(page.locator('.ant-message-success')).toBeVisible();
    await expect(page.locator('.ant-message-success')).toContainText('客戶資訊更新成功');
    
    // Verify changes in list
    await page.waitForTimeout(1000);
    await expect(customerRow).toContainText('0987654321');
  });

  test('Should handle customer quick selection in order form', async ({ page }) => {
    // Navigate to orders page
    await page.goto('/orders');
    await page.waitForLoadState('networkidle');
    
    // Open create order modal
    await page.click('button:has-text("新增訂單")');
    await page.waitForSelector('[role="dialog"]', { state: 'visible' });
    
    // Click customer select
    await page.click('[data-testid="customer-select"]');
    
    // Test search within dropdown
    await page.type('[data-testid="customer-search"]', '王');
    await page.waitForTimeout(500); // Wait for debounce
    
    // Verify search results in dropdown
    const dropdownItems = await page.locator('.ant-select-item').count();
    expect(dropdownItems).toBeGreaterThan(0);
    
    // Select first customer
    await page.click('.ant-select-item:first-child');
    
    // Verify customer details are populated
    const selectedCustomer = await page.locator('[data-testid="selected-customer-name"]').textContent();
    expect(selectedCustomer).toBeTruthy();
    
    // Verify address is auto-filled
    const deliveryAddress = await page.locator('[data-testid="delivery-address"]').inputValue();
    expect(deliveryAddress).toBeTruthy();
    
    // Test quick add new customer
    await page.click('[data-testid="customer-select"]');
    await page.click('[data-testid="add-new-customer-quick"]');
    
    // Quick add form should open
    await expect(page.locator('[data-testid="quick-add-customer-form"]')).toBeVisible();
    
    // Fill minimal required fields
    await page.fill('[data-testid="quick-customer-name"]', '快速新增客戶');
    await page.fill('[data-testid="quick-customer-phone"]', '0911222333');
    await page.fill('[data-testid="quick-customer-address"]', '台北市信義區信義路五段7號');
    
    // Save quick customer
    await page.click('button:has-text("快速建立")');
    
    // Verify customer is selected
    await expect(page.locator('[data-testid="selected-customer-name"]')).toContainText('快速新增客戶');
  });

  test('Should manage customer delivery history', async ({ page }) => {
    // Click on a customer to view details
    const customerRow = page.locator('tr[data-row-key]').first();
    await customerRow.click();
    
    // Wait for customer details drawer
    await page.waitForSelector('.ant-drawer', { state: 'visible' });
    
    // Verify customer information is displayed
    await expect(page.locator('.ant-drawer-title')).toContainText('客戶詳情');
    
    // Navigate to delivery history tab
    await page.click('[data-testid="delivery-history-tab"]');
    
    // Verify delivery history is shown
    await expect(page.locator('[data-testid="delivery-history-table"]')).toBeVisible();
    
    // Check if there are past deliveries
    const deliveryCount = await page.locator('[data-testid="delivery-history-table"] tbody tr').count();
    if (deliveryCount > 0) {
      // Verify delivery details are shown
      const firstDelivery = page.locator('[data-testid="delivery-history-table"] tbody tr').first();
      await expect(firstDelivery).toContainText(/\d{4}-\d{2}-\d{2}/); // Date format
      
      // Click to view delivery details
      await firstDelivery.click();
      await expect(page.locator('[data-testid="delivery-details-modal"]')).toBeVisible();
      
      // Close modal
      await page.click('[data-testid="close-delivery-details"]');
    }
    
    // Check statistics
    await page.click('[data-testid="customer-statistics-tab"]');
    await expect(page.locator('[data-testid="total-orders-stat"]')).toBeVisible();
    await expect(page.locator('[data-testid="average-order-value"]')).toBeVisible();
    await expect(page.locator('[data-testid="last-order-date"]')).toBeVisible();
    
    // Close drawer
    await page.click('.ant-drawer-close');
    await page.waitForSelector('.ant-drawer', { state: 'hidden' });
  });

  test('Should export customer data', async ({ page }) => {
    // Select multiple customers
    await page.click('input[type="checkbox"][aria-label="Select all"]');
    
    // Verify selection
    const selectedCount = await page.locator('.ant-alert').textContent();
    expect(selectedCount).toContain('已選擇');
    
    // Click export button
    const downloadPromise = page.waitForEvent('download');
    await page.click('button:has-text("匯出")');
    
    // Select export options
    await page.click('label:has-text("包含聯絡人資訊")');
    await page.click('label:has-text("包含配送偏好")');
    await page.click('label:has-text("包含歷史記錄")');
    
    // Confirm export
    await page.click('button:has-text("確認匯出")');
    
    // Wait for download
    const download = await downloadPromise;
    
    // Verify download
    expect(download.suggestedFilename()).toContain('customers');
    expect(download.suggestedFilename()).toMatch(/\.(xlsx|csv)$/);
  });

  test('Should handle customer validation errors', async ({ page }) => {
    // Click create customer
    await page.click('button:has-text("新增客戶")');
    
    // Try to submit without required fields
    await page.click('button:has-text("建立客戶")');
    
    // Verify validation messages
    await expect(page.locator('.ant-form-item-explain-error')).toContainText('請輸入客戶名稱');
    
    // Fill name but invalid phone
    await page.fill('[data-testid="customer-name"]', '測試客戶');
    await page.fill('[data-testid="customer-phone"]', '123'); // Invalid phone
    
    await page.click('button:has-text("建立客戶")');
    await expect(page.locator('.ant-form-item-explain-error')).toContainText('請輸入有效的電話號碼');
    
    // Fix phone but invalid email
    await page.fill('[data-testid="customer-phone"]', '0912345678');
    await page.fill('[data-testid="customer-email"]', 'invalid-email'); // Invalid email
    
    await page.click('button:has-text("建立客戶")');
    await expect(page.locator('.ant-form-item-explain-error')).toContainText('請輸入有效的電子郵件');
    
    // Fix all validation errors
    await page.fill('[data-testid="customer-email"]', 'test@example.com');
    await page.fill('[data-testid="customer-street"]', '測試地址');
    
    // Should now be able to submit
    await page.click('button:has-text("建立客戶")');
    await expect(page.locator('.ant-form-item-explain-error')).not.toBeVisible();
  });

  test('Should manage customer tags and categories', async ({ page }) => {
    // Find a customer row
    const customerRow = page.locator('tr[data-row-key]').first();
    
    // Click quick tag button
    await customerRow.locator('[data-testid="quick-tag-btn"]').click();
    
    // Add tags
    await page.click('[data-testid="tag-vip"]');
    await page.click('[data-testid="tag-priority"]');
    await page.click('[data-testid="tag-long-term"]');
    
    // Save tags
    await page.click('button:has-text("儲存標籤")');
    
    // Verify tags appear in list
    await expect(customerRow.locator('.ant-tag')).toContainText('VIP');
    await expect(customerRow.locator('.ant-tag')).toContainText('優先');
    
    // Filter by tag
    await page.click('[data-testid="tag-filter"]');
    await page.click('label:has-text("VIP")');
    await page.click('button:has-text("確定")');
    
    await page.waitForTimeout(500);
    
    // Verify filtered results all have VIP tag
    const taggedCustomers = await page.locator('tr:has(.ant-tag:has-text("VIP"))').count();
    const totalFiltered = await page.locator('tbody tr').count();
    expect(taggedCustomers).toBe(totalFiltered);
  });
});

test.describe('Customer Management - Batch Operations', () => {
  test.beforeEach(async ({ page }) => {
    await loginAsOfficeStaff(page);
    await page.goto('/customers');
    await page.waitForLoadState('networkidle');
  });

  test('Should perform batch customer updates', async ({ page }) => {
    // Select multiple customers
    const checkboxes = page.locator('tbody input[type="checkbox"]');
    const count = Math.min(await checkboxes.count(), 5);
    
    for (let i = 0; i < count; i++) {
      await checkboxes.nth(i).click();
    }
    
    // Click batch operations
    await page.click('button:has-text("批次操作")');
    
    // Select batch update
    await page.click('li:has-text("批次更新")');
    
    // Wait for batch update modal
    await page.waitForSelector('[data-testid="batch-update-modal"]', { state: 'visible' });
    
    // Update delivery preferences for all selected
    await page.selectOption('[data-testid="batch-preferred-time"]', 'morning');
    await page.click('[data-testid="batch-tag-regular"]');
    
    // Confirm batch update
    await page.click('button:has-text("確認更新")');
    
    // Wait for confirmation dialog
    await page.click('button:has-text("確定")');
    
    // Wait for success message
    await expect(page.locator('.ant-message-success')).toBeVisible();
    await expect(page.locator('.ant-message-success')).toContainText(`成功更新 ${count} 位客戶`);
  });

  test('Should merge duplicate customers', async ({ page }) => {
    // Click tools menu
    await page.click('[data-testid="tools-menu"]');
    
    // Select find duplicates
    await page.click('li:has-text("查找重複客戶")');
    
    // Wait for duplicate detection
    await page.waitForSelector('[data-testid="duplicate-customers-modal"]', { state: 'visible' });
    
    // If duplicates found
    const duplicates = await page.locator('[data-testid="duplicate-group"]').count();
    if (duplicates > 0) {
      // Select first duplicate group
      const firstGroup = page.locator('[data-testid="duplicate-group"]').first();
      
      // Select primary record
      await firstGroup.locator('[data-testid="select-primary"]').first().click();
      
      // Select fields to merge
      await firstGroup.locator('[data-testid="merge-phone"]').click();
      await firstGroup.locator('[data-testid="merge-address"]').click();
      
      // Perform merge
      await firstGroup.locator('button:has-text("合併")').click();
      
      // Confirm merge
      await page.click('button:has-text("確認合併")');
      
      // Wait for success
      await expect(page.locator('.ant-message-success')).toContainText('客戶合併成功');
    } else {
      // No duplicates found
      await expect(page.locator('[data-testid="no-duplicates-message"]')).toBeVisible();
    }
    
    // Close modal
    await page.click('[data-testid="close-duplicates-modal"]');
  });
});