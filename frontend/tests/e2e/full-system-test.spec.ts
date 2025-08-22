import { test, expect, webkit, Browser, BrowserContext, Page } from '@playwright/test';

interface TestResult {
  component: string;
  success: boolean;
  errors: string[];
  screenshot?: string;
}

test.describe('Lucky Gas Full System Test', () => {
  test('Test all tabs and fix issues iteratively', async () => {
    const results: TestResult[] = [];
    const allErrors: string[] = [];
    
    // Launch webkit (Safari engine) with visual debugging
    const browser: Browser = await webkit.launch({ 
      headless: false,  // Show browser for visual debugging
      slowMo: 500      // Slow down for observation
    });
    
    const context: BrowserContext = await browser.newContext();
    const page: Page = await context.newPage();
    
    // Capture ALL console messages
    page.on('console', msg => {
      const text = msg.text();
      if (msg.type() === 'error') {
        allErrors.push(text);
        console.error('❌ ERROR:', text);
      }
      if (text.includes('http://')) {
        console.error('⚠️ HTTP URL FOUND:', text);
        allErrors.push(`HTTP URL: ${text}`);
      }
    });
    
    // Monitor network failures
    page.on('requestfailed', request => {
      const failure = request.failure();
      console.error(`❌ Request Failed: ${request.url()}`, failure?.errorText);
      allErrors.push(`Failed Request: ${request.url()} - ${failure?.errorText}`);
    });
    
    console.log('====================================');
    console.log('🚀 Starting Full System Test');
    console.log('====================================\\n');
    
    try {
      // Test Login
      const loginResult = await testLogin(page);
      results.push(loginResult);
      
      // Test Dashboard
      const dashboardResult = await testDashboard(page);
      results.push(dashboardResult);
      
      // Test Customer Management
      const customerResult = await testCustomerManagement(page);
      results.push(customerResult);
      
      // Test Order Management
      const orderResult = await testOrderManagement(page);
      results.push(orderResult);
      
      // Test Route Planning
      const routeResult = await testRoutePlanning(page);
      results.push(routeResult);
      
      // Test Driver Assignment
      const driverResult = await testDriverAssignment(page);
      results.push(driverResult);
      
      // Test Delivery History
      const deliveryResult = await testDeliveryHistory(page);
      results.push(deliveryResult);
      
      // Test Emergency Dispatch
      const emergencyResult = await testEmergencyDispatch(page);
      results.push(emergencyResult);
      
      // Test Dispatch Dashboard
      const dispatchResult = await testDispatchDashboard(page);
      results.push(dispatchResult);
      
    } finally {
      // Generate summary report
      console.log('\\n====================================');
      console.log('📊 TEST RESULTS SUMMARY');
      console.log('====================================\\n');
      
      let passedCount = 0;
      let failedCount = 0;
      
      for (const result of results) {
        const status = result.success ? '✅' : '❌';
        console.log(`${status} ${result.component}: ${result.success ? 'PASSED' : 'FAILED'}`);
        if (!result.success) {
          console.log(`   Errors: ${result.errors.join(', ')}`);
          failedCount++;
        } else {
          passedCount++;
        }
      }
      
      console.log(`\\n📈 Total: ${passedCount} passed, ${failedCount} failed`);
      console.log(`📝 Total errors collected: ${allErrors.length}`);
      
      if (allErrors.length > 0) {
        console.log('\\n❌ All Errors:');
        allErrors.forEach((err, idx) => {
          console.log(`   ${idx + 1}. ${err}`);
        });
      }
      
      // Keep browser open for manual inspection
      console.log('\\n⏸️ Browser kept open for manual inspection. Press Ctrl+C to close.');
      await page.waitForTimeout(60000); // Keep open for 1 minute
      
      await browser.close();
    }
    
    // Assert all tests passed
    const failedTests = results.filter(r => !r.success);
    expect(failedTests.length, `${failedTests.length} components failed`).toBe(0);
  });
});

// Individual component test functions
async function testLogin(page: Page): Promise<TestResult> {
  console.log('\\n📝 Testing Login...');
  const errors: string[] = [];
  
  try {
    await page.goto('https://vast-tributary-466619-m8.web.app', {
      waitUntil: 'networkidle',
      timeout: 30000
    });
    
    // Wait for login form
    await page.waitForSelector('input[type="email"], input[name="email"]', { timeout: 10000 });
    
    // Fill login form
    await page.fill('input[type="email"], input[name="email"]', 'admin@luckygas.com');
    await page.fill('input[type="password"], input[name="password"]', 'admin123');
    
    // Click login button
    await page.click('button[type="submit"]');
    
    // Wait for navigation
    await page.waitForURL('**/dashboard', { timeout: 10000 });
    
    console.log('   ✅ Login successful');
    
    await page.screenshot({ 
      path: 'screenshots/01-login-success.png',
      fullPage: true 
    });
    
    return { component: 'Login', success: true, errors };
  } catch (error) {
    errors.push(error.message);
    console.error('   ❌ Login failed:', error.message);
    await page.screenshot({ 
      path: 'screenshots/01-login-error.png',
      fullPage: true 
    });
    return { component: 'Login', success: false, errors };
  }
}

