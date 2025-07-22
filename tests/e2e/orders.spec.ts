import { test, expect } from '@playwright/test';

test.describe('Order Management', () => {
  test.beforeEach(async ({ page }) => {
    // Login first
    await page.goto('/login');
    await page.getByPlaceholder('電子郵件').fill('admin@luckygas.tw');
    await page.getByPlaceholder('密碼').fill('Admin123!');
    await page.getByRole('button', { name: '登入' }).click();
    await expect(page).toHaveURL(/.*dashboard/);
    
    // Navigate to order management
    await page.getByRole('link', { name: '訂單管理' }).click();
    await expect(page).toHaveURL(/.*orders/);
  });

  test('should display order statistics', async ({ page }) => {
    // Check statistics cards
    await expect(page.locator('.ant-statistic-title')).toContainText('總訂單數');
    await expect(page.locator('.ant-statistic-title')).toContainText('待處理');
    await expect(page.locator('.ant-statistic-title')).toContainText('今日配送');
    await expect(page.locator('.ant-statistic-title')).toContainText('本月營收');
  });

  test('should create new order', async ({ page }) => {
    await page.getByRole('button', { name: '新增訂單' }).click();
    
    // Select customer
    await page.getByLabel('客戶').click();
    await page.getByText('王小明').click();
    
    // Select cylinder type
    await page.getByLabel('瓦斯桶類型').click();
    await page.getByText('20kg').click();
    
    // Set quantity
    await page.getByLabel('數量').fill('2');
    
    // Select delivery date
    await page.getByLabel('配送日期').click();
    await page.locator('.ant-picker-today-btn').click();
    
    // Select priority
    await page.getByLabel('優先級').click();
    await page.getByText('緊急').click();
    
    await page.getByRole('button', { name: '確定' }).click();
    
    // Should show success message
    await expect(page.locator('.ant-message-success')).toContainText('訂單建立成功');
  });

  test('should filter orders by status', async ({ page }) => {
    // Filter by pending
    await page.getByRole('combobox').click();
    await page.getByText('待處理').click();
    
    // Check filtered results
    const rows = page.locator('.ant-table-tbody tr');
    await expect(rows).toHaveCount(5);
    
    // All should have pending status
    for (let i = 0; i < 5; i++) {
      await expect(rows.nth(i)).toContainText('待處理');
    }
  });

  test('should search orders', async ({ page }) => {
    await page.getByPlaceholder('搜尋訂單號、客戶名稱...').fill('ORD-2025');
    await page.getByPlaceholder('搜尋訂單號、客戶名稱...').press('Enter');
    
    // Should filter results
    const rows = page.locator('.ant-table-tbody tr');
    const count = await rows.count();
    expect(count).toBeGreaterThan(0);
    
    // All should contain search term
    for (let i = 0; i < count; i++) {
      await expect(rows.nth(i)).toContainText('ORD-2025');
    }
  });

  test('should view order details', async ({ page }) => {
    // Click eye icon on first order
    await page.locator('.ant-table-tbody tr').first().getByRole('button', { name: 'eye' }).click();
    
    // Should show order details drawer
    await expect(page.locator('.ant-drawer-title')).toContainText('訂單詳情');
    
    // Check timeline
    await expect(page.locator('.ant-timeline')).toBeVisible();
    await expect(page.locator('.ant-timeline-item')).toHaveCount(3);
  });

  test('should update order status', async ({ page }) => {
    // Click on first pending order
    const firstOrder = page.locator('.ant-table-tbody tr').first();
    await firstOrder.getByRole('button', { name: 'edit' }).click();
    
    // Change status
    await page.getByLabel('狀態').click();
    await page.getByText('已確認').click();
    
    await page.getByRole('button', { name: '確定' }).click();
    
    // Should show success message
    await expect(page.locator('.ant-message-success')).toContainText('訂單更新成功');
  });

  test('should assign order to driver', async ({ page }) => {
    // Filter confirmed orders
    await page.getByRole('combobox').click();
    await page.getByText('已確認').click();
    
    // Select first order
    await page.locator('.ant-checkbox-input').first().click();
    
    // Click assign button
    await page.getByRole('button', { name: '指派司機' }).click();
    
    // Select driver
    await page.getByLabel('選擇司機').click();
    await page.getByText('陳大明').click();
    
    await page.getByRole('button', { name: '確定' }).click();
    
    // Should show success message
    await expect(page.locator('.ant-message-success')).toContainText('訂單指派成功');
  });

  test('should handle payment status update', async ({ page }) => {
    // Click on unpaid order
    const unpaidOrder = page.locator('.ant-table-tbody tr').filter({ hasText: '未付款' }).first();
    await unpaidOrder.getByRole('button', { name: 'edit' }).click();
    
    // Update payment status
    await page.getByLabel('付款狀態').click();
    await page.getByText('已付款').click();
    
    // Update payment method
    await page.getByLabel('付款方式').click();
    await page.getByText('轉帳').click();
    
    await page.getByRole('button', { name: '確定' }).click();
    
    // Should show success message
    await expect(page.locator('.ant-message-success')).toContainText('訂單更新成功');
  });

  test('should export orders', async ({ page }) => {
    const downloadPromise = page.waitForEvent('download');
    
    // Click export button
    await page.getByRole('button', { name: '匯出' }).click();
    await page.getByText('匯出 Excel').click();
    
    const download = await downloadPromise;
    expect(download.suggestedFilename()).toContain('orders');
    expect(download.suggestedFilename()).toMatch(/\.(xlsx|xls)$/);
  });

  test('should display real-time order updates', async ({ page }) => {
    // Check for WebSocket connection indicator
    await expect(page.locator('[data-testid="ws-status"]')).toHaveAttribute('data-connected', 'true');
    
    // Wait for potential real-time update
    await page.waitForTimeout(2000);
    
    // Should maintain connection
    await expect(page.locator('[data-testid="ws-status"]')).toHaveAttribute('data-connected', 'true');
  });
});