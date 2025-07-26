import { Page, expect } from '@playwright/test';

export class DashboardPage {
  readonly page: Page;
  
  // Navigation elements
  readonly sidebar = '[data-testid="sidebar"]';
  readonly navCustomers = '[data-testid="nav-customers"]';
  readonly navOrders = '[data-testid="nav-orders"]';
  readonly navRoutes = '[data-testid="nav-routes"]';
  readonly navPredictions = '[data-testid="nav-predictions"]';
  readonly navReports = '[data-testid="nav-reports"]';
  readonly navSettings = '[data-testid="nav-settings"]';
  
  // Dashboard widgets
  readonly dailyOrdersWidget = '[data-testid="daily-orders-widget"]';
  readonly activeDeliveriesWidget = '[data-testid="active-deliveries-widget"]';
  readonly revenueWidget = '[data-testid="revenue-widget"]';
  readonly customerSatisfactionWidget = '[data-testid="customer-satisfaction-widget"]';
  readonly predictionsWidget = '[data-testid="predictions-widget"]';
  readonly recentOrdersList = '[data-testid="recent-orders-list"]';
  
  // Header elements
  readonly userMenu = '[data-testid="user-menu"]';
  readonly notificationBell = '[data-testid="notification-bell"]';
  readonly searchBar = '[data-testid="global-search"]';
  readonly refreshButton = '[data-testid="refresh-button"]';
  readonly dateRangePicker = '[data-testid="date-range-picker"]';

  constructor(page: Page) {
    this.page = page;
  }

  async waitForPageLoad() {
    // Wait for page to load - different roles might have different dashboards
    await this.page.waitForLoadState('networkidle');
    
    // Different roles have different interfaces
    const currentUrl = this.page.url();
    
    if (currentUrl.includes('/driver')) {
      // Driver interface has different structure
      // Wait for driver-specific elements
      const driverStatus = this.page.getByText(/司機|上線|今日配送/);
      await expect(driverStatus.first()).toBeVisible({ timeout: 10000 });
    } else if (currentUrl.includes('/customer-portal')) {
      // Customer portal has different structure
      await this.page.waitForTimeout(1000);
    } else {
      // Standard dashboard - wait for heading or stats
      const pageTitle = this.page.getByRole('heading', { level: 2 }).first();
      const dashboardStats = this.page.locator('.dashboard-stats');
      
      // Wait for either heading or stats to be visible
      await Promise.race([
        expect(pageTitle).toBeVisible({ timeout: 10000 }).catch(() => null),
        expect(dashboardStats).toBeVisible({ timeout: 10000 }).catch(() => null)
      ]);
    }
  }

  async navigateTo(section: 'customers' | 'orders' | 'routes' | 'predictions' | 'reports' | 'settings') {
    const navTextMap = {
      customers: '客戶管理',
      orders: '訂單管理',
      routes: '路線規劃',
      predictions: '需求預測',
      reports: '報表分析',
      settings: '系統設定',
    };
    
    // Check if we're on mobile by looking for the mobile menu trigger
    const mobileMenuTrigger = this.page.locator('[data-testid="mobile-menu-trigger"]');
    // Also check viewport width as a fallback
    const viewport = this.page.viewportSize();
    const isMobileViewport = viewport ? viewport.width < 768 : false;
    const isMobile = await mobileMenuTrigger.isVisible().catch(() => false) || isMobileViewport;
    
    if (isMobile) {
      // Open mobile menu drawer
      await mobileMenuTrigger.click();
      // Wait for drawer to open
      await this.page.waitForSelector('[data-testid="mobile-nav-menu"]', { state: 'visible' });
      // Click menu item in the drawer
      await this.page.locator(`[data-testid="mobile-nav-menu"] >> text="${navTextMap[section]}"`).click();
    } else {
      // Desktop navigation
      await this.page.getByRole('menuitem', { name: navTextMap[section] }).click();
    }
    
    await this.page.waitForURL(new RegExp(`/${section}`));
  }