async function testDashboard(page: Page): Promise<TestResult> {
  console.log('\\n📊 Testing Dashboard...');
  const errors: string[] = [];
  
  try {
    // Click dashboard if not already there
    if (!page.url().includes('/dashboard')) {
      await page.click('text=儀表板');
      await page.waitForTimeout(2000);
    }
    
    // Check for dashboard content
    await page.waitForSelector('h2:has-text("最小化儀表板")', { timeout: 5000 });
    
    console.log('   ✅ Dashboard loaded');
    
    await page.screenshot({ 
      path: 'screenshots/02-dashboard-success.png',
      fullPage: true 
    });
    
    return { component: 'Dashboard', success: true, errors };
  } catch (error) {
    errors.push(error.message);
    console.error('   ❌ Dashboard failed:', error.message);
    await page.screenshot({ 
      path: 'screenshots/02-dashboard-error.png',
      fullPage: true 
    });
    return { component: 'Dashboard', success: false, errors };
  }
}

async function testCustomerManagement(page: Page): Promise<TestResult> {
  console.log('\\n👥 Testing Customer Management...');
  const errors: string[] = [];
  
  try {
    // Click Customer Management
    await page.click('text=客戶管理');
    await page.waitForTimeout(3000);
    
    // Check for error or success
    const hasError = await page.locator('.ant-alert-error, text=載入失敗').isVisible();
    
    if (hasError) {
      errors.push('Component failed to load - MIME type or module error');
      console.error('   ❌ CustomerManagement failed to load');
      
      // Check console for specific errors
      const errorText = await page.locator('.ant-alert-error, text=載入失敗').textContent();
      errors.push(`Error message: ${errorText}`);
    } else {
      // Wait for table or content
      await page.waitForSelector('table, .ant-table', { timeout: 5000 });
      
      // Check if data loads
      const rows = await page.locator('tbody tr').count();
      console.log(`   📊 Found ${rows} customer records`);
      
      if (rows === 0) {
        errors.push('No customer data displayed');
        console.log('   ⚠️ No customer data displayed');
      } else {
        console.log('   ✅ Customer Management loaded with data');
      }
    }
    
    await page.screenshot({ 
      path: 'screenshots/03-customer-management.png',
      fullPage: true 
    });
    
    return { 
      component: 'Customer Management', 
      success: errors.length === 0, 
      errors 
    };
  } catch (error) {
    errors.push(error.message);
    console.error('   ❌ Customer Management error:', error.message);
    await page.screenshot({ 
      path: 'screenshots/03-customer-error.png',
      fullPage: true 
    });
    return { component: 'Customer Management', success: false, errors };
  }
}

async function testOrderManagement(page: Page): Promise<TestResult> {
  console.log('\\n📦 Testing Order Management...');
  const errors: string[] = [];
  
  try {
    await page.click('text=訂單管理');
    await page.waitForTimeout(3000);
    
    // Check for error or success
    const hasError = await page.locator('.ant-alert-error, text=載入失敗').isVisible();
    
    if (hasError) {
      errors.push('Component failed to load');
      console.error('   ❌ OrderManagement failed to load');
    } else {
      await page.waitForSelector('table, .ant-table, .order-list', { timeout: 5000 });
      console.log('   ✅ Order Management loaded');
    }
    
    await page.screenshot({ 
      path: 'screenshots/04-order-management.png',
      fullPage: true 
    });
    
    return { 
      component: 'Order Management', 
      success: errors.length === 0, 
      errors 
    };
  } catch (error) {
    errors.push(error.message);
    console.error('   ❌ Order Management error:', error.message);
    return { component: 'Order Management', success: false, errors };
  }
}

