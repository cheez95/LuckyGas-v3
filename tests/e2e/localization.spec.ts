import { test, expect } from '@playwright/test';

test.describe('Localization Tests', () => {
  test('should display all UI elements in Traditional Chinese', async ({ page }) => {
    await page.goto('/login');
    
    // Check login page
    await expect(page.locator('h2')).toContainText('登入');
    await expect(page.getByText('歡迎回到幸福氣配送管理系統')).toBeVisible();
    await expect(page.getByPlaceholder('電子郵件')).toBeVisible();
    await expect(page.getByPlaceholder('密碼')).toBeVisible();
    await expect(page.getByRole('button', { name: '登入' })).toBeVisible();
    await expect(page.getByRole('link', { name: '忘記密碼？' })).toBeVisible();
  });

  test('should use Taiwan date format', async ({ page }) => {
    // Login
    await page.goto('/login');
    await page.getByPlaceholder('電子郵件').fill('admin@luckygas.tw');
    await page.getByPlaceholder('密碼').fill('Admin123!');
    await page.getByRole('button', { name: '登入' }).click();
    
    // Go to orders
    await page.goto('/orders');
    
    // Check date format in table
    const dateCell = page.locator('.ant-table-tbody td').filter({ hasText: /\d{4}\/\d{2}\/\d{2}/ }).first();
    const dateText = await dateCell.textContent();
    
    // Should match Taiwan date format YYYY/MM/DD
    expect(dateText).toMatch(/^\d{4}\/\d{2}\/\d{2}/);
  });

  test('should validate Taiwan phone number format', async ({ page }) => {
    await page.goto('/login');
    await page.getByPlaceholder('電子郵件').fill('admin@luckygas.tw');
    await page.getByPlaceholder('密碼').fill('Admin123!');
    await page.getByRole('button', { name: '登入' }).click();
    
    await page.goto('/customers');
    await page.getByRole('button', { name: '新增客戶' }).click();
    
    // Test mobile number format
    await page.getByLabel('電話').fill('0912-345-678');
    await page.getByLabel('電話').blur();
    await expect(page.locator('.ant-form-item-explain-error')).not.toBeVisible();
    
    // Test landline format
    await page.getByLabel('電話').clear();
    await page.getByLabel('電話').fill('02-2345-6789');
    await page.getByLabel('電話').blur();
    await expect(page.locator('.ant-form-item-explain-error')).not.toBeVisible();
    
    // Test invalid format
    await page.getByLabel('電話').clear();
    await page.getByLabel('電話').fill('123456');
    await page.getByLabel('電話').blur();
    await expect(page.locator('.ant-form-item-explain-error')).toContainText('請輸入有效的台灣電話號碼');
  });

  test('should use Traditional Chinese for all labels and messages', async ({ page }) => {
    await page.goto('/login');
    await page.getByPlaceholder('電子郵件').fill('admin@luckygas.tw');
    await page.getByPlaceholder('密碼').fill('Admin123!');
    await page.getByRole('button', { name: '登入' }).click();
    
    // Check dashboard
    await expect(page.locator('h1')).toContainText('儀表板');
    await expect(page.locator('.ant-card-head-title')).toContainText('今日概況');
    
    // Check navigation menu
    await expect(page.getByRole('menuitem', { name: '客戶管理' })).toBeVisible();
    await expect(page.getByRole('menuitem', { name: '訂單管理' })).toBeVisible();
    await expect(page.getByRole('menuitem', { name: '路線規劃' })).toBeVisible();
    await expect(page.getByRole('menuitem', { name: '配送歷史' })).toBeVisible();
  });

  test('should display currency in TWD format', async ({ page }) => {
    await page.goto('/login');
    await page.getByPlaceholder('電子郵件').fill('admin@luckygas.tw');
    await page.getByPlaceholder('密碼').fill('Admin123!');
    await page.getByRole('button', { name: '登入' }).click();
    
    await page.goto('/orders');
    
    // Check currency format
    const priceCell = page.locator('.ant-table-tbody td').filter({ hasText: /NT\$/ }).first();
    const priceText = await priceCell.textContent();
    
    // Should use NT$ prefix
    expect(priceText).toMatch(/^NT\$\s*[\d,]+/);
  });

  test('should validate Taiwan address format', async ({ page }) => {
    await page.goto('/login');
    await page.getByPlaceholder('電子郵件').fill('admin@luckygas.tw');
    await page.getByPlaceholder('密碼').fill('Admin123!');
    await page.getByRole('button', { name: '登入' }).click();
    
    await page.goto('/customers');
    await page.getByRole('button', { name: '新增客戶' }).click();
    
    // Test valid Taiwan address
    await page.getByLabel('地址').fill('台北市信義區信義路五段7號');
    await page.getByLabel('地址').blur();
    await expect(page.locator('.ant-form-item-explain-error')).not.toBeVisible();
    
    // Test invalid address
    await page.getByLabel('地址').clear();
    await page.getByLabel('地址').fill('Some random address');
    await page.getByLabel('地址').blur();
    await expect(page.locator('.ant-form-item-explain-error')).toContainText('請輸入有效的台灣地址');
  });

  test('should display error messages in Traditional Chinese', async ({ page }) => {
    await page.goto('/login');
    
    // Submit empty form
    await page.getByRole('button', { name: '登入' }).click();
    
    // Check validation messages
    await expect(page.locator('.ant-form-item-explain-error').first()).toContainText('請輸入電子郵件');
    await expect(page.locator('.ant-form-item-explain-error').nth(1)).toContainText('請輸入密碼');
    
    // Test invalid email
    await page.getByPlaceholder('電子郵件').fill('invalid');
    await page.getByRole('button', { name: '登入' }).click();
    await expect(page.locator('.ant-form-item-explain-error').first()).toContainText('請輸入有效的電子郵件');
  });

  test('should display success messages in Traditional Chinese', async ({ page }) => {
    await page.goto('/login');
    await page.getByPlaceholder('電子郵件').fill('admin@luckygas.tw');
    await page.getByPlaceholder('密碼').fill('Admin123!');
    
    // Mock successful login
    await page.route('**/api/v1/auth/login', route => {
      route.fulfill({
        status: 200,
        body: JSON.stringify({
          access_token: 'mock-token',
          user: { id: '1', name: '管理員', role: 'admin' }
        })
      });
    });
    
    await page.getByRole('button', { name: '登入' }).click();
    
    // Should show Chinese success message
    await expect(page.locator('.ant-message-success')).toContainText('登入成功');
  });
});