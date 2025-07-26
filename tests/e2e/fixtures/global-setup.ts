import { chromium, FullConfig } from '@playwright/test';
import { LoginPage } from '../pages/LoginPage';
import { TestUsers } from './test-data';
import { setupAuthInterceptor } from './auth-interceptor';
import path from 'path';
import fs from 'fs';

/**
 * Global setup to create authenticated states for different user roles
 * This runs once before all tests and saves the auth state
 */
async function globalSetup(config: FullConfig) {
  const { baseURL } = config.projects[0].use;
  const storageDir = path.join(__dirname, '../.auth');
  
  // Create auth directory if it doesn't exist
  if (!fs.existsSync(storageDir)) {
    fs.mkdirSync(storageDir, { recursive: true });
  }

  // User roles to authenticate
  const userRoles = [
    { role: 'officeStaff', user: TestUsers.officeStaff },
    { role: 'manager', user: TestUsers.manager },
    { role: 'superAdmin', user: TestUsers.superAdmin },
    { role: 'driver', user: TestUsers.driver },
    { role: 'customer', user: TestUsers.customer },
  ];

  console.log('\n🔐 Setting up authentication for all user roles...');

  for (const { role, user } of userRoles) {
    console.log(`\n  Authenticating ${role}...`);
    
    const browser = await chromium.launch();
    const context = await browser.newContext();
    const page = await context.newPage();
    
    try {
      // Perform login
      const loginPage = new LoginPage(page);
      // Set base URL context for the page
      page.context().setDefaultNavigationTimeout(30000);
      await loginPage.goto();
      await loginPage.login(user.email, user.password);
      
      // Set up auth interceptor to ensure API requests have tokens
      await setupAuthInterceptor(page);
      
      // Wait for successful login
      await page.waitForFunction(
        () => {
          const token = localStorage.getItem('access_token');
          return token !== null && token !== undefined && token !== '';
        },
        { timeout: 30000 }
      );
      
      // Verify we're no longer on login page and check for valid redirects
      const currentUrl = page.url();
      if (currentUrl.includes('/login')) {
        throw new Error(`Login failed for ${role} - still on login page`);
      }
      
      // Verify based on role with relaxed validation
      if (role === 'driver' && !currentUrl.includes('/driver')) {
        console.warn(`  ⚠️ Driver role expected /driver, but got ${currentUrl}`);
      }
      if (role === 'customer' && !currentUrl.includes('/customer') && !currentUrl.includes('/customer-portal')) {
        console.warn(`  ⚠️ Customer role expected /customer or /customer-portal, but got ${currentUrl}`);
      }
      
      // Save storage state
      const statePath = path.join(storageDir, `${role}.json`);
      await context.storageState({ path: statePath });
      console.log(`  ✅ ${role} authenticated successfully`);
      
    } catch (error) {
      console.error(`  ❌ Failed to authenticate ${role}:`, error);
      // Don't fail the entire setup if one role fails
    } finally {
      await context.close();
      await browser.close();
    }
  }
  
  console.log('\n✅ Global setup completed\n');
}

export default globalSetup;