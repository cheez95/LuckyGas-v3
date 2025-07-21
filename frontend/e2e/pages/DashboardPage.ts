import { Page } from '@playwright/test';
import { BasePage } from './BasePage';

export class DashboardPage extends BasePage {
  constructor(page: Page) {
    super(page);
  }

  // Locators
  get pageTitle() {
    return this.page.locator('[data-testid="page-title"]');
  }

  get todayOrdersCard() {
    return this.page.locator('.ant-card').filter({ hasText: '今日訂單' });
  }

  get activeCustomersCard() {
    return this.page.locator('.ant-card').filter({ hasText: '活躍客戶' });
  }

  get driversOnRouteCard() {
    return this.page.locator('.ant-card').filter({ hasText: '配送中司機' });
  }

  get todayRevenueCard() {
    return this.page.locator('.ant-card').filter({ hasText: '今日營收' });
  }

  get upcomingFeaturesCard() {
    return this.page.locator('.ant-card').filter({ hasText: '即將實現功能' });
  }

  get navigationMenu() {
    return this.page.locator('.ant-menu');
  }

  get userMenu() {
    return this.page.locator('[data-testid="user-menu-trigger"]');
  }

  get logoutMenuItem() {
    return this.page.locator('.ant-dropdown-menu-item').filter({ hasText: '登出' });
  }

  // Navigation menu items
  get customersMenuItem() {
    return this.page.locator('.ant-menu-item').filter({ hasText: '客戶管理' });
  }

  get ordersMenuItem() {
    return this.page.locator('.ant-menu-item').filter({ hasText: '訂單管理' });
  }

  get deliveriesMenuItem() {
    return this.page.locator('.ant-menu-item').filter({ hasText: '配送管理' });
  }

  get routesMenuItem() {
    return this.page.locator('.ant-menu-item').filter({ hasText: '路線管理' });
  }

  // Actions
  async navigateToDashboard() {
    await this.goto('/dashboard');
    await this.waitForLoadComplete();
  }

  async isDashboardVisible(): Promise<boolean> {
    return await this.pageTitle.isVisible();
  }

  async getStatisticValue(cardName: string): Promise<string> {
    let card;
    switch (cardName) {
      case 'todayOrders':
        card = this.todayOrdersCard;
        break;
      case 'activeCustomers':
        card = this.activeCustomersCard;
        break;
      case 'driversOnRoute':
        card = this.driversOnRouteCard;
        break;
      case 'todayRevenue':
        card = this.todayRevenueCard;
        break;
      default:
        throw new Error(`Unknown card name: ${cardName}`);
    }

    const valueElement = card.locator('.ant-statistic-content-value');
    return await valueElement.textContent() || '';
  }

  async navigateToCustomers() {
    await this.customersMenuItem.click();
    await this.page.waitForURL('**/customers');
  }

  async navigateToOrders() {
    await this.ordersMenuItem.click();
    await this.page.waitForURL('**/orders');
  }

  async navigateToDeliveries() {
    await this.deliveriesMenuItem.click();
    await this.page.waitForURL('**/delivery-history');
  }

  async navigateToRoutes() {
    await this.routesMenuItem.click();
    await this.page.waitForURL('**/routes');
  }

  async logout() {
    // Ensure page is loaded
    await this.page.waitForLoadState('networkidle');
    
    // For mobile, might need to scroll to top to ensure header is visible
    const viewport = this.page.viewportSize();
    if (viewport && viewport.width < 768) {
      await this.page.evaluate(() => window.scrollTo(0, 0));
      await this.page.waitForTimeout(500);
    }
    
    // Click user menu with force option to bypass any overlapping elements
    await this.userMenu.click({ force: true });
    
    // Wait for dropdown to be visible
    await this.logoutMenuItem.waitFor({ state: 'visible', timeout: 5000 });
    
    // Click logout
    await this.logoutMenuItem.click();
    
    // Wait for redirect to login
    await this.page.waitForURL('**/login');
  }

  async checkAllStatisticsLoaded(): Promise<boolean> {
    const cards = [
      this.todayOrdersCard,
      this.activeCustomersCard,
      this.driversOnRouteCard,
      this.todayRevenueCard
    ];

    for (const card of cards) {
      if (!await card.isVisible()) {
        return false;
      }
      const value = await card.locator('.ant-statistic-content-value').textContent();
      if (!value || value === '0') {
        console.log(`Card has no value: ${await card.textContent()}`);
      }
    }
    return true;
  }

  async checkChineseLocalization(): Promise<boolean> {
    // Check if all UI elements are in Traditional Chinese
    const expectedTexts = [
      '儀表板',
      '今日訂單',
      '活躍客戶',
      '配送中司機',
      '今日營收',
      '即將實現功能'
    ];

    for (const text of expectedTexts) {
      const element = this.page.getByText(text);
      if (!await element.isVisible()) {
        console.log(`Missing Chinese text: ${text}`);
        return false;
      }
    }
    return true;
  }

  async checkMobileResponsive(): Promise<boolean> {
    const viewport = this.page.viewportSize();
    if (!viewport || viewport.width >= 768) {
      return false;
    }

    // Check if cards stack vertically on mobile
    const firstCard = await this.todayOrdersCard.boundingBox();
    const secondCard = await this.activeCustomersCard.boundingBox();
    
    if (firstCard && secondCard) {
      // Cards should be stacked vertically, not side by side
      return secondCard.y > firstCard.y + firstCard.height;
    }
    return false;
  }
}