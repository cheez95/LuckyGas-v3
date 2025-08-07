import { test, expect, Page } from '@playwright/test';

// Mock authentication by setting local storage
async function mockLogin(page: Page, role = 'office_staff') {
  // Set mock auth token and user data in local storage
  await page.addInitScript(() => {
    localStorage.setItem('token', 'mock-jwt-token');
    localStorage.setItem('user', JSON.stringify({
      id: 1,
      username: 'office1',
      email: 'office1@luckygas.com',
      full_name: '辦公室員工一',
      role: 'office_staff',
      is_active: true
    }));
  });
  
  // Also set as cookies for API requests
  await page.context().addCookies([
    {
      name: 'token',
      value: 'mock-jwt-token',
      domain: 'localhost',
      path: '/'
    }
  ]);
}

// Realistic test data for Taiwan office staff
const CUSTOMERS = {
  regular: {
    name: '王小明',
    phone: '0912345678',
    address: '台北市大安區信義路四段123號5樓',
    deliveryNotes: '請按電鈴，狗不會咬人'
  },
  commercial: {
    name: '幸福餐廳',
    phone: '02-27123456',
    address: '台北市信義區忠孝東路五段68號',
    deliveryNotes: '後門收貨，找陳經理'
  }
};

// Helper to simulate realistic typing speed
async function typeRealistic(page: Page, selector: string, text: string) {
  await page.fill(selector, '');
  await page.type(selector, text, { delay: 50 + Math.random() * 50 });
}

// Helper to simulate thinking time
async function thinkingPause(minMs = 500, maxMs = 1500) {
  await new Promise(resolve => setTimeout(resolve, minMs + Math.random() * (maxMs - minMs)));
}

// Take screenshot with annotation
async function annotatedScreenshot(page: Page, name: string, annotation?: string) {
  if (annotation) {
    console.log(`📸 Screenshot: ${name} - ${annotation}`);
  }
  await page.screenshot({ 
    path: `test-results/ux-analysis/${name}.png`,
    fullPage: true 
  });
}

