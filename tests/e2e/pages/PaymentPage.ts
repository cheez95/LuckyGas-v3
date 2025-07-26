import { Page, expect } from '@playwright/test';

export class PaymentPage {
  constructor(private page: Page) {}

  async waitForPageLoad() {
    await this.page.waitForLoadState('networkidle');
    await expect(this.page.locator('[data-testid="payment-page"]')).toBeVisible();
  }

  async filterByStatus(status: 'pending' | 'paid' | 'partial' | 'overdue') {
    await this.page.selectOption('[data-testid="payment-status-filter"]', status);
    await this.page.waitForTimeout(1000);
  }

  async selectDateRange(startDate: string, endDate: string) {
    await this.page.fill('[data-testid="date-range-start"]', startDate);
    await this.page.fill('[data-testid="date-range-end"]', endDate);
    await this.page.click('[data-testid="apply-date-filter"]');
    await this.page.waitForTimeout(1000);
  }

  async getPendingPaymentCount(): Promise<number> {
    const countElement = await this.page.locator('[data-testid="pending-payment-count"]');
    const text = await countElement.textContent();
    return parseInt(text || '0');
  }

  async selectAllPayments() {
    await this.page.click('[data-testid="select-all-payments"]');
  }

  async createPaymentBatch(options: {
    batchName: string;
    paymentMethod: string;
    dueDate: Date;
  }) {
    await this.page.click('[data-testid="create-batch-button"]');
    
    // Fill batch details
    await this.page.fill('[data-testid="batch-name"]', options.batchName);
    await this.page.selectOption('[data-testid="batch-payment-method"]', options.paymentMethod);
    await this.page.fill('[data-testid="batch-due-date"]', options.dueDate.toISOString().split('T')[0]);
    
    await this.page.click('[data-testid="confirm-create-batch"]');
    await this.page.waitForTimeout(2000);
  }

  async getLatestBatchNumber(): Promise<string> {
    const batchNumber = await this.page.locator('[data-testid="batch-number"]').first().textContent();
    return batchNumber || '';
  }

  async navigateToBatchList() {
    await this.page.click('[data-testid="payment-batches-tab"]');
    await this.page.waitForTimeout(1000);
  }

  async selectLatestBatch() {
    const latestBatch = this.page.locator('[data-testid="batch-row"]').first();
    await latestBatch.click();
    
    const batchId = await latestBatch.getAttribute('data-batch-id');
    return { id: batchId };
  }

  async generateBankFile(options: {
    fileFormat: string;
    bankCode: string;
    accountNumber: string;
  }) {
    await this.page.click('[data-testid="generate-bank-file"]');
    
    await this.page.selectOption('[data-testid="file-format"]', options.fileFormat);
    await this.page.fill('[data-testid="bank-code"]', options.bankCode);
    await this.page.fill('[data-testid="account-number"]', options.accountNumber);
    
    await this.page.click('[data-testid="confirm-generate"]');
  }

  async createMixedPaymentBatch(methods: Array<{ method: string; count: number }>) {
    await this.page.click('[data-testid="create-mixed-batch"]');
    
    for (const item of methods) {
      await this.page.fill(`[data-testid="${item.method}-count"]`, item.count.toString());
    }
    
    await this.page.click('[data-testid="create-batch"]');
    await this.page.waitForTimeout(2000);
  }

  async getBatchSummary() {
    const summary = {
      cash: parseInt(await this.page.locator('[data-testid="cash-count"]').textContent() || '0'),
      bankTransfer: parseInt(await this.page.locator('[data-testid="bank-transfer-count"]').textContent() || '0'),
      creditCard: parseInt(await this.page.locator('[data-testid="credit-card-count"]').textContent() || '0'),
      total: parseInt(await this.page.locator('[data-testid="total-count"]').textContent() || '0')
    };
    return summary;
  }

  async recordPayment(details: {
    amount: number;
    method: string;
    referenceNumber: string;
    notes?: string;
  }) {
    await this.page.fill('[data-testid="payment-amount"]', details.amount.toString());
    await this.page.selectOption('[data-testid="payment-method"]', details.method);
    await this.page.fill('[data-testid="reference-number"]', details.referenceNumber);
    
    if (details.notes) {
      await this.page.fill('[data-testid="payment-notes"]', details.notes);
    }
    
    await this.page.click('[data-testid="record-payment"]');
    await this.page.waitForTimeout(1000);
  }

  async findOrderWithBalance() {
    const order = this.page.locator('[data-testid="order-with-balance"]').first();
    const orderNumber = await order.getAttribute('data-order-number') || '';
    const total = parseInt(await order.getAttribute('data-total') || '0');
    
    return { number: orderNumber, total };
  }

