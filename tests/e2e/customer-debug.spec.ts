import { test, expect } from '@playwright/test';

test.describe('Customer Management Debug', () => {
  test('should navigate to customer page after login', async ({ page }) => {
    // Login first
    await page.goto('/', { waitUntil: 'networkidle' });
    
    // Wait for login response
    const loginResponsePromise = page.waitForResponse(resp => 
      resp.url().includes('/auth/login') && resp.status() === 200
    );
    
    await page.locator('input[type="text"]').fill('admin');
    await page.locator('input[type="password"]').fill('admin123');
    
    await Promise.all([
      page.locator('button[type="submit"]').click(),
      loginResponsePromise
    ]);
    
    // Wait for redirect
    await page.waitForTimeout(2000);
    
    // Verify we're on dashboard
    const currentUrl = page.url();
    console.log('After login URL:', currentUrl);
    expect(currentUrl).toContain('/dashboard');
    
    // Look for customer management link
    const customerLinkSelectors = [
      'a:has-text("客戶管理")',
      'span:has-text("客戶管理")',
      '[data-menu-id*="customer"]',
      'a[href*="/customer"]',
      '.ant-menu-item:has-text("客戶")'
    ];
    
    let customerLinkFound = false;
    for (const selector of customerLinkSelectors) {
      const element = page.locator(selector).first();
      if (await element.isVisible({ timeout: 2000 }).catch(() => false)) {
        console.log('Found customer link with selector:', selector);
        await element.click();
        customerLinkFound = true;
        break;
      }
    }
    
    if (!customerLinkFound) {
      // Take screenshot to see what's on the page
      await page.screenshot({ path: 'customer-nav-debug.png' });
      console.log('Customer link not found, screenshot saved');
      
      // List all visible links
      const links = await page.locator('a:visible').allTextContents();
      console.log('Visible links:', links);
      
      // List all menu items
      const menuItems = await page.locator('.ant-menu-item').allTextContents();
      console.log('Menu items:', menuItems);
    } else {
      // Wait for navigation
      await page.waitForLoadState('networkidle');
      
      // Check current URL
      const customerUrl = page.url();
      console.log('Customer page URL:', customerUrl);
      
      // Check if we're on customer page
      if (customerUrl.includes('/customer')) {
        console.log('Successfully navigated to customer page');
        
        // Check for customer table or list
        const tableVisible = await page.locator('.ant-table').isVisible({ timeout: 5000 }).catch(() => false);
        const listVisible = await page.locator('.ant-list').isVisible({ timeout: 5000 }).catch(() => false);
        
        console.log('Table visible:', tableVisible);
        console.log('List visible:', listVisible);
        
        if (!tableVisible && !listVisible) {
          await page.screenshot({ path: 'customer-page-debug.png' });
          console.log('No table or list found, screenshot saved');
        }
      }
    }
  });
});