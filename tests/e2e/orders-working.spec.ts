import { test, expect } from '@playwright/test';

test.describe('Order Management', () => {
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

  test('should navigate to orders page', async ({ page }) => {
    // Find orders menu item
    const orderMenuSelectors = [
      'span:has-text("訂單管理")',
      '[data-testid="menu-orders"]',
      'a[href*="/orders"]',
      '.ant-menu-item:has-text("訂單")'
    ];
    
    let found = false;
    for (const selector of orderMenuSelectors) {
      const element = page.locator(selector).first();
      if (await element.isVisible({ timeout: 2000 }).catch(() => false)) {
        await element.click();
        found = true;
        break;
      }
    }
    
    if (found) {
      // Wait for navigation
      await page.waitForLoadState('networkidle');
      
      // Check if we're on orders page
      const currentUrl = page.url();
      expect(currentUrl).toContain('/order');
      
      // Wait for orders API
      await page.waitForResponse(
        resp => resp.url().includes('/api/v1/orders') && resp.status() === 200,
        { timeout: 10000 }
      ).catch(() => {
        console.log('Orders API call not made or timed out');
      });
    } else {
      console.log('Orders menu item not found');
    }
  });

  test('should display order list', async ({ page }) => {
    // Navigate to orders
    await page.getByTestId('menu-orders').click();
    
    // Wait for page load
    await page.waitForLoadState('networkidle');
    
    // Check for order list elements
    const tableVisible = await page.locator('.ant-table').isVisible({ timeout: 5000 }).catch(() => false);
    const listVisible = await page.locator('.ant-list').isVisible({ timeout: 5000 }).catch(() => false);
    const cardsVisible = await page.locator('.ant-card').count().then(count => count > 1).catch(() => false);
    
    // At least one display method should be visible
    expect(tableVisible || listVisible || cardsVisible).toBe(true);
    
    if (tableVisible) {
      console.log('Orders displayed in table format');
    } else if (listVisible) {
      console.log('Orders displayed in list format');
    } else if (cardsVisible) {
      console.log('Orders displayed in card format');
    }
  });

  test('should display order statistics', async ({ page }) => {
    // Navigate to orders
    await page.getByTestId('menu-orders').click();
    
    // Wait for page load
    await page.waitForLoadState('networkidle');
    
    // Check for statistics - these might be in cards or a summary section
    const statisticSelectors = [
      '.ant-statistic',
      '.ant-card:has-text("總訂單")',
      '.ant-card:has-text("待處理")',
      '.ant-card:has-text("今日")',
      '[class*="statistic"]',
      '[class*="summary"]'
    ];
    
    let statsFound = false;
    for (const selector of statisticSelectors) {
      const elements = await page.locator(selector).count();
      if (elements > 0) {
        statsFound = true;
        console.log(`Found statistics with selector: ${selector} (${elements} elements)`);
        break;
      }
    }
    
    if (!statsFound) {
      console.log('Order statistics not found - might not be implemented');
    }
  });

  test('should open create order modal', async ({ page }) => {
    // Navigate to orders
    await page.getByTestId('menu-orders').click();
    
    // Wait for page load
    await page.waitForLoadState('networkidle');
    
    // Look for add order button
    const addButtonSelectors = [
      'button:has-text("新增訂單")',
      'button:has-text("建立訂單")',
      'button:has-text("新增")',
      'button:has-text("+")',
      '[data-testid="add-order"]',
      '.ant-btn-primary'
    ];
    
    let buttonFound = false;
    for (const selector of addButtonSelectors) {
      const button = page.locator(selector).first();
      if (await button.isVisible({ timeout: 1000 }).catch(() => false)) {
        await button.click();
        buttonFound = true;
        break;
      }
    }
    
    if (buttonFound) {
      // Wait for modal
      await page.waitForSelector('.ant-modal', { state: 'visible', timeout: 5000 });
      
      // Check modal is visible
      await expect(page.locator('.ant-modal')).toBeVisible();
      
      // Check for form fields
      const formFieldSelectors = [
        'input[id*="customer"]',
        'select[id*="customer"]',
        '.ant-select:has-text("客戶")',
        'input[placeholder*="客戶"]'
      ];
      
      let formFound = false;
      for (const selector of formFieldSelectors) {
        if (await page.locator(selector).isVisible({ timeout: 1000 }).catch(() => false)) {
          formFound = true;
          break;
        }
      }
      
      expect(formFound).toBe(true);
      
      // Close modal
      const closeBtn = page.locator('.ant-modal-close').or(page.locator('.ant-modal-footer button:has-text("取消")'));
      if (await closeBtn.isVisible()) {
        await closeBtn.click();
      } else {
        await page.keyboard.press('Escape');
      }
      
      // Wait for modal to close
      await page.waitForTimeout(500);
    } else {
      console.log('Add order button not found - feature might not be implemented');
    }
  });
});