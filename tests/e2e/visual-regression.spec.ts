import { test, expect } from '@playwright/test';

test.describe('Visual Regression Tests', () => {
  test.beforeEach(async ({ page }) => {
    // Set consistent viewport for visual tests
    await page.setViewportSize({ width: 1280, height: 720 });
  });

  test('login page visual test', async ({ page }) => {
    await page.goto('/');
    await page.waitForLoadState('networkidle');
    
    // Wait for any animations to complete
    await page.waitForTimeout(1000);
    
    // Take screenshot and compare with baseline
    await expect(page).toHaveScreenshot('login-page.png', {
      fullPage: true,
      animations: 'disabled',
      mask: [
        // Mask dynamic content like timestamps
        page.locator('.timestamp'),
        page.locator('.version-info')
      ],
    });
  });

  test('dashboard visual test', async ({ page }) => {
    // Login first
    await page.goto('/');
    await page.locator('input[type="text"]').fill('admin');
    await page.locator('input[type="password"]').fill('admin123');
    await page.locator('button[type="submit"]').click();
    
    await page.waitForLoadState('networkidle');
    await page.waitForTimeout(1000);
    
    // Take dashboard screenshot
    await expect(page).toHaveScreenshot('dashboard.png', {
      fullPage: true,
      animations: 'disabled',
      mask: [
        // Mask dynamic content
        page.locator('.ant-statistic-content'),
        page.locator('.timestamp'),
        page.locator('.chart-container')
      ],
    });
  });

  test('customer list visual test', async ({ page }) => {
    // Login and navigate to customers
    await page.goto('/');
    await page.locator('input[type="text"]').fill('admin');
    await page.locator('input[type="password"]').fill('admin123');
    await page.locator('button[type="submit"]').click();
    
    await page.waitForLoadState('networkidle');
    
    // Navigate to customers
    await page.getByRole('link', { name: /customer|客戶/i }).click();
    await page.waitForLoadState('networkidle');
    await page.waitForTimeout(1000);
    
    // Take screenshot
    await expect(page).toHaveScreenshot('customer-list.png', {
      fullPage: false, // Table might be long
      animations: 'disabled',
      mask: [
        // Mask dynamic data
        page.locator('.ant-table-cell:has-text("2024")'),
        page.locator('.timestamp')
      ],
    });
  });

  test('mobile responsive visual test', async ({ page }) => {
    // Set mobile viewport
    await page.setViewportSize({ width: 375, height: 667 });
    
    await page.goto('/');
    await page.waitForLoadState('networkidle');
    await page.waitForTimeout(1000);
    
    // Mobile login page
    await expect(page).toHaveScreenshot('mobile-login.png', {
      fullPage: true,
      animations: 'disabled',
    });
    
    // Login and test mobile dashboard
    await page.locator('input[type="text"]').fill('admin');
    await page.locator('input[type="password"]').fill('admin123');
    await page.locator('button[type="submit"]').click();
    
    await page.waitForLoadState('networkidle');
    await page.waitForTimeout(1000);
    
    await expect(page).toHaveScreenshot('mobile-dashboard.png', {
      fullPage: true,
      animations: 'disabled',
      mask: [
        page.locator('.ant-statistic-content'),
        page.locator('.timestamp')
      ],
    });
  });

  test('dark mode visual test', async ({ page }) => {
    // If dark mode is implemented
    await page.goto('/');
    
    // Enable dark mode if available
    const darkModeToggle = page.locator('[data-testid="dark-mode-toggle"], .dark-mode-toggle');
    if (await darkModeToggle.isVisible()) {
      await darkModeToggle.click();
      await page.waitForTimeout(500); // Wait for theme transition
      
      await expect(page).toHaveScreenshot('dark-mode-login.png', {
        fullPage: true,
        animations: 'disabled',
      });
    }
  });

  test('form validation states visual test', async ({ page }) => {
    await page.goto('/');
    await page.waitForLoadState('networkidle');
    
    // Trigger validation errors
    await page.locator('button[type="submit"]').click();
    await page.waitForTimeout(500);
    
    // Capture form with errors
    await expect(page).toHaveScreenshot('form-validation-errors.png', {
      fullPage: false,
      clip: {
        x: 0,
        y: 0,
        width: 600,
        height: 400
      },
      animations: 'disabled',
    });
  });

  test('loading states visual test', async ({ page }) => {
    await page.goto('/');
    
    // Intercept API call to delay it
    await page.route('**/api/v1/auth/login', async (route) => {
      await page.waitForTimeout(2000);
      await route.continue();
    });
    
    await page.locator('input[type="text"]').fill('admin');
    await page.locator('input[type="password"]').fill('admin123');
    
    // Click and immediately capture loading state
    const submitPromise = page.locator('button[type="submit"]').click();
    await page.waitForTimeout(100); // Small delay to ensure loading state appears
    
    await expect(page.locator('form')).toHaveScreenshot('login-loading-state.png', {
      animations: 'disabled',
    });
    
    await submitPromise;
  });
});