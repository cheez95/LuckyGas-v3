import { test, expect, devices } from '@playwright/test';
import { LoginPage } from './pages/LoginPage';
import { DashboardPage } from './pages/DashboardPage';
import { CustomerPage } from './pages/CustomerPage';
import { OrderPage } from './pages/OrderPage';

// Test on different mobile devices
const mobileDevices = [
  { name: 'iPhone 12', device: devices['iPhone 12'] },
  { name: 'Pixel 5', device: devices['Pixel 5'] },
  { name: 'iPhone SE', device: devices['iPhone SE'] },
];

mobileDevices.forEach(({ name, device }) => {
  test.describe(`Mobile Responsiveness - ${name}`, () => {
    test.use(device);
    
    let loginPage: LoginPage;
    let dashboardPage: DashboardPage;
    let customerPage: CustomerPage;
    let orderPage: OrderPage;

    test.beforeEach(async ({ page }) => {
      loginPage = new LoginPage(page);
      dashboardPage = new DashboardPage(page);
      customerPage = new CustomerPage(page);
      orderPage = new OrderPage(page);
    });

    test('should display login page correctly on mobile', async ({ page }) => {
      await loginPage.navigateToLogin();
      
      // Check mobile layout
      const isMobileLayout = await loginPage.checkMobileLayout();
      expect(isMobileLayout).toBe(true);
      
      // Login form should be full width on mobile
      const loginBox = page.locator('.login-box');
      const boxWidth = await loginBox.evaluate(el => el.offsetWidth);
      const viewportWidth = page.viewportSize()?.width || 0;
      
      // Box should take most of the viewport width (with some padding)
      expect(boxWidth).toBeGreaterThan(viewportWidth * 0.8);
      
      // All form elements should be visible and touchable
      await expect(loginPage.usernameInput).toBeVisible();
      await expect(loginPage.passwordInput).toBeVisible();
      await expect(loginPage.loginButton).toBeVisible();
      
      // Touch login button (should be large enough for touch)
      const buttonBox = await loginPage.loginButton.boundingBox();
      expect(buttonBox?.height).toBeGreaterThanOrEqual(44); // iOS touch target size
    });

    test('should handle mobile navigation menu', async ({ page }) => {
      // Login first
      await loginPage.navigateToLogin();
      await loginPage.login('admin', 'admin123');
      await loginPage.waitForLoginSuccess();
      
      // Check if hamburger menu is visible on mobile
      const hamburgerMenu = page.locator('.mobile-menu-trigger');
      await expect(hamburgerMenu).toBeVisible();
      
      // Click hamburger to open menu
      await hamburgerMenu.click();
      
      // Menu should slide in
      const mobileMenu = page.locator('.ant-drawer');
      await expect(mobileMenu).toBeVisible();
      
      // All menu items should be visible
      await expect(page.getByText('客戶管理')).toBeVisible();
      await expect(page.getByText('訂單管理')).toBeVisible();
      await expect(page.getByText('路線規劃')).toBeVisible();
      
      // Click outside to close
      await page.locator('.ant-drawer-mask').click();
      await expect(mobileMenu).not.toBeVisible();
    });

    test('should stack dashboard cards vertically on mobile', async ({ page }) => {
      await loginPage.navigateToLogin();
      await loginPage.login('admin', 'admin123');
      await loginPage.waitForLoginSuccess();
      
      // Check mobile responsive layout
      const isMobileResponsive = await dashboardPage.checkMobileResponsive();
      expect(isMobileResponsive).toBe(true);
      
      // Cards should be full width
      const cards = page.locator('.ant-card');
      const cardCount = await cards.count();
      
      for (let i = 0; i < cardCount; i++) {
        const card = cards.nth(i);
        const cardBox = await card.boundingBox();
        const viewportWidth = page.viewportSize()?.width || 0;
        
        // Each card should take most of viewport width
        expect(cardBox?.width).toBeGreaterThan(viewportWidth * 0.9);
      }
    });

    test('should make customer table horizontally scrollable on mobile', async ({ page }) => {
      await loginPage.navigateToLogin();
      await loginPage.login('admin', 'admin123');
      await loginPage.waitForLoginSuccess();
      await dashboardPage.navigateToCustomers();
      
      // Check mobile table layout
      const isMobileResponsive = await customerPage.checkMobileResponsive();
      expect(isMobileResponsive).toBe(true);
      
      // Table container should have horizontal scroll
      const tableContainer = page.locator('.ant-table-container');
      const hasHorizontalScroll = await tableContainer.evaluate(el => {
        return el.scrollWidth > el.clientWidth;
      });
      expect(hasHorizontalScroll).toBe(true);
      
      // Test horizontal scrolling
      await tableContainer.evaluate(el => {
        el.scrollLeft = 100;
      });
      
      const scrollLeft = await tableContainer.evaluate(el => el.scrollLeft);
      expect(scrollLeft).toBe(100);
    });

    test('should handle mobile form inputs correctly', async ({ page }) => {
      await loginPage.navigateToLogin();
      await loginPage.login('admin', 'admin123');
      await loginPage.waitForLoginSuccess();
      await dashboardPage.navigateToCustomers();
      
      // Open add customer modal
      await customerPage.clickAddCustomer();
      
      // Modal should be full screen on mobile
      const modal = page.locator('.ant-modal');
      const modalBox = await modal.boundingBox();
      const viewportSize = page.viewportSize();
      
      if (viewportSize) {
        expect(modalBox?.width).toBeGreaterThan(viewportSize.width * 0.95);
      }
      
      // Test touch input
      await customerPage.customerCodeInput.tap();
      await page.keyboard.type('MOB001');
      
      await customerPage.nameInput.tap();
      await page.keyboard.type('手機測試客戶');
      
      // Date picker should be mobile optimized
      await page.locator('#customer_deliveryTimeStart').tap();
      const timePicker = page.locator('.ant-picker-dropdown');
      await expect(timePicker).toBeVisible();
      
      // Close modal
      await customerPage.modalCancelButton.click();
    });

    test('should handle touch gestures for order management', async ({ page }) => {
      await loginPage.navigateToLogin();
      await loginPage.login('admin', 'admin123');
      await loginPage.waitForLoginSuccess();
      await dashboardPage.navigateToOrders();
      
      // Test swipe actions on order rows (if implemented)
      const firstOrder = orderPage.orderRows.first();
      const orderBox = await firstOrder.boundingBox();
      
      if (orderBox) {
        // Simulate swipe left to reveal actions
        await page.mouse.move(orderBox.x + orderBox.width - 20, orderBox.y + orderBox.height / 2);
        await page.mouse.down();
        await page.mouse.move(orderBox.x + 20, orderBox.y + orderBox.height / 2);
        await page.mouse.up();
        
        // Action buttons should be visible (if swipe is implemented)
        // await expect(page.locator('.order-actions')).toBeVisible();
      }
    });

    test('should optimize button sizes for touch targets', async ({ page }) => {
      await loginPage.navigateToLogin();
      await loginPage.login('admin', 'admin123');
      await loginPage.waitForLoginSuccess();
      
      // Check all buttons meet minimum touch target size (44x44 for iOS, 48x48 for Android)
      const buttons = page.locator('button');
      const buttonCount = await buttons.count();
      
      for (let i = 0; i < Math.min(buttonCount, 5); i++) { // Check first 5 buttons
        const button = buttons.nth(i);
        const box = await button.boundingBox();
        
        if (box && await button.isVisible()) {
          expect(box.height).toBeGreaterThanOrEqual(44);
          expect(box.width).toBeGreaterThanOrEqual(44);
        }
      }
    });

    test('should handle mobile keyboard properly', async ({ page }) => {
      await loginPage.navigateToLogin();
      
      // Focus on input should bring up keyboard
      await loginPage.usernameInput.tap();
      
      // Wait a bit for keyboard animation
      await page.waitForTimeout(500);
      
      // Login button should still be visible (not covered by keyboard)
      await expect(loginPage.loginButton).toBeInViewport();
      
      // Test keyboard dismissal
      await page.tap('body', { position: { x: 10, y: 10 } }); // Tap outside
    });

    test('should display mobile-optimized error messages', async ({ page }) => {
      await loginPage.navigateToLogin();
      
      // Trigger error
      await loginPage.login('wrong', 'wrong');
      
      // Error should be visible and properly sized
      await expect(loginPage.errorAlert).toBeVisible();
      
      const errorBox = await loginPage.errorAlert.boundingBox();
      const viewportWidth = page.viewportSize()?.width || 0;
      
      // Error should be nearly full width on mobile
      expect(errorBox?.width).toBeGreaterThan(viewportWidth * 0.8);
    });

    test('should handle offline mode gracefully', async ({ page, context }) => {
      await loginPage.navigateToLogin();
      await loginPage.login('admin', 'admin123');
      await loginPage.waitForLoginSuccess();
      
      // Go offline
      await context.setOffline(true);
      
      // Try to navigate
      await dashboardPage.navigateToCustomers();
      
      // Should show offline message
      const offlineMessage = page.locator('.offline-message, .ant-alert-error');
      await expect(offlineMessage).toBeVisible({ timeout: 5000 });
      
      // Go back online
      await context.setOffline(false);
      
      // Should recover
      await page.reload();
      await expect(customerPage.pageTitle).toBeVisible();
    });

    test('should optimize images for mobile', async ({ page }) => {
      await loginPage.navigateToLogin();
      
      // Check logo size
      const logo = page.locator('img[alt*="Lucky Gas"], img[alt*="幸福氣"]');
      if (await logo.isVisible()) {
        const logoBox = await logo.boundingBox();
        const viewportWidth = page.viewportSize()?.width || 0;
        
        // Logo should be appropriately sized for mobile
        expect(logoBox?.width).toBeLessThan(viewportWidth * 0.5);
      }
    });

    test('should handle portrait and landscape orientations', async ({ page }) => {
      await loginPage.navigateToLogin();
      await loginPage.login('admin', 'admin123');
      await loginPage.waitForLoginSuccess();
      
      // Test portrait (default)
      const portraitCards = await dashboardPage.todayOrdersCard.boundingBox();
      
      // Switch to landscape
      await page.setViewportSize({ 
        width: device.viewport.height, 
        height: device.viewport.width 
      });
      
      // Layout should adjust
      const landscapeCards = await dashboardPage.todayOrdersCard.boundingBox();
      
      // Cards might be arranged differently in landscape
      expect(landscapeCards?.width).not.toBe(portraitCards?.width);
    });
  });
});

