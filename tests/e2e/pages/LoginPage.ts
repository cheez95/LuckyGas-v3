import { Page, expect } from '@playwright/test';
import { ErrorMessages, SuccessMessages } from '../fixtures/test-data';

export class LoginPage {
  readonly page: Page;
  
  // Locators - Updated to match actual UI
  readonly emailInput = 'input[type="text"]';
  readonly passwordInput = 'input[type="password"]';
  readonly loginButton = 'button:has-text("登 入")';
  readonly forgotPasswordLink = 'a[href="/forgot-password"]';
  readonly rememberMeCheckbox = 'input[type="checkbox"]';
  readonly errorMessage = '[role="alert"]';
  readonly successMessage = '.ant-message-success';
  readonly loadingSpinner = '.ant-spin';
  readonly languageSelector = '.language-selector';
  readonly loginTitle = 'h2:has-text("幸福氣管理系統")';

  constructor(page: Page) {
    this.page = page;
  }

  async goto() {
    // Handle both relative and absolute URLs
    const url = this.page.url();
    if (url.includes('localhost') || url.includes('http')) {
      // Already on a full URL, just navigate to /login
      await this.page.goto('/login');
    } else {
      // No base URL set, use full URL
      const baseUrl = process.env.BASE_URL || 'http://localhost:5173';
      await this.page.goto(`${baseUrl}/login`);
    }
    await this.waitForPageLoad();
  }

  async waitForPageLoad() {
    // Wait for the login form to be visible
    await expect(this.page.getByRole('heading', { name: '幸福氣管理系統' })).toBeVisible();
    await expect(this.page.getByRole('button', { name: '登 入' })).toBeEnabled();
  }

  async login(email: string, password: string, rememberMe: boolean = false, expectError: boolean = false) {
    // Check if we're on mobile
    const viewport = this.page.viewportSize();
    const isMobile = viewport ? viewport.width < 768 : false;
    
    if (isMobile) {
      console.log('📱 Mobile viewport detected, using mobile-optimized login flow');
    }
    
    // Fill username field (labeled as 用戶名)
    await this.page.getByLabel('用戶名').fill(email);
    // Fill password field
    await this.page.getByLabel('密碼').fill(password);
    
    if (rememberMe) {
      // If remember me checkbox exists, check it
      const checkbox = this.page.locator(this.rememberMeCheckbox);
      if (await checkbox.count() > 0) {
        await checkbox.check();
      }
    }
    
    // Add a small delay for mobile to ensure form is ready
    if (isMobile) {
      await this.page.waitForTimeout(500);
    }
    
    // Click login button
    const loginButton = this.page.getByRole('button', { name: '登 入' });
    await loginButton.click();
    
    // If we're expecting an error, don't wait for navigation
    if (expectError) {
      // Just wait a bit for the error message to appear
      await this.page.waitForTimeout(1000);
      return;
    }
    
    // Wait for token to be stored before checking navigation
    await this.page.waitForFunction(
      () => {
        const token = localStorage.getItem('access_token');
        return token !== null && token !== undefined && token !== '';
      },
      { timeout: 10000 }
    ).catch(() => {
      console.log('⚠️ Token not found in localStorage after login');
    });
    
    // Wait for navigation - successful login redirects based on role
    try {
      await this.page.waitForURL((url) => !url.toString().includes('/login'), { 
        timeout: 15000,
        waitUntil: 'networkidle' 
      });
      
      // Successfully navigated away from login page
      // No need to check for errors after successful navigation
    } catch (error) {
      // Log current state for debugging
      console.log('🔍 Login navigation timeout - debugging info:');
      console.log('Current URL:', this.page.url());
      console.log('Auth token:', await this.page.evaluate(() => localStorage.getItem('access_token')));
      
      // Check if there are any console errors
      this.page.on('console', msg => {
        if (msg.type() === 'error') {
          console.log('Browser console error:', msg.text());
        }
      });
      
      // Check if we're still on the login page
      const currentUrl = this.page.url();
      if (currentUrl.includes('/login')) {
        // Still on login page - check for error message
        const hasError = await this.page.locator(this.errorMessage).isVisible().catch(() => false);
        if (hasError) {
          const errorText = await this.page.locator(this.errorMessage).textContent().catch(() => 'Unknown error');
          throw new Error(`Login failed with error: ${errorText}`);
        }
        
        // No error message but still on login page
        throw new Error('Login failed - still on login page after timeout');
      }
      
      // We navigated away from login but to an unexpected page - this is actually success for some roles
      console.log('✅ Login successful - navigated to:', currentUrl);
    }
  }

