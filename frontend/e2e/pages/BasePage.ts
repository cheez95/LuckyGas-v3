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

  // Wait for Ant Design animations to complete
  async waitForAntAnimation(timeout: number = 500) {
    // Wait for any active animations to complete
    await this.page.waitForTimeout(timeout);
    // Also wait for any .ant-motion elements to become stable
    try {
      await this.page.waitForFunction(() => {
        const motionElements = document.querySelectorAll('.ant-motion, .ant-zoom, .ant-fade, .ant-slide');
        return motionElements.length === 0;
      }, { timeout: 2000 });
    } catch {
      // If no motion elements found or timeout, continue
    }
  }

  // Wait for specific API call to complete
  async waitForApiCall(urlPattern: string | RegExp, method: string = 'GET', timeout: number = 10000) {
    return await this.page.waitForResponse(
      response => {
        const matches = typeof urlPattern === 'string' 
          ? response.url().includes(urlPattern)
          : urlPattern.test(response.url());
        return matches && response.request().method() === method && response.status() < 400;
      },
      { timeout }
    );
  }

  // Wait for loading indicators to disappear
  async waitForLoadingComplete(timeout: number = 10000) {
    // Wait for Ant Design spin/loading indicators
    const loadingSelectors = [
      '.ant-spin-spinning',
      '.ant-skeleton-active',
      '.ant-table-placeholder .ant-spin',
      '.ant-btn-loading',
      '[class*="loading"]'
    ];

    for (const selector of loadingSelectors) {
      try {
        await this.page.waitForSelector(selector, { state: 'hidden', timeout: timeout / loadingSelectors.length });
      } catch {
        // If selector not found or already hidden, continue
      }
    }
  }

  // Retryable click with better error handling
  async retryableClick(selector: string | Locator, retries: number = 3, delay: number = 500) {
    let lastError: Error | null = null;
    
    for (let i = 0; i < retries; i++) {
      try {
        const element = typeof selector === 'string' ? this.page.locator(selector) : selector;
        
        // Wait for element to be visible and stable
        await element.waitFor({ state: 'visible', timeout: 5000 });
        await element.scrollIntoViewIfNeeded();
        
        // Check if element is covered by other elements
        const isClickable = await element.evaluate(el => {
          const rect = el.getBoundingClientRect();
          const centerX = rect.left + rect.width / 2;
          const centerY = rect.top + rect.height / 2;
          const topElement = document.elementFromPoint(centerX, centerY);
          return el.contains(topElement as Node);
        });

        if (!isClickable && i < retries - 1) {
          await this.page.waitForTimeout(delay);
          continue;
        }

        await element.click();
        return; // Success
      } catch (_error) {
        lastError = error as Error;
        if (i < retries - 1) {
          await this.page.waitForTimeout(delay);
        }
      }
    }
    
    throw new Error(`Failed to click after ${retries} attempts: ${lastError?.message}`);
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