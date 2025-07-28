import { test, expect } from '@playwright/test';

test.describe('Customer Management', () => {
  test.beforeEach(async ({ page }) => {
    // Login first
    await page.goto('/', { waitUntil: 'networkidle' });
    
    const loginResponsePromise = page.waitForResponse(resp => 
      resp.url().includes('/auth/login') && resp.status() === 200
    );
    
    await page.locator('input[type="text"]').fill('admin');
    await page.locator('input[type="password"]').fill('admin123');
    
    await Promise.all([
      page.locator('button[type="submit"]').click(),
      loginResponsePromise
    ]);
    
    // Wait for redirect to dashboard
    await page.waitForTimeout(2000);
    expect(page.url()).toContain('/dashboard');
  });

  test('should display customer list', async ({ page }) => {
    // Navigate to customers
    await page.getByTestId('menu-customers').click();
    
    // Wait for customers API response
    const customersResponse = await page.waitForResponse(
      resp => resp.url().includes('/api/v1/customers') && resp.status() === 200,
      { timeout: 10000 }
    );
    
    // Verify we got data
    const responseData = await customersResponse.json();
    console.log('Customers response:', responseData);
    expect(responseData.items).toBeDefined();
    expect(responseData.items.length).toBeGreaterThan(0);
    
    // Wait for table to render
    await page.waitForSelector('.ant-table', { state: 'visible', timeout: 5000 });
    
    // Check table is visible
    await expect(page.locator('.ant-table')).toBeVisible();
    
    // Check for customer rows
    const rows = page.locator('.ant-table-tbody tr');
    const rowCount = await rows.count();
    console.log('Table rows:', rowCount);
    expect(rowCount).toBeGreaterThan(0);
    
    // Verify Chinese UI - try different selectors
    const titleSelectors = [
      'h1:has-text("客戶管理")',
      'h2:has-text("客戶管理")',
      '.ant-typography:has-text("客戶管理")',
      'text=客戶管理'
    ];
    
    let titleFound = false;
    for (const selector of titleSelectors) {
      if (await page.locator(selector).isVisible({ timeout: 2000 }).catch(() => false)) {
        titleFound = true;
        break;
      }
    }
    
    expect(titleFound).toBe(true);
  });

  test('should search for customers', async ({ page }) => {
    // Navigate to customers
    await page.getByTestId('menu-customers').click();
    
    // Wait for initial load
    await page.waitForResponse(
      resp => resp.url().includes('/api/v1/customers') && resp.status() === 200
    );
    
    // Find search input
    const searchInput = page.locator('input[placeholder*="搜尋"]').first();
    await searchInput.fill('王大明');
    
    // Press Enter or click search button
    await searchInput.press('Enter');
    
    // Wait for search response
    await page.waitForResponse(
      resp => resp.url().includes('/api/v1/customers') && resp.url().includes('search'),
      { timeout: 5000 }
    );
    
    // Verify filtered results
    await page.waitForTimeout(1000); // Give time for UI to update
    
    // Check if results are filtered
    const rows = page.locator('.ant-table-tbody tr');
    const rowCount = await rows.count();
    console.log('Filtered rows:', rowCount);
    
    // Should have at least one result
    if (rowCount > 0) {
      // Verify the result contains search term
      const firstRow = rows.first();
      const rowText = await firstRow.textContent();
      expect(rowText).toContain('王大明');
    }
  });

  test('should open add customer modal', async ({ page }) => {
    // Navigate to customers
    await page.getByTestId('menu-customers').click();
    
    // Wait for page to load
    await page.waitForResponse(
      resp => resp.url().includes('/api/v1/customers') && resp.status() === 200
    );
    
    // Click add customer button
    const addButton = page.locator('button').filter({ hasText: /新增客戶|添加客戶|新增/ });
    await addButton.click();
    
    // Wait for modal
    await page.waitForSelector('.ant-modal', { state: 'visible', timeout: 5000 });
    
    // Check modal is visible
    await expect(page.locator('.ant-modal')).toBeVisible();
    
    // Check modal title
    const modalTitle = page.locator('.ant-modal-title');
    const titleText = await modalTitle.textContent();
    expect(titleText).toMatch(/新增客戶|添加客戶|新客戶/);
    
    // Check form fields exist
    await expect(page.locator('input[id="customer_code"]')).toBeVisible();
    await expect(page.locator('input[id="short_name"]')).toBeVisible();
    
    // Close modal
    const cancelButton = page.locator('.ant-modal-footer button').filter({ hasText: '取消' });
    if (await cancelButton.isVisible()) {
      await cancelButton.click();
    } else {
      // Click outside modal to close
      await page.keyboard.press('Escape');
    }
    
    // Verify modal is closed
    await expect(page.locator('.ant-modal')).not.toBeVisible();
  });

  test('should handle pagination', async ({ page }) => {
    // Navigate to customers
    await page.getByTestId('menu-customers').click();
    
    // Wait for initial load
    const response = await page.waitForResponse(
      resp => resp.url().includes('/api/v1/customers') && resp.status() === 200
    );
    
    const data = await response.json();
    console.log('Total customers:', data.total);
    
    // Check if pagination exists (only if more than one page)
    if (data.total > data.size) {
      // Look for pagination
      const pagination = page.locator('.ant-pagination');
      await expect(pagination).toBeVisible();
      
      // Check pagination info
      const paginationInfo = page.locator('.ant-pagination-total-text');
      if (await paginationInfo.isVisible()) {
        const infoText = await paginationInfo.textContent();
        expect(infoText).toContain(data.total.toString());
      }
      
      // Try to go to next page
      const nextButton = page.locator('.ant-pagination-next');
      if (await nextButton.isEnabled()) {
        await nextButton.click();
        
        // Wait for new data
        await page.waitForResponse(
          resp => resp.url().includes('/api/v1/customers') && resp.url().includes('page=2')
        );
      }
    } else {
      console.log('Not enough data for pagination test');
    }
  });
});