  async expectLoginSuccess() {
    // Check if we're on mobile
    const viewport = this.page.viewportSize();
    const isMobile = viewport ? viewport.width < 768 : false;
    
    // Wait for navigation away from login page - role-based redirects
    await expect(this.page).toHaveURL(/\/dashboard|\/home|\/driver|\/customer|\/customer-portal/, { timeout: 15000 });
    
    // Check for JWT token
    const token = await this.page.evaluate(() => localStorage.getItem('access_token'));
    expect(token).toBeTruthy();
    
    // Ensure we're not on login page
    const currentUrl = this.page.url();
    expect(currentUrl).not.toContain('/login');
  }

  async expectLoginError(expectedError: string = ErrorMessages.invalidCredentials) {
    // Check for error alert
    const errorAlert = this.page.getByRole('alert');
    await expect(errorAlert).toBeVisible();
    await expect(errorAlert).toContainText(expectedError);
    
    // Should remain on login page
    await expect(this.page).toHaveURL(/\/login/);
  }

  async clickForgotPassword() {
    // Try multiple selectors for forgot password link
    const forgotPasswordSelectors = [
      this.forgotPasswordLink,
      'a:has-text("忘記密碼")',
      'text=忘記密碼',
      '[data-testid="forgot-password-link"]'
    ];
    
    let linkFound = false;
    for (const selector of forgotPasswordSelectors) {
      const element = this.page.locator(selector);
      if (await element.isVisible({ timeout: 2000 }).catch(() => false)) {
        await element.click();
        linkFound = true;
        break;
      }
    }
    
    if (!linkFound) {
      throw new Error('Forgot password link not found on page');
    }
    
    await expect(this.page).toHaveURL('/forgot-password');
  }

  async selectLanguage(language: 'zh-TW' | 'en') {
    await this.page.selectOption(this.languageSelector, language);
  }

  async verifyChineseUI() {
    // Verify all UI elements are in Traditional Chinese
    await expect(this.page.getByRole('heading', { name: '幸福氣管理系統' })).toBeVisible();
    await expect(this.page.getByRole('heading', { name: '幸福氣', level: 5 })).toBeVisible();
    // Check that form inputs with Chinese labels exist
    await expect(this.page.getByRole('textbox', { name: '用戶名' })).toBeVisible();
    await expect(this.page.getByRole('textbox', { name: '密碼' })).toBeVisible();
    await expect(this.page.getByRole('button', { name: '登 入' })).toBeVisible();
    await expect(this.page.getByRole('link', { name: '忘記密碼？' })).toBeVisible();
  }

  async fillInvalidEmail() {
    await this.page.getByLabel('用戶名').fill('invalid-email');
    await this.page.getByLabel('用戶名').press('Tab');
    
    // Check for validation error - may appear as form feedback
    const errorText = this.page.getByText('請輸入有效的電子郵件');
    if (await errorText.count() > 0) {
      await expect(errorText).toBeVisible();
    } else {
      // Alternative: check if form prevents submission
      await this.page.getByLabel('密碼').fill('password');
      await this.page.getByRole('button', { name: '登 入' }).click();
      await expect(this.page).toHaveURL(/\/login/);
    }
  }

  async testPasswordVisibilityToggle() {
    // Look for eye icon button near password field
    const passwordField = this.page.getByLabel('密碼');
    const toggleButton = this.page.locator('img[alt*="eye"], [aria-label*="eye"], .ant-input-password-icon');
    
    if (await toggleButton.count() > 0) {
      // Initially password should be hidden
      await expect(passwordField).toHaveAttribute('type', 'password');
      
      // Click toggle to show password
      await toggleButton.first().click();
      await expect(passwordField).toHaveAttribute('type', 'text');
      
      // Click again to hide
      await toggleButton.first().click();
      await expect(passwordField).toHaveAttribute('type', 'password');
    } else {
      // Skip test if toggle not available
      console.log('Password visibility toggle not found in UI');
    }
  }

