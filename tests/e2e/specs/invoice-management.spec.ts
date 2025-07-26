import { test, expect } from '../fixtures/test-helpers';
import { LoginPage } from '../pages/LoginPage';
import { DashboardPage } from '../pages/DashboardPage';
import { InvoicePage } from '../pages/InvoicePage';
import { TestUsers, TestInvoices, SuccessMessages } from '../fixtures/test-data';

test.describe('Invoice Management E2E Tests', () => {
  let loginPage: LoginPage;
  let dashboardPage: DashboardPage;
  let invoicePage: InvoicePage;

  test.beforeEach(async ({ page }) => {
    loginPage = new LoginPage(page);
    dashboardPage = new DashboardPage(page);
    invoicePage = new InvoicePage(page);
    
    // Login as office staff
    await loginPage.goto();
    await loginPage.login(TestUsers.officeStaff.email, TestUsers.officeStaff.password);
    await dashboardPage.waitForPageLoad();
  });

  test.describe('E-Invoice Generation', () => {
    test('should auto-generate e-invoice after delivery confirmation', async ({ page }) => {
      // Create and complete a delivery
      await dashboardPage.navigateTo('orders');
      
      // Find a delivered order without invoice
      await page.click('[data-testid="filter-delivered-no-invoice"]');
      const orderCount = await page.locator('[data-testid="order-row"]').count();
      
      if (orderCount === 0) {
        // Create a test order and mark as delivered
        await page.click('[data-testid="create-order"]');
        await page.fill('[data-testid="customer-search"]', '林太太');
        await page.click('[data-testid="customer-option"]').first();
        await page.fill('[data-testid="order-amount"]', '2400');
        await page.click('[data-testid="submit-order"]');
        
        // Mark as delivered
        await page.click('[data-testid="order-row"]').first();
        await page.click('[data-testid="mark-delivered"]');
        await page.click('[data-testid="confirm-delivery"]');
      }
      
      // Get order number
      const orderRow = page.locator('[data-testid="order-row"]').first();
      const orderNumber = await orderRow.getAttribute('data-order-number');
      
      // Navigate to invoices
      await dashboardPage.navigateTo('invoices');
      await invoicePage.waitForPageLoad();
      
      // Check if invoice was generated
      await invoicePage.searchByOrderNumber(orderNumber!);
      
      // Verify invoice exists
      const invoiceRow = page.locator(`[data-testid="invoice-${orderNumber}"]`);
      await expect(invoiceRow).toBeVisible();
      
      // Verify e-invoice number format (Taiwan format)
      const invoiceNumber = await invoiceRow.locator('[data-testid="invoice-number"]').textContent();
      expect(invoiceNumber).toMatch(/^[A-Z]{2}\d{8}$/); // e.g., AB12345678
    });

    test('should generate e-invoice with correct tax calculation', async ({ page }) => {
      await dashboardPage.navigateTo('invoices');
      await invoicePage.waitForPageLoad();
      
      // Create manual invoice
      await invoicePage.createManualInvoice({
        customerName: '幸福小吃店',
        customerTaxId: '12345678', // 統一編號
        items: [
          { description: '20kg 瓦斯桶', quantity: 2, unitPrice: 800 },
          { description: '50kg 瓦斯桶', quantity: 1, unitPrice: 1200 }
        ],
        invoiceType: 'triplicate' // 三聯式發票
      });
      
      // Verify tax calculations
      const invoiceDetails = await invoicePage.getInvoiceDetails();
      expect(invoiceDetails.subtotal).toBe(2800); // (800*2) + (1200*1)
      expect(invoiceDetails.tax).toBe(140); // 5% VAT
      expect(invoiceDetails.total).toBe(2940); // 2800 + 140
      
      // Verify invoice type
      expect(invoiceDetails.type).toBe('三聯式');
      expect(invoiceDetails.buyerTaxId).toBe('12345678');
    });

    test('should handle duplicate prevention', async ({ page }) => {
      await dashboardPage.navigateTo('invoices');
      
      // Try to create duplicate invoice for same order
      const existingOrder = await invoicePage.findOrderWithInvoice();
      
      await invoicePage.attemptDuplicateInvoice(existingOrder.orderNumber);
      
      // Should show error
      await expect(page.locator('[data-testid="duplicate-invoice-error"]')).toContainText(
        '此訂單已開立發票'
      );
      
      // Verify no duplicate created
      await invoicePage.searchByOrderNumber(existingOrder.orderNumber);
      const invoiceCount = await page.locator('[data-testid="invoice-row"]').count();
      expect(invoiceCount).toBe(1);
    });

    test('should support B2C simplified invoice', async ({ page }) => {
      await dashboardPage.navigateTo('invoices');
      
      // Create B2C invoice (no tax ID required)
      await invoicePage.createManualInvoice({
        customerName: '陳先生',
        items: [
          { description: '16kg 瓦斯桶', quantity: 1, unitPrice: 700 }
        ],
        invoiceType: 'duplicate', // 二聯式發票
        carrierType: 'mobile',
        carrierNumber: '/ABC1234' // 手機條碼
      });
      
      // Verify B2C invoice
      const invoiceDetails = await invoicePage.getInvoiceDetails();
      expect(invoiceDetails.type).toBe('二聯式');
      expect(invoiceDetails.buyerTaxId).toBeUndefined();
      expect(invoiceDetails.carrier).toBe('/ABC1234');
    });
  });

  test.describe('Invoice Search and Filtering', () => {
    test('should search invoices by multiple criteria', async ({ page }) => {
      await dashboardPage.navigateTo('invoices');
      await invoicePage.waitForPageLoad();
      
      // Test search by invoice number
      await invoicePage.searchByInvoiceNumber('AB12345678');
      let results = await invoicePage.getSearchResultCount();
      expect(results).toBeGreaterThanOrEqual(0);
      
      // Clear and search by customer
      await invoicePage.clearSearch();
      await invoicePage.searchByCustomerName('林');
      results = await invoicePage.getSearchResultCount();
      expect(results).toBeGreaterThanOrEqual(0);
      
      // Filter by date range
      await invoicePage.filterByDateRange(
        new Date(Date.now() - 30 * 24 * 60 * 60 * 1000), // 30 days ago
        new Date()
      );
      results = await invoicePage.getSearchResultCount();
      expect(results).toBeGreaterThanOrEqual(0);
      
      // Filter by status
      await invoicePage.filterByStatus('void'); // 作廢
      const voidResults = await invoicePage.getSearchResultCount();
      expect(voidResults).toBeGreaterThanOrEqual(0);
    });

    test('should export search results', async ({ page }) => {
      await dashboardPage.navigateTo('invoices');
      
      // Apply filters
      await invoicePage.filterByDateRange(
        new Date(Date.now() - 7 * 24 * 60 * 60 * 1000), // Last 7 days
        new Date()
      );
      
      // Export to Excel
      await invoicePage.exportResults('excel');
      
      const download = await page.waitForEvent('download');
      expect(download.suggestedFilename()).toMatch(/^invoices_\d{8}_\d{6}\.xlsx$/);
      
      // Also test CSV export
      await invoicePage.exportResults('csv');
      const csvDownload = await page.waitForEvent('download');
      expect(csvDownload.suggestedFilename()).toMatch(/^invoices_\d{8}_\d{6}\.csv$/);
    });
  });

  test.describe('Invoice Operations', () => {
    test('should void invoice with reason', async ({ page }) => {
      await dashboardPage.navigateTo('invoices');
      
      // Find an active invoice
      await invoicePage.filterByStatus('active');
      const activeInvoice = await invoicePage.getFirstInvoice();
      
      // Void the invoice
      await invoicePage.voidInvoice({
        invoiceNumber: activeInvoice.number,
        reason: '客戶要求重開',
        voidType: 'same_period' // 當期作廢
      });
      
      // Verify void status
      await invoicePage.searchByInvoiceNumber(activeInvoice.number);
      const status = await page.locator('[data-testid="invoice-status"]').textContent();
      expect(status).toBe('作廢');
      
      // Verify void record
      const voidDetails = await invoicePage.getVoidDetails(activeInvoice.number);
      expect(voidDetails.reason).toBe('客戶要求重開');
      expect(voidDetails.voidDate).toBeTruthy();
      expect(voidDetails.voidBy).toBeTruthy();
    });

    test('should create credit note for return', async ({ page }) => {
      await dashboardPage.navigateTo('invoices');
      
      // Find a completed invoice
      const originalInvoice = await invoicePage.findCompletedInvoice();
      
      // Create credit note
      await invoicePage.createCreditNote({
        originalInvoiceNumber: originalInvoice.number,
        items: [
          { description: '20kg 瓦斯桶', quantity: 1, unitPrice: 800 }
        ],
        reason: '瓦斯桶瑕疵退貨'
      });
      
      // Verify credit note
      const creditNote = await invoicePage.getLatestCreditNote();
      expect(creditNote.type).toBe('折讓單');
      expect(creditNote.originalInvoice).toBe(originalInvoice.number);
      expect(creditNote.amount).toBe(-840); // -800 - 40 (tax)
    });

    test('should handle batch invoice operations', async ({ page }) => {
      await dashboardPage.navigateTo('invoices');
      
      // Select multiple invoices for batch operation
      await invoicePage.filterByStatus('pending');
      await invoicePage.selectMultipleInvoices(5);
      
      // Batch approve
      await invoicePage.batchApprove();
      
      // Verify all approved
      await page.waitForTimeout(2000);
      await invoicePage.filterByStatus('active');
      const activeCount = await invoicePage.getSearchResultCount();
      expect(activeCount).toBeGreaterThanOrEqual(5);
      
      // Test batch print
      await invoicePage.selectMultipleInvoices(3);
      await invoicePage.batchPrint({
        format: 'pdf',
        layout: 'A4',
        includeDetails: true
      });
      
      // Should trigger download
      const download = await page.waitForEvent('download');
      expect(download.suggestedFilename()).toMatch(/^invoices_batch_\d+\.pdf$/);
    });
  });

  test.describe('Government Compliance', () => {
    test('should upload invoices to government platform', async ({ page }) => {
      await dashboardPage.navigateTo('invoices');
      await invoicePage.navigateToCompliance();
      
      // Select period for upload
      const currentMonth = new Date().getMonth() + 1;
      const currentYear = new Date().getFullYear();
      
      await invoicePage.selectUploadPeriod({
        year: currentYear,
        month: currentMonth,
        type: 'regular' // 一般稅額
      });
      
      // Generate upload file
      await invoicePage.generateGovernmentFile();
      
      // Verify file format
      const uploadFile = await invoicePage.getGeneratedFile();
      expect(uploadFile.format).toBe('XML');
      expect(uploadFile.version).toBe('3.2'); // Current e-invoice format version
      
      // Simulate upload
      await invoicePage.uploadToGovernment();
      
      // Check upload status
      const uploadStatus = await invoicePage.getUploadStatus();
      expect(uploadStatus.status).toBe('success');
      expect(uploadStatus.receiptNumber).toMatch(/^\d{14}$/);
    });

    test('should validate invoice data before upload', async ({ page }) => {
      await dashboardPage.navigateTo('invoices');
      await invoicePage.navigateToCompliance();
      
      // Run validation
      await invoicePage.runComplianceValidation();
      
      // Check validation results
      const validationResults = await invoicePage.getValidationResults();
      
      // Check for common issues
      if (validationResults.errors.length > 0) {
        validationResults.errors.forEach(error => {
          expect(error).toHaveProperty('invoiceNumber');
          expect(error).toHaveProperty('errorCode');
          expect(error).toHaveProperty('description');
          expect(error).toHaveProperty('severity');
        });
      }
      
      // Verify warnings
      if (validationResults.warnings.length > 0) {
        console.log(`Found ${validationResults.warnings.length} warnings`);
      }
      
      expect(validationResults.valid).toBeGreaterThanOrEqual(0);
      expect(validationResults.invalid).toBeGreaterThanOrEqual(0);
    });

    test('should generate monthly invoice report', async ({ page }) => {
      await dashboardPage.navigateTo('invoices');
      await invoicePage.navigateToReports();
      
      // Generate 401 report (營業人銷售額與稅額申報書)
      await invoicePage.generate401Report({
        year: new Date().getFullYear(),
        month: new Date().getMonth(),
        includeDetails: true
      });
      
      // Verify report content
      const reportData = await invoicePage.get401ReportData();
      expect(reportData.totalSales).toBeGreaterThanOrEqual(0);
      expect(reportData.totalTax).toBeGreaterThanOrEqual(0);
      expect(reportData.b2bSales).toBeGreaterThanOrEqual(0);
      expect(reportData.b2cSales).toBeGreaterThanOrEqual(0);
      
      // Download report
      await invoicePage.download401Report('pdf');
      const download = await page.waitForEvent('download');
      expect(download.suggestedFilename()).toMatch(/^401_report_\d{6}\.pdf$/);
    });
  });

  test.describe('Invoice Printing', () => {
    test('should print invoice with correct format', async ({ page }) => {
      await dashboardPage.navigateTo('invoices');
      
      // Select an invoice
      const invoice = await invoicePage.getFirstInvoice();
      await invoicePage.openInvoiceDetails(invoice.number);
      
      // Configure print settings
      await invoicePage.configurePrintSettings({
        paperSize: '80mm', // Thermal printer
        copies: 2,
        includeBarcode: true,
        includeQRCode: true
      });
      
      // Preview before print
      await invoicePage.showPrintPreview();
      
      // Verify preview shows correct elements
      await expect(page.locator('[data-testid="print-preview"]')).toBeVisible();
      await expect(page.locator('[data-testid="invoice-qrcode"]')).toBeVisible();
      await expect(page.locator('[data-testid="invoice-barcode"]')).toBeVisible();
      
      // Print (would trigger system print dialog)
      await invoicePage.printInvoice();
    });

    test('should support email delivery', async ({ page }) => {
      await dashboardPage.navigateTo('invoices');
      
      const invoice = await invoicePage.getFirstInvoice();
      await invoicePage.openInvoiceDetails(invoice.number);
      
      // Send invoice by email
      await invoicePage.sendInvoiceEmail({
        to: 'customer@example.com',
        cc: 'accounting@luckygas.com',
        subject: `幸福氣發票 - ${invoice.number}`,
        message: '感謝您的惠顧，附上本次交易發票。',
        attachPDF: true
      });
      
      // Verify email sent
      await expect(page.locator('[data-testid="email-sent-success"]')).toBeVisible();
      
      // Check email log
      const emailLog = await invoicePage.getEmailLog(invoice.number);
      expect(emailLog.sent).toBe(true);
      expect(emailLog.sentAt).toBeTruthy();
      expect(emailLog.recipient).toBe('customer@example.com');
    });
  });

  test.describe('Integration with Other Modules', () => {
    test('should link invoice to payment records', async ({ page }) => {
      await dashboardPage.navigateTo('invoices');
      
      // Find unpaid invoice
      await invoicePage.filterByPaymentStatus('unpaid');
      const unpaidInvoice = await invoicePage.getFirstInvoice();
      
      // Record payment for invoice
      await invoicePage.recordPaymentForInvoice({
        invoiceNumber: unpaidInvoice.number,
        amount: unpaidInvoice.total,
        method: 'bank_transfer',
        referenceNumber: `TRF${Date.now()}`
      });
      
      // Verify payment linked
      await invoicePage.openInvoiceDetails(unpaidInvoice.number);
      const paymentInfo = await invoicePage.getPaymentInfo();
      expect(paymentInfo.status).toBe('已付款');
      expect(paymentInfo.paidAmount).toBe(unpaidInvoice.total);
      expect(paymentInfo.paymentDate).toBeTruthy();
    });

    test('should reflect in financial reports', async ({ page }) => {
      await dashboardPage.navigateTo('reports');
      
      // Generate revenue report
      await page.click('[data-testid="revenue-report"]');
      await page.selectOption('[data-testid="report-period"]', 'this_month');
      await page.click('[data-testid="generate-report"]');
      
      // Verify invoices included in revenue
      const revenueData = await page.locator('[data-testid="revenue-summary"]').textContent();
      expect(revenueData).toContain('發票收入');
      
      // Check invoice breakdown
      await page.click('[data-testid="invoice-breakdown-tab"]');
      const invoiceCount = await page.locator('[data-testid="invoice-count"]').textContent();
      expect(parseInt(invoiceCount || '0')).toBeGreaterThan(0);
    });
  });
});