  async recordPartialPayment(details: {
    orderNumber: string;
    totalAmount: number;
    paidAmount: number;
    method: string;
  }) {
    await this.page.click(`[data-testid="order-${details.orderNumber}"]`);
    await this.page.click('[data-testid="record-partial-payment"]');
    
    await this.page.fill('[data-testid="partial-amount"]', details.paidAmount.toString());
    await this.page.selectOption('[data-testid="payment-method"]', details.method);
    
    await this.page.click('[data-testid="confirm-partial-payment"]');
    await this.page.waitForTimeout(1000);
  }

  async uploadBankResponse(file: any) {
    const fileInput = await this.page.locator('[data-testid="bank-response-upload"]');
    await fileInput.setInputFiles(file);
    
    await this.page.click('[data-testid="process-upload"]');
    await this.page.waitForTimeout(2000);
  }

  async processImportedPayments() {
    await this.page.click('[data-testid="process-imported-payments"]');
    await this.page.waitForTimeout(3000);
  }

  async getProcessedPaymentCount(): Promise<number> {
    const count = await this.page.locator('[data-testid="processed-count"]').textContent();
    return parseInt(count || '0');
  }

  async getPaymentSuccessRate(): Promise<number> {
    const rate = await this.page.locator('[data-testid="success-rate"]').textContent();
    return parseFloat(rate?.replace('%', '') || '0');
  }

  async navigateToReconciliation() {
    await this.page.click('[data-testid="reconciliation-tab"]');
    await this.page.waitForTimeout(1000);
  }

  async selectReconciliationDate(date: string) {
    await this.page.fill('[data-testid="reconciliation-date"]', date);
  }

  async runReconciliation() {
    await this.page.click('[data-testid="run-reconciliation"]');
    await this.page.waitForTimeout(3000);
  }

  async getReconciliationResults() {
    return {
      matched: parseInt(await this.page.locator('[data-testid="matched-count"]').textContent() || '0'),
      unmatched: parseInt(await this.page.locator('[data-testid="unmatched-count"]').textContent() || '0'),
      total: parseInt(await this.page.locator('[data-testid="total-reconciled"]').textContent() || '0')
    };
  }

  async getDiscrepancies() {
    const discrepancies = [];
    const rows = await this.page.locator('[data-testid="discrepancy-row"]').all();
    
    for (const row of rows) {
      discrepancies.push({
        orderNumber: await row.getAttribute('data-order-number') || '',
        expectedAmount: parseFloat(await row.getAttribute('data-expected') || '0'),
        actualAmount: parseFloat(await row.getAttribute('data-actual') || '0'),
        difference: parseFloat(await row.getAttribute('data-difference') || '0')
      });
    }
    
    return discrepancies;
  }

  async generateReconciliationReport(options: {
    period: string;
    month?: number;
    year?: number;
    format: string;
  }) {
    await this.page.click('[data-testid="generate-report"]');
    
    await this.page.selectOption('[data-testid="report-period"]', options.period);
    
    if (options.month !== undefined) {
      await this.page.selectOption('[data-testid="report-month"]', options.month.toString());
    }
    
    if (options.year) {
      await this.page.selectOption('[data-testid="report-year"]', options.year.toString());
    }
    
    await this.page.selectOption('[data-testid="report-format"]', options.format);
    await this.page.click('[data-testid="generate"]');
  }

  async findDiscrepancy() {
    const discrepancy = this.page.locator('[data-testid="discrepancy-row"]').first();
    
    if (await discrepancy.isVisible()) {
      return {
        orderNumber: await discrepancy.getAttribute('data-order-number') || '',
        difference: parseFloat(await discrepancy.getAttribute('data-difference') || '0')
      };
    }
    
    return null;
  }

  async createAdjustment(details: {
    orderNumber: string;
    adjustmentType: string;
    amount: number;
    reason: string;
    approvedBy: string;
  }) {
    await this.page.click(`[data-testid="adjust-${details.orderNumber}"]`);
    
    await this.page.selectOption('[data-testid="adjustment-type"]', details.adjustmentType);
    await this.page.fill('[data-testid="adjustment-amount"]', details.amount.toString());
    await this.page.fill('[data-testid="adjustment-reason"]', details.reason);
    await this.page.fill('[data-testid="approved-by"]', details.approvedBy);
    
    await this.page.click('[data-testid="create-adjustment"]');
    await this.page.waitForTimeout(1000);
  }

  async navigateToOverdue() {
    await this.page.click('[data-testid="overdue-accounts-tab"]');
    await this.page.waitForTimeout(1000);
  }

  async getOverdueAccountCount(): Promise<number> {
    const count = await this.page.locator('[data-testid="overdue-count"]').textContent();
    return parseInt(count || '0');
  }