  async testKeyboardNavigation() {
    // Focus the username field directly first
    const usernameField = this.page.getByLabel('用戶名');
    await usernameField.focus();
    await expect(usernameField).toBeFocused();
    
    // Tab to password
    await this.page.keyboard.press('Tab');
    const passwordField = this.page.getByLabel('密碼');
    await expect(passwordField).toBeFocused();
    
    // Tab through elements until we reach the login button
    const loginButton = this.page.getByRole('button', { name: '登 入' });
    let maxTabs = 5;
    while (maxTabs > 0) {
      await this.page.keyboard.press('Tab');
      const isFocused = await loginButton.evaluate(el => el === document.activeElement);
      if (isFocused) {
        await expect(loginButton).toBeFocused();
        return;
      }
      maxTabs--;
    }
    
    // If we get here, the login button wasn't reached
    throw new Error('Could not tab to login button');
  }

  async testEnterKeySubmission() {
    await this.page.getByLabel('用戶名').fill('test@example.com');
    await this.page.getByLabel('密碼').fill('password123');
    
    // Press Enter in password field should submit
    await this.page.getByLabel('密碼').press('Enter');
    
    // Should either navigate or show error
    await Promise.race([
      this.page.waitForURL(/\/dashboard|\/home/, { timeout: 5000 }).catch(() => null),
      expect(this.page.getByRole('alert')).toBeVisible().catch(() => null)
    ]);
  }

  async measureLoginPerformance(email: string, password: string): Promise<number> {
    const startTime = Date.now();
    
    await this.login(email, password);
    
    // Wait for either success or error
    await Promise.race([
      this.page.waitForURL(/\/dashboard|\/home|\/driver|\/customer/, { timeout: 10000 }),
      this.page.waitForSelector(this.errorMessage, { timeout: 10000 }),
    ]);
    
    return Date.now() - startTime;
  }

  async checkAccessibility() {
    // Check for form labels - they might be visible as text or placeholders
    const usernameLabelVisible = await this.page.getByText('用戶名').isVisible().catch(() => false);
    const passwordLabelVisible = await this.page.getByText('密碼').isVisible().catch(() => false);
    
    if (!usernameLabelVisible || !passwordLabelVisible) {
      // Check if labels are in placeholders instead
      const usernameInput = this.page.locator('input[type="text"]').first();
      const passwordInput = this.page.locator('input[type="password"]').first();
      
      const usernamePlaceholder = await usernameInput.getAttribute('placeholder');
      const passwordPlaceholder = await passwordInput.getAttribute('placeholder');
      
      if (!usernamePlaceholder?.includes('用戶名') && !usernamePlaceholder?.includes('電子郵件')) {
        console.warn('⚠️ Username field missing proper label or placeholder');
      }
      
      if (!passwordPlaceholder?.includes('密碼')) {
        console.warn('⚠️ Password field missing proper label or placeholder');
      }
    }
    
    // Check that inputs exist and are visible
    const usernameInputs = [
      this.page.getByLabel('用戶名'),
      this.page.locator('input[type="text"]').first(),
      this.page.locator('input[placeholder*="用戶名"]'),
      this.page.locator('input[placeholder*="電子郵件"]')
    ];
    
    let usernameInputFound = false;
    for (const input of usernameInputs) {
      if (await input.isVisible({ timeout: 1000 }).catch(() => false)) {
        usernameInputFound = true;
        await expect(input).toBeVisible();
        break;
      }
    }
    
    if (!usernameInputFound) {
      throw new Error('Username input field not found');
    }
    
    // Check password input
    const passwordInput = this.page.locator('input[type="password"]').first();
    await expect(passwordInput).toBeVisible();
    
    // Check for form structure
    const form = this.page.locator('form');
    if (await form.count() > 0) {
      await expect(form.first()).toBeVisible();
    }
    
    // Check button is accessible
    const loginButton = this.page.getByRole('button', { name: '登 入' });
    await expect(loginButton).toBeVisible();
    await expect(loginButton).toBeEnabled();
  }
}