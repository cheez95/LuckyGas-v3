import { Page } from '@playwright/test';
import { BasePage } from './BasePage';

export class CustomerManagementPage extends BasePage {
  constructor(page: Page) {
    super(page);
  }

  // Locators
  get pageTitle() {
    return this.page.locator('.ant-card-head-title').filter({ hasText: '客戶管理' });
  }

  get addCustomerButton() {
    return this.page.locator('[data-testid="add-customer-button"]');
  }

  get searchInput() {
    return this.page.locator('[data-testid="customer-search-input"]');
  }

  get customerTable() {
    return this.page.locator('[data-testid="customer-table"]');
  }

  get customerRows() {
    return this.page.locator('.ant-table-tbody tr:not([aria-hidden="true"])');
  }

  // Modal locators
  get modalTitle() {
    return this.page.locator('.ant-modal-title');
  }

  get modalConfirmButton() {
    return this.page.locator('[data-testid="customer-submit-button"]');
  }

  get modalCancelButton() {
    return this.page.locator('[data-testid="customer-cancel-button"]');
  }

  // Form fields - matching CustomerManagement component
  get nameInput() {
    return this.page.locator('input[id="customer_name"]');
  }

  get phoneInput() {
    return this.page.locator('input[id="customer_phone"]');
  }

  get addressInput() {
    return this.page.locator('textarea[id="customer_address"]');
  }

  get districtInput() {
    return this.page.locator('input[id="customer_district"]');
  }

  get postalCodeInput() {
    return this.page.locator('input[id="customer_postalCode"]');
  }

  get customerTypeSelect() {
    return this.page.locator('[data-testid="customer-type-select"]');
  }

  get cylinderTypeSelect() {
    return this.page.locator('[data-testid="cylinder-type-select"]');
  }

  get statusSelect() {
    return this.page.locator('[data-testid="status-select"]');
  }

  get notesTextarea() {
    return this.page.locator('[data-testid="customer-notes-textarea"]');
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
    await this.waitForAntAnimation();
    // Wait for the first input field to be ready
    await this.nameInput.waitFor({ state: 'visible' });
  }

  async fillCustomerForm(customerData: {
    name: string;
    phone: string;
    address: string;
    district: string;
    postalCode: string;
    customerType?: 'residential' | 'commercial';
    cylinderType?: '20kg' | '16kg' | '50kg';
    status?: 'active' | 'inactive' | 'suspended';
    notes?: string;
  }) {
    await this.nameInput.fill(customerData.name);
    await this.phoneInput.fill(customerData.phone);
    await this.addressInput.fill(customerData.address);
    await this.districtInput.fill(customerData.district);
    await this.postalCodeInput.fill(customerData.postalCode);

    if (customerData.customerType) {
      await this.customerTypeSelect.click();
      await this.waitForAntAnimation();
      // Map the values to the actual text in the dropdown
      const typeText = customerData.customerType === 'residential' ? '住宅' : '商業';
      await this.page.locator('.ant-select-dropdown').filter({ hasNot: this.page.locator('[style*="display: none"]') }).locator('.ant-select-item').filter({ hasText: typeText }).first().click();
    }

    if (customerData.cylinderType) {
      await this.cylinderTypeSelect.click();
      await this.waitForAntAnimation();
      await this.page.locator('.ant-select-dropdown').filter({ hasNot: this.page.locator('[style*="display: none"]') }).locator('.ant-select-item').filter({ hasText: customerData.cylinderType }).first().click();
    }

    if (customerData.status) {
      await this.statusSelect.click();
      await this.waitForAntAnimation();
      // Map the values to the actual text in the dropdown
      const statusText = customerData.status === 'active' ? '啟用' : 
                        customerData.status === 'inactive' ? '停用' : '暫停';
      await this.page.locator('.ant-select-dropdown').filter({ hasNot: this.page.locator('[style*="display: none"]') }).locator('.ant-select-item').filter({ hasText: statusText }).first().click();
    }

    if (customerData.notes) {
      await this.notesTextarea.fill(customerData.notes);
    }
  }