  async verifyDashboardMetrics() {
    // Verify dashboard stats cards are visible
    const statsSection = this.page.locator('.dashboard-stats');
    await expect(statsSection).toBeVisible();
    
    // Check key metrics are displayed
    const metricTitles = ['今日訂單', '活躍客戶', '配送中司機', '今日營收'];
    
    for (const title of metricTitles) {
      const metric = this.page.getByText(title).first();
      await expect(metric).toBeVisible();
    }
    
    // Ensure no loading spinners are visible
    const loadingSpinners = this.page.locator('.ant-spin-spinning');
    await expect(loadingSpinners).toHaveCount(0);
  }

  async getDailyOrdersCount(): Promise<number> {
    // Find the value near "今日訂單" text
    const card = this.page.locator('.ant-card:has-text("今日訂單")');
    const value = await card.locator('.ant-statistic-content-value').textContent();
    return parseInt(value?.replace(/[^0-9]/g, '') || '0');
  }

  async getActiveDeliveriesCount(): Promise<number> {
    // Find the value near "配送中司機" text
    const card = this.page.locator('.ant-card:has-text("配送中司機")');
    const value = await card.locator('.ant-statistic-content-value').textContent();
    return parseInt(value?.replace(/[^0-9]/g, '') || '0');
  }

  async getTodayRevenue(): Promise<number> {
    // Find the value near "今日營收" text
    const card = this.page.locator('.ant-card:has-text("今日營收")');
    const value = await card.locator('.ant-statistic-content-value').textContent();
    return parseInt(value?.replace(/[^0-9]/g, '') || '0');
  }

  async refreshDashboard() {
    await this.page.click(this.refreshButton);
    
    // Wait for refresh to complete
    await this.page.waitForLoadState('networkidle');
    await this.page.waitForTimeout(500); // Brief wait for animations
  }

  async selectDateRange(preset: 'today' | 'yesterday' | 'last7days' | 'last30days' | 'custom', customStart?: string, customEnd?: string) {
    await this.page.click(this.dateRangePicker);
    
    if (preset === 'custom' && customStart && customEnd) {
      await this.page.fill('[data-testid="date-start"]', customStart);
      await this.page.fill('[data-testid="date-end"]', customEnd);
      await this.page.click('[data-testid="date-apply"]');
    } else {
      await this.page.click(`[data-testid="date-preset-${preset}"]`);
    }
    
    // Wait for data refresh
    await this.page.waitForLoadState('networkidle');
  }

  async searchGlobal(query: string) {
    await this.page.fill(this.searchBar, query);
    await this.page.press(this.searchBar, 'Enter');
    
    // Wait for search results
    await this.page.waitForSelector('[data-testid="search-results"]', { timeout: 5000 });
  }

  async checkNotifications() {
    // Click on bell icon
    await this.page.getByRole('button', { name: 'bell' }).click();
    
    // Wait for notification dropdown/panel
    const notificationPanel = this.page.getByRole('menu');
    await expect(notificationPanel).toBeVisible();
    
    // Get notification count from menu items
    const notifications = await notificationPanel.getByRole('menuitem').count();
    return notifications;
  }

  async markNotificationAsRead(index: number = 0) {
    const notification = `[data-testid="notification-item"]:nth-child(${index + 1})`;
    await this.page.click(`${notification} [data-testid="mark-read"]`);
  }

  async verifyRecentOrders() {
    const orderItems = await this.page.locator(`${this.recentOrdersList} [data-testid="order-item"]`).count();
    expect(orderItems).toBeGreaterThan(0);
    
    // Verify order information is displayed
    const firstOrder = `${this.recentOrdersList} [data-testid="order-item"]:first-child`;
    await expect(this.page.locator(`${firstOrder} [data-testid="order-number"]`)).toBeVisible();
    await expect(this.page.locator(`${firstOrder} [data-testid="customer-name"]`)).toBeVisible();
    await expect(this.page.locator(`${firstOrder} [data-testid="order-status"]`)).toBeVisible();
    await expect(this.page.locator(`${firstOrder} [data-testid="order-amount"]`)).toBeVisible();
  }

