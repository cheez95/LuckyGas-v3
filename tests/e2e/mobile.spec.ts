import { test, expect, devices } from '@playwright/test';

// Use mobile viewport
test.use({ ...devices['iPhone 12'] });

test.describe('Mobile Driver Interface', () => {
  test.beforeEach(async ({ page }) => {
    // Login as driver
    await page.goto('/login');
    await page.getByPlaceholder('電子郵件').fill('driver@luckygas.tw');
    await page.getByPlaceholder('密碼').fill('Driver123!');
    await page.getByRole('button', { name: '登入' }).click();
    
    // Should redirect to driver dashboard
    await expect(page).toHaveURL(/.*driver/);
  });

  test('should display driver dashboard on mobile', async ({ page }) => {
    // Check mobile layout
    await expect(page.locator('h4')).toContainText('今日路線');
    await expect(page.getByRole('button', { name: '開始配送' })).toBeVisible();
    
    // Check route progress
    await expect(page.locator('.ant-progress')).toBeVisible();
    
    // Check statistics
    await expect(page.locator('.ant-statistic-title')).toContainText('總站點');
    await expect(page.locator('.ant-statistic-title')).toContainText('已完成');
  });

  test('should toggle online/offline status', async ({ page }) => {
    const statusButton = page.getByRole('button', { name: '結束上線' });
    await expect(statusButton).toBeVisible();
    
    // Click to go offline
    await statusButton.click();
    await expect(page.getByRole('button', { name: '開始上線' })).toBeVisible();
    
    // Click to go online again
    await page.getByRole('button', { name: '開始上線' }).click();
    await expect(page.getByRole('button', { name: '結束上線' })).toBeVisible();
  });

  test('should navigate to route navigation', async ({ page }) => {
    await page.getByRole('button', { name: '開始配送' }).click();
    
    // Should navigate to navigation page
    await expect(page).toHaveURL(/.*driver\/navigation/);
    await expect(page.locator('#map')).toBeVisible();
  });

  test('should show current delivery stop', async ({ page }) => {
    // Check current stop card
    await expect(page.locator('h5')).toContainText('當前配送點');
    
    // Check action buttons
    await expect(page.getByRole('button', { name: '導航' })).toBeVisible();
    await expect(page.getByRole('button', { name: '掃描確認' })).toBeVisible();
    await expect(page.getByRole('button', { name: '聯絡客戶' })).toBeVisible();
  });

  test('should navigate to QR scanner', async ({ page }) => {
    await page.getByRole('button', { name: '掃描確認' }).click();
    
    // Should navigate to scanner page
    await expect(page).toHaveURL(/.*driver\/scan/);
    await expect(page.locator('h5')).toContainText('掃描確認配送');
    await expect(page.getByRole('button', { name: '開始掃描' })).toBeVisible();
  });

  test('should handle manual delivery confirmation', async ({ page }) => {
    await page.goto('/driver/scan');
    await page.getByRole('button', { name: '手動輸入' }).click();
    
    // Fill manual form
    await page.getByLabel('訂單編號').fill('ORD20250722-001');
    await page.getByLabel('瓦斯桶序號').fill('GAS123456');
    await page.getByRole('button', { name: '確認配送' }).click();
    
    // Should show success message
    await expect(page.locator('.ant-modal-content')).toContainText('配送完成');
  });

  test('should display delivery list', async ({ page }) => {
    // Check stops list
    await expect(page.locator('.ant-list')).toBeVisible();
    await expect(page.locator('.ant-list-item')).toHaveCount(3);
    
    // Check stop details
    const firstStop = page.locator('.ant-list-item').first();
    await expect(firstStop).toContainText('王小明');
    await expect(firstStop).toContainText('台北市大安區');
    await expect(firstStop).toContainText('20kg');
  });

  test('should handle touch interactions', async ({ page }) => {
    // Test swipe on list items
    const stopItem = page.locator('.ant-list-item').nth(2);
    await stopItem.click();
    
    // Should navigate to that stop
    await expect(page).toHaveURL(/.*driver\/navigation/);
  });

  test('should work offline (PWA)', async ({ page, context }) => {
    // Go offline
    await context.setOffline(true);
    
    // Should still display cached content
    await page.reload();
    await expect(page.locator('h4')).toContainText('今日路線');
    
    // Go back online
    await context.setOffline(false);
  });

  test('should request location permission', async ({ page, context }) => {
    // Grant location permission
    await context.grantPermissions(['geolocation']);
    
    // Navigate to navigation page
    await page.goto('/driver/navigation');
    
    // Should start tracking location
    await expect(page.locator('#map')).toBeVisible();
  });
});