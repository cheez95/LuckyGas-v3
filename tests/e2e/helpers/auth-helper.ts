import { Page, BrowserContext } from '@playwright/test';
import { LoginPage } from '../pages/LoginPage';
import { TestUsers } from '../fixtures/test-data';

export class AuthHelper {
  /**
   * Perform login and save authentication state
   */
  static async login(page: Page, user: keyof typeof TestUsers = 'officeStaff'): Promise<void> {
    const loginPage = new LoginPage(page);
    await loginPage.goto();
    
    // Clear any existing auth state
    await page.context().clearCookies();
    await page.evaluate(() => {
      localStorage.clear();
      sessionStorage.clear();
    });
    
    // Wait for page to be ready
    await page.waitForLoadState('networkidle');
    
    // Perform login with retry
    let retries = 3;
    while (retries > 0) {
      try {
        await loginPage.login(TestUsers[user].email, TestUsers[user].password);
        
        // Wait for successful navigation
        await page.waitForURL(url => !url.includes('/login'), { timeout: 10000 });
        
        // Verify we're authenticated
        const token = await page.evaluate(() => localStorage.getItem('access_token'));
        if (token) {
          console.log(`✅ Successfully logged in as ${user}`);
          break;
        }
      } catch (error) {
        retries--;
        if (retries === 0) throw error;
        console.log(`⚠️ Login attempt failed, retrying... (${retries} attempts left)`);
        await page.waitForTimeout(1000);
      }
    }
  }

  /**
   * Save authentication state to reuse across tests
   */
  static async saveAuthState(context: BrowserContext, fileName: string): Promise<void> {
    await context.storageState({ path: `./auth/${fileName}.json` });
  }

  /**
   * Load authentication state
   */
  static async loadAuthState(context: BrowserContext, fileName: string): Promise<void> {
    try {
      await context.addInitScript({
        path: `./auth/${fileName}.json`
      });
    } catch (error) {
      console.log('No saved auth state found, will perform fresh login');
    }
  }

  /**
   * Ensure user remains authenticated throughout the test
   */
  static async ensureAuthenticated(page: Page): Promise<void> {
    const token = await page.evaluate(() => localStorage.getItem('access_token'));
    if (!token) {
      console.log('⚠️ Token missing, re-authenticating...');
      await this.login(page);
    }
  }

  /**
   * Handle authentication errors and retry
   */
  static async handleAuthError(page: Page, error: any): Promise<void> {
    if (error.message?.includes('401') || error.message?.includes('Unauthorized')) {
      console.log('🔄 Authentication error detected, attempting to re-login...');
      await this.login(page);
    } else {
      throw error;
    }
  }
}