test.describe('Office Staff UX Analysis - Mock Auth', () => {
  test.beforeEach(async ({ page }) => {
    // Set up mock authentication
    await mockLogin(page);
    
    // Navigate directly to dashboard (bypassing login)
    await page.goto('http://localhost:5173/dashboard');
  });

  test('📊 Dashboard UX Analysis', async ({ page }) => {
    console.log('🌅 Analyzing dashboard user experience...');
    
    // Wait for dashboard to load
    await page.waitForTimeout(2000);
    await annotatedScreenshot(page, 'dashboard-overview', 'Initial dashboard view');
    
    // Analyze dashboard layout
    const dashboardElements = {
      title: await page.locator('h1, h2').first().textContent(),
      statsCards: await page.locator('[class*="stat"], [class*="card"]').count(),
      navigationItems: await page.locator('nav a, [role="navigation"] a').count(),
      actionButtons: await page.locator('button').count()
    };
    
    console.log('Dashboard Elements:', dashboardElements);
    
    // Check for responsive design
    const viewports = [
      { width: 1920, height: 1080, name: 'desktop' },
      { width: 768, height: 1024, name: 'tablet' },
      { width: 375, height: 667, name: 'mobile' }
    ];
    
    for (const viewport of viewports) {
      await page.setViewportSize(viewport);
      await page.waitForTimeout(500);
      await annotatedScreenshot(page, `dashboard-${viewport.name}`, `Dashboard on ${viewport.name}`);
    }
    
    // Reset to desktop view
    await page.setViewportSize({ width: 1280, height: 720 });
  });

  test('🛒 Order Creation Flow Analysis', async ({ page }) => {
    console.log('📞 Analyzing order creation workflow...');
    
    // Navigate to orders page
    await page.goto('http://localhost:5173/orders');
    await page.waitForTimeout(1000);
    await annotatedScreenshot(page, 'orders-list', 'Orders list page');
    
    // Look for create order button
    const createButton = page.locator('button:has-text("新增"), button:has-text("建立"), button:has-text("Create"), [data-testid*="create"]');
    if (await createButton.isVisible()) {
      await createButton.click();
      await thinkingPause(1000, 1500);
      await annotatedScreenshot(page, 'order-create-modal', 'Order creation form');
      
      // Analyze form fields
      const formFields = {
        customerInput: await page.locator('input[placeholder*="客戶"], input[placeholder*="Customer"]').count(),
        phoneInput: await page.locator('input[placeholder*="電話"], input[placeholder*="Phone"]').count(),
        addressInput: await page.locator('input[placeholder*="地址"], input[placeholder*="Address"], textarea[placeholder*="地址"]').count(),
        productSelect: await page.locator('select, [role="combobox"]').count(),
        quantityInput: await page.locator('input[type="number"]').count()
      };
      
      console.log('Form Fields Found:', formFields);
      
      // Try to fill in customer information
      const customerInput = page.locator('input').first();
      if (await customerInput.isVisible()) {
        await typeRealistic(page, 'input:first-of-type', CUSTOMERS.regular.name);
        await thinkingPause(500, 1000);
      }
    }
  });

  test('📋 Customer Management Analysis', async ({ page }) => {
    console.log('👥 Analyzing customer management interface...');
    
    // Navigate to customers page
    await page.goto('http://localhost:5173/customers');
    await page.waitForTimeout(1000);
    await annotatedScreenshot(page, 'customers-list', 'Customer list view');
    
    // Analyze list features
    const listFeatures = {
      searchBox: await page.locator('input[placeholder*="搜尋"], input[placeholder*="Search"]').isVisible(),
      filters: await page.locator('[class*="filter"], button:has-text("篩選")').count(),
      sortOptions: await page.locator('[class*="sort"], select').count(),
      pagination: await page.locator('[class*="pagination"], [class*="page"]').isVisible()
    };
    
    console.log('List Features:', listFeatures);
    
    // Check table/grid layout
    const hasTable = await page.locator('table').isVisible();
    const hasCards = await page.locator('[class*="card"], [class*="grid"]').count() > 0;
    
    console.log(`Display Format: ${hasTable ? 'Table' : hasCards ? 'Cards' : 'Other'}`);
  });

  test('🗺️ Route Planning Interface Analysis', async ({ page }) => {
    console.log('🚚 Analyzing route planning interface...');
    
    // Navigate to routes page
    await page.goto('http://localhost:5173/routes');
    await page.waitForTimeout(1000);
    await annotatedScreenshot(page, 'routes-overview', 'Routes overview page');
    
    // Check for map integration
    const hasMap = await page.locator('canvas, [class*="map"], iframe[src*="maps"]').isVisible();
    console.log(`Map Integration: ${hasMap ? 'Yes' : 'No'}`);
    
    // Check for route optimization features
    const routeFeatures = {
      optimizeButton: await page.locator('button:has-text("優化"), button:has-text("Optimize")').isVisible(),
      driverAssignment: await page.locator('select, [role="combobox"]').count(),
      dateSelector: await page.locator('input[type="date"], [class*="date"]').isVisible()
    };
    
    console.log('Route Features:', routeFeatures);
  });

  test('📱 Mobile Responsiveness Analysis', async ({ page }) => {
    console.log('📱 Testing mobile responsiveness...');
    
    // Test key pages on mobile viewport
    const pages = [
      { url: '/dashboard', name: 'dashboard' },
      { url: '/orders', name: 'orders' },
      { url: '/customers', name: 'customers' }
    ];
    
    // Set mobile viewport
    await page.setViewportSize({ width: 375, height: 667 });
    
    for (const pageInfo of pages) {
      await page.goto(`http://localhost:5173${pageInfo.url}`);
      await page.waitForTimeout(1000);
      
      // Check if navigation is accessible (hamburger menu)
      const hasMobileNav = await page.locator('[class*="burger"], [class*="menu-icon"], button[aria-label*="menu"]').isVisible();
      console.log(`${pageInfo.name} - Mobile Navigation: ${hasMobileNav ? 'Yes' : 'No'}`);
      
      await annotatedScreenshot(page, `mobile-${pageInfo.name}`, `Mobile view of ${pageInfo.name}`);
    }
  });

  test('⚡ Performance and Loading States', async ({ page }) => {
    console.log('⚡ Analyzing loading states and performance...');
    
    // Monitor network requests
    const requests: string[] = [];
    page.on('request', request => {
      if (request.url().includes('/api/')) {
        requests.push(`${request.method()} ${request.url()}`);
      }
    });
    
    // Navigate to a data-heavy page
    await page.goto('http://localhost:5173/orders');
    
    // Check for loading indicators
    const loadingIndicators = {
      spinner: await page.locator('[class*="spin"], [class*="load"], [role="progressbar"]').isVisible(),
      skeleton: await page.locator('[class*="skeleton"]').count(),
      shimmer: await page.locator('[class*="shimmer"]').count()
    };
    
    console.log('Loading Indicators:', loadingIndicators);
    console.log('API Requests Made:', requests.length);
    
    // Wait for content to load
    await page.waitForTimeout(2000);
    await annotatedScreenshot(page, 'loaded-content', 'Fully loaded page');
  });

  test('🌏 Traditional Chinese Localization', async ({ page }) => {
    console.log('🌏 Checking Traditional Chinese localization...');
    
    await page.goto('http://localhost:5173/dashboard');
    await page.waitForTimeout(1000);
    
    // Extract all visible text
    const textContent = await page.evaluate(() => {
      const walker = document.createTreeWalker(
        document.body,
        NodeFilter.SHOW_TEXT,
        null,
        false
      );
      
      const texts: string[] = [];
      let node;
      while (node = walker.nextNode()) {
        const text = node.textContent?.trim();
        if (text && text.length > 1) {
          texts.push(text);
        }
      }
      return texts;
    });
    
    // Check for Traditional Chinese characters
    const chineseTexts = textContent.filter(text => /[\u4e00-\u9fa5]/.test(text));
    const englishTexts = textContent.filter(text => /^[A-Za-z\s]+$/.test(text) && text.length > 3);
    
    console.log(`Traditional Chinese texts found: ${chineseTexts.length}`);
    console.log(`English texts found: ${englishTexts.length}`);
    console.log('Sample Chinese texts:', chineseTexts.slice(0, 5));
    
    // Check specific UI elements for proper localization
    const localizationChecks = {
      submitButton: await page.locator('button:has-text("提交"), button:has-text("確認"), button:has-text("儲存")').count(),
      cancelButton: await page.locator('button:has-text("取消"), button:has-text("返回")').count(),
      dateFormat: await page.locator('text=/\\d{3,4}年\\d{1,2}月\\d{1,2}日/').count()
    };
    
    console.log('Localization Elements:', localizationChecks);
  });
});