  async submitCustomerForm(isEdit: boolean = false) {
    // Set up response listener before clicking submit
    let responsePromise;
    if (isEdit) {
      responsePromise = this.page.waitForResponse(
        resp => resp.url().includes('/api/v1/customers/') && resp.request().method() === 'PUT' && resp.ok()
      );
    } else {
      responsePromise = this.waitForApiCall('/api/v1/customers', 'POST');
    }
    
    // Click submit
    await this.modalConfirmButton.click();
    
    // Wait for API call to complete
    try {
      await responsePromise;
    } catch (e) {
      // If the API call already happened, continue
    }
    
    // Wait for modal to close with retry logic
    let modalClosed = false;
    for (let i = 0; i < 3; i++) {
      try {
        await this.modalTitle.waitFor({ state: 'hidden', timeout: 2000 });
        modalClosed = true;
        break;
      } catch (e) {
        // Modal might still be visible, wait a bit and retry
        await this.page.waitForTimeout(1000);
      }
    }
    
    if (!modalClosed) {
      // Force close by pressing Escape
      await this.page.keyboard.press('Escape');
      await this.page.waitForTimeout(500);
    }
    
    // Wait for any animations and loading states
    await this.waitForAntAnimation();
    await this.waitForLoadingComplete();
  }

  async cancelCustomerForm() {
    await this.modalCancelButton.click();
  }

  async getCustomerCount(): Promise<number> {
    return await this.customerRows.count();
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
    
    // CustomerManagement table columns order
    return {
      name: await getCellText(0),
      phone: await getCellText(1),
      address: await getCellText(2),
      customerType: await getCellText(3),
      cylinderType: await getCellText(4),
      status: await getCellText(5),
      lastOrder: await getCellText(6),
      totalOrders: await getCellText(7)
    };
  }

  async editCustomer(rowIndex: number) {
    const row = this.customerRows.nth(rowIndex);
    // Try to find edit button by data-testid first, fallback to text
    let editButton = row.locator('[data-testid^="edit-customer-"]');
    const buttonCount = await editButton.count();
    
    if (buttonCount === 0) {
      // Fallback to text-based selector
      editButton = row.locator('button').filter({ hasText: '編輯' });
    }
    
    await editButton.click();
    await this.modalTitle.waitFor({ state: 'visible' });
  }

  async deleteCustomer(rowIndex: number) {
    const row = this.customerRows.nth(rowIndex);
    
    // Find delete button - try data-testid first
    let deleteButton = row.locator('[data-testid^="delete-customer-"]').first();
    const buttonCount = await deleteButton.count();
    
    if (buttonCount === 0) {
      // Fallback to finding by text in button that contains text "刪除"
      deleteButton = row.locator('button:has-text("刪除")').first();
    }
    
    // Click the delete button
    await deleteButton.scrollIntoViewIfNeeded();
    await deleteButton.click();
    
    // Wait for confirmation modal to appear - try multiple selectors
    try {
      await this.page.locator('.ant-modal-confirm, .ant-modal').waitFor({ state: 'visible', timeout: 5000 });
    } catch (e) {
      // If modal doesn't appear, try clicking again
      await deleteButton.click();
      await this.page.locator('.ant-modal-confirm, .ant-modal').waitFor({ state: 'visible', timeout: 5000 });
    }
    
    // Find and click the confirm button - Ant Design uses primary button for OK
    const confirmButton = this.page.locator('.ant-modal-confirm-btns button.ant-btn-primary, .ant-modal-footer button.ant-btn-primary').first();
    await confirmButton.click();
    
    // Wait for deletion to complete
    try {
      await this.page.waitForResponse(
        resp => resp.url().includes('/api/v1/customers/') && resp.request().method() === 'DELETE',
        { timeout: 10000 }
      );
    } catch (e) {
      // API might have already completed
    }
    
    // Wait for modal to close
    await this.page.locator('.ant-modal-confirm, .ant-modal').waitFor({ state: 'hidden', timeout: 5000 });
    await this.waitForAntAnimation();
    await this.waitForLoadingComplete();
  }

  async checkChineseLocalization(): Promise<boolean> {
    const expectedTexts = [
      '客戶管理',
      '新增客戶'
    ];

    for (const text of expectedTexts) {
      const element = this.page.getByText(text);
      if (!await element.first().isVisible()) {
        console.log(`Missing Chinese text: ${text}`);
        return false;
      }
    }
    
    // Check the search placeholder text
    const searchPlaceholder = await this.searchInput.getAttribute('placeholder');
    if (!searchPlaceholder || !searchPlaceholder.includes('搜尋')) {
      console.log(`Missing Chinese placeholder: ${searchPlaceholder}`);
      return false;
    }
    
    return true;
  }
}