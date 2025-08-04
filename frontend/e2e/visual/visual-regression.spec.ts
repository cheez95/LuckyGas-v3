import { test, expect } from '@playwright/test';
import { loginAsTestUser } from '../helpers/auth.helper';

test.describe('Visual Regression Tests', () => {
  const viewports = [
    { width: 1920, height: 1080, name: 'desktop' },
    { width: 768, height: 1024, name: 'tablet' },
    { width: 375, height: 667, name: 'mobile' }
  ];

  // Login page screenshots
  test.describe('Login Page', () => {
    for (const viewport of viewports) {
      test(`Login page - ${viewport.name}`, async ({ page }) => {
        await page.setViewportSize(viewport);
        await page.goto('http://localhost:5173');
        
        // Wait for page to be fully loaded
        await page.waitForLoadState('networkidle');
        
        // Hide dynamic elements that might change
        await page.addStyleTag({
          content: `
            .timestamp, .version, .build-number { visibility: hidden !important; }
            img[src*="placeholder"] { opacity: 0 !important; }
          `
        });
        
        await expect(page).toHaveScreenshot(`login-${viewport.name}.png`, {
          fullPage: true,
          animations: 'disabled',
          mask: [page.locator('.copyright-year')] // Mask year that might change
        });
      });
    }
  });

  // Dashboard screenshots
  test.describe('Dashboard', () => {
    for (const viewport of viewports) {
      test(`Dashboard - ${viewport.name}`, async ({ page }) => {
        await page.setViewportSize(viewport);
        await loginAsTestUser(page);
        
        // Wait for dashboard to fully load
        await page.waitForLoadState('networkidle');
        await page.waitForTimeout(1000); // Extra wait for animations
        
        // Hide dynamic content
        await page.addStyleTag({
          content: `
            .real-time-data, .live-updates, .timestamp, .current-time { visibility: hidden !important; }
            .chart, .graph, canvas { opacity: 0.1 !important; }
            .loading, .spinner { display: none !important; }
          `
        });
        
        await expect(page).toHaveScreenshot(`dashboard-${viewport.name}.png`, {
          fullPage: true,
          animations: 'disabled',
          mask: [
            page.locator('text=/[0-9]{4}[\/-][0-9]{2}[\/-][0-9]{2}/'), // Mask dates
            page.locator('text=/[0-9]+:[0-9]+/'), // Mask times
          ]
        });
      });
    }
  });

  // Customer Management screenshots
  test.describe('Customer Management', () => {
    for (const viewport of viewports) {
      test(`Customer list - ${viewport.name}`, async ({ page }) => {
        await page.setViewportSize(viewport);
        await loginAsTestUser(page);
        
        // Navigate to customers
        await page.click('text=客戶管理');
        await page.waitForURL(/customers/);
        await page.waitForLoadState('networkidle');
        
        // Hide dynamic content
        await page.addStyleTag({
          content: `
            .ant-table-tbody { opacity: 0.1 !important; } /* Dim table data */
            .loading-indicator { display: none !important; }
          `
        });
        
        await expect(page).toHaveScreenshot(`customers-${viewport.name}.png`, {
          fullPage: false, // Table might be long
          animations: 'disabled'
        });
      });
    }
  });

  // Order Management screenshots
  test.describe('Order Management', () => {
    for (const viewport of viewports) {
      test(`Order list - ${viewport.name}`, async ({ page }) => {
        await page.setViewportSize(viewport);
        await loginAsTestUser(page);
        
        // Navigate to orders
        await page.click('text=訂單管理');
        await page.waitForURL(/orders/);
        await page.waitForLoadState('networkidle');
        
        await page.addStyleTag({
          content: `
            .order-status, .status-badge { filter: grayscale(1) !important; }
            .ant-table-tbody { opacity: 0.1 !important; }
          `
        });
        
        await expect(page).toHaveScreenshot(`orders-${viewport.name}.png`, {
          fullPage: false,
          animations: 'disabled'
        });
      });
    }
  });

  // Route Planning screenshots
  test.describe('Route Planning', () => {
    for (const viewport of viewports) {
      test(`Route planning - ${viewport.name}`, async ({ page }) => {
        await page.setViewportSize(viewport);
        await loginAsTestUser(page);
        
        // Navigate to routes
        await page.click('text=路線規劃');
        await page.waitForURL(/routes/);
        await page.waitForLoadState('networkidle');
        
        // Hide map to avoid flakiness
        await page.addStyleTag({
          content: `
            #map, .route-map, .leaflet-container { opacity: 0.1 !important; }
            .map-overlay, .map-controls { display: none !important; }
          `
        });
        
        await expect(page).toHaveScreenshot(`routes-${viewport.name}.png`, {
          fullPage: false,
          animations: 'disabled'
        });
      });
    }
  });

  // Component-specific screenshots
  test.describe('UI Components', () => {
    test('Navigation menu - desktop', async ({ page }) => {
      await page.setViewportSize({ width: 1920, height: 1080 });
      await loginAsTestUser(page);
      
      // Focus on navigation
      const nav = page.locator('aside, nav, .ant-menu');
      await expect(nav).toHaveScreenshot('navigation-desktop.png');
    });

    test('Navigation menu - mobile', async ({ page }) => {
      await page.setViewportSize({ width: 375, height: 667 });
      await loginAsTestUser(page);
      
      // Open mobile menu if exists
      const menuTrigger = page.locator('[data-testid="mobile-menu-trigger"], .menu-trigger, button[aria-label*="menu"]');
      if (await menuTrigger.isVisible()) {
        await menuTrigger.click();
        await page.waitForTimeout(300); // Wait for animation
        
        const mobileNav = page.locator('.mobile-menu, .ant-drawer');
        await expect(mobileNav).toHaveScreenshot('navigation-mobile.png');
      }
    });

    test('Form elements', async ({ page }) => {
      await page.setViewportSize({ width: 1920, height: 1080 });
      await page.goto('http://localhost:5173');
      
      // Focus on login form
      const loginForm = page.locator('form, .login-form, .ant-form');
      await expect(loginForm).toHaveScreenshot('login-form.png');
    });

    test('Empty states', async ({ page }) => {
      await page.setViewportSize({ width: 1920, height: 1080 });
      await loginAsTestUser(page);
      
      // Navigate to a page that might have empty state
      await page.click('text=訂單管理');
      await page.waitForURL(/orders/);
      
      // If empty state exists, capture it
      const emptyState = page.locator('.ant-empty');
      if (await emptyState.isVisible()) {
        await expect(emptyState).toHaveScreenshot('empty-state.png');
      }
    });
  });

  // Dark mode tests (if implemented)
  test.describe('Theme Variations', () => {
    test('Check for theme toggle', async ({ page }) => {
      await loginAsTestUser(page);
      
      // Look for theme toggle
      const themeToggle = page.locator('[data-testid="theme-toggle"], button[aria-label*="theme"], .theme-switch');
      
      if (await themeToggle.isVisible()) {
        // Capture light mode
        await expect(page).toHaveScreenshot('theme-light.png', {
          fullPage: false,
          clip: { x: 0, y: 0, width: 1920, height: 600 }
        });
        
        // Switch theme
        await themeToggle.click();
        await page.waitForTimeout(300); // Wait for transition
        
        // Capture dark mode
        await expect(page).toHaveScreenshot('theme-dark.png', {
          fullPage: false,
          clip: { x: 0, y: 0, width: 1920, height: 600 }
        });
      }
    });
  });
});