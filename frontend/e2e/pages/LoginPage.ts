import { Page } from '@playwright/test';
import { BasePage } from './BasePage';

export class LoginPage extends BasePage {
  constructor(page: Page) {
    super(page);
  }

  // Locators
  get usernameInput() {
    return this.page.locator('input#login_username');
  }

  get passwordInput() {
    return this.page.locator('input#login_password');
  }

  get loginButton() {
    return this.page.locator('button[type="submit"]');
  }

  get errorAlert() {
    return this.page.locator('.ant-alert-error');
  }

  get loginTitle() {
    return this.page.locator('h2.ant-typography');
  }

  // Actions
  async navigateToLogin() {
    await this.goto('/login');
    await this.waitForLoadComplete();
  }

  async fillUsername(username: string) {
    await this.usernameInput.fill(username);
  }

  async fillPassword(password: string) {
    await this.passwordInput.fill(password);
  }

  async clickLogin() {
    await this.loginButton.click();
  }

  async login(username: string, password: string) {
    await this.fillUsername(username);
    await this.fillPassword(password);
    await this.clickLogin();
  }

  async getErrorMessage(): Promise<string | null> {
    if (await this.errorAlert.isVisible()) {
      return await this.errorAlert.textContent();
    }
    return null;
  }

  async isLoginFormVisible(): Promise<boolean> {
    return await this.usernameInput.isVisible() && 
           await this.passwordInput.isVisible() && 
           await this.loginButton.isVisible();
  }

  async waitForLoginSuccess() {
    // Wait for navigation away from login page
    await this.page.waitForURL((url) => !url.pathname.includes('/login'), {
      timeout: 10000
    });
  }

  async checkChineseLocalization() {
    // Check if the login page displays Chinese text
    const titleText = await this.loginTitle.textContent();
    return titleText?.includes('幸福氣瓦斯配送管理系統');
  }

  async checkMobileLayout() {
    const viewport = this.page.viewportSize();
    if (viewport && viewport.width < 768) {
      // Check if login card is properly sized for mobile
      const loginCard = this.page.locator('.login-box');
      const cardBox = await loginCard.boundingBox();
      // On mobile, the card should take most of the width
      return cardBox !== null && cardBox.width >= viewport.width * 0.8;
    }
    return false;
  }
}