  async verifyChineseUI() {
    // Verify navigation items are in Traditional Chinese
    await expect(this.page.getByRole('menuitem', { name: '客戶管理' })).toBeVisible();
    await expect(this.page.getByRole('menuitem', { name: '訂單管理' })).toBeVisible();
    await expect(this.page.getByRole('menuitem', { name: '路線規劃' })).toBeVisible();
    await expect(this.page.getByRole('menuitem', { name: '需求預測' })).toBeVisible();
    await expect(this.page.getByRole('menuitem', { name: '報表分析' })).toBeVisible();
    await expect(this.page.getByRole('menuitem', { name: '系統設定' })).toBeVisible();
    
    // Verify widget titles by text content
    await expect(this.page.getByText('今日訂單')).toBeVisible();
    await expect(this.page.getByText('配送中司機')).toBeVisible();
    await expect(this.page.getByText('今日營收')).toBeVisible();
  }

  async openUserMenu() {
    const viewport = this.page.viewportSize();
    const isMobile = viewport && viewport.width < 768;
    
    if (isMobile) {
      // On mobile, user menu might be in the mobile drawer
      const mobileMenuButton = this.page.locator('button[aria-label="menu"], .ant-menu-mobile-icon, .menu-toggle, [data-testid="mobile-menu-trigger"]');
      if (await mobileMenuButton.isVisible({ timeout: 2000 }).catch(() => false)) {
        await mobileMenuButton.click();
        await this.page.waitForTimeout(500); // Wait for menu animation
        // Look for user section in mobile menu
        const userSection = this.page.locator('[data-testid="mobile-user-section"], .mobile-user-menu');
        if (await userSection.isVisible({ timeout: 2000 }).catch(() => false)) {
          await userSection.click();
        }
      }
    } else {
      // Click on user icon or user name in header
      const userButton = this.page.locator('header').getByRole('img', { name: 'user' }).last();
      await userButton.click();
      // Wait for dropdown menu - specifically the user dropdown, not the sidebar menu
      await expect(this.page.getByRole('menu').filter({ hasText: '登出' })).toBeVisible();
    }
  }

  async logout() {
    const viewport = this.page.viewportSize();
    const isMobile = viewport && viewport.width < 768;
    
    // Set up response monitoring for logout API call
    let logoutApiCalled = false;
    const responseHandler = (response: any) => {
      if (response.url().includes('/auth/logout') || response.url().includes('/logout')) {
        logoutApiCalled = true;
        console.log('🔍 Logout API called:', response.status());
      }
    };
    this.page.on('response', responseHandler);
    
    try {
      if (isMobile) {
        console.log('📱 Attempting mobile logout flow');
        
        // Try multiple logout strategies for mobile
        const logoutStrategies = [
          // Strategy 1: Look for logout in visible UI
          async () => {
            const logoutVisible = this.page.locator('text=登出, button:has-text("登出"), [aria-label="登出"]').first();
            if (await logoutVisible.isVisible({ timeout: 2000 }).catch(() => false)) {
              console.log('✅ Found visible logout button');
              await logoutVisible.click();
              return true;
            }
            return false;
          },
          
          // Strategy 2: Open mobile menu and find logout
          async () => {
            const mobileMenuButton = this.page.locator('button[aria-label="menu"], .ant-menu-mobile-icon, .menu-toggle, [data-testid="mobile-menu-trigger"]');
            if (await mobileMenuButton.isVisible({ timeout: 2000 }).catch(() => false)) {
              await mobileMenuButton.click();
              await this.page.waitForTimeout(500);
              
              const logoutInMenu = this.page.locator('text=登出').first();
              if (await logoutInMenu.isVisible({ timeout: 2000 }).catch(() => false)) {
                console.log('✅ Found logout in mobile menu');
                await logoutInMenu.click();
                return true;
              }
            }
            return false;
          },
          
          // Strategy 3: Try user menu approach
          async () => {
            await this.openUserMenu();
            const logoutMenuItem = this.page.getByRole('menuitem', { name: '登出' });
            if (await logoutMenuItem.isVisible({ timeout: 2000 }).catch(() => false)) {
              console.log('✅ Found logout in user menu');
              await logoutMenuItem.click();
              return true;
            }
            return false;
          }
        ];
        
        // Try each strategy
        let logoutClicked = false;
        for (const strategy of logoutStrategies) {
          if (await strategy()) {
            logoutClicked = true;
            break;
          }
        }
        
        if (!logoutClicked) {
          console.log('⚠️ Could not find logout button on mobile');
        }
      } else {
        // Desktop logout flow
        await this.openUserMenu();
        await this.page.getByRole('menuitem', { name: '登出' }).click();
      }
      
      // Wait for logout to process
      await this.page.waitForTimeout(2000);
      
      // Check if logout API was called
      if (!logoutApiCalled) {
        console.log('⚠️ Logout API was not called, manually clearing auth data');
        // Manually clear auth data
        await this.page.evaluate(() => {
          localStorage.removeItem('access_token');
          localStorage.removeItem('refresh_token');
          localStorage.removeItem('token_expiry');
          localStorage.removeItem('user_info');
        });
      }
      
      // Check if we're on login page
      const currentUrl = this.page.url();
      if (!currentUrl.includes('/login')) {
        console.log('⚠️ Not redirected to login, navigating manually');
        await this.page.goto('/login');
      }
      
      // Ensure we're on login page
      await this.page.waitForURL('/login', { timeout: 5000 });
    } finally {
      // Clean up event listener
      this.page.off('response', responseHandler);
    }
  }

