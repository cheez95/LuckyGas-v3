/**
 * Feature flags configuration
 * These flags control which features are enabled in the application
 */

export const features = {
  // Payment and financial features
  payments: import.meta.env.VITE_ENABLE_PAYMENTS === 'true',
  invoices: import.meta.env.VITE_ENABLE_INVOICES === 'true',
  banking: import.meta.env.VITE_ENABLE_BANKING === 'true',
  financialReports: import.meta.env.VITE_ENABLE_FINANCIAL_REPORTS === 'true',
  
  // Combined flag for any payment-related feature
  get anyPaymentFeature() {
    return this.payments || this.invoices || this.banking || this.financialReports;
  },
  
  // Combined flag for all payment features
  get allPaymentFeatures() {
    return this.payments && this.invoices && this.banking && this.financialReports;
  }
};

// Export individual flags for convenience
export const enablePayments = features.payments;
export const enableInvoices = features.invoices;
export const enableBanking = features.banking;
export const enableFinancialReports = features.financialReports;