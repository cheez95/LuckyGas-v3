import { test, expect } from '@playwright/test';

test.describe('Authentication Flow', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/login');
  });

  test('should display login page in Traditional Chinese', async ({ page }) => {
    await expect(page.locator('h2')).toContainText('登入');
    await expect(page.getByPlaceholder('電子郵件')).toBeVisible();
    await expect(page.getByPlaceholder('密碼')).toBeVisible();
    await expect(page.getByRole('button', { name: '登入' })).toBeVisible();
  });

  test('should show validation errors for empty fields', async ({ page }) => {
    await page.getByRole('button', { name: '登入' }).click();
    await expect(page.locator('.ant-form-item-explain-error')).toHaveCount(2);
  });

  test('should show validation error for invalid email', async ({ page }) => {
    await page.getByPlaceholder('電子郵件').fill('invalid-email');
    await page.getByPlaceholder('密碼').fill('password123');
    await page.getByRole('button', { name: '登入' }).click();
    
    await expect(page.locator('.ant-form-item-explain-error')).toContainText('請輸入有效的電子郵件');
  });

  test('should successfully login with valid credentials', async ({ page }) => {
    await page.getByPlaceholder('電子郵件').fill('admin@luckygas.tw');
    await page.getByPlaceholder('密碼').fill('Admin123!');
    await page.getByRole('button', { name: '登入' }).click();
    
    // Should redirect to dashboard
    await expect(page).toHaveURL(/.*dashboard/);
    await expect(page.locator('h1')).toContainText('儀表板');
  });

  test('should handle forgot password flow', async ({ page }) => {
    await page.getByRole('link', { name: '忘記密碼' }).click();
    
    await expect(page).toHaveURL(/.*forgot-password/);
    await expect(page.locator('h2')).toContainText('忘記密碼');
    
    // Submit forgot password form
    await page.getByPlaceholder('電子郵件').fill('user@example.com');
    await page.getByRole('button', { name: '發送重設連結' }).click();
    
    // Should show success message
    await expect(page.locator('.ant-message-success')).toContainText('密碼重設連結已發送');
  });

  test('should handle logout', async ({ page }) => {
    // First login
    await page.getByPlaceholder('電子郵件').fill('admin@luckygas.tw');
    await page.getByPlaceholder('密碼').fill('Admin123!');
    await page.getByRole('button', { name: '登入' }).click();
    
    await expect(page).toHaveURL(/.*dashboard/);
    
    // Logout
    await page.getByRole('button', { name: 'user' }).click();
    await page.getByRole('menuitem', { name: '登出' }).click();
    
    // Should redirect to login
    await expect(page).toHaveURL(/.*login/);
  });

  test('should persist session across page refresh', async ({ page }) => {
    // Login
    await page.getByPlaceholder('電子郵件').fill('admin@luckygas.tw');
    await page.getByPlaceholder('密碼').fill('Admin123!');
    await page.getByRole('button', { name: '登入' }).click();
    
    await expect(page).toHaveURL(/.*dashboard/);
    
    // Refresh page
    await page.reload();
    
    // Should still be on dashboard
    await expect(page).toHaveURL(/.*dashboard/);
    await expect(page.locator('h1')).toContainText('儀表板');
  });

  test('should redirect to login when accessing protected routes', async ({ page }) => {
    // Try to access dashboard without login
    await page.goto('/dashboard');
    
    // Should redirect to login
    await expect(page).toHaveURL(/.*login/);
  });
});