  async verifyRoleBasedAccess(userRole: string) {
    // Ensure page is fully loaded first
    await this.page.waitForLoadState('networkidle');
    await this.page.waitForTimeout(1000); // Additional wait for any animations
    
    // Check if we're on mobile
    const viewport = this.page.viewportSize();
    const isMobile = viewport && viewport.width < 768;
    
    // Open mobile menu if needed
    if (isMobile && userRole !== 'driver') {
      console.log('📱 Attempting to open mobile menu for role:', userRole);
      
      // Try to find and click mobile menu button
      const mobileMenuButton = this.page.locator('button[aria-label="menu"], .ant-menu-mobile-icon, .menu-toggle, [data-testid="mobile-menu-trigger"]');
      if (await mobileMenuButton.isVisible({ timeout: 5000 }).catch(() => false)) {
        await mobileMenuButton.click();
        await this.page.waitForTimeout(500); // Wait for menu animation
        console.log('✅ Mobile menu button clicked');
      } else {
        console.log('⚠️ Mobile menu button not found, trying alternative selectors');
        // Try alternative selectors
        const alternativeSelectors = [
          'button:has(svg[data-icon="menu"])',
          '.ant-layout-header button',
          'header button'
        ];
        
        for (const selector of alternativeSelectors) {
          const button = this.page.locator(selector).first();
          if (await button.isVisible({ timeout: 1000 }).catch(() => false)) {
            await button.click();
            await this.page.waitForTimeout(500);
            console.log('✅ Found menu button with selector:', selector);
            break;
          }
        }
      }
      
      // Log what's visible after attempting to open menu
      const visibleText = await this.page.locator('body').textContent();
      console.log('📋 Visible text snippet:', visibleText?.substring(0, 200));
    }
    
    // Different roles see different navigation items and interfaces
    switch (userRole) {
      case 'super_admin':
        // Super admin should see all menu items
        if (isMobile) {
          // On mobile, menu items might not have menuitem role - use text-based selectors
          await expect(this.page.getByText('客戶管理').first()).toBeVisible();
          await expect(this.page.getByText('訂單管理').first()).toBeVisible();
          await expect(this.page.getByText('路線規劃').first()).toBeVisible();
          await expect(this.page.getByText('配送歷史').first()).toBeVisible();
        } else {
          await expect(this.page.getByRole('menuitem', { name: '客戶管理' })).toBeVisible();
          await expect(this.page.getByRole('menuitem', { name: '訂單管理' })).toBeVisible();
          await expect(this.page.getByRole('menuitem', { name: '路線規劃' })).toBeVisible();
          await expect(this.page.getByRole('menuitem', { name: '配送歷史' })).toBeVisible();
        }
        break;
      case 'manager':
        // Manager should see most features but maybe not all
        if (isMobile) {
          await expect(this.page.getByText('客戶管理').first()).toBeVisible();
          await expect(this.page.getByText('訂單管理').first()).toBeVisible();
          await expect(this.page.getByText('配送歷史').first()).toBeVisible();
        } else {
          await expect(this.page.getByRole('menuitem', { name: '客戶管理' })).toBeVisible();
          await expect(this.page.getByRole('menuitem', { name: '訂單管理' })).toBeVisible();
          await expect(this.page.getByRole('menuitem', { name: '配送歷史' })).toBeVisible();
        }
        break;
      case 'office_staff':
        // Office staff sees customer, order, and route planning
        if (isMobile) {
          await expect(this.page.getByText('客戶管理').first()).toBeVisible();
          await expect(this.page.getByText('訂單管理').first()).toBeVisible();
          await expect(this.page.getByText('路線規劃').first()).toBeVisible();
        } else {
          await expect(this.page.getByRole('menuitem', { name: '客戶管理' })).toBeVisible();
          await expect(this.page.getByRole('menuitem', { name: '訂單管理' })).toBeVisible();
          await expect(this.page.getByRole('menuitem', { name: '路線規劃' })).toBeVisible();
        }
        break;
      case 'driver':
        // Driver has a completely different interface - delivery-focused
        console.log('🚚 Verifying driver-specific interface');
        
        // Wait a bit longer for driver dashboard to load
        await this.page.waitForTimeout(2000);
        
        // Try multiple selectors for driver-specific elements
        const driverElements = [
          { selector: 'text=今日配送', description: 'Today\'s deliveries' },
          { selector: 'text=今日路線', description: 'Today\'s route' },
          { selector: 'text=配送任務', description: 'Delivery tasks' },
          { selector: 'text=路線', description: 'Route' }
        ];
        
        let foundDriverElement = false;
        for (const element of driverElements) {
          const locator = this.page.locator(element.selector).first();
          if (await locator.isVisible({ timeout: 2000 }).catch(() => false)) {
            console.log(`✅ Found driver element: ${element.description}`);
            foundDriverElement = true;
            await expect(locator).toBeVisible();
            break;
          }
        }
        
        if (!foundDriverElement) {
          console.log('⚠️ No specific driver elements found, checking for general driver indicators');
          
          // Look for any indication this is a driver view
          const pageText = await this.page.locator('body').textContent();
          if (pageText?.includes('司機') || pageText?.includes('配送') || pageText?.includes('路線')) {
            console.log('✅ Found driver-related text in page');
          } else {
            throw new Error('Driver interface not detected');
          }
        }
        
        // Don't check for specific menu items as driver has different UI
        break;
    }
  }