  async generatePaymentReminders(options: {
    reminderType: string;
    template: string;
    includeSummary: boolean;
  }) {
    await this.page.click('[data-testid="generate-reminders"]');
    
    await this.page.selectOption('[data-testid="reminder-type"]', options.reminderType);
    await this.page.selectOption('[data-testid="reminder-template"]', options.template);
    
    if (options.includeSummary) {
      await this.page.check('[data-testid="include-summary"]');
    }
    
    await this.page.click('[data-testid="send-reminders"]');
    await this.page.waitForTimeout(2000);
  }

  async getRemindersSentCount(): Promise<number> {
    const count = await this.page.locator('[data-testid="reminders-sent"]').textContent();
    return parseInt(count || '0');
  }

  async navigateToReminderLog() {
    await this.page.click('[data-testid="reminder-log-link"]');
    await this.page.waitForTimeout(1000);
  }

  async getLatestReminder() {
    const reminder = this.page.locator('[data-testid="reminder-log-entry"]').first();
    
    return {
      status: await reminder.getAttribute('data-status') || '',
      recipientCount: parseInt(await reminder.getAttribute('data-recipients') || '0')
    };
  }

  async navigateToReports() {
    await this.page.click('[data-testid="payment-reports-tab"]');
    await this.page.waitForTimeout(1000);
  }

  async generateDailySummary(options: {
    date: string;
    includeDetails: boolean;
  }) {
    await this.page.click('[data-testid="daily-summary-report"]');
    
    await this.page.fill('[data-testid="summary-date"]', options.date);
    
    if (options.includeDetails) {
      await this.page.check('[data-testid="include-details"]');
    }
    
    await this.page.click('[data-testid="generate-summary"]');
    await this.page.waitForTimeout(2000);
  }

  async getDailySummaryData() {
    return {
      totalCollected: parseFloat(await this.page.locator('[data-testid="total-collected"]').textContent() || '0'),
      cashAmount: parseFloat(await this.page.locator('[data-testid="cash-amount"]').textContent() || '0'),
      bankTransferAmount: parseFloat(await this.page.locator('[data-testid="bank-transfer-amount"]').textContent() || '0'),
      creditCardAmount: parseFloat(await this.page.locator('[data-testid="credit-card-amount"]').textContent() || '0'),
      pendingAmount: parseFloat(await this.page.locator('[data-testid="pending-amount"]').textContent() || '0')
    };
  }

  async generateAgingReport(options: {
    asOfDate: string;
    groupBy: string;
    agingBuckets: number[];
  }) {
    await this.page.click('[data-testid="aging-report"]');
    
    await this.page.fill('[data-testid="as-of-date"]', options.asOfDate);
    await this.page.selectOption('[data-testid="group-by"]', options.groupBy);
    
    await this.page.click('[data-testid="generate-aging"]');
    await this.page.waitForTimeout(2000);
  }

  async getAgingReportData() {
    return {
      current: parseFloat(await this.page.locator('[data-testid="aging-current"]').textContent() || '0'),
      days30: parseFloat(await this.page.locator('[data-testid="aging-30-days"]').textContent() || '0'),
      days60: parseFloat(await this.page.locator('[data-testid="aging-60-days"]').textContent() || '0'),
      days90: parseFloat(await this.page.locator('[data-testid="aging-90-days"]').textContent() || '0'),
      over120: parseFloat(await this.page.locator('[data-testid="aging-over-120"]').textContent() || '0')
    };
  }

  async downloadAgingDetails(format: string) {
    await this.page.click('[data-testid="download-aging-details"]');
    await this.page.selectOption('[data-testid="download-format"]', format);
    await this.page.click('[data-testid="download"]');
  }

  async navigateToIntegration() {
    await this.page.click('[data-testid="integration-settings"]');
    await this.page.waitForTimeout(1000);
  }

  async configureAccountingSync(options: {
    system: string;
    syncFrequency: string;
    accountMapping: any;
  }) {
    await this.page.selectOption('[data-testid="accounting-system"]', options.system);
    await this.page.selectOption('[data-testid="sync-frequency"]', options.syncFrequency);
    
    // Map accounts
    for (const [key, value] of Object.entries(options.accountMapping)) {
      await this.page.fill(`[data-testid="account-${key}"]`, value as string);
    }
    
    await this.page.click('[data-testid="save-configuration"]');
    await this.page.waitForTimeout(1000);
  }

  async runAccountingSync() {
    await this.page.click('[data-testid="run-sync"]');
    await this.page.waitForTimeout(3000);
  }

  async getSyncResults() {
    return {
      status: await this.page.locator('[data-testid="sync-status"]').textContent() || '',
      recordsSynced: parseInt(await this.page.locator('[data-testid="records-synced"]').textContent() || '0'),
      errors: []
    };
  }
}