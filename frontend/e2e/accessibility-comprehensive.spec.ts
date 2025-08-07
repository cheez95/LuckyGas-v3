import { test, expect } from '@playwright/test';
import { injectAxe, checkA11y, getViolations } from 'axe-playwright';
import { LoginPage } from './pages/LoginPage';

// WCAG 2.1 Level AA compliance categories
const A11Y_RULES = {
  CRITICAL: ['aria-valid-attr', 'button-name', 'color-contrast', 'duplicate-id', 'label'],
  HIGH: ['heading-order', 'image-alt', 'link-name', 'list', 'listitem'],
  MEDIUM: ['landmark-one-main', 'page-has-heading-one', 'region', 'skip-link'],
  LOW: ['aria-allowed-role', 'tabindex', 'valid-lang']
};

// Helper to format violations
function formatViolations(violations: any[]) {
  return violations.map(v => ({
    id: v.id,
    impact: v.impact,
    description: v.description,
    nodes: v.nodes.length,
    help: v.help,
    helpUrl: v.helpUrl
  }));
}

test.describe('Comprehensive Accessibility Testing', () => {
  test.beforeEach(async ({ page }) => {
    // Inject axe-core on each page
    await injectAxe(page);
  });

  test.describe('Authentication Pages', () => {
    test('Login page accessibility', async ({ page }) => {
      await page.goto('/login');
      
      // Run axe scan
      const violations = await getViolations(page, undefined, {
        detailedReport: true,
        detailedReportOptions: {
          html: true
        }
      });

      // Check critical violations
      const criticalViolations = violations.filter(v => v.impact === 'critical');
      expect(criticalViolations).toHaveLength(0);

      // Check form labels
      const usernameInput = page.locator('[data-testid="username-input"]');
      await expect(usernameInput).toHaveAttribute('aria-label', /.+/);
      
      const passwordInput = page.locator('[data-testid="password-input"]');
      await expect(passwordInput).toHaveAttribute('aria-label', /.+/);

      // Check keyboard navigation
      await page.keyboard.press('Tab');
      await expect(usernameInput).toBeFocused();
      
      await page.keyboard.press('Tab');
      await expect(passwordInput).toBeFocused();
      
      await page.keyboard.press('Tab');
      await expect(page.locator('[data-testid="login-btn"]')).toBeFocused();

      // Check error announcement
      await page.locator('[data-testid="login-btn"]').click();
      const errorMessage = page.locator('[role="alert"]');
      await expect(errorMessage).toBeVisible();
      await expect(errorMessage).toHaveAttribute('aria-live', 'polite');
    });

    test('Password reset accessibility', async ({ page }) => {
      await page.goto('/forgot-password');
      
      await checkA11y(page, undefined, {
        detailedReport: true,
        rules: {
          'color-contrast': { enabled: true },
          'label': { enabled: true }
        }
      });

      // Check form structure
      const form = page.locator('form');
      await expect(form).toHaveAttribute('aria-label', /.+/);

      // Check instructions are associated with input
      const emailInput = page.locator('input[type="email"]');
      const instructions = await emailInput.getAttribute('aria-describedby');
      expect(instructions).toBeTruthy();
    });
  });

  test.describe('Main Application', () => {
    test.beforeEach(async ({ page }) => {
      const loginPage = new LoginPage(page);
      await loginPage.goto();
      await loginPage.login('office1', 'office123');
    });

    test('Dashboard accessibility', async ({ page }) => {
      await page.goto('/dashboard');
      
      // Check page structure
      await expect(page.locator('main')).toBeVisible();
      await expect(page.locator('h1')).toBeVisible();

      // Run comprehensive scan
      const violations = await getViolations(page);
      console.log('Dashboard violations:', formatViolations(violations));
      
      // Check specific elements
      const statsCards = page.locator('[data-testid^="stat-"]');
      const count = await statsCards.count();
      
      for (let i = 0; i < count; i++) {
        const card = statsCards.nth(i);
        await expect(card).toHaveAttribute('role', 'article');
        await expect(card.locator('[role="heading"]')).toBeVisible();
      }

      // Check data tables
      const tables = page.locator('table');
      const tableCount = await tables.count();
      
      for (let i = 0; i < tableCount; i++) {
        const table = tables.nth(i);
        await expect(table).toHaveAttribute('aria-label', /.+/);
        await expect(table.locator('thead')).toBeVisible();
      }
    });

    test('Navigation accessibility', async ({ page }) => {
      await page.goto('/dashboard');

      // Check main navigation
      const nav = page.locator('nav[role="navigation"]');
      await expect(nav).toBeVisible();
      await expect(nav).toHaveAttribute('aria-label', /.+/);

      // Check skip links
      await page.keyboard.press('Tab');
      const skipLink = page.locator('[data-testid="skip-to-content"]');
      if (await skipLink.isVisible()) {
        await expect(skipLink).toBeFocused();
        await skipLink.press('Enter');
        await expect(page.locator('main')).toBeFocused();
      }

      // Check menu keyboard navigation
      await page.locator('[data-testid="menu-toggle"]').focus();
      await page.keyboard.press('Enter');
      await expect(page.locator('.ant-menu')).toBeVisible();

      // Navigate through menu items
      await page.keyboard.press('ArrowDown');
      await expect(page.locator('.ant-menu-item').first()).toHaveAttribute('aria-selected', 'true');
    });

    test('Forms accessibility', async ({ page }) => {
      await page.goto('/orders');
      await page.locator('[data-testid="create-order-btn"]').click();

      // Check form structure
      const form = page.locator('.ant-modal form');
      await expect(form).toBeVisible();

      // Check all form fields have labels
      const inputs = form.locator('input, select, textarea');
      const inputCount = await inputs.count();

      for (let i = 0; i < inputCount; i++) {
        const input = inputs.nth(i);
        const id = await input.getAttribute('id');
        
        if (id) {
          const label = page.locator(`label[for="${id}"]`);
          await expect(label).toBeVisible();
        } else {
          // Check for aria-label
          await expect(input).toHaveAttribute('aria-label', /.+/);
        }
      }

      // Check error messages association
      await form.locator('button[type="submit"]').click();
      const errorMessages = form.locator('[role="alert"]');
      const errorCount = await errorMessages.count();

      for (let i = 0; i < errorCount; i++) {
        const error = errorMessages.nth(i);
        const describedById = await error.getAttribute('id');
        expect(describedById).toBeTruthy();
      }
    });

    test('Data tables accessibility', async ({ page }) => {
      await page.goto('/customers');

      const table = page.locator('.ant-table');
      await expect(table).toBeVisible();

      // Check table structure
      await expect(table.locator('table')).toHaveAttribute('role', 'table');
      await expect(table.locator('thead')).toHaveAttribute('role', 'rowgroup');
      await expect(table.locator('tbody')).toHaveAttribute('role', 'rowgroup');

      // Check sortable columns
      const sortableHeaders = table.locator('th[aria-sort]');
      const sortableCount = await sortableHeaders.count();
      expect(sortableCount).toBeGreaterThan(0);

      // Check row selection
      const checkboxes = table.locator('input[type="checkbox"]');
      const firstCheckbox = checkboxes.first();
      await expect(firstCheckbox).toHaveAttribute('aria-label', /.+/);

      // Check pagination
      const pagination = page.locator('.ant-pagination');
      await expect(pagination).toHaveAttribute('role', 'navigation');
      await expect(pagination).toHaveAttribute('aria-label', /.+/);
    });

    test('Modal dialogs accessibility', async ({ page }) => {
      await page.goto('/orders');
      await page.locator('[data-testid="create-order-btn"]').click();

      const modal = page.locator('.ant-modal');
      await expect(modal).toBeVisible();

      // Check modal attributes
      await expect(modal).toHaveAttribute('role', 'dialog');
      await expect(modal).toHaveAttribute('aria-modal', 'true');
      await expect(modal).toHaveAttribute('aria-labelledby', /.+/);

      // Check focus trap
      await page.keyboard.press('Tab');
      const focusedElement = await page.evaluate(() => document.activeElement?.tagName);
      expect(focusedElement).not.toBe('BODY');

      // Check escape key closes modal
      await page.keyboard.press('Escape');
      await expect(modal).not.toBeVisible();
    });

    test('Color contrast compliance', async ({ page }) => {
      await page.goto('/dashboard');

      // Run color contrast check
      await checkA11y(page, undefined, {
        rules: {
          'color-contrast': { enabled: true }
        }
      });

      // Check specific high-contrast mode
      await page.emulateMedia({ colorScheme: 'dark' });
      await page.waitForTimeout(1000);

      // Re-run contrast check in dark mode
      const darkModeViolations = await getViolations(page, undefined, {
        rules: {
          'color-contrast': { enabled: true }
        }
      });

      expect(darkModeViolations.filter(v => v.id === 'color-contrast')).toHaveLength(0);
    });

    test('Responsive accessibility', async ({ page }) => {
      const viewports = [
        { width: 375, height: 667, name: 'mobile' },
        { width: 768, height: 1024, name: 'tablet' },
        { width: 1920, height: 1080, name: 'desktop' }
      ];

      for (const viewport of viewports) {
        await page.setViewportSize(viewport);
        await page.goto('/dashboard');

        // Check touch targets on mobile
        if (viewport.name === 'mobile') {
          const buttons = page.locator('button');
          const buttonCount = await buttons.count();

          for (let i = 0; i < buttonCount; i++) {
            const button = buttons.nth(i);
            const box = await button.boundingBox();
            if (box) {
              expect(box.width).toBeGreaterThanOrEqual(44);
              expect(box.height).toBeGreaterThanOrEqual(44);
            }
          }
        }

        // Run accessibility check for each viewport
        await checkA11y(page, undefined, {
          includedImpacts: ['critical', 'serious']
        });
      }
    });

    test('Keyboard navigation complete flow', async ({ page }) => {
      await page.goto('/orders');

      // Navigate through entire page with keyboard
      const focusableElements = page.locator('a, button, input, select, textarea, [tabindex]:not([tabindex="-1"])');
      const count = await focusableElements.count();

      for (let i = 0; i < Math.min(count, 20); i++) {
        await page.keyboard.press('Tab');
        
        const focusedElement = await page.evaluate(() => {
          const el = document.activeElement;
          return {
            tagName: el?.tagName,
            role: el?.getAttribute('role'),
            ariaLabel: el?.getAttribute('aria-label'),
            visible: el ? window.getComputedStyle(el).visibility !== 'hidden' : false
          };
        });

        expect(focusedElement.visible).toBeTruthy();
        expect(focusedElement.tagName).not.toBe('BODY');
      }
    });

    test('Screen reader announcements', async ({ page }) => {
      await page.goto('/dashboard');

      // Check live regions
      const liveRegions = page.locator('[aria-live]');
      const liveCount = await liveRegions.count();
      expect(liveCount).toBeGreaterThan(0);

      // Test dynamic content announcement
      await page.goto('/orders');
      await page.locator('[data-testid="create-order-btn"]').click();
      await page.locator('[data-testid="submit-order-btn"]').click();

      // Check error announcement
      const errorAnnouncement = page.locator('[role="alert"][aria-live="assertive"]');
      await expect(errorAnnouncement).toBeVisible();

      // Test success announcement
      // Fill form properly and submit
      // Check success message has proper ARIA attributes
    });

    test('Focus management in SPA navigation', async ({ page }) => {
      await page.goto('/dashboard');

      // Navigate to different route
      await page.locator('a[href="/orders"]').click();
      await page.waitForURL('**/orders');

      // Check focus moved to main content
      const focusedElement = await page.evaluate(() => {
        return document.activeElement?.tagName;
      });

      expect(['MAIN', 'H1', 'H2']).toContain(focusedElement);

      // Test back navigation
      await page.goBack();
      await page.waitForURL('**/dashboard');

      // Focus should be restored or moved to main
      const backFocus = await page.evaluate(() => {
        return document.activeElement?.tagName;
      });

      expect(backFocus).not.toBe('BODY');
    });
  });

  test.describe('Driver Mobile Accessibility', () => {
    test('Touch target sizes', async ({ browser }) => {
      const context = await browser.newContext({
        viewport: { width: 375, height: 667 },
        isMobile: true,
        hasTouch: true
      });
      const page = await context.newPage();

      const loginPage = new LoginPage(page);
      await loginPage.goto();
      await loginPage.login('driver1', 'driver123');

      await page.waitForURL('**/driver');

      // Check all touch targets
      const touchTargets = page.locator('button, a, [role="button"]');
      const count = await touchTargets.count();

      for (let i = 0; i < count; i++) {
        const target = touchTargets.nth(i);
        const box = await target.boundingBox();
        
        if (box && await target.isVisible()) {
          expect(box.width).toBeGreaterThanOrEqual(44);
          expect(box.height).toBeGreaterThanOrEqual(44);
        }
      }

      await context.close();
    });

    test('Mobile screen reader support', async ({ browser }) => {
      const context = await browser.newContext({
        viewport: { width: 375, height: 667 },
        isMobile: true
      });
      const page = await context.newPage();

      const loginPage = new LoginPage(page);
      await loginPage.goto();
      await loginPage.login('driver1', 'driver123');

      // Check swipe navigation hints
      const swipeHints = page.locator('[aria-label*="滑動"]');
      if (await swipeHints.count() > 0) {
        await expect(swipeHints.first()).toHaveAttribute('role', 'text');
      }

      // Check delivery completion flow
      await page.goto('/driver/route/1');
      const deliveryButton = page.locator('[data-testid="complete-delivery-btn"]');
      await expect(deliveryButton).toHaveAttribute('aria-label', /.+/);

      await context.close();
    });
  });

  test('Comprehensive WCAG 2.1 AA audit', async ({ page }) => {
    const pagesToAudit = [
      '/login',
      '/dashboard',
      '/orders',
      '/customers',
      '/routes',
      '/analytics'
    ];

    const auditResults = [];

    for (const pageUrl of pagesToAudit) {
      if (pageUrl !== '/login') {
        const loginPage = new LoginPage(page);
        await loginPage.goto();
        await loginPage.login('admin', 'admin123');
      }

      await page.goto(pageUrl);
      await page.waitForLoadState('networkidle');

      const violations = await getViolations(page, undefined, {
        runOnly: {
          type: 'tag',
          values: ['wcag2a', 'wcag2aa']
        }
      });

      auditResults.push({
        page: pageUrl,
        violations: violations.length,
        critical: violations.filter(v => v.impact === 'critical').length,
        serious: violations.filter(v => v.impact === 'serious').length,
        details: formatViolations(violations)
      });
    }

    // Generate report
    console.log('WCAG 2.1 AA Compliance Report:');
    console.table(auditResults.map(r => ({
      page: r.page,
      violations: r.violations,
      critical: r.critical,
      serious: r.serious
    })));

    // Assert no critical violations
    const criticalCount = auditResults.reduce((sum, r) => sum + r.critical, 0);
    expect(criticalCount).toBe(0);
  });
});