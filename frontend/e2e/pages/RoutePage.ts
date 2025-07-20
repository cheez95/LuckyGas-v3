import { Page } from '@playwright/test';
import { BasePage } from './BasePage';

export class RoutePage extends BasePage {
  constructor(page: Page) {
    super(page);
  }

  // Locators
  get pageTitle() {
    return this.page.locator('h2.ant-typography').filter({ hasText: '路線規劃' });
  }

  get optimizeRouteButton() {
    return this.page.locator('button').filter({ hasText: '優化路線' });
  }

  get createRouteButton() {
    return this.page.locator('button').filter({ hasText: '新增路線' });
  }

  get datePicker() {
    return this.page.locator('.ant-picker').first();
  }

  get driverSelect() {
    return this.page.locator('.ant-select').filter({ hasText: '選擇司機' });
  }

  get vehicleSelect() {
    return this.page.locator('.ant-select').filter({ hasText: '選擇車輛' });
  }

  get routeList() {
    return this.page.locator('.route-list');
  }

  get routeCards() {
    return this.page.locator('.route-card');
  }

  get mapContainer() {
    return this.page.locator('#route-map');
  }

  get stopsList() {
    return this.page.locator('.stops-list');
  }

  get stopItems() {
    return this.page.locator('.stop-item');
  }

  // Modal locators
  get modalTitle() {
    return this.page.locator('.ant-modal-title');
  }

  get modalConfirmButton() {
    return this.page.locator('.ant-modal-footer button.ant-btn-primary');
  }

  get modalCancelButton() {
    return this.page.locator('.ant-modal-footer button').filter({ hasText: '取消' });
  }

  // Route form fields
  get routeNameInput() {
    return this.page.locator('#route_name');
  }

  get routeDatePicker() {
    return this.page.locator('#route_date');
  }

  get routeDriverSelect() {
    return this.page.locator('#route_driverId');
  }

  get routeVehicleSelect() {
    return this.page.locator('#route_vehicleId');
  }

  get startTimeInput() {
    return this.page.locator('#route_startTime');
  }

  // Statistics
  get totalStopsText() {
    return this.page.locator('.stat-total-stops');
  }

  get totalDistanceText() {
    return this.page.locator('.stat-total-distance');
  }

  get estimatedDurationText() {
    return this.page.locator('.stat-estimated-duration');
  }

  // Actions
  async navigateToRoutes() {
    await this.goto('/office/routes');
    await this.waitForLoadComplete();
  }

  async selectDate(date: string) {
    await this.datePicker.click();
    await this.page.locator('.ant-picker-input input').fill(date);
    await this.page.keyboard.press('Enter');
    await this.waitForLoadComplete();
  }

  async filterByDriver(driverName: string) {
    await this.driverSelect.click();
    await this.page.locator(`.ant-select-dropdown .ant-select-item[title="${driverName}"]`).click();
    await this.waitForLoadComplete();
  }

  async filterByVehicle(vehicleName: string) {
    await this.vehicleSelect.click();
    await this.page.locator(`.ant-select-dropdown .ant-select-item[title="${vehicleName}"]`).click();
    await this.waitForLoadComplete();
  }

  async clickOptimizeRoute() {
    await this.optimizeRouteButton.click();
    await this.waitForToast('路線優化中...');
    // Wait for optimization to complete
    await this.page.waitForTimeout(3000);
    await this.waitForToast('路線優化完成');
  }

  async clickCreateRoute() {
    await this.createRouteButton.click();
    await this.modalTitle.waitFor({ state: 'visible' });
  }

  async fillRouteForm(routeData: {
    name: string;
    date: string;
    driverId: string;
    vehicleId: string;
    startTime?: string;
  }) {
    await this.routeNameInput.fill(routeData.name);
    
    // Set date
    await this.routeDatePicker.click();
    await this.page.locator('.ant-picker-input input').fill(routeData.date);
    await this.page.keyboard.press('Enter');
    
    // Select driver
    await this.selectDropdownOption('#route_driverId', routeData.driverId);
    
    // Select vehicle
    await this.selectDropdownOption('#route_vehicleId', routeData.vehicleId);
    
    if (routeData.startTime) {
      await this.startTimeInput.fill(routeData.startTime);
    }
  }

  async submitRouteForm() {
    await this.modalConfirmButton.click();
    await this.waitForToast('路線建立成功');
  }

  async getRouteCount(): Promise<number> {
    return await this.routeCards.count();
  }

  async selectRoute(index: number) {
    const routeCard = this.routeCards.nth(index);
    await routeCard.click();
    await this.waitForLoadComplete();
  }

