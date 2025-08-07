import { test, expect } from '@playwright/test';
import { loginAsTestUser } from '../helpers/auth.helper';

test.describe('Error Recovery Tests', () => {
  test('should recover from errors gracefully', async ({ page, context }) => {
    await loginAsTestUser(page);
    
    // Navigate to customers page
    await page.click('text=客戶管理');
    await page.waitForURL(/customers/);
    
    // Ensure page loaded successfully first
    await page.waitForLoadState('networkidle');
    
    // Block all API calls
    await context.route('**/api/v1/**', route => route.abort());
    
    // Try to refresh the page
    await page.reload();
    
    // Should show error message or loading state
    const errorIndicators = [
      'text=/網路連線錯誤|連線失敗|無法載入|載入失敗|錯誤/',
      'text=/重試|重新載入|刷新/',
      '.ant-result-error',
      '.error-message',
      'text=/請檢查網路連線|請稍後再試/'
    ];
    
    let foundError = false;
    for (const indicator of errorIndicators) {
      if (await page.locator(indicator).isVisible({ timeout: 5000 }).catch(() => false)) {
        foundError = true;
        break;
      }
    }
    
    // Some indication of error should be shown
    expect(foundError).toBeTruthy();
    
    // Restore network
    await context.unroute('**/api/v1/**');
    
    // Try to recover - either by clicking retry or refreshing
    const retryButton = page.locator('button:has-text("重試"), button:has-text("重新載入")');
    if (await retryButton.isVisible()) {
      await retryButton.click();
    } else {
      await page.reload();
    }
    
    // Should recover and show data
    await expect(page.locator('.ant-table, [data-testid="customer-table"]')).toBeVisible({ timeout: 10000 });
  });

  test('should recover from errors gracefully - 2', async ({ page, context }) => {
    await loginAsTestUser(page);
    
    // Mock API to return errors
    await context.route('**/api/v1/orders', route => {
      route.fulfill({
        status: 500,
        contentType: 'application/json',
        body: JSON.stringify({ detail: 'Internal server error' })
      });
    });
    
    // Navigate to orders
    await page.click('text=訂單管理');
    
    // Should show error state
    const errorStates = [
      '.ant-alert-error',
      '.ant-result-error',
      'text=/錯誤|失敗|無法載入/',
      '.error-boundary'
    ];
    
    let hasErrorState = false;
    for (const errorState of errorStates) {
      if (await page.locator(errorState).isVisible({ timeout: 5000 }).catch(() => false)) {
        hasErrorState = true;
        break;
      }
    }
    
    // Should not crash - either show error or empty state
    const hasEmptyState = await page.locator('.ant-empty').isVisible();
    expect(hasErrorState || hasEmptyState).toBeTruthy();
  });

  test('should recover from errors gracefully - 3', async ({ page, context }) => {
    await loginAsTestUser(page);
    
    // Mock auth to return 401
    await context.route('**/api/v1/auth/me', route => {
      route.fulfill({
        status: 401,
        contentType: 'application/json',
        body: JSON.stringify({ detail: 'Token expired' })
      });
    });
    
    // Trigger an API call that checks auth
    await page.click('text=客戶管理');
    
    // Should redirect to login or show auth error
    await page.waitForURL(/login/, { timeout: 10000 }).catch(() => {
      // If not redirected, check for auth error message
      expect(page.locator('text=/登入已過期|請重新登入|授權失敗/')).toBeVisible();
    });
  });

  test('should recover from errors gracefully - 4', async ({ page, context }) => {
    await loginAsTestUser(page);
    
    // Navigate to orders
    await page.click('text=訂單管理');
    await page.waitForURL(/orders/);
    
    // Check if add order button exists
    const addButton = page.locator('button:has-text("新增訂單"), button:has-text("建立訂單")');
    
    if (await addButton.isVisible()) {
      // Mock order creation to fail
      await context.route('**/api/v1/orders', route => {
        if (route.request().method() === 'POST') {
          route.fulfill({
            status: 400,
            contentType: 'application/json',
            body: JSON.stringify({ 
              detail: 'Invalid order data',
              errors: {
                customer_id: 'Customer not found',
                products: 'At least one product required'
              }
            })
          });
        } else {
          route.continue();
        }
      });
      
      await addButton.click();
      
      // Fill form if it appears
      const submitButton = page.locator('button:has-text("確認"), button:has-text("提交")');
      if (await submitButton.isVisible()) {
        await submitButton.click();
        
        // Should show validation errors
        const errorMessages = [
          'text=/客戶不存在|無效的客戶/',
          'text=/請選擇產品|產品必填/',
          '.ant-form-item-explain-error',
          '.ant-message-error'
        ];
        
        let hasErrorMessage = false;
        for (const error of errorMessages) {
          if (await page.locator(error).isVisible({ timeout: 3000 }).catch(() => false)) {
            hasErrorMessage = true;
            break;
          }
        }
        
        // Should show some error feedback
        expect(hasErrorMessage).toBeTruthy();
        
        // Form should still be visible (not closed)
        expect(submitButton).toBeVisible();
      }
    }
  });

  test('should recover from errors gracefully - 5', async ({ page, context }) => {
    await loginAsTestUser(page);
    
    // Simulate slow network
    await context.route('**/api/v1/**', async route => {
      await new Promise(resolve => setTimeout(resolve, 3000)); // 3 second delay
      await route.continue();
    });
    
    // Navigate to customers
    await page.click('text=客戶管理');
    
    // Should show loading state
    const loadingIndicators = [
      '.ant-spin',
      '.loading',
      'text=/載入中|加載中|請稍候/',
      '.ant-skeleton'
    ];
    
    let hasLoadingState = false;
    for (const indicator of loadingIndicators) {
      if (await page.locator(indicator).isVisible({ timeout: 1000 }).catch(() => false)) {
        hasLoadingState = true;
        break;
      }
    }
    
    // Should show loading indication
    expect(hasLoadingState).toBeTruthy();
    
    // Eventually should load
    await expect(page.locator('.ant-table, .ant-empty')).toBeVisible({ timeout: 10000 });
  });

  test('should recover from errors gracefully - 6', async ({ page, context }) => {
    await loginAsTestUser(page);
    
    let requestCount = 0;
    
    // Make some API calls fail randomly
    await context.route('**/api/v1/**', route => {
      requestCount++;
      if (requestCount % 3 === 0) {
        // Fail every third request
        route.abort();
      } else {
        route.continue();
      }
    });
    
    // Navigate to dashboard
    await page.click('text=儀表板');
    await page.waitForTimeout(2000);
    
    // Dashboard should still be functional with partial data
    await expect(page.locator('h2:has-text("儀表板")')).toBeVisible();
    
    // Some widgets might show error or empty state
    const widgets = page.locator('.ant-card, .dashboard-widget');
    const widgetCount = await widgets.count();
    
    // At least some widgets should render
    expect(widgetCount).toBeGreaterThan(0);
  });

  test('should recover from errors gracefully - 7', async ({ page }) => {
    await loginAsTestUser(page);
    
    // Navigate through multiple pages
    await page.click('text=客戶管理');
    await page.waitForURL(/customers/);
    
    await page.click('text=訂單管理');
    await page.waitForURL(/orders/);
    
    await page.click('text=路線規劃');
    await page.waitForURL(/routes/);
    
    // Go back
    await page.goBack();
    await expect(page).toHaveURL(/orders/);
    await expect(page.locator('h2:has-text("訂單管理"), h1:has-text("訂單管理")')).toBeVisible();
    
    // Go back again
    await page.goBack();
    await expect(page).toHaveURL(/customers/);
    await expect(page.locator('h2:has-text("客戶管理"), h1:has-text("客戶管理")')).toBeVisible();
    
    // Go forward
    await page.goForward();
    await expect(page).toHaveURL(/orders/);
    
    // State should be preserved
    const pageContent = page.locator('.ant-table, .ant-empty, .page-content');
    await expect(pageContent).toBeVisible();
  });

  test('should recover from errors gracefully - 8', async ({ page, context }) => {
    await loginAsTestUser(page);
    
    // Simulate session timeout after some time
    await page.waitForTimeout(2000);
    
    // Mock all API calls to return 401
    await context.route('**/api/v1/**', route => {
      if (!route.request().url().includes('/auth/login')) {
        route.fulfill({
          status: 401,
          contentType: 'application/json',
          body: JSON.stringify({ detail: 'Session expired' })
        });
      } else {
        route.continue();
      }
    });
    
    // Try to navigate
    await page.click('text=客戶管理');
    
    // Should redirect to login or show session expired message
    const loginRedirected = await page.waitForURL(/login/, { timeout: 5000 })
      .then(() => true)
      .catch(() => false);
    
    if (!loginRedirected) {
      // Check for session expired message
      await expect(page.locator('text=/登入已過期|session.*expired|請重新登入/i')).toBeVisible();
    } else {
      // Verify on login page
      await expect(page.locator('button:has-text("登 入")')).toBeVisible();
    }
  });
});