import { Page } from '@playwright/test';
import { BasePage } from './BasePage';

export class CustomerPage extends BasePage {
  constructor(page: Page) {
    super(page);
  }

  // Locators
  get pageTitle() {
    return this.page.locator('h2.ant-typography').filter({ hasText: '客戶管理' });
  }

  get addCustomerButton() {
    return this.page.locator('button').filter({ hasText: '新增客戶' });
  }

  get searchInput() {
    return this.page.locator('input[placeholder*="搜尋客戶"]');
  }

  get customerTable() {
    return this.page.locator('.ant-table');
  }

  get customerRows() {
    // Exclude measurement rows and only get actual data rows
    return this.page.locator('.ant-table-tbody tr:not([aria-hidden="true"])');
  }

  get paginationInfo() {
    return this.page.locator('.ant-pagination-total-text');
  }

  get nextPageButton() {
    return this.page.locator('.ant-pagination-next');
  }

  get previousPageButton() {
    return this.page.locator('.ant-pagination-prev');
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

  // Form fields
  get customerCodeInput() {
    return this.page.locator('input[id="customer_code"]');
  }

  get shortNameInput() {
    return this.page.locator('input[id="short_name"]');
  }

  get invoiceTitleInput() {
    return this.page.locator('input[id="invoice_title"]');
  }

  get addressInput() {
    return this.page.locator('textarea[id="address"]');
  }

  get areaSelect() {
    return this.page.locator('input[id="area"]');
  }

  get deliveryTimeInput() {
    return this.page.locator('input[id="delivery_time"]');
  }

  get paymentMethodSelect() {
    return this.page.locator('input[id="payment_method"]');
  }

  get avgDailyUsageInput() {
    return this.page.locator('input[id="avg_daily_usage"]');
  }

  get maxCycleDaysInput() {
    return this.page.locator('input[id="max_cycle_days"]');
  }

  get canDelayDaysInput() {
    return this.page.locator('input[id="can_delay_days"]');
  }
  
  get phoneInput() {
    return this.page.locator('input[id="phone"]');
  }

  // Actions
  async navigateToCustomers() {
    await this.goto('/customers');
    await this.waitForLoadComplete();
  }

  async searchCustomer(keyword: string) {
    await this.searchInput.fill(keyword);
    await this.page.keyboard.press('Enter');
    await this.waitForLoadComplete();
  }

  async clickAddCustomer() {
    await this.addCustomerButton.click();
    await this.modalTitle.waitFor({ state: 'visible' });
  }

  async fillCustomerForm(customerData: {
    customerCode: string;
    name?: string;
    shortName?: string;
    invoiceTitle?: string;
    phone?: string;
    mobile?: string;
    address?: string;
    area?: string;
    deliveryTimeStart?: string;
    deliveryTimeEnd?: string;
    avgDailyUsage?: number;
    maxCycleDays?: number;
    canDelayDays?: number;
  }) {
    await this.customerCodeInput.fill(customerData.customerCode);
    
    if (customerData.shortName) {
      await this.shortNameInput.fill(customerData.shortName);
    }
    if (customerData.invoiceTitle) {
      await this.invoiceTitleInput.fill(customerData.invoiceTitle);
    }
    if (customerData.phone) {
      await this.phoneInput.fill(customerData.phone);
    }
    if (customerData.address) {
      await this.addressInput.fill(customerData.address);
    }
    if (customerData.area) {
      await this.areaSelect.click();
      await this.page.waitForTimeout(500); // Wait for dropdown animation
      await this.page.locator('.ant-select-dropdown .ant-select-item[title="' + customerData.area + '"]').click();
    }
    
    // Handle delivery time range picker
    if (customerData.deliveryTimeStart && customerData.deliveryTimeEnd) {
      const rangePickerInput = this.page.locator('input[id="delivery_time"]');
      // Click the first input field
      await rangePickerInput.first().click();
      await this.page.waitForTimeout(500);
      // Clear and type start time
      await this.page.keyboard.press('Control+A');
      await this.page.keyboard.type(customerData.deliveryTimeStart);
      await this.page.keyboard.press('Tab');
      // Type end time
      await this.page.keyboard.type(customerData.deliveryTimeEnd);
      await this.page.keyboard.press('Enter');
    }
    
    if (customerData.avgDailyUsage !== undefined) {
      await this.avgDailyUsageInput.fill(customerData.avgDailyUsage.toString());
    }
    if (customerData.maxCycleDays !== undefined) {
      await this.maxCycleDaysInput.fill(customerData.maxCycleDays.toString());
    }
    if (customerData.canDelayDays !== undefined) {
      await this.canDelayDaysInput.fill(customerData.canDelayDays.toString());
    }
  }

  async submitCustomerForm() {
    await this.modalConfirmButton.click();
    
    // Wait for success indication - either modal closes or success message appears
    await this.page.waitForResponse(
      response => response.url().includes('/api/v1/customers') && response.status() === 200,
      { timeout: 10000 }
    );
    
    // Give a bit more time for UI to update
    await this.page.waitForTimeout(1000);
  }

  async cancelCustomerForm() {
    await this.modalCancelButton.click();
  }

  async getCustomerCount(): Promise<number> {
    return await this.customerRows.count();
  }

  async clickCustomerRow(index: number) {
    const row = this.customerRows.nth(index);
    await row.click();
    await this.waitForLoadComplete();
  }

  async getCustomerData(rowIndex: number) {
    const row = this.customerRows.nth(rowIndex);
    const cells = row.locator('td');
    
    // Wait for cells to be present
    await cells.first().waitFor({ state: 'visible', timeout: 5000 });
    
    // Get text content with trimming
    const getCellText = async (index: number) => {
      const text = await cells.nth(index).textContent();
      return text?.trim() || '';
    };
    
    return {
      customerCode: await getCellText(0),
      shortName: await getCellText(1),
      invoiceTitle: await getCellText(2),
      address: await getCellText(3),
      area: await getCellText(4),
      deliveryTime: await getCellText(5),
      avgDailyUsage: await getCellText(6),
      paymentMethod: await getCellText(7),
      customerType: await getCellText(8),
      status: await getCellText(9)
    };
  }

  async editCustomer(rowIndex: number) {
    const row = this.customerRows.nth(rowIndex);
    const editButton = row.locator('button').filter({ hasText: '編輯' });
    await editButton.click();
    await this.modalTitle.waitFor({ state: 'visible' });
  }

  async deleteCustomer(rowIndex: number) {
    const row = this.customerRows.nth(rowIndex);
    const deleteButton = row.locator('button').filter({ hasText: '刪除' });
    await deleteButton.click();
    
    // Confirm deletion in the modal
    const confirmButton = this.page.locator('.ant-modal-confirm-btns button.ant-btn-primary');
    await confirmButton.click();
    await this.waitForToast('刪除成功');
  }

  async getTotalCustomerCount(): Promise<number> {
    const paginationText = await this.paginationInfo.textContent() || '';
    const match = paginationText.match(/共 (\d+) 筆資料/);
    return match ? parseInt(match[1]) : 0;
  }

  async goToNextPage() {
    await this.nextPageButton.click();
    await this.waitForLoadComplete();
  }

  async goToPreviousPage() {
    await this.previousPageButton.click();
    await this.waitForLoadComplete();
  }

  async checkChineseLocalization(): Promise<boolean> {
    const expectedTexts = [
      '客戶管理',
      '新增客戶',
      '客戶代碼',
      '客戶簡稱',
      '發票抬頭',
      '地址',
      '配送區域'
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

    // Check if table is scrollable on mobile
    const tableContainer = this.customerTable.locator('.ant-table-container');
    const containerBox = await tableContainer.boundingBox();
    const tableBox = await this.customerTable.boundingBox();
    
    if (containerBox && tableBox) {
      // Table should be scrollable horizontally on mobile
      return tableBox.width > containerBox.width;
    }
    return false;
  }

  async selectCustomersByCheckbox(indices: number[]) {
    for (const index of indices) {
      const row = this.customerRows.nth(index);
      const checkbox = row.locator('input[type="checkbox"]');
      await checkbox.check();
    }
  }

  async bulkDelete() {
    const bulkDeleteButton = this.page.locator('button').filter({ hasText: '批量刪除' });
    await bulkDeleteButton.click();
    
    // Confirm bulk deletion
    const confirmButton = this.page.locator('.ant-modal-confirm-btns button.ant-btn-primary');
    await confirmButton.click();
    await this.waitForToast();
  }
}