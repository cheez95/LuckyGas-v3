import { Page, Locator } from '@playwright/test';

export class BasePage {
  readonly page: Page;

  constructor(page: Page) {
    this.page = page;
  }

  async goto(path: string = '') {
    await this.page.goto(path);
  }

  async waitForLoadComplete() {
    await this.page.waitForLoadState('networkidle');
  }

  async getTitle(): Promise<string> {
    return await this.page.title();
  }

  async takeScreenshot(name: string) {
    await this.page.screenshot({ path: `screenshots/${name}.png`, fullPage: true });
  }

  async waitForElement(selector: string, timeout: number = 30000) {
    await this.page.waitForSelector(selector, { timeout });
  }

  async clickElement(selector: string) {
    await this.page.click(selector);
  }

  async fillInput(selector: string, value: string) {
    await this.page.fill(selector, value);
  }

  async getElementText(selector: string): Promise<string> {
    return await this.page.textContent(selector) || '';
  }

  async isElementVisible(selector: string): Promise<boolean> {
    return await this.page.isVisible(selector);
  }

  async waitForNavigation(url?: string | RegExp) {
    if (url) {
      await this.page.waitForURL(url);
    } else {
      await this.page.waitForNavigation();
    }
  }

  async getErrorMessage(): Promise<string | null> {
    const errorAlert = this.page.locator('.ant-alert-error');
    if (await errorAlert.isVisible()) {
      return await errorAlert.textContent();
    }
    return null;
  }

  async closeModal() {
    const closeButton = this.page.locator('.ant-modal-close');
    if (await closeButton.isVisible()) {
      await closeButton.click();
    }
  }

  async selectDropdownOption(dropdownSelector: string, optionText: string) {
    await this.page.click(dropdownSelector);
    await this.page.click(`.ant-select-dropdown .ant-select-item[title="${optionText}"]`);
  }

  async getTableRowCount(): Promise<number> {
    const rows = await this.page.locator('.ant-table-tbody tr').count();
    return rows;
  }

  async waitForToast(message?: string) {
    const toastLocator = message 
      ? this.page.locator(`.ant-message-notice:has-text("${message}")`)
      : this.page.locator('.ant-message-notice');
    
    await toastLocator.waitFor({ state: 'visible' });
    return await toastLocator.textContent();
  }

  async checkMobileResponsive() {
    // Check if viewport is mobile
    const viewport = this.page.viewportSize();
    return viewport && viewport.width < 768;
  }

  async checkLocalization(key: string, expectedText: string) {
    const element = this.page.getByText(expectedText);
    return await element.isVisible();
  }
}