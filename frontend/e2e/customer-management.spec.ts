import { test, expect } from '@playwright/test';
import { LoginPage } from './pages/LoginPage';
import { DashboardPage } from './pages/DashboardPage';
import { CustomerManagementPage } from './pages/CustomerManagementPage';
import { TestDataFactory } from './utils/TestDataFactory';

test.describe('Customer Management', () => {
  let loginPage: LoginPage;
  let dashboardPage: DashboardPage;
  let customerPage: CustomerManagementPage;

  test.beforeEach(async ({ page }) => {
    loginPage = new LoginPage(page);
    dashboardPage = new DashboardPage(page);
    customerPage = new CustomerManagementPage(page);
    
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
    // Click add customer button
    await customerPage.clickAddCustomer();
    
    // Generate unique customer name for this test
    const customerName = '測試客戶' + Date.now();
    
    // Fill form with test data
    await customerPage.fillCustomerForm({
      name: customerName,
      phone: '0912345678',
      address: '台北市信義區測試路123號',
      district: '信義區',
      postalCode: '11001',
      customerType: 'commercial',
      cylinderType: '20kg',
      notes: '這是測試客戶'
    });
    
    // Submit form
    await customerPage.submitCustomerForm();
    
    // Wait a moment for the table to refresh
    await page.waitForTimeout(1000);
    
    // Search for the created customer to verify it was created
    await customerPage.searchInput.fill(customerName);
    await page.keyboard.press('Enter');
    
    // Wait a moment for search to complete
    await page.waitForTimeout(1000);
    
    // Verify customer appears in search results
    const searchCount = await customerPage.getCustomerCount();
    expect(searchCount).toBeGreaterThan(0);
    
    // Verify the customer data in the first row
    const customerData = await customerPage.getCustomerData(0);
    expect(customerData.name).toBe(customerName);
    expect(customerData.phone).toBe('0912345678');
    expect(customerData.address).toContain('台北市信義區測試路123號');
    expect(customerData.customerType).toBe('商業');
    expect(customerData.cylinderType).toBe('20kg');
  });

  test('should edit an existing customer', async ({ page }) => {
    // Clear any search to show all customers
    await customerPage.searchInput.clear();
    await page.keyboard.press('Enter');
    await customerPage.waitForLoadingComplete();
    
    // Ensure we have customers to edit
    const customerCount = await customerPage.getCustomerCount();
    expect(customerCount).toBeGreaterThan(0);
    
    // Edit first customer in the table
    await customerPage.editCustomer(0);
    
    // Wait for modal to be fully loaded
    await customerPage.modalTitle.waitFor({ state: 'visible' });
    await customerPage.waitForAntAnimation();
    
    // Update phone number with a timestamp to ensure uniqueness
    const timestamp = Date.now().toString().slice(-4);
    const newPhone = `091234${timestamp}`;
    await customerPage.phoneInput.clear();
    await customerPage.phoneInput.fill(newPhone);
    
    // Submit changes (pass true for edit mode)
    await customerPage.submitCustomerForm(true);
    
    // Give the system time to process the update
    await page.waitForTimeout(2000);
    
    // Instead of immediately checking the table, let's verify the edit was successful
    // by opening the edit modal again and checking the phone value
    await customerPage.editCustomer(0);
    await customerPage.modalTitle.waitFor({ state: 'visible' });
    await customerPage.waitForAntAnimation();
    
    // Check if the phone number was updated
    const phoneValue = await customerPage.phoneInput.inputValue();
    expect(phoneValue).toBe(newPhone);
    
    // Close the modal
    await customerPage.modalCancelButton.click();
    await customerPage.modalTitle.waitFor({ state: 'hidden' });
  });

  test('should delete a customer', async ({ page }) => {
    // First ensure we have customers to delete by creating one
    await customerPage.clickAddCustomer();
    const timestamp = Date.now();
    await customerPage.fillCustomerForm({
      name: '刪除測試客戶' + timestamp,
      phone: '0944555666',
      address: '台北市松山區刪除路789號',
      district: '松山區',
      postalCode: '10501',
      customerType: 'commercial',
      cylinderType: '50kg'
    });
    
    await customerPage.submitCustomerForm();
    await customerPage.waitForLoadingComplete();
    
    // Clear search to show all customers
    await customerPage.searchInput.clear();
    await page.keyboard.press('Enter');
    await customerPage.waitForLoadingComplete();
    
    // Get initial count
    const initialCount = await customerPage.getCustomerCount();
    expect(initialCount).toBeGreaterThan(0);
    
    // Delete the last customer in the table (most recently added)
    await customerPage.deleteCustomer(initialCount - 1);
    
    // Wait for deletion to complete
    await customerPage.waitForLoadingComplete();
    
    // Verify count decreased
    const newCount = await customerPage.getCustomerCount();
    expect(newCount).toBe(initialCount - 1);
  });

  test('should search customers by name', async ({ page }) => {
    // First create a customer we can search for
    await customerPage.clickAddCustomer();
    const searchableName = '可搜尋客戶' + Date.now();
    
    await customerPage.fillCustomerForm({
      name: searchableName,
      phone: '0988777666',
      address: '台北市中山區搜尋路100號',
      district: '中山區',
      postalCode: '10401',
      customerType: 'residential',
      cylinderType: '16kg'
    });
    
    await customerPage.submitCustomerForm();
    await page.waitForTimeout(1000);
    
    // Search by partial name
    await customerPage.searchInput.fill('可搜尋');
    await page.keyboard.press('Enter');
    
    // Wait for filtering to complete
    await page.waitForTimeout(500);
    
    // Check results
    const count = await customerPage.getCustomerCount();
    expect(count).toBeGreaterThan(0);
    
    // Verify the search results contain our customer
    const firstCustomer = await customerPage.getCustomerData(0);
    expect(firstCustomer.name).toContain('可搜尋');
  });

  test('should validate required fields', async ({ page }) => {
    // Open add customer modal
    await customerPage.clickAddCustomer();
    
    // Try to submit without filling required fields - click the submit button directly
    await customerPage.modalConfirmButton.click();
    
    // Wait for validation to trigger
    await page.waitForTimeout(500);
    
    // Check validation errors - at least name, phone, address should show errors
    const errorCount = await page.locator('.ant-form-item-explain-error').count();
    expect(errorCount).toBeGreaterThan(0);
    
    // Modal should still be open
    await expect(customerPage.modalTitle).toBeVisible();
  });

  test('should validate phone number format', async ({ page }) => {
    await customerPage.clickAddCustomer();
    
    // Fill invalid phone
    await customerPage.phoneInput.fill('123'); // Too short
    await customerPage.nameInput.click(); // Trigger validation
    
    // Should show validation error
    const phoneField = page.locator('#customer_phone');
    const phoneFormItem = phoneField.locator('xpath=ancestor::div[contains(@class, "ant-form-item")]').first();
    await expect(phoneFormItem.locator('.ant-form-item-explain-error')).toContainText('電話格式必須為 09XXXXXXXX');
  });
});