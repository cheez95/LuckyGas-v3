import { test, expect, devices } from '@playwright/test';
import { TestHelpers } from '../utils/test-helpers';
import testData from '../fixtures/test-data.json';

test.describe('Mobile Responsiveness Tests', () => {
  test.describe('Mobile Phone View (375x667)', () => {
    test.use({
      viewport: { width: 375, height: 667 },
      userAgent: devices['iPhone 12'].userAgent,
      hasTouch: true,
      isMobile: true
    });

    test('should display responsive navigation on mobile', async ({ page }) => {
      await page.goto('/');
      
      // Desktop navigation should be hidden
      await expect(page.locator('.desktop-nav')).not.toBeVisible();
      
      // Mobile hamburger menu should be visible
      await expect(page.locator('.mobile-menu-toggle')).toBeVisible();
      
      // Click hamburger menu
      await page.tap('.mobile-menu-toggle');
      
      // Mobile menu should slide in
      await expect(page.locator('.mobile-menu')).toBeVisible();
      await expect(page.locator('.mobile-menu')).toHaveClass(/active|open/);
      
      // Menu items should be stacked vertically
      const menuItems = page.locator('.mobile-menu-item');
      const count = await menuItems.count();
      expect(count).toBeGreaterThan(0);
      
      // Close menu by tapping overlay
      await page.tap('.mobile-menu-overlay');
      await expect(page.locator('.mobile-menu')).not.toBeVisible();
    });

    test('should handle login form on mobile', async ({ page }) => {
      await page.goto('/login');
      
      // Form should be full width on mobile
      const loginForm = page.locator('.login-form');
      await expect(loginForm).toBeVisible();
      
      // Check form is mobile-optimized
      const formBox = await loginForm.boundingBox();
      expect(formBox?.width).toBeGreaterThan(300);
      expect(formBox?.width).toBeLessThan(360);
      
      // Input fields should be touch-friendly
      const usernameInput = page.locator('input[name="username"]');
      const passwordInput = page.locator('input[name="password"]');
      
      // Tap to focus
      await usernameInput.tap();
      await expect(usernameInput).toBeFocused();
      
      // Virtual keyboard should not obscure inputs
      await page.keyboard.type('admin');
      
      await passwordInput.tap();
      await page.keyboard.type('password');
      
      // Submit button should be easily tappable
      const submitButton = page.locator('button[type="submit"]');
      const buttonBox = await submitButton.boundingBox();
      expect(buttonBox?.height).toBeGreaterThanOrEqual(44); // iOS minimum touch target
    });

    test('should display customer list in mobile-friendly format', async ({ page }) => {
      await TestHelpers.loginUI(page, 'administrator', 'SuperSecure#9876');
      await page.goto('/customers');
      
      // Table should transform to cards on mobile
      await expect(page.locator('table.desktop-only')).not.toBeVisible();
      await expect(page.locator('.customer-cards')).toBeVisible();
      
      // Each customer should be a card
      const customerCards = page.locator('.customer-card');
      const cardCount = await customerCards.count();
      expect(cardCount).toBeGreaterThan(0);
      
      // Card should contain essential info
      const firstCard = customerCards.first();
      await expect(firstCard.locator('.customer-name')).toBeVisible();
      await expect(firstCard.locator('.customer-phone')).toBeVisible();
      await expect(firstCard.locator('.customer-address')).toBeVisible();
      
      // Actions should be accessible via tap
      await firstCard.tap();
      await expect(page.locator('.card-actions')).toBeVisible();
    });

    test('should handle order creation on mobile', async ({ page }) => {
      await TestHelpers.loginUI(page, 'administrator', 'SuperSecure#9876');
      await page.goto('/orders/new');
      
      // Form should be single column on mobile
      const formFields = page.locator('.form-field');
      const firstField = formFields.first();
      const secondField = formFields.nth(1);
      
      const firstBox = await firstField.boundingBox();
      const secondBox = await secondField.boundingBox();
      
      // Fields should stack vertically
      expect(secondBox?.y).toBeGreaterThan(firstBox?.y! + firstBox?.height!);
      
      // Date picker should be mobile-optimized
      await page.tap('input[name="預定配送日期"]');
      await expect(page.locator('.mobile-date-picker')).toBeVisible();
      
      // Select tomorrow
      const tomorrow = new Date();
      tomorrow.setDate(tomorrow.getDate() + 1);
      await page.tap(`[data-date="${tomorrow.toISOString().split('T')[0]}"]`);
      
      // Customer selection should use mobile-friendly dropdown
      await page.tap('select[name="客戶ID"]');
      
      // Product selection should be touch-friendly
      await page.tap('.add-product-button');
      await expect(page.locator('.product-modal')).toBeVisible();
      
      // Modal should be full screen on mobile
      const modalBox = await page.locator('.product-modal').boundingBox();
      expect(modalBox?.width).toBeCloseTo(375, 10);
    });

    test('should display responsive analytics dashboard', async ({ page }) => {
      await TestHelpers.loginUI(page, 'administrator', 'SuperSecure#9876');
      await page.goto('/analytics/executive');
      
      // Metric cards should stack vertically
      const metricCards = page.locator('.metric-card');
      const cardBoxes = await metricCards.evaluateAll(cards => 
        cards.map(card => card.getBoundingClientRect())
      );
      
      // Verify vertical stacking
      for (let i = 1; i < cardBoxes.length; i++) {
        expect(cardBoxes[i].top).toBeGreaterThan(cardBoxes[i-1].bottom);
      }
      
      // Charts should be responsive
      const revenueChart = page.locator('#revenue-chart');
      const chartBox = await revenueChart.boundingBox();
      expect(chartBox?.width).toBeLessThan(360);
      
      // Swipe gestures for date range
      const dateRangeSelector = page.locator('.date-range-selector');
      await expect(dateRangeSelector).toBeVisible();
      
      // Horizontal scroll for date options
      await dateRangeSelector.evaluate(el => el.scrollLeft = 100);
    });

    test('should handle touch interactions for route planning', async ({ page }) => {
      await TestHelpers.loginUI(page, 'administrator', 'SuperSecure#9876');
      await page.goto('/routes');
      
      // Map should be touch-enabled
      await page.tap('button:has-text("規劃新路線")');
      await expect(page.locator('#route-map')).toBeVisible();
      
      // Pinch to zoom
      const map = page.locator('#route-map');
      const box = await map.boundingBox();
      
      if (box) {
        // Simulate pinch gesture
        await page.touchscreen.tap(box.x + box.width / 2, box.y + box.height / 2);
        
        // Drag to pan
        await page.touchscreen.down();
        await page.touchscreen.move(box.x + 50, box.y);
        await page.touchscreen.up();
      }
      
      // Waypoint reordering via drag
      const waypoints = page.locator('.waypoint-item');
      const firstWaypoint = waypoints.first();
      
      // Touch and hold to initiate drag
      const waypointBox = await firstWaypoint.boundingBox();
      if (waypointBox) {
        await page.touchscreen.tap(waypointBox.x + 10, waypointBox.y + 10, { delay: 500 });
        await expect(firstWaypoint).toHaveClass(/dragging/);
      }
    });

    test('should show mobile-specific features', async ({ page }) => {
      await TestHelpers.loginUI(page, 'administrator', 'SuperSecure#9876');
      
      // Bottom navigation bar
      await expect(page.locator('.bottom-navigation')).toBeVisible();
      
      // Quick action button (FAB)
      await expect(page.locator('.fab-button')).toBeVisible();
      
      // Pull to refresh
      await page.goto('/orders');
      
      // Simulate pull down gesture
      await page.touchscreen.down();
      await page.touchscreen.move(187, 300);
      await page.touchscreen.up();
      
      // Should show refresh indicator
      await expect(page.locator('.pull-to-refresh')).toBeVisible();
    });

    test('should optimize form inputs for mobile keyboard', async ({ page }) => {
      await TestHelpers.loginUI(page, 'administrator', 'SuperSecure#9876');
      await page.goto('/customers/new');
      
      // Phone input should show numeric keyboard
      const phoneInput = page.locator('input[name="聯絡電話"]');
      const phoneType = await phoneInput.getAttribute('type');
      expect(phoneType).toBe('tel');
      
      // Email should show email keyboard
      const emailInput = page.locator('input[name="電子郵件"]');
      const emailType = await emailInput.getAttribute('type');
      expect(emailType).toBe('email');
      
      // Number inputs should show numeric keyboard
      const creditInput = page.locator('input[name="信用額度"]');
      const creditPattern = await creditInput.getAttribute('pattern');
      expect(creditPattern).toMatch(/\d/);
    });
  });

  test.describe('Tablet View (768x1024)', () => {
    test.use({
      viewport: { width: 768, height: 1024 },
      userAgent: devices['iPad'].userAgent,
      hasTouch: true
    });

    test('should display split-view layout on tablet', async ({ page }) => {
      await TestHelpers.loginUI(page, 'administrator', 'SuperSecure#9876');
      await page.goto('/orders');
      
      // Should show both list and detail view
      await expect(page.locator('.orders-list')).toBeVisible();
      await expect(page.locator('.order-detail-panel')).toBeVisible();
      
      // List should be narrower on tablet
      const listBox = await page.locator('.orders-list').boundingBox();
      expect(listBox?.width).toBeCloseTo(320, 50);
      
      // Detail panel should take remaining space
      const detailBox = await page.locator('.order-detail-panel').boundingBox();
      expect(detailBox?.width).toBeCloseTo(448, 50);
      
      // Tap order to show in detail panel
      await page.tap('.order-list-item:first-child');
      await expect(page.locator('.order-detail-content')).toBeVisible();
    });

    test('should show adaptive navigation on tablet', async ({ page }) => {
      await page.goto('/');
      
      // Should show condensed navigation
      await expect(page.locator('.tablet-nav')).toBeVisible();
      
      // Main items visible, secondary in dropdown
      const mainNavItems = page.locator('.nav-item.main');
      const mainCount = await mainNavItems.count();
      expect(mainCount).toBeGreaterThan(3);
      expect(mainCount).toBeLessThan(8);
      
      // More menu for additional items
      await expect(page.locator('.nav-more-button')).toBeVisible();
    });

    test('should optimize analytics layout for tablet', async ({ page }) => {
      await TestHelpers.loginUI(page, 'administrator', 'SuperSecure#9876');
      await page.goto('/analytics/executive');
      
      // Metric cards in 2-column grid
      const metricCards = page.locator('.metric-card');
      const cardBoxes = await metricCards.evaluateAll(cards => 
        cards.map(card => card.getBoundingClientRect())
      );
      
      // Verify 2-column layout
      if (cardBoxes.length >= 2) {
        expect(cardBoxes[1].left).toBeGreaterThan(cardBoxes[0].right);
        expect(Math.abs(cardBoxes[0].top - cardBoxes[1].top)).toBeLessThan(5);
      }
      
      // Charts side by side where appropriate
      const charts = page.locator('.chart-container');
      const chartCount = await charts.count();
      expect(chartCount).toBeGreaterThan(0);
    });

    test('should handle modal dialogs on tablet', async ({ page }) => {
      await TestHelpers.loginUI(page, 'administrator', 'SuperSecure#9876');
      await page.goto('/customers');
      
      await page.tap('button:has-text("新增客戶")');
      
      // Modal should be centered, not full screen
      const modal = page.locator('.modal-content');
      await expect(modal).toBeVisible();
      
      const modalBox = await modal.boundingBox();
      expect(modalBox?.width).toBeCloseTo(600, 100);
      expect(modalBox?.left).toBeGreaterThan(50);
      
      // Should have visible backdrop
      await expect(page.locator('.modal-backdrop')).toBeVisible();
      
      // Tap backdrop to close
      await page.tap('.modal-backdrop');
      await expect(modal).not.toBeVisible();
    });

    test('should support landscape orientation', async ({ page }) => {
      // Rotate to landscape
      await page.setViewportSize({ width: 1024, height: 768 });
      
      await TestHelpers.loginUI(page, 'administrator', 'SuperSecure#9876');
      await page.goto('/routes');
      
      // Map should expand in landscape
      const mapContainer = page.locator('.route-map-container');
      const mapBox = await mapContainer.boundingBox();
      expect(mapBox?.width).toBeGreaterThan(600);
      
      // Controls should reposition
      await expect(page.locator('.landscape-controls')).toBeVisible();
    });
  });

  test.describe('Touch Interaction Tests', () => {
    test.use({
      viewport: { width: 375, height: 667 },
      hasTouch: true
    });

    test('should handle swipe gestures', async ({ page }) => {
      await TestHelpers.loginUI(page, 'administrator', 'SuperSecure#9876');
      await page.goto('/orders');
      
      // Swipe to reveal actions
      const orderItem = page.locator('.order-list-item:first-child');
      const box = await orderItem.boundingBox();
      
      if (box) {
        // Swipe left to reveal actions
        await page.touchscreen.down();
        await page.touchscreen.move(box.x + box.width - 50, box.y + box.height / 2);
        await page.touchscreen.move(box.x + 50, box.y + box.height / 2);
        await page.touchscreen.up();
        
        // Actions should be visible
        await expect(page.locator('.swipe-actions')).toBeVisible();
      }
    });

    test('should support long press actions', async ({ page }) => {
      await TestHelpers.loginUI(page, 'administrator', 'SuperSecure#9876');
      await page.goto('/customers');
      
      const customerCard = page.locator('.customer-card:first-child');
      const box = await customerCard.boundingBox();
      
      if (box) {
        // Long press to show context menu
        await page.touchscreen.tap(
          box.x + box.width / 2,
          box.y + box.height / 2,
          { delay: 800 }
        );
        
        // Context menu should appear
        await expect(page.locator('.context-menu')).toBeVisible();
        
        // Menu items should be touch-friendly
        const menuItems = page.locator('.context-menu-item');
        const itemBoxes = await menuItems.evaluateAll(items =>
          items.map(item => item.getBoundingClientRect())
        );
        
        itemBoxes.forEach(itemBox => {
          expect(itemBox.height).toBeGreaterThanOrEqual(44);
        });
      }
    });

    test('should handle drag and drop on touch devices', async ({ page }) => {
      await TestHelpers.loginUI(page, 'administrator', 'SuperSecure#9876');
      await page.goto('/routes/1/edit');
      
      // Wait for waypoints to load
      await page.waitForSelector('.waypoint-item');
      
      const firstWaypoint = page.locator('.waypoint-item:first-child');
      const thirdWaypoint = page.locator('.waypoint-item:nth-child(3)');
      
      const firstBox = await firstWaypoint.boundingBox();
      const thirdBox = await thirdWaypoint.boundingBox();
      
      if (firstBox && thirdBox) {
        // Touch and drag first waypoint to third position
        await page.touchscreen.tap(firstBox.x + 20, firstBox.y + 20);
        await page.waitForTimeout(100);
        
        await page.touchscreen.down();
        await page.touchscreen.move(firstBox.x + 20, firstBox.y + 20);
        await page.waitForTimeout(100);
        
        await page.touchscreen.move(thirdBox.x + 20, thirdBox.y + 20);
        await page.touchscreen.up();
        
        // Order should be updated
        await expect(page.locator('.reorder-indicator')).toBeVisible();
      }
    });
  });

  test.describe('Responsive Images and Media', () => {
    test('should load appropriate image sizes', async ({ page, viewport }) => {
      await page.goto('/');
      
      // Check logo loads correct size
      const logo = page.locator('.logo img');
      const logoSrc = await logo.getAttribute('src');
      
      if (viewport?.width && viewport.width < 768) {
        expect(logoSrc).toContain('mobile');
      } else {
        expect(logoSrc).toContain('desktop');
      }
      
      // Product images should use srcset
      await TestHelpers.loginUI(page, 'administrator', 'SuperSecure#9876');
      await page.goto('/products');
      
      const productImages = page.locator('.product-image');
      const firstImage = productImages.first();
      const srcset = await firstImage.getAttribute('srcset');
      expect(srcset).toBeTruthy();
      expect(srcset).toContain('1x');
      expect(srcset).toContain('2x');
    });

    test('should handle responsive tables', async ({ page }) => {
      await TestHelpers.loginUI(page, 'administrator', 'SuperSecure#9876');
      
      // Test different viewports
      const viewports = [
        { width: 320, height: 568 },  // iPhone SE
        { width: 768, height: 1024 }, // iPad
        { width: 1920, height: 1080 } // Desktop
      ];
      
      for (const vp of viewports) {
        await page.setViewportSize(vp);
        await page.goto('/orders');
        
        if (vp.width < 768) {
          // Should show cards on mobile
          await expect(page.locator('.order-cards')).toBeVisible();
          await expect(page.locator('table')).not.toBeVisible();
        } else {
          // Should show table on larger screens
          await expect(page.locator('table')).toBeVisible();
          await expect(page.locator('.order-cards')).not.toBeVisible();
        }
      }
    });
  });

  test.describe('Performance on Mobile', () => {
    test.use({
      viewport: { width: 375, height: 667 }
    });

    test('should load quickly on mobile networks', async ({ page }) => {
      // Simulate 3G network
      await page.route('**/*', route => {
        return new Promise(resolve => {
          setTimeout(() => resolve(route.continue()), 100);
        });
      });
      
      const start = Date.now();
      await page.goto('/login');
      const loadTime = Date.now() - start;
      
      // Should load within reasonable time even on slow network
      expect(loadTime).toBeLessThan(5000);
      
      // Critical content should be visible quickly
      await expect(page.locator('.login-form')).toBeVisible({ timeout: 2000 });
    });

    test('should minimize JavaScript bundle for mobile', async ({ page }) => {
      const resources: { url: string; size: number }[] = [];
      
      page.on('response', response => {
        const url = response.url();
        if (url.endsWith('.js')) {
          const size = parseInt(response.headers()['content-length'] || '0');
          resources.push({ url, size });
        }
      });
      
      await page.goto('/');
      
      // Calculate total JS size
      const totalSize = resources.reduce((sum, r) => sum + r.size, 0);
      console.log(`Total mobile JS size: ${(totalSize / 1024).toFixed(2)}KB`);
      
      // Mobile bundle should be smaller
      expect(totalSize).toBeLessThan(500 * 1024); // 500KB limit for mobile
    });
  });

  test.describe('Accessibility on Mobile', () => {
    test.use({
      viewport: { width: 375, height: 667 }
    });

    test('should maintain accessibility on mobile', async ({ page }) => {
      await TestHelpers.loginUI(page, 'administrator', 'SuperSecure#9876');
      await page.goto('/dashboard');
      
      // Touch targets should meet minimum size
      const buttons = page.locator('button, a, [role="button"]');
      const buttonBoxes = await buttons.evaluateAll(btns =>
        btns.map(btn => btn.getBoundingClientRect())
      );
      
      buttonBoxes.forEach(box => {
        expect(box.width).toBeGreaterThanOrEqual(44);
        expect(box.height).toBeGreaterThanOrEqual(44);
      });
      
      // Text should be readable
      const bodyFontSize = await page.evaluate(() => {
        const body = document.body;
        return window.getComputedStyle(body).fontSize;
      });
      expect(parseInt(bodyFontSize)).toBeGreaterThanOrEqual(14);
      
      // Focus indicators should be visible
      await page.keyboard.press('Tab');
      const focusedElement = page.locator(':focus');
      const focusStyles = await focusedElement.evaluate(el => {
        const styles = window.getComputedStyle(el);
        return {
          outline: styles.outline,
          outlineWidth: styles.outlineWidth,
          boxShadow: styles.boxShadow
        };
      });
      
      // Should have visible focus indicator
      expect(
        focusStyles.outline !== 'none' ||
        focusStyles.outlineWidth !== '0px' ||
        focusStyles.boxShadow !== 'none'
      ).toBeTruthy();
    });
  });
});