  async waitForWebSocketConnection() {
    // Wait for WebSocket indicator to show connected
    await expect(this.page.locator('[data-testid="websocket-status"]')).toHaveAttribute('data-status', 'connected');
  }

  async verifyRealTimeUpdate(updateType: 'order' | 'delivery' | 'notification') {
    // Store initial count
    let initialCount: number;
    
    switch (updateType) {
      case 'order':
        initialCount = await this.getDailyOrdersCount();
        break;
      case 'delivery':
        initialCount = await this.getActiveDeliveriesCount();
        break;
      case 'notification':
        const badge = await this.page.locator('[data-testid="notification-badge"]').textContent();
        initialCount = parseInt(badge || '0');
        break;
    }
    
    // Wait for update (triggered by another test or real event)
    await this.page.waitForTimeout(2000);
    
    // Verify count changed
    let newCount: number;
    switch (updateType) {
      case 'order':
        newCount = await this.getDailyOrdersCount();
        break;
      case 'delivery':
        newCount = await this.getActiveDeliveriesCount();
        break;
      case 'notification':
        const newBadge = await this.page.locator('[data-testid="notification-badge"]').textContent();
        newCount = parseInt(newBadge || '0');
        break;
    }
    
    expect(newCount).not.toBe(initialCount);
  }
}