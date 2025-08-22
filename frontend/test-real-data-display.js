import { chromium } from 'playwright';

async function testRealDataDisplay() {
  const browser = await chromium.launch({ headless: false });
  const context = await browser.newContext();
  const page = await context.newPage();

  try {
    console.log('🔍 Testing real data display on production site...');
    
    // Navigate to the app
    await page.goto('https://vast-tributary-466619-m8.web.app');
    console.log('✅ Loaded application');
    
    // Wait for login form
    await page.waitForSelector('input[name="email"]', { timeout: 10000 });
    
    // Login
    await page.fill('input[name="email"]', 'admin@luckygas.com');
    await page.fill('input[name="password"]', 'admin123');
    await page.click('button[type="submit"]');
    console.log('✅ Logged in successfully');
    
    // Wait for dashboard to load
    await page.waitForSelector('[data-testid="page-title"]', { timeout: 10000 });
    console.log('✅ Dashboard loaded');
    
    // Navigate to Customer Management
    await page.click('text=客戶管理');
    await page.waitForSelector('[data-testid="customer-management-page"]', { timeout: 10000 });
    console.log('✅ Customer Management page loaded');
    
    // Check if real customer data is displayed
    await page.waitForSelector('table tbody tr', { timeout: 10000 });
    const customerRows = await page.locator('table tbody tr').count();
    console.log(`📊 Found ${customerRows} customer rows in the table`);
    
    // Get customer stats
    const totalCustomersText = await page.locator('.ant-statistic-content-value').first().textContent();
    console.log(`📊 Total customers stat shows: ${totalCustomersText}`);
    
    // Check pagination info
    const paginationText = await page.locator('.ant-pagination-total-text').textContent().catch(() => 'No pagination found');
    console.log(`📄 Pagination info: ${paginationText}`);
    
    // Navigate to Delivery History
    await page.click('text=配送歷史');
    await page.waitForTimeout(3000); // Wait for page to load
    
    // Check if delivery history data is displayed
    const hasDeliveryTable = await page.locator('table').isVisible().catch(() => false);
    if (hasDeliveryTable) {
      const deliveryRows = await page.locator('table tbody tr').count();
      console.log(`📊 Found ${deliveryRows} delivery history rows`);
    } else {
      console.log('⚠️ No delivery history table found - might be empty or still loading');
    }
    
    // Check delivery stats
    const deliveryStatsCards = await page.locator('.ant-card').count();
    console.log(`📊 Found ${deliveryStatsCards} stats cards on delivery history page`);
    
    // Take a screenshot of the customer page
    await page.click('text=客戶管理');
    await page.waitForTimeout(2000);
    await page.screenshot({ path: 'customer-data-display.png', fullPage: false });
    console.log('📸 Screenshot saved as customer-data-display.png');
    
    // Verify data is real (not mock)
    const firstCustomerName = await page.locator('table tbody tr:first-child td:first-child').textContent().catch(() => '');
    if (firstCustomerName && !firstCustomerName.includes("Customer matching")) {
      console.log('✅ Real customer data is being displayed (not mock data)');
      console.log(`   First customer name: ${firstCustomerName}`);
    } else {
      console.log('⚠️ Might still be showing mock data or no data');
    }
    
    console.log('\n🎉 Test completed successfully!');
    
    // Summary
    console.log('\n📋 Summary:');
    console.log(`- Customer rows displayed: ${customerRows}`);
    console.log(`- Total customers: ${totalCustomersText}`);
    console.log(`- Pagination: ${paginationText}`);
    console.log(`- Data appears to be: ${firstCustomerName && !firstCustomerName.includes("Customer matching") ? 'REAL' : 'MOCK or EMPTY'}`);
    
  } catch (error) {
    console.error('❌ Test failed:', error.message);
    await page.screenshot({ path: 'error-screenshot.png' });
    console.log('📸 Error screenshot saved');
  } finally {
    await browser.close();
  }
}

// Run the test
testRealDataDisplay().catch(console.error);