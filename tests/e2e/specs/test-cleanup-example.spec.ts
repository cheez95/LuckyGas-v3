import { test, cleanupTestData } from '../fixtures/test-helpers';
import { CustomerPage } from '../pages/CustomerPage';
import { TestCustomers } from '../fixtures/test-data';

/**
 * Example test demonstrating test data cleanup functionality
 */
test.describe('Test Data Cleanup Example', () => {
  let customerPage: CustomerPage;
  const TEST_PREFIX = 'E2E_TEST_';
  
  test.beforeEach(async ({ page }) => {
    customerPage = new CustomerPage(page);
  });
  
  test.afterEach(async ({ page }) => {
    // Clean up test data after each test
    await cleanupTestData(page, TEST_PREFIX);
  });
  
  test('should create and clean up test customer', async ({ page }) => {
    // Create a test customer with specific prefix
    const testCustomer = {
      ...TestCustomers.residential,
      name: `${TEST_PREFIX}Customer_${Date.now()}`,
      notes: `test_id:cleanup_test_${Date.now()}`,
    };
    
    // Navigate to customers page
    await customerPage.goto();
    
    // Create the customer
    await customerPage.createNewCustomer(testCustomer);
    
    // Verify customer was created
    await customerPage.verifyCustomerInList(testCustomer);
    
    // The cleanup will happen in afterEach hook
  });
  
  test('should handle bulk test data creation and cleanup', async ({ page }) => {
    await customerPage.goto();
    
    // Create multiple test customers
    for (let i = 1; i <= 3; i++) {
      const testCustomer = {
        ...TestCustomers.commercial,
        name: `${TEST_PREFIX}BulkCustomer_${i}_${Date.now()}`,
        phone: `091234567${i}`,
        notes: `test_id:bulk_test_${Date.now()}`,
      };
      
      await customerPage.createNewCustomer(testCustomer);
    }
    
    // Get customer count before cleanup
    const countBefore = await customerPage.getCustomerCount();
    console.log(`Customers before cleanup: ${countBefore}`);
    
    // Manual cleanup to demonstrate
    await cleanupTestData(page, TEST_PREFIX);
    
    // Refresh page to see results
    await page.reload();
    await customerPage.waitForPageLoad();
    
    // Get customer count after cleanup
    const countAfter = await customerPage.getCustomerCount();
    console.log(`Customers after cleanup: ${countAfter}`);
    
    // Verify cleanup worked
    test.expect(countAfter).toBeLessThan(countBefore);
  });
});

/**
 * Best Practices for Test Data Cleanup:
 * 
 * 1. Use consistent prefixes for test data (e.g., E2E_TEST_, PERF_TEST_)
 * 2. Add test_id to notes/metadata fields for precise cleanup
 * 3. Clean up in afterEach hooks to ensure isolation
 * 4. Use try/catch in cleanup to prevent test failures
 * 5. Log cleanup results for debugging
 * 6. Consider using global setup/teardown for suite-wide cleanup
 */