// Test specific mobile interactions
test.describe('Mobile Touch Interactions', () => {
  test.use(devices['iPhone 12']);

  test('should handle pull-to-refresh', async ({ page }) => {
    const loginPage = new LoginPage(page);
    const dashboardPage = new DashboardPage(page);
    
    await loginPage.navigateToLogin();
    await loginPage.login('admin', 'admin123');
    await loginPage.waitForLoginSuccess();
    
    // Simulate pull-to-refresh gesture
    await page.touchscreen.tap(100, 100);
    await page.waitForTimeout(100);
    
    // Drag down from top
    for (let i = 0; i < 10; i++) {
      await page.touchscreen.tap(100, 100 + i * 20);
      await page.waitForTimeout(50);
    }
    
    // If pull-to-refresh is implemented, check for refresh indicator
    // await expect(page.locator('.refresh-indicator')).toBeVisible();
  });

  test('should handle long press actions', async ({ page }) => {
    const loginPage = new LoginPage(page);
    const dashboardPage = new DashboardPage(page);
    const customerPage = new CustomerPage(page);
    
    await loginPage.navigateToLogin();
    await loginPage.login('admin', 'admin123');
    await loginPage.waitForLoginSuccess();
    await dashboardPage.navigateToCustomers();
    
    // Long press on a customer row
    const firstRow = customerPage.customerRows.first();
    const box = await firstRow.boundingBox();
    
    if (box) {
      // Simulate long press
      await page.touchscreen.tap(box.x + box.width / 2, box.y + box.height / 2, {
        delay: 1000 // 1 second press
      });
      
      // If context menu is implemented for long press
      // await expect(page.locator('.context-menu')).toBeVisible();
    }
  });
});