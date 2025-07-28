import { test, expect } from '@playwright/test';
import { LoginPage } from './pages/LoginPage';
import { DashboardPage } from './pages/DashboardPage';
import { CustomerPage } from './pages/CustomerPage';
import { TestDataFactory } from './utils/TestDataFactory';

test.describe('Customer Management', () => {
  let loginPage: LoginPage;
  let dashboardPage: DashboardPage;
  let customerPage: CustomerPage;

  test.beforeEach(async ({ page }) => {
    loginPage = new LoginPage(page);
    dashboardPage = new DashboardPage(page);
    customerPage = new CustomerPage(page);
    
    // Login first
    await loginPage.navigateToLogin();
    await loginPage.login('admin', 'admin123');
    await loginPage.waitForLoginSuccess();
    
    // Navigate to customers
    await dashboardPage.navigateToCustomers();
  });

  test('should display customer list in Traditional Chinese', async ({ page }) => {
    // Check page title
    await expect(customerPage.pageTitle).toContainText('客戶管理');
    
    // Check Chinese localization
    const isChineseLocalized = await customerPage.checkChineseLocalization();
    expect(isChineseLocalized).toBe(true);
    
    // Check table is visible
    await expect(customerPage.customerTable).toBeVisible();
  });

  test('should create a new customer', async ({ page }) => {
    // Generate unique customer data
    const customerData = TestDataFactory.createCustomer();
    
    // Click add customer button
    await customerPage.clickAddCustomer();
    
    // Fill form with generated data
    await customerPage.fillCustomerForm(customerData);
    
    // Submit form
    await customerPage.submitCustomerForm();
    
    // Verify success by checking if modal closed and searching for the customer
    await customerPage.searchCustomer(customerData.customerCode);
    
    // Wait for search API call to complete
    await customerPage.waitForApiCall('/api/v1/customers', 'GET');
    await customerPage.waitForLoadingComplete();
    
    // Verify customer appears in list
    const customerCount = await customerPage.getCustomerCount();
    expect(customerCount).toBeGreaterThan(0);
    
    const foundCustomer = await customerPage.getCustomerData(0);
    expect(foundCustomer.customerCode).toBe(customerData.customerCode);
    expect(foundCustomer.shortName).toBe(customerData.shortName);
  });

  test('should edit an existing customer', async ({ page }) => {
    // Search for a specific customer
    await customerPage.searchCustomer('張');
    
    // Edit first customer in results
    await customerPage.editCustomer(0);
    
    // Update some fields
    await customerPage.fillCustomerForm({
      customerCode: '', // Keep existing
      name: '', // Keep existing
      mobile: '0922-333-444',
      avgDailyUsage: 15
    });
    
    // Submit changes
    await customerPage.submitCustomerForm();
    
    // Check success toast
    await expect(page.locator('.ant-message-notice')).toContainText('更新成功');
    
    // Refresh and verify changes
    await page.reload();
    await customerPage.searchCustomer('張');
    
    // Check updated data (would need to open detail view to verify)
  });

  test('should delete a customer', async ({ page }) => {
    // Get initial count
    const initialCount = await customerPage.getTotalCustomerCount();
    
    // Search for test customer
    await customerPage.searchCustomer('TEST');
    
    // Delete first result
    await customerPage.deleteCustomer(0);
    
    // Verify count decreased
    const newCount = await customerPage.getTotalCustomerCount();
    expect(newCount).toBe(initialCount - 1);
  });

  test('should search customers by name', async ({ page }) => {
    // Search by partial name
    await customerPage.searchCustomer('測試');
    
    // Check results
    const count = await customerPage.getCustomerCount();
    expect(count).toBeGreaterThan(0);
    
    // Verify all results contain search term
    for (let i = 0; i < count; i++) {
      const data = await customerPage.getCustomerData(i);
      // Check if search term appears in any relevant field
      const searchTerm = '測試';
      const containsSearchTerm = 
        data.shortName.includes(searchTerm) || 
        data.invoiceTitle.includes(searchTerm) ||
        data.customerCode.includes(searchTerm);
      expect(containsSearchTerm).toBe(true);
    }
  });

  test('should paginate customer list', async ({ page }) => {
    // Check pagination info
    const totalCount = await customerPage.getTotalCustomerCount();
    expect(totalCount).toBeGreaterThan(0);
    
    // If more than one page
    if (totalCount > 10) {
      // Go to next page
      await customerPage.goToNextPage();
      
      // Verify different customers are shown
      const firstPageCustomer = await customerPage.getCustomerData(0);
      
      await customerPage.goToPreviousPage();
      const previousPageCustomer = await customerPage.getCustomerData(0);
      
      expect(firstPageCustomer.customerCode).not.toBe(previousPageCustomer.customerCode);
    }
  });

  test('should validate required fields', async ({ page }) => {
    // Open add customer modal
    await customerPage.clickAddCustomer();
    
    // Try to submit without filling required fields
    await customerPage.submitCustomerForm();
    
    // Check validation errors
    const codeError = page.locator('#customer_customerCode_help');
    const nameError = page.locator('#customer_name_help');
    
    await expect(codeError).toBeVisible();
    await expect(nameError).toBeVisible();
    
    // Modal should still be open
    await expect(customerPage.modalTitle).toBeVisible();
  });

  test('should handle duplicate customer code', async ({ page }) => {
    // Try to create customer with existing code
    await customerPage.clickAddCustomer();
    
    await customerPage.fillCustomerForm({
      customerCode: 'C001', // Assuming this exists
      name: '重複測試'
    });
    
    await customerPage.submitCustomerForm();
    
    // Should show error
    await expect(page.locator('.ant-message-notice')).toContainText('客戶代碼已存在');
  });

  test('should bulk delete customers', async ({ page }) => {
    // Select multiple customers
    await customerPage.selectCustomersByCheckbox([0, 1, 2]);
    
    // Click bulk delete
    await customerPage.bulkDelete();
    
    // Check success message
    await expect(page.locator('.ant-message-notice')).toContainText('批量刪除成功');
  });

  test('should display customer details on row click', async ({ page }) => {
    // Click on a customer row
    await customerPage.clickCustomerRow(0);
    
    // Should navigate to customer detail page
    await expect(page).toHaveURL(/.*\/customers\/\d+/);
    
    // Detail page should show customer information
    await expect(page.locator('h2')).toContainText('客戶詳情');
  });

  test('should export customer list', async ({ page }) => {
    // Click export button
    const exportButton = page.locator('button').filter({ hasText: '匯出' });
    await exportButton.click();
    
    // Select Excel format
    await page.locator('.ant-dropdown-menu-item').filter({ hasText: 'Excel' }).click();
    
    // Wait for download
    const downloadPromise = page.waitForEvent('download');
    const download = await downloadPromise;
    
    // Verify filename
    expect(download.suggestedFilename()).toContain('customers');
    expect(download.suggestedFilename()).toContain('.xlsx');
  });

  test('should handle mobile responsive layout', async ({ page }) => {
    // Set mobile viewport
    await page.setViewportSize({ width: 375, height: 812 });
    
    // Check mobile layout
    const isMobileResponsive = await customerPage.checkMobileResponsive();
    expect(isMobileResponsive).toBe(true);
    
    // Table should be scrollable
    await expect(customerPage.customerTable).toBeVisible();
  });

  test('should validate phone number format', async ({ page }) => {
    await customerPage.clickAddCustomer();
    
    // Fill invalid phone
    await customerPage.phoneInput.fill('123'); // Too short
    await customerPage.mobileInput.fill('123456'); // Invalid format
    
    // Try to submit
    await customerPage.submitCustomerForm();
    
    // Should show validation errors
    const phoneError = page.locator('#customer_phone_help');
    const mobileError = page.locator('#customer_mobile_help');
    
    await expect(phoneError).toContainText('請輸入有效的電話號碼');
    await expect(mobileError).toContainText('請輸入有效的手機號碼');
  });

  test('should filter customers by area', async ({ page }) => {
    // Use area filter
    const areaFilter = page.locator('.ant-select').filter({ hasText: '選擇區域' });
    await areaFilter.click();
    await page.locator('.ant-select-dropdown .ant-select-item').filter({ hasText: '信義區' }).click();
    
    // Wait for filtered results
    await customerPage.waitForLoadComplete();
    
    // Verify all results are from selected area
    const count = await customerPage.getCustomerCount();
    for (let i = 0; i < count; i++) {
      const data = await customerPage.getCustomerData(i);
      expect(data.area).toBe('信義區');
    }
  });

  test('should show customer inventory', async ({ page }) => {
    // Click on a customer with inventory
    await customerPage.clickCustomerRow(0);
    
    // Click inventory tab
    await page.locator('.ant-tabs-tab').filter({ hasText: '庫存' }).click();
    
    // Should show inventory list
    await expect(page.locator('.inventory-list')).toBeVisible();
    
    // Should show cylinder information
    await expect(page.getByText('瓦斯桶')).toBeVisible();
  });

  test('should handle network errors gracefully', async ({ page }) => {
    // Simulate network failure
    await page.route('**/api/v1/customers', route => route.abort('failed'));
    
    // Try to refresh page
    await page.reload();
    
    // Should show error message
    await expect(page.locator('.ant-alert-error')).toBeVisible();
    await expect(page.locator('.ant-alert-error')).toContainText('網路連線錯誤');
  });
});