async function testRoutePlanning(page: Page): Promise<TestResult> {
  console.log('\\n🗺️ Testing Route Planning...');
  const errors: string[] = [];
  
  try {
    await page.click('text=路線規劃');
    await page.waitForTimeout(3000);
    
    const hasError = await page.locator('.ant-alert-error, text=載入失敗').isVisible();
    
    if (hasError) {
      errors.push('Component failed to load');
      console.error('   ❌ RoutePlanning failed to load');
    } else {
      console.log('   ✅ Route Planning loaded');
    }
    
    await page.screenshot({ 
      path: 'screenshots/05-route-planning.png',
      fullPage: true 
    });
    
    return { 
      component: 'Route Planning', 
      success: errors.length === 0, 
      errors 
    };
  } catch (error) {
    errors.push(error.message);
    console.error('   ❌ Route Planning error:', error.message);
    return { component: 'Route Planning', success: false, errors };
  }
}

async function testDriverAssignment(page: Page): Promise<TestResult> {
  console.log('\\n🚗 Testing Driver Assignment...');
  const errors: string[] = [];
  
  try {
    await page.click('text=司機指派');
    await page.waitForTimeout(3000);
    
    const hasError = await page.locator('.ant-alert-error, text=載入失敗').isVisible();
    
    if (hasError) {
      errors.push('Component failed to load');
      console.error('   ❌ DriverAssignment failed to load');
    } else {
      console.log('   ✅ Driver Assignment loaded');
    }
    
    await page.screenshot({ 
      path: 'screenshots/06-driver-assignment.png',
      fullPage: true 
    });
    
    return { 
      component: 'Driver Assignment', 
      success: errors.length === 0, 
      errors 
    };
  } catch (error) {
    errors.push(error.message);
    console.error('   ❌ Driver Assignment error:', error.message);
    return { component: 'Driver Assignment', success: false, errors };
  }
}

async function testDeliveryHistory(page: Page): Promise<TestResult> {
  console.log('\\n📜 Testing Delivery History...');
  const errors: string[] = [];
  
  try {
    await page.click('text=配送歷史');
    await page.waitForTimeout(3000);
    
    const hasError = await page.locator('.ant-alert-error, text=載入失敗').isVisible();
    
    if (hasError) {
      errors.push('Component failed to load');
      console.error('   ❌ DeliveryHistory failed to load');
    } else {
      console.log('   ✅ Delivery History loaded');
    }
    
    await page.screenshot({ 
      path: 'screenshots/07-delivery-history.png',
      fullPage: true 
    });
    
    return { 
      component: 'Delivery History', 
      success: errors.length === 0, 
      errors 
    };
  } catch (error) {
    errors.push(error.message);
    console.error('   ❌ Delivery History error:', error.message);
    return { component: 'Delivery History', success: false, errors };
  }
}

async function testEmergencyDispatch(page: Page): Promise<TestResult> {
  console.log('\\n🚨 Testing Emergency Dispatch...');
  const errors: string[] = [];
  
  try {
    await page.click('text=緊急派遣');
    await page.waitForTimeout(3000);
    
    const hasError = await page.locator('.ant-alert-error, text=載入失敗').isVisible();
    
    if (hasError) {
      errors.push('Component failed to load');
      console.error('   ❌ EmergencyDispatch failed to load');
    } else {
      console.log('   ✅ Emergency Dispatch loaded');
    }
    
    await page.screenshot({ 
      path: 'screenshots/08-emergency-dispatch.png',
      fullPage: true 
    });
    
    return { 
      component: 'Emergency Dispatch', 
      success: errors.length === 0, 
      errors 
    };
  } catch (error) {
    errors.push(error.message);
    console.error('   ❌ Emergency Dispatch error:', error.message);
    return { component: 'Emergency Dispatch', success: false, errors };
  }
}

async function testDispatchDashboard(page: Page): Promise<TestResult> {
  console.log('\\n📋 Testing Dispatch Dashboard...');
  const errors: string[] = [];
  
  try {
    await page.click('text=派遣看板');
    await page.waitForTimeout(3000);
    
    const hasError = await page.locator('.ant-alert-error, text=載入失敗').isVisible();
    
    if (hasError) {
      errors.push('Component failed to load');
      console.error('   ❌ DispatchDashboard failed to load');
    } else {
      console.log('   ✅ Dispatch Dashboard loaded');
    }
    
    await page.screenshot({ 
      path: 'screenshots/09-dispatch-dashboard.png',
      fullPage: true 
    });
    
    return { 
      component: 'Dispatch Dashboard', 
      success: errors.length === 0, 
      errors 
    };
  } catch (error) {
    errors.push(error.message);
    console.error('   ❌ Dispatch Dashboard error:', error.message);
    return { component: 'Dispatch Dashboard', success: false, errors };
  }
}

// Set test timeout to 2 minutes
test.setTimeout(120000);