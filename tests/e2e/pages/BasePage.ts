import { Page } from '@playwright/test';

export class BasePage {
  readonly page: Page;

  constructor(page: Page) {
    this.page = page;
  }

  async waitForPageLoad() {
    await this.page.waitForLoadState('networkidle');
  }

  async takeScreenshot(name: string) {
    await this.page.screenshot({ path: `test-results/${name}.png`, fullPage: true });
  }

  async logout() {
    // Click user menu
    const userMenu = this.page.locator('.ant-dropdown-trigger, [data-testid="user-menu"]').first();
    await userMenu.click();
    
    // Click logout
    await this.page.locator('text=/logout|登出|Logout/i').click();
    await this.waitForPageLoad();
  }

  async expectNotification(type: 'success' | 'error' | 'warning' | 'info') {
    const notificationSelector = `.ant-message-${type}, .ant-notification-${type}`;
    await this.page.locator(notificationSelector).waitFor({ state: 'visible', timeout: 5000 });
  }

  async closeNotifications() {
    await this.page.locator('.ant-message-notice-close, .ant-notification-close').click({ force: true });
  }

  async waitForApiResponse(url: string | RegExp) {
    return this.page.waitForResponse(response => 
      (typeof url === 'string' ? response.url().includes(url) : url.test(response.url())) && 
      response.status() === 200
    );
  }
}