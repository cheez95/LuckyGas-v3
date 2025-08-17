import { Page, Locator, expect } from '@playwright/test';

/**
 * Order Management Page Object Model
 * Handles all interactions with the Order Management page
 */
export class OrderManagementPage {
  readonly page: Page;
  readonly pageTitle: Locator;
  readonly searchInput: Locator;
  readonly searchButton: Locator;
  readonly createOrderButton: Locator;
  readonly ordersTable: Locator;
  readonly orderRows: Locator;
  readonly statisticsCards: Locator;
  readonly loadingSpinner: Locator;
  readonly errorBoundary: Locator;
  readonly customerSearch: Locator;
  readonly exportButton: Locator;
  readonly filterButtons: Locator;
  readonly dateRangePicker: Locator;
  readonly statusFilter: Locator;
  readonly timeline: Locator;
  
  constructor(page: Page) {
    this.page = page;
    this.pageTitle = page.locator('h1:has-text("訂單管理"), h2:has-text("訂單管理")');
    this.searchInput = page.locator('input[placeholder*="搜尋"], input[placeholder*="搜索"]');
    this.searchButton = page.locator('button:has-text("搜尋"), button:has-text("搜索")');
    this.createOrderButton = page.locator('button:has-text("新增訂單"), button:has-text("建立訂單")');
    this.ordersTable = page.locator('.ant-table, table');
    this.orderRows = page.locator('.ant-table-tbody tr, tbody tr');
    this.statisticsCards = page.locator('.ant-card, .statistics-card, .stat-card');
    this.loadingSpinner = page.locator('.ant-spin, .loading-spinner');
    this.errorBoundary = page.locator('.error-boundary, .error-container, .ant-alert-error');
    this.customerSearch = page.locator('input[placeholder*="客戶"]');
    this.exportButton = page.locator('button:has-text("匯出"), button:has-text("導出")');
    this.filterButtons = page.locator('.ant-radio-button, .filter-button');
    this.dateRangePicker = page.locator('.ant-picker-range, .date-range-picker');
    this.statusFilter = page.locator('.ant-select, select').filter({ hasText: /狀態|status/i });
    this.timeline = page.locator('.ant-timeline, .order-timeline');
  }

  async goto() {
    await this.page.goto('/#/office/orders');
    await this.page.waitForLoadState('networkidle');
    // Wait for the page to be ready
    await this.waitForPageLoad();
  }

  async waitForPageLoad() {
    try {
      // Wait for either the table or an error to appear
      await Promise.race([
        this.ordersTable.waitFor({ state: 'visible', timeout: 15000 }),
        this.errorBoundary.waitFor({ state: 'visible', timeout: 15000 })
      ]);
      
      // Wait for loading to complete
      await this.waitForLoadingComplete();
    } catch (error) {
      console.log('Page load timeout:', error);
    }
  }

  async waitForLoadingComplete() {
    try {
      // Wait for any loading spinners to disappear
      await this.loadingSpinner.waitFor({ state: 'hidden', timeout: 10000 }).catch(() => {});
    } catch {
      // Loading might not be visible, continue
    }
  }

  async searchOrders(query: string) {
    await this.searchInput.waitFor({ state: 'visible' });
    await this.searchInput.clear();
    await this.searchInput.fill(query);
    await this.searchButton.click();
    await this.waitForLoadingComplete();
  }

  async searchCustomers(query: string) {
    if (await this.customerSearch.isVisible()) {
      await this.customerSearch.clear();
      await this.customerSearch.fill(query);
      await this.page.keyboard.press('Enter');
      await this.waitForLoadingComplete();
    }
  }

  async getOrderCount(): Promise<number> {
    try {
      await this.orderRows.first().waitFor({ state: 'visible', timeout: 5000 });
      return await this.orderRows.count();
    } catch {
      return 0;
    }
  }

  async getStatisticsValue(statName: string): Promise<string | null> {
    try {
      const stat = this.statisticsCards.filter({ hasText: statName });
      await stat.waitFor({ state: 'visible', timeout: 5000 });
      return await stat.textContent();
    } catch {
      return null;
    }
  }

  async isErrorDisplayed(): Promise<boolean> {
    return await this.errorBoundary.isVisible();
  }

  async getErrorMessage(): Promise<string | null> {
    if (await this.isErrorDisplayed()) {
      return await this.errorBoundary.textContent();
    }
    return null;
  }

  async clickCreateOrder() {
    await this.createOrderButton.waitFor({ state: 'visible' });
    await this.createOrderButton.click();
  }

  async exportOrders() {
    if (await this.exportButton.isVisible()) {
      await this.exportButton.click();
      // Wait for download to start
      await this.page.waitForTimeout(2000);
    }
  }

  async filterByStatus(status: string) {
    if (await this.statusFilter.isVisible()) {
      await this.statusFilter.click();
      await this.page.locator(`[title="${status}"]`).click();
      await this.waitForLoadingComplete();
    }
  }

  async selectDateRange(startDate: string, endDate: string) {
    if (await this.dateRangePicker.isVisible()) {
      await this.dateRangePicker.click();
      // Implementation depends on the date picker component
      await this.page.waitForTimeout(1000);
    }
  }

  async checkForJavaScriptErrors(): Promise<string[]> {
    const errors: string[] = [];
    
    // Listen for console errors
    this.page.on('console', msg => {
      if (msg.type() === 'error') {
        errors.push(msg.text());
      }
    });
    
    // Listen for page errors
    this.page.on('pageerror', error => {
      errors.push(error.message);
    });
    
    // Wait a bit to collect any errors
    await this.page.waitForTimeout(2000);
    
    return errors;
  }

  async checkForMapErrors(): Promise<boolean> {
    const errors = await this.checkForJavaScriptErrors();
    return errors.some(error => 
      error.includes('map is not a function') || 
      error.includes('Cannot read properties of undefined')
    );
  }

  async isWebSocketConnected(): Promise<boolean> {
    // Check for WebSocket connection indicator
    const wsIndicator = this.page.locator('.websocket-status, .ws-status, .connection-status');
    if (await wsIndicator.isVisible()) {
      const text = await wsIndicator.textContent();
      return text?.includes('連線') || text?.includes('已連接') || text?.includes('connected') || false;
    }
    return false;
  }

  async getTimelineEvents(): Promise<string[]> {
    if (await this.timeline.isVisible()) {
      const events = await this.timeline.locator('.ant-timeline-item').allTextContents();
      return events;
    }
    return [];
  }
}