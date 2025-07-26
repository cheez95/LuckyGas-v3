import { test, expect } from '../fixtures/test-helpers';
import { LoginPage } from '../pages/LoginPage';
import { DashboardPage } from '../pages/DashboardPage';
import { PaymentPage } from '../pages/PaymentPage';
import { TestUsers, TestPayments, SuccessMessages } from '../fixtures/test-data';

test.describe('Payment Processing E2E Tests', () => {
  let loginPage: LoginPage;
  let dashboardPage: DashboardPage;
  let paymentPage: PaymentPage;

  test.beforeEach(async ({ page }) => {
    loginPage = new LoginPage(page);
    dashboardPage = new DashboardPage(page);
    paymentPage = new PaymentPage(page);
    
    // Login as office staff
    await loginPage.goto();
    await loginPage.login(TestUsers.officeStaff.email, TestUsers.officeStaff.password);
    await dashboardPage.waitForPageLoad();
  });

  test.describe('Payment Batch Creation', () => {
    test('should create payment batch for pending orders', async ({ page }) => {
      await dashboardPage.navigateTo('payments');
      await paymentPage.waitForPageLoad();
      
      // Filter pending payments
      await paymentPage.filterByStatus('pending');
      
      // Select orders for batch
      await paymentPage.selectDateRange(
        new Date().toISOString().split('T')[0],
        new Date().toISOString().split('T')[0]
      );
      
      // Check if there are pending payments
      const pendingCount = await paymentPage.getPendingPaymentCount();
      if (pendingCount === 0) {
        test.skip();
        return;
      }
      
      // Select all pending payments
      await paymentPage.selectAllPayments();
      
      // Create batch
      await paymentPage.createPaymentBatch({
        batchName: `批次_${new Date().toLocaleDateString('zh-TW')}`,
        paymentMethod: 'bank_transfer',
        dueDate: new Date(Date.now() + 7 * 24 * 60 * 60 * 1000) // 7 days from now
      });
      
      // Verify batch creation
      await expect(page.locator('[data-testid="success-message"]')).toContainText('付款批次已建立');
      
      // Verify batch appears in list
      const batchNumber = await paymentPage.getLatestBatchNumber();
      expect(batchNumber).toMatch(/^PAY\d{8}-\d{3}$/);
    });

    test('should generate bank transfer file', async ({ page }) => {
      await dashboardPage.navigateTo('payments');
      await paymentPage.waitForPageLoad();
      
      // Navigate to batch list
      await paymentPage.navigateToBatchList();
      
      // Select latest batch
      const latestBatch = await paymentPage.selectLatestBatch();
      
      // Generate bank file
      await paymentPage.generateBankFile({
        fileFormat: 'ach', // ACH format for Taiwan banks
        bankCode: '812', // Bank of Taiwan
        accountNumber: '1234567890123'
      });
      
      // Verify file download
      const download = await page.waitForEvent('download');
      expect(download.suggestedFilename()).toMatch(/^ACH_\d{8}_\d{6}\.txt$/);
      
      // Verify file content format
      const content = await download.createReadStream();
      // Would verify ACH format here
    });

    test('should handle multiple payment methods in batch', async ({ page }) => {
      await dashboardPage.navigateTo('payments');
      await paymentPage.waitForPageLoad();
      
      // Create mixed payment batch
      await paymentPage.createMixedPaymentBatch([
        { method: 'cash', count: 5 },
        { method: 'bank_transfer', count: 10 },
        { method: 'credit_card', count: 3 }
      ]);
      
      // Verify batch summary shows correct breakdown
      const summary = await paymentPage.getBatchSummary();
      expect(summary.cash).toBe(5);
      expect(summary.bankTransfer).toBe(10);
      expect(summary.creditCard).toBe(3);
      expect(summary.total).toBe(18);
    });
  });

  test.describe('Payment Recording', () => {
    test('should record individual payment', async ({ page }) => {
      await dashboardPage.navigateTo('orders');
      
      // Find unpaid order
      await page.click('[data-testid="filter-unpaid"]');
      const unpaidOrder = page.locator('[data-testid="order-row"]').first();
      const orderNumber = await unpaidOrder.getAttribute('data-order-number');
      
      // Record payment
      await unpaidOrder.click();
      await page.click('[data-testid="record-payment-button"]');
      
      await paymentPage.recordPayment({
        amount: 2400,
        method: 'cash',
        referenceNumber: `CASH${Date.now()}`,
        notes: '現金收款'
      });
      
      // Verify payment recorded
      await expect(page.locator('[data-testid="payment-status"]')).toContainText('已付款');
      
      // Verify in payment history
      await page.click('[data-testid="payment-history-tab"]');
      await expect(page.locator(`[data-testid="payment-${orderNumber}"]`)).toBeVisible();
    });

    test('should handle partial payments', async ({ page }) => {
      await dashboardPage.navigateTo('payments');
      
      // Find order with balance
      const orderWithBalance = await paymentPage.findOrderWithBalance();
      
      // Record partial payment
      await paymentPage.recordPartialPayment({
        orderNumber: orderWithBalance.number,
        totalAmount: orderWithBalance.total,
        paidAmount: orderWithBalance.total * 0.5,
        method: 'bank_transfer'
      });
      
      // Verify partial payment status
      await expect(page.locator('[data-testid="payment-status"]')).toContainText('部分付款');
      await expect(page.locator('[data-testid="remaining-balance"]')).toContainText(
        `餘額: NT$ ${orderWithBalance.total * 0.5}`
      );
    });

    test('should process payment import from bank', async ({ page }) => {
      await dashboardPage.navigateTo('payments');
      await paymentPage.navigateToBatchList();
      
      // Upload bank response file
      const bankResponseFile = TestPayments.generateBankResponseFile();
      await paymentPage.uploadBankResponse(bankResponseFile);
      
      // Process imported payments
      await paymentPage.processImportedPayments();
      
      // Verify payments updated
      const processedCount = await paymentPage.getProcessedPaymentCount();
      expect(processedCount).toBeGreaterThan(0);
      
      // Verify success rate
      const successRate = await paymentPage.getPaymentSuccessRate();
      expect(successRate).toBeGreaterThan(90);
    });
  });

  test.describe('Payment Reconciliation', () => {
    test('should reconcile daily payments', async ({ page }) => {
      await dashboardPage.navigateTo('payments');
      await paymentPage.navigateToReconciliation();
      
      // Select date for reconciliation
      const today = new Date().toISOString().split('T')[0];
      await paymentPage.selectReconciliationDate(today);
      
      // Run reconciliation
      await paymentPage.runReconciliation();
      
      // Verify reconciliation results
      const results = await paymentPage.getReconciliationResults();
      expect(results.matched).toBeGreaterThanOrEqual(0);
      expect(results.unmatched).toBeGreaterThanOrEqual(0);
      expect(results.total).toBe(results.matched + results.unmatched);
      
      // Check for discrepancies
      if (results.unmatched > 0) {
        const discrepancies = await paymentPage.getDiscrepancies();
        expect(discrepancies).toHaveLength(results.unmatched);
        
        // Each discrepancy should have required fields
        discrepancies.forEach(d => {
          expect(d).toHaveProperty('orderNumber');
          expect(d).toHaveProperty('expectedAmount');
          expect(d).toHaveProperty('actualAmount');
          expect(d).toHaveProperty('difference');
        });
      }
    });

    test('should generate reconciliation report', async ({ page }) => {
      await dashboardPage.navigateTo('payments');
      await paymentPage.navigateToReconciliation();
      
      // Generate monthly reconciliation report
      await paymentPage.generateReconciliationReport({
        period: 'monthly',
        month: new Date().getMonth(),
        year: new Date().getFullYear(),
        format: 'excel'
      });
      
      // Verify report download
      const download = await page.waitForEvent('download');
      expect(download.suggestedFilename()).toMatch(/^reconciliation_\d{6}\.xlsx$/);
    });

    test('should handle payment adjustments', async ({ page }) => {
      await dashboardPage.navigateTo('payments');
      await paymentPage.navigateToReconciliation();
      
      // Find discrepancy
      const discrepancy = await paymentPage.findDiscrepancy();
      if (!discrepancy) {
        test.skip();
        return;
      }
      
      // Create adjustment
      await paymentPage.createAdjustment({
        orderNumber: discrepancy.orderNumber,
        adjustmentType: 'credit',
        amount: discrepancy.difference,
        reason: '銀行手續費',
        approvedBy: TestUsers.manager.name
      });
      
      // Verify adjustment applied
      await expect(page.locator('[data-testid="adjustment-applied"]')).toBeVisible();
      
      // Re-run reconciliation
      await paymentPage.runReconciliation();
      
      // Verify discrepancy resolved
      const newResults = await paymentPage.getReconciliationResults();
      expect(newResults.unmatched).toBe(0);
    });
  });

  test.describe('Customer Credit Management', () => {
    test('should update customer credit after payment', async ({ page }) => {
      // Create order for customer with credit limit
      const customerWithCredit = TestPayments.customerWithCredit;
      
      await dashboardPage.navigateTo('orders');
      await page.click('[data-testid="create-order"]');
      
      // Create order that uses credit
      const orderAmount = 5000;
      await page.fill('[data-testid="customer-search"]', customerWithCredit.name);
      await page.click(`[data-testid="customer-${customerWithCredit.id}"]`);
      
      // Check available credit
      const availableCredit = await page.locator('[data-testid="available-credit"]').textContent();
      expect(parseInt(availableCredit?.replace(/\D/g, '') || '0')).toBeGreaterThan(orderAmount);
      
      // Complete order
      await page.fill('[data-testid="order-amount"]', orderAmount.toString());
      await page.selectOption('[data-testid="payment-method"]', 'credit');
      await page.click('[data-testid="submit-order"]');
      
      // Verify credit updated
      await page.waitForTimeout(1000);
      const newCredit = await page.locator('[data-testid="available-credit"]').textContent();
      expect(parseInt(newCredit?.replace(/\D/g, '') || '0')).toBe(
        parseInt(availableCredit?.replace(/\D/g, '') || '0') - orderAmount
      );
    });

    test('should enforce credit limits', async ({ page }) => {
      const customerWithLowCredit = TestPayments.customerWithLowCredit;
      
      await dashboardPage.navigateTo('orders');
      await page.click('[data-testid="create-order"]');
      
      // Try to create order exceeding credit
      await page.fill('[data-testid="customer-search"]', customerWithLowCredit.name);
      await page.click(`[data-testid="customer-${customerWithLowCredit.id}"]`);
      
      const availableCredit = 1000; // Low credit limit
      const orderAmount = 5000; // Exceeds limit
      
      await page.fill('[data-testid="order-amount"]', orderAmount.toString());
      await page.selectOption('[data-testid="payment-method"]', 'credit');
      await page.click('[data-testid="submit-order"]');
      
      // Should show credit limit error
      await expect(page.locator('[data-testid="credit-limit-error"]')).toContainText('信用額度不足');
      
      // Order should not be created
      await expect(page.locator('[data-testid="order-created-message"]')).not.toBeVisible();
    });

    test('should generate payment reminder for overdue accounts', async ({ page }) => {
      await dashboardPage.navigateTo('payments');
      await paymentPage.navigateToOverdue();
      
      // Check for overdue accounts
      const overdueCount = await paymentPage.getOverdueAccountCount();
      if (overdueCount === 0) {
        test.skip();
        return;
      }
      
      // Generate reminders
      await paymentPage.generatePaymentReminders({
        reminderType: 'sms_and_email',
        template: 'friendly_reminder',
        includeSummary: true
      });
      
      // Verify reminders sent
      const sentCount = await paymentPage.getRemindersSentCount();
      expect(sentCount).toBe(overdueCount);
      
      // Check reminder log
      await paymentPage.navigateToReminderLog();
      const latestReminder = await paymentPage.getLatestReminder();
      expect(latestReminder.status).toBe('sent');
      expect(latestReminder.recipientCount).toBe(overdueCount);
    });
  });

  test.describe('Payment Reports', () => {
    test('should generate daily payment summary', async ({ page }) => {
      await dashboardPage.navigateTo('payments');
      await paymentPage.navigateToReports();
      
      // Generate daily summary
      await paymentPage.generateDailySummary({
        date: new Date().toISOString().split('T')[0],
        includeDetails: true
      });
      
      // Verify report content
      const summary = await paymentPage.getDailySummaryData();
      expect(summary).toHaveProperty('totalCollected');
      expect(summary).toHaveProperty('cashAmount');
      expect(summary).toHaveProperty('bankTransferAmount');
      expect(summary).toHaveProperty('creditCardAmount');
      expect(summary).toHaveProperty('pendingAmount');
      
      // Verify totals add up
      const calculatedTotal = summary.cashAmount + summary.bankTransferAmount + summary.creditCardAmount;
      expect(calculatedTotal).toBe(summary.totalCollected);
    });

    test('should generate aging report', async ({ page }) => {
      await dashboardPage.navigateTo('payments');
      await paymentPage.navigateToReports();
      
      // Generate aging report
      await paymentPage.generateAgingReport({
        asOfDate: new Date().toISOString().split('T')[0],
        groupBy: 'customer',
        agingBuckets: [30, 60, 90, 120]
      });
      
      // Verify aging buckets
      const agingData = await paymentPage.getAgingReportData();
      expect(agingData).toHaveProperty('current');
      expect(agingData).toHaveProperty('days30');
      expect(agingData).toHaveProperty('days60');
      expect(agingData).toHaveProperty('days90');
      expect(agingData).toHaveProperty('over120');
      
      // Download detailed report
      await paymentPage.downloadAgingDetails('excel');
      const download = await page.waitForEvent('download');
      expect(download.suggestedFilename()).toMatch(/^aging_report_\d{8}\.xlsx$/);
    });
  });

  test.describe('Payment Integration', () => {
    test('should sync with accounting system', async ({ page }) => {
      await dashboardPage.navigateTo('payments');
      await paymentPage.navigateToIntegration();
      
      // Configure accounting sync
      await paymentPage.configureAccountingSync({
        system: 'quickbooks',
        syncFrequency: 'daily',
        accountMapping: {
          cash: '1010',
          bankTransfer: '1020',
          creditCard: '1030',
          accountsReceivable: '1200'
        }
      });
      
      // Run manual sync
      await paymentPage.runAccountingSync();
      
      // Verify sync results
      const syncResults = await paymentPage.getSyncResults();
      expect(syncResults.status).toBe('success');
      expect(syncResults.recordsSynced).toBeGreaterThan(0);
      expect(syncResults.errors).toHaveLength(0);
    });
  });
});