import { Page, Locator } from '@playwright/test';

/**
 * Login Page Object Model
 * Handles all interactions with the login page
 */
export class LoginPage {
  readonly page: Page;
  readonly usernameInput: Locator;
  readonly passwordInput: Locator;
  readonly loginButton: Locator;
  readonly errorMessage: Locator;
  readonly forgotPasswordLink: Locator;
  readonly loginForm: Locator;
  readonly loginTitle: Locator;

  constructor(page: Page) {
    this.page = page;
    this.usernameInput = page.locator('input[placeholder*="用戶名"], input[placeholder*="使用者名稱"], input#username');
    this.passwordInput = page.locator('input[type="password"], input#password');
    this.loginButton = page.locator('button[type="submit"]:has-text("登入"), button:has-text("登入")');
    this.errorMessage = page.locator('.ant-message-error, .ant-alert-error, [role="alert"]');
    this.forgotPasswordLink = page.locator('a:has-text("忘記密碼")');
    this.loginForm = page.locator('form, .login-form, .ant-form');
    this.loginTitle = page.locator('h1:has-text("幸福氣"), h2:has-text("登入"), .login-title');
  }

  async goto() {
    await this.page.goto('/');
    await this.page.waitForLoadState('networkidle');
  }

  async login(username: string, password: string) {
    // Wait for login form to be visible
    await this.loginForm.waitFor({ state: 'visible', timeout: 10000 });
    
    // Clear and fill username
    await this.usernameInput.waitFor({ state: 'visible' });
    await this.usernameInput.clear();
    await this.usernameInput.fill(username);
    
    // Clear and fill password
    await this.passwordInput.waitFor({ state: 'visible' });
    await this.passwordInput.clear();
    await this.passwordInput.fill(password);
    
    // Click login button
    await this.loginButton.waitFor({ state: 'visible' });
    await this.loginButton.click();
    
    // Wait for navigation or error
    await Promise.race([
      this.page.waitForURL('**/dashboard/**', { timeout: 10000 }).catch(() => {}),
      this.page.waitForURL('**/#/dashboard/**', { timeout: 10000 }).catch(() => {}),
      this.errorMessage.waitFor({ state: 'visible', timeout: 5000 }).catch(() => {})
    ]);
  }

  async isLoggedIn(): Promise<boolean> {
    try {
      // Check if we're on a dashboard page
      const url = this.page.url();
      return url.includes('dashboard') || url.includes('orders') || url.includes('customers');
    } catch {
      return false;
    }
  }

  async getErrorMessage(): Promise<string | null> {
    try {
      await this.errorMessage.waitFor({ state: 'visible', timeout: 2000 });
      return await this.errorMessage.textContent();
    } catch {
      return null;
    }
  }

  async waitForLoginPage() {
    await this.loginForm.waitFor({ state: 'visible', timeout: 10000 });
  }
}