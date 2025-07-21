import { Page, Locator } from '@playwright/test';
import { BasePage } from './BasePage';

export class DriverMobilePage extends BasePage {
  readonly routesList: Locator;
  readonly currentRoute: Locator;
  readonly deliveryItems: Locator;
  readonly completeDeliveryButton: Locator;
  readonly offlineIndicator: Locator;
  readonly syncStatus: Locator;
  readonly navigationMenu: Locator;
  readonly logoutButton: Locator;

  constructor(page: Page) {
    super(page);
    this.routesList = page.locator('[data-testid="routes-list"]');
    this.currentRoute = page.locator('[data-testid="current-route"]');
    this.deliveryItems = page.locator('[data-testid="delivery-item"]');
    this.completeDeliveryButton = page.locator('[data-testid="complete-delivery-btn"]');
    this.offlineIndicator = page.locator('[data-testid="offline-indicator"]');
    this.syncStatus = page.locator('[data-testid="sync-status"]');
    this.navigationMenu = page.locator('[data-testid="mobile-nav-menu"]');
    this.logoutButton = page.locator('[data-testid="logout-btn"]');
  }

  async navigateToDriverInterface() {
    await this.goto('/driver');
  }

  async selectRoute(routeId: string) {
    await this.routesList.locator(`[data-route-id="${routeId}"]`).click();
    await this.page.waitForSelector('[data-testid="current-route"]');
  }

  async getDeliveryItemCount(): Promise<number> {
    return await this.deliveryItems.count();
  }

  async selectDeliveryItem(index: number) {
    await this.deliveryItems.nth(index).click();
  }

  async clickCompleteDelivery() {
    await this.completeDeliveryButton.click();
  }

  async isOffline(): Promise<boolean> {
    return await this.offlineIndicator.isVisible();
  }

  async getSyncQueueCount(): Promise<number> {
    const syncText = await this.syncStatus.textContent();
    const match = syncText?.match(/\d+/);
    return match ? parseInt(match[0]) : 0;
  }

  async checkMobileResponsiveness(): Promise<boolean> {
    // Check if viewport is mobile size
    const viewportSize = this.page.viewportSize();
    if (!viewportSize || viewportSize.width > 768) {
      return false;
    }

    // Check if mobile-specific elements are visible
    // Mobile menu trigger should be visible on mobile
    const isMobileMenuTriggerVisible = await this.page.locator('[data-testid="mobile-menu-trigger"]').isVisible();
    // Desktop nav should be hidden on mobile
    const isDesktopNavHidden = await this.page.locator('[data-testid="desktop-nav"]').isHidden();

    return isMobileMenuTriggerVisible && isDesktopNavHidden;
  }

  async toggleMobileMenu() {
    await this.page.locator('[data-testid="mobile-menu-trigger"]').click();
  }

  async logout() {
    await this.toggleMobileMenu();
    await this.logoutButton.click();
  }

  async waitForRouteLoad() {
    // Wait for either routes list or no routes message
    await Promise.race([
      this.page.waitForSelector('[data-testid="routes-list"]', {
        state: 'visible',
        timeout: 10000
      }),
      this.page.waitForSelector('text=今日沒有配送路線', {
        state: 'visible',
        timeout: 10000
      })
    ]);
  }

  async checkTouchTargets(): Promise<boolean> {
    // Check if all interactive elements meet minimum touch target size (44x44px)
    const buttons = await this.page.$$('[role="button"], button, a');
    
    for (const button of buttons) {
      const box = await button.boundingBox();
      if (box && (box.width < 44 || box.height < 44)) {
        return false;
      }
    }
    
    return true;
  }

  async simulateOfflineMode() {
    await this.page.context().setOffline(true);
  }

  async simulateOnlineMode() {
    await this.page.context().setOffline(false);
  }

  async checkOfflineQueuePersistence(): Promise<boolean> {
    // Get initial queue count
    const initialCount = await this.getSyncQueueCount();
    
    // Reload page
    await this.page.reload();
    
    // Check if queue count persists
    const afterReloadCount = await this.getSyncQueueCount();
    
    return initialCount === afterReloadCount;
  }
}