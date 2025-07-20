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
    return this.page.locator('.ant-table-tbody tr');
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
    return this.page.locator('#customer_customerCode');
  }

  get nameInput() {
    return this.page.locator('#customer_name');
  }

  get shortNameInput() {
    return this.page.locator('#customer_shortName');
  }

  get invoiceTitleInput() {
    return this.page.locator('#customer_invoiceTitle');
  }

  get phoneInput() {
    return this.page.locator('#customer_phone');
  }

  get mobileInput() {
    return this.page.locator('#customer_mobile');
  }

  get addressInput() {
    return this.page.locator('#customer_address');
  }

  get areaSelect() {
    return this.page.locator('#customer_area');
  }

  get deliveryTimeStartInput() {
    return this.page.locator('#customer_deliveryTimeStart');
  }

  get deliveryTimeEndInput() {
    return this.page.locator('#customer_deliveryTimeEnd');
  }

  get avgDailyUsageInput() {
    return this.page.locator('#customer_avgDailyUsage');
  }

  get maxCycleDaysInput() {
    return this.page.locator('#customer_maxCycleDays');
  }

  get canDelayDaysInput() {
    return this.page.locator('#customer_canDelayDays');
  }

  // Actions
  async navigateToCustomers() {
    await this.goto('/office/customers');
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
    name: string;
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
    await this.nameInput.fill(customerData.name);
    
    if (customerData.shortName) {
      await this.shortNameInput.fill(customerData.shortName);
    }
    if (customerData.invoiceTitle) {
      await this.invoiceTitleInput.fill(customerData.invoiceTitle);
    }
    if (customerData.phone) {
      await this.phoneInput.fill(customerData.phone);
    }
    if (customerData.mobile) {
      await this.mobileInput.fill(customerData.mobile);
    }
    if (customerData.address) {
      await this.addressInput.fill(customerData.address);
    }
    if (customerData.area) {
      await this.selectDropdownOption('#customer_area', customerData.area);
    }
    if (customerData.deliveryTimeStart) {
      await this.deliveryTimeStartInput.fill(customerData.deliveryTimeStart);
    }
    if (customerData.deliveryTimeEnd) {
      await this.deliveryTimeEndInput.fill(customerData.deliveryTimeEnd);
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
    await this.waitForToast();
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
    
    return {
      customerCode: await cells.nth(0).textContent() || '',
      name: await cells.nth(1).textContent() || '',
      shortName: await cells.nth(2).textContent() || '',
      phone: await cells.nth(3).textContent() || '',
      address: await cells.nth(4).textContent() || '',
      area: await cells.nth(5).textContent() || '',
      status: await cells.nth(6).textContent() || ''
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
    const match = paginationText.match(/共 (\d+) 項/);
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
      '客戶名稱',
      '聯絡電話',
      '地址',
      '區域',
      '狀態'
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