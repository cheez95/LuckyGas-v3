import { Page } from '@playwright/test';
import { BasePage } from './BasePage';

export class OrderPage extends BasePage {
  constructor(page: Page) {
    super(page);
  }

  // Locators
  get pageTitle() {
    return this.page.locator('h2.ant-typography').filter({ hasText: '訂單管理' });
  }

  get createOrderButton() {
    return this.page.locator('button').filter({ hasText: '新增訂單' });
  }

  get searchInput() {
    return this.page.locator('input[placeholder*="搜尋訂單"]');
  }

  get dateRangePicker() {
    return this.page.locator('.ant-picker-range');
  }

  get statusFilter() {
    return this.page.locator('.ant-select').filter({ hasText: '狀態' });
  }

  get orderTable() {
    return this.page.locator('.ant-table');
  }

  get orderRows() {
    return this.page.locator('.ant-table-tbody tr');
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

  // Order form fields
  get customerSelect() {
    return this.page.locator('#order_customerId');
  }

  get scheduledDatePicker() {
    return this.page.locator('#order_scheduledDate');
  }

  get deliveryTimeRangePicker() {
    return this.page.locator('#order_deliveryTime');
  }

  get deliveryAddressInput() {
    return this.page.locator('#order_deliveryAddress');
  }

  get deliveryNotesTextarea() {
    return this.page.locator('#order_deliveryNotes');
  }

  get urgentCheckbox() {
    return this.page.locator('#order_isUrgent');
  }

  get paymentMethodSelect() {
    return this.page.locator('#order_paymentMethod');
  }

  // Product selection
  get addProductButton() {
    return this.page.locator('button').filter({ hasText: '新增產品' });
  }

  get productRows() {
    return this.page.locator('.product-selector-row');
  }

  get totalAmountText() {
    return this.page.locator('.order-total-amount');
  }

  // Actions
  async navigateToOrders() {
    await this.goto('/office/orders');
    await this.waitForLoadComplete();
  }

  async searchOrder(keyword: string) {
    await this.searchInput.fill(keyword);
    await this.page.keyboard.press('Enter');
    await this.waitForLoadComplete();
  }

  async filterByDateRange(startDate: string, endDate: string) {
    await this.dateRangePicker.click();
    
    // Clear and select start date
    const startInput = this.page.locator('.ant-picker-panel input').first();
    await startInput.clear();
    await startInput.fill(startDate);
    
    // Clear and select end date
    const endInput = this.page.locator('.ant-picker-panel input').last();
    await endInput.clear();
    await endInput.fill(endDate);
    
    // Confirm selection
    await this.page.locator('.ant-picker-ok button').click();
    await this.waitForLoadComplete();
  }

  async filterByStatus(status: string) {
    await this.statusFilter.click();
    await this.page.locator(`.ant-select-dropdown .ant-select-item[title="${status}"]`).click();
    await this.waitForLoadComplete();
  }

  async clickCreateOrder() {
    await this.createOrderButton.click();
    await this.modalTitle.waitFor({ state: 'visible' });
  }

  async fillOrderForm(orderData: {
    customerId: string;
    scheduledDate: string;
    deliveryTimeStart?: string;
    deliveryTimeEnd?: string;
    deliveryAddress?: string;
    deliveryNotes?: string;
    isUrgent?: boolean;
    paymentMethod?: string;
  }) {
    // Select customer
    await this.selectDropdownOption('#order_customerId', orderData.customerId);
    
    // Set scheduled date
    await this.scheduledDatePicker.click();
    await this.page.locator('.ant-picker-input input').fill(orderData.scheduledDate);
    await this.page.keyboard.press('Enter');
    
    // Set delivery time range if provided
    if (orderData.deliveryTimeStart && orderData.deliveryTimeEnd) {
      await this.deliveryTimeRangePicker.click();
      const timeInputs = this.page.locator('.ant-picker-time-panel-column');
      // This would need more specific implementation based on time picker behavior
    }
    
    if (orderData.deliveryAddress) {
      await this.deliveryAddressInput.fill(orderData.deliveryAddress);
    }
    
    if (orderData.deliveryNotes) {
      await this.deliveryNotesTextarea.fill(orderData.deliveryNotes);
    }
    
    if (orderData.isUrgent) {
      await this.urgentCheckbox.check();
    }
    
    if (orderData.paymentMethod) {
      await this.selectDropdownOption('#order_paymentMethod', orderData.paymentMethod);
    }
  }

  async addProduct(productData: {
    productName: string;
    quantity: number;
    isExchange?: boolean;
    discount?: number;
    meterReadingStart?: number;
    meterReadingEnd?: number;
  }) {
    await this.addProductButton.click();
    
    const newRow = this.productRows.last();
    
    // Select product
    const productSelect = newRow.locator('.product-select');
    await productSelect.click();
    await this.page.locator(`.ant-select-dropdown .ant-select-item[title*="${productData.productName}"]`).click();
    
    // Enter quantity
    const quantityInput = newRow.locator('input[type="number"]').first();
    await quantityInput.fill(productData.quantity.toString());
    
    // Handle exchange checkbox if applicable
    if (productData.isExchange !== undefined) {
      const exchangeCheckbox = newRow.locator('input[type="checkbox"]');
      if (productData.isExchange) {
        await exchangeCheckbox.check();
      }
    }
    
    // Enter discount if provided
    if (productData.discount !== undefined) {
      const discountInput = newRow.locator('.discount-input');
      await discountInput.fill(productData.discount.toString());
    }
    
    // Enter meter readings for flow delivery
    if (productData.meterReadingStart !== undefined) {
      const startReadingInput = newRow.locator('.meter-reading-start');
      await startReadingInput.fill(productData.meterReadingStart.toString());
    }
    
    if (productData.meterReadingEnd !== undefined) {
      const endReadingInput = newRow.locator('.meter-reading-end');
      await endReadingInput.fill(productData.meterReadingEnd.toString());
    }
  }

  async removeProduct(index: number) {
    const row = this.productRows.nth(index);
    const removeButton = row.locator('button').filter({ hasText: '刪除' });
    await removeButton.click();
  }

  async submitOrderForm() {
    await this.modalConfirmButton.click();
    await this.waitForToast('訂單建立成功');
  }

  async getOrderCount(): Promise<number> {
    return await this.orderRows.count();
  }

  async getOrderData(rowIndex: number) {
    const row = this.orderRows.nth(rowIndex);
    const cells = row.locator('td');
    
    return {
      orderNumber: await cells.nth(0).textContent() || '',
      customer: await cells.nth(1).textContent() || '',
      scheduledDate: await cells.nth(2).textContent() || '',
      products: await cells.nth(3).textContent() || '',
      totalAmount: await cells.nth(4).textContent() || '',
      status: await cells.nth(5).textContent() || '',
      paymentStatus: await cells.nth(6).textContent() || ''
    };
  }

  async clickOrderRow(index: number) {
    const row = this.orderRows.nth(index);
    await row.click();
    await this.waitForLoadComplete();
  }

  async changeOrderStatus(rowIndex: number, newStatus: string) {
    const row = this.orderRows.nth(rowIndex);
    const statusDropdown = row.locator('.status-dropdown');
    await statusDropdown.click();
    await this.page.locator(`.ant-dropdown-menu-item:has-text("${newStatus}")`).click();
    await this.waitForToast();
  }

  async printOrder(rowIndex: number) {
    const row = this.orderRows.nth(rowIndex);
    const printButton = row.locator('button').filter({ hasText: '列印' });
    await printButton.click();
  }

  async getTotalAmount(): Promise<string> {
    return await this.totalAmountText.textContent() || '0';
  }

  async checkChineseLocalization(): Promise<boolean> {
    const expectedTexts = [
      '訂單管理',
      '新增訂單',
      '訂單編號',
      '客戶',
      '預定配送日',
      '產品',
      '總金額',
      '狀態',
      '付款狀態'
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

    // Check if action buttons stack vertically on mobile
    const createButton = await this.createOrderButton.boundingBox();
    const searchInput = await this.searchInput.boundingBox();
    
    if (createButton && searchInput) {
      // Buttons should stack vertically on mobile
      return createButton.y !== searchInput.y;
    }
    return false;
  }

  async bulkUpdateStatus(orderIndices: number[], newStatus: string) {
    // Select orders
    for (const index of orderIndices) {
      const row = this.orderRows.nth(index);
      const checkbox = row.locator('input[type="checkbox"]');
      await checkbox.check();
    }
    
    // Click bulk action button
    const bulkActionButton = this.page.locator('button').filter({ hasText: '批量操作' });
    await bulkActionButton.click();
    
    // Select new status
    await this.page.locator(`.ant-dropdown-menu-item:has-text("更改狀態為${newStatus}")`).click();
    
    // Confirm
    const confirmButton = this.page.locator('.ant-modal-confirm-btns button.ant-btn-primary');
    await confirmButton.click();
    await this.waitForToast();
  }

  async exportOrders() {
    const exportButton = this.page.locator('button').filter({ hasText: '匯出' });
    await exportButton.click();
    
    // Wait for download
    const downloadPromise = this.page.waitForEvent('download');
    await this.page.locator('.ant-dropdown-menu-item:has-text("匯出Excel")').click();
    const download = await downloadPromise;
    
    return download.suggestedFilename();
  }
}