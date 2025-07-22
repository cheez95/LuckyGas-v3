import { test, expect } from '@playwright/test';

test.describe('Customer Management', () => {
  test.beforeEach(async ({ page }) => {
    // Login first
    await page.goto('/login');
    await page.getByPlaceholder('電子郵件').fill('admin@luckygas.tw');
    await page.getByPlaceholder('密碼').fill('Admin123!');
    await page.getByRole('button', { name: '登入' }).click();
    await expect(page).toHaveURL(/.*dashboard/);
    
    // Navigate to customer management
    await page.getByRole('link', { name: '客戶管理' }).click();
    await expect(page).toHaveURL(/.*customers/);
  });

  test('should display customer list', async ({ page }) => {
    await expect(page.locator('h1')).toContainText('客戶管理');
    await expect(page.locator('.ant-table')).toBeVisible();
    
    // Check table headers
    await expect(page.locator('th')).toContainText('客戶編號');
    await expect(page.locator('th')).toContainText('姓名');
    await expect(page.locator('th')).toContainText('電話');
    await expect(page.locator('th')).toContainText('地址');
  });

  test('should search customers', async ({ page }) => {
    await page.getByPlaceholder('搜尋客戶...').fill('王');
    await page.getByPlaceholder('搜尋客戶...').press('Enter');
    
    // Should filter results
    await expect(page.locator('.ant-table-tbody tr')).toHaveCount(3);
  });

  test('should add new customer', async ({ page }) => {
    await page.getByRole('button', { name: '新增客戶' }).click();
    
    // Fill form
    await page.getByLabel('姓名').fill('測試客戶');
    await page.getByLabel('電話').fill('0912345678');
    await page.getByLabel('電子郵件').fill('test@example.com');
    await page.getByLabel('地址').fill('台北市信義區信義路五段7號');
    await page.getByLabel('瓦斯桶類型').click();
    await page.getByText('20kg').click();
    
    await page.getByRole('button', { name: '確定' }).click();
    
    // Should show success message
    await expect(page.locator('.ant-message-success')).toContainText('客戶新增成功');
  });

  test('should edit customer', async ({ page }) => {
    // Click edit on first customer
    await page.locator('.ant-table-tbody tr').first().getByRole('button', { name: 'edit' }).click();
    
    // Update name
    await page.getByLabel('姓名').clear();
    await page.getByLabel('姓名').fill('更新的客戶名稱');
    
    await page.getByRole('button', { name: '確定' }).click();
    
    // Should show success message
    await expect(page.locator('.ant-message-success')).toContainText('客戶更新成功');
  });

  test('should view customer details', async ({ page }) => {
    // Click on customer name
    await page.locator('.ant-table-tbody tr').first().locator('a').click();
    
    // Should show customer details drawer
    await expect(page.locator('.ant-drawer-title')).toContainText('客戶詳情');
    await expect(page.locator('.ant-descriptions')).toBeVisible();
    
    // Check order history section
    await expect(page.locator('h3')).toContainText('訂單歷史');
  });

  test('should filter by customer type', async ({ page }) => {
    await page.getByRole('combobox').click();
    await page.getByText('住宅').click();
    
    // Should filter results
    await expect(page.locator('.ant-table-tbody tr')).toHaveCount(8);
  });

  test('should export customer data', async ({ page }) => {
    const downloadPromise = page.waitForEvent('download');
    await page.getByRole('button', { name: '匯出' }).click();
    
    const download = await downloadPromise;
    expect(download.suggestedFilename()).toContain('customers');
    expect(download.suggestedFilename()).toContain('.xlsx');
  });

  test('should validate Taiwan phone number format', async ({ page }) => {
    await page.getByRole('button', { name: '新增客戶' }).click();
    
    // Try invalid phone number
    await page.getByLabel('電話').fill('123456');
    await page.getByLabel('姓名').fill('測試');
    await page.getByRole('button', { name: '確定' }).click();
    
    // Should show validation error
    await expect(page.locator('.ant-form-item-explain-error')).toContainText('請輸入有效的台灣電話號碼');
    
    // Try valid phone number
    await page.getByLabel('電話').clear();
    await page.getByLabel('電話').fill('0912345678');
    await page.getByRole('button', { name: '確定' }).click();
    
    // Should not show phone error
    await expect(page.locator('.ant-form-item-explain-error')).not.toContainText('電話');
  });
});