  async getRouteData(index: number) {
    const routeCard = this.routeCards.nth(index);
    
    return {
      name: await routeCard.locator('.route-name').textContent() || '',
      driver: await routeCard.locator('.route-driver').textContent() || '',
      vehicle: await routeCard.locator('.route-vehicle').textContent() || '',
      stops: await routeCard.locator('.route-stops').textContent() || '',
      status: await routeCard.locator('.route-status').textContent() || ''
    };
  }

  async getStopCount(): Promise<number> {
    return await this.stopItems.count();
  }

  async reorderStop(fromIndex: number, toIndex: number) {
    const fromStop = this.stopItems.nth(fromIndex);
    const toStop = this.stopItems.nth(toIndex);
    
    // Drag and drop
    await fromStop.dragTo(toStop);
    await this.waitForLoadComplete();
  }

  async removeStop(index: number) {
    const stop = this.stopItems.nth(index);
    const removeButton = stop.locator('button').filter({ hasText: '移除' });
    await removeButton.click();
    
    // Confirm removal
    const confirmButton = this.page.locator('.ant-popconfirm button.ant-btn-primary');
    await confirmButton.click();
    await this.waitForToast();
  }

  async addStopToRoute(customerName: string) {
    const addStopButton = this.page.locator('button').filter({ hasText: '新增站點' });
    await addStopButton.click();
    
    // Search and select customer
    const searchInput = this.page.locator('.ant-modal input[placeholder*="搜尋客戶"]');
    await searchInput.fill(customerName);
    await this.page.keyboard.press('Enter');
    
    // Select from results
    const customerItem = this.page.locator('.customer-search-result').filter({ hasText: customerName });
    await customerItem.click();
    
    // Confirm
    await this.modalConfirmButton.click();
    await this.waitForToast('站點已新增');
  }

  async printRoute() {
    const printButton = this.page.locator('button').filter({ hasText: '列印路線' });
    await printButton.click();
  }

  async startNavigation() {
    const startButton = this.page.locator('button').filter({ hasText: '開始導航' });
    await startButton.click();
    await this.waitForToast('導航已啟動');
  }

  async isMapVisible(): Promise<boolean> {
    return await this.mapContainer.isVisible();
  }

  async getTotalStops(): Promise<string> {
    return await this.totalStopsText.textContent() || '0';
  }

  async getTotalDistance(): Promise<string> {
    return await this.totalDistanceText.textContent() || '0';
  }

  async getEstimatedDuration(): Promise<string> {
    return await this.estimatedDurationText.textContent() || '0';
  }

  async checkChineseLocalization(): Promise<boolean> {
    const expectedTexts = [
      '路線規劃',
      '優化路線',
      '新增路線',
      '選擇司機',
      '選擇車輛',
      '站點',
      '距離',
      '預計時間'
    ];

    for (const text of expectedTexts) {
      const element = this.page.getByText(text);
      if (!await element.first().isVisible()) {
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

    // Check if map and list stack vertically on mobile
    const mapBox = await this.mapContainer.boundingBox();
    const listBox = await this.stopsList.boundingBox();
    
    if (mapBox && listBox) {
      // Map and list should stack vertically on mobile
      return listBox.y > mapBox.y + mapBox.height;
    }
    return false;
  }

  async assignMultipleOrders(orderIds: string[]) {
    const assignButton = this.page.locator('button').filter({ hasText: '批量指派訂單' });
    await assignButton.click();
    
    // Select orders in modal
    for (const orderId of orderIds) {
      const orderCheckbox = this.page.locator(`.order-item input[type="checkbox"][value="${orderId}"]`);
      await orderCheckbox.check();
    }
    
    // Confirm assignment
    await this.modalConfirmButton.click();
    await this.waitForToast(`已指派 ${orderIds.length} 個訂單`);
  }

  async exportRoute(format: 'pdf' | 'excel' = 'pdf') {
    const exportButton = this.page.locator('button').filter({ hasText: '匯出' });
    await exportButton.click();
    
    // Select format
    const formatOption = format === 'pdf' ? '匯出PDF' : '匯出Excel';
    await this.page.locator(`.ant-dropdown-menu-item:has-text("${formatOption}")`).click();
    
    // Wait for download
    const downloadPromise = this.page.waitForEvent('download');
    const download = await downloadPromise;
    
    return download.suggestedFilename();
  }

  async changeRouteStatus(status: string) {
    const statusButton = this.page.locator('button').filter({ hasText: '更改狀態' });
    await statusButton.click();
    
    await this.page.locator(`.ant-dropdown-menu-item:has-text("${status}")`).click();
    await this.waitForToast('狀態已更新');
  }
}