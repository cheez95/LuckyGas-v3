import { test, expect } from '@playwright/test';

test.describe('Customer List Display Test', () => {
  test('Check how many customers show in the UI', async ({ page }) => {
    console.log('🔍 Testing customer list display...');
    
    // Navigate to the local application (where we have the imported data)
    await page.goto('http://localhost:5173');
    
    // Wait for page to load
    await page.waitForLoadState('networkidle');
    await page.waitForTimeout(2000);
    
    // Check if we need to login
    const loginButton = page.locator('button:has-text("登入"), button:has-text("Login")');
    if (await loginButton.isVisible()) {
      console.log('📝 Login required, attempting to login...');
      
      // Fill in the login form
      await page.fill('input[type="email"], input[name="username"], input[name="email"], input[placeholder*="用戶"]', 'admin@luckygas.com');
      await page.fill('input[type="password"], input[name="password"], input[placeholder*="密碼"]', 'admin-password-2025');
      await loginButton.click();
      
      // Wait for navigation after login
      await page.waitForLoadState('networkidle');
      await page.waitForTimeout(3000);
    }
    
    // Navigate to customers page
    console.log('🚀 Navigating to customers page...');
    
    // Try different selectors for the customers link
    const customerLinkSelectors = [
      'a:has-text("客戶")',
      'a:has-text("Customers")',
      '[href*="customers"]',
      'nav a:has-text("客戶")',
      '.menu-item:has-text("客戶")',
      'button:has-text("客戶")'
    ];
    
    let found = false;
    for (const selector of customerLinkSelectors) {
      const element = page.locator(selector).first();
      if (await element.isVisible()) {
        await element.click();
        found = true;
        console.log(`✅ Clicked customer link using selector: ${selector}`);
        break;
      }
    }
    
    if (!found) {
      // Try direct navigation
      console.log('⚠️ Could not find customer link, navigating directly...');
      await page.goto('http://localhost:5173/customers');
    }
    
    // Wait for customer list to load
    await page.waitForLoadState('networkidle');
    await page.waitForTimeout(3000); // Give extra time for data to load
    
    // Count customers in different possible containers
    const customerSelectors = [
      'tr[data-row], tbody tr',  // Table rows
      '.customer-row',            // Custom customer row class
      '.ant-table-row',          // Ant Design table
      '.MuiTableRow-root',       // Material UI table
      '[role="row"]',            // Accessible table rows
      '.customer-item',          // List items
      '.card.customer',          // Card layout
    ];
    
    let customerCount = 0;
    let selector = '';
    
    for (const sel of customerSelectors) {
      const elements = await page.locator(sel).count();
      if (elements > customerCount) {
        customerCount = elements;
        selector = sel;
      }
    }
    
    console.log(`\n📊 Customer Count Results:`);
    console.log(`   Found ${customerCount} customers using selector: ${selector}`);
    
    // Check if there's pagination
    const paginationSelectors = [
      '.pagination',
      '.ant-pagination',
      '.MuiPagination-root',
      '[role="navigation"]',
      '.page-numbers'
    ];
    
    let hasPagination = false;
    for (const paginationSel of paginationSelectors) {
      if (await page.locator(paginationSel).isVisible()) {
        hasPagination = true;
        console.log(`   ⚠️ Pagination detected: ${paginationSel}`);
        
        // Try to get total count from pagination text
        const totalTextSelectors = [
          '.ant-pagination-total-text',
          '.total-count',
          'text=/共.*條/',
          'text=/Total.*items/',
          'text=/[0-9]+ of [0-9]+/'
        ];
        
        for (const textSel of totalTextSelectors) {
          const textElement = page.locator(textSel).first();
          if (await textElement.isVisible()) {
            const text = await textElement.textContent();
            console.log(`   Total count text: ${text}`);
            
            // Extract number from text
            const match = text?.match(/(\d+)/g);
            if (match && match.length > 0) {
              const totalCount = Math.max(...match.map(Number));
              console.log(`   📈 Total customers from pagination: ${totalCount}`);
            }
          }
        }
        break;
      }
    }
    
    // Check for "Load More" button
    const loadMoreSelectors = [
      'button:has-text("載入更多")',
      'button:has-text("Load More")',
      'button:has-text("Show More")',
      '.load-more-button'
    ];
    
    for (const loadMoreSel of loadMoreSelectors) {
      const loadMoreBtn = page.locator(loadMoreSel).first();
      if (await loadMoreBtn.isVisible()) {
        console.log(`   ⚠️ Load More button found: ${loadMoreSel}`);
        
        // Click load more until no more data
        let clickCount = 0;
        while (await loadMoreBtn.isVisible() && clickCount < 20) {
          await loadMoreBtn.click();
          await page.waitForTimeout(1000);
          clickCount++;
        }
        
        // Recount after loading all
        customerCount = await page.locator(selector).count();
        console.log(`   📈 After loading more: ${customerCount} customers`);
      }
    }
    
    // Check page size selector
    const pageSizeSelectors = [
      '.ant-pagination-options-size-changer',
      '.page-size-selector',
      'select[aria-label*="page size"]'
    ];
    
    for (const pageSizeSel of pageSizeSelectors) {
      const pageSizeElement = page.locator(pageSizeSel).first();
      if (await pageSizeElement.isVisible()) {
        console.log(`   📄 Page size selector found: ${pageSizeSel}`);
        
        // Try to select maximum page size
        await pageSizeElement.click();
        
        // Look for maximum option
        const maxOptions = ['100', '500', '1000', 'All', '全部'];
        for (const option of maxOptions) {
          const optionElement = page.locator(`text="${option}"`).first();
          if (await optionElement.isVisible()) {
            await optionElement.click();
            console.log(`   Selected page size: ${option}`);
            await page.waitForTimeout(2000);
            
            // Recount
            customerCount = await page.locator(selector).count();
            console.log(`   📈 After changing page size: ${customerCount} customers`);
            break;
          }
        }
      }
    }
    
    // Final summary
    console.log('\n' + '='.repeat(50));
    console.log('📊 FINAL RESULTS:');
    console.log(`   Customers displayed: ${customerCount}`);
    console.log(`   Expected: 1270`);
    console.log(`   Difference: ${1270 - customerCount}`);
    
    if (customerCount < 1270) {
      console.log('\n⚠️ ISSUE IDENTIFIED:');
      if (hasPagination) {
        console.log('   - Pagination is limiting the display');
        console.log('   - Need to either:');
        console.log('     1. Implement infinite scroll');
        console.log('     2. Increase default page size');
        console.log('     3. Add "Show All" option');
      } else {
        console.log('   - API might be limiting results');
        console.log('   - Check backend pagination settings');
      }
    } else if (customerCount >= 1270) {
      console.log('\n✅ SUCCESS! All customers are displayed!');
    }
    
    // Take screenshot for evidence
    await page.screenshot({ 
      path: 'customer-list-screenshot.png',
      fullPage: true 
    });
    console.log('\n📸 Screenshot saved as customer-list-screenshot.png');
    
    // Assertion for test result
    expect(customerCount).toBeGreaterThanOrEqual(1267);
  });
});