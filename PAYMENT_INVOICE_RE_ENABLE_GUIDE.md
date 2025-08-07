# Payment and Invoice System Re-enabling Guide

## Overview

The payment and invoice management system has been temporarily disabled using feature flags. All data has been preserved and the system can be re-enabled at any time without data loss.

## What Was Disabled

### Backend Components
1. **API Endpoints** (return 404 when disabled):
   - `/api/v1/invoices/*` - Invoice management endpoints
   - `/api/v1/payments/*` - Payment recording endpoints
   - `/api/v1/banking/*` - Banking integration endpoints
   - `/api/v1/financial-reports/*` - Financial reporting endpoints

2. **Database Tables** (data preserved):
   - `invoices` - Invoice records
   - `invoice_items` - Invoice line items
   - `credit_notes` - Credit note records
   - `payments` - Payment records
   - `payment_batches` - Batch payment records
   - `payment_transactions` - Transaction records
   - `reconciliation_logs` - Bank reconciliation logs
   - `invoice_sequences` - Invoice numbering sequences

### Frontend Components
1. **Hidden UI Elements**:
   - Revenue statistics on dashboard
   - Monthly revenue card in order management
   - Payment status and amount columns in orders table
   - Payment method and status fields in order forms
   - Credit summary component
   - Invoice title and payment method in customer list
   - Financial dashboard route (`/admin/financial`)
   - Total amount displays in order details

2. **Removed Form Fields**:
   - Payment method selection
   - Payment status selection
   - Invoice title input
   - Credit-related fields

## How to Re-enable

### Step 1: Enable Backend Features

Set the following environment variables:

```bash
# Enable all payment/invoice features
export ENABLE_PAYMENT_SYSTEM=true
export ENABLE_INVOICE_SYSTEM=true
export ENABLE_BANKING_SYSTEM=true
export ENABLE_FINANCIAL_REPORTS=true

# Or add to your .env file
ENABLE_PAYMENT_SYSTEM=true
ENABLE_INVOICE_SYSTEM=true
ENABLE_BANKING_SYSTEM=true
ENABLE_FINANCIAL_REPORTS=true
```

### Step 2: Enable Frontend Features

Set the following environment variables for the frontend:

```bash
# Enable frontend payment/invoice features
export VITE_ENABLE_PAYMENTS=true
export VITE_ENABLE_INVOICES=true
export VITE_ENABLE_BANKING=true
export VITE_ENABLE_FINANCIAL_REPORTS=true

# Or add to your .env file
VITE_ENABLE_PAYMENTS=true
VITE_ENABLE_INVOICES=true
VITE_ENABLE_BANKING=true
VITE_ENABLE_FINANCIAL_REPORTS=true
```

### Step 3: Restart Services

```bash
# Backend
cd backend
uv run uvicorn app.main:app --reload

# Frontend
cd frontend
npm run dev
```

### Step 4: Verify Re-enabling

1. Check API endpoints are accessible:
   ```bash
   curl http://localhost:8000/api/v1/invoices
   # Should return data instead of 404
   ```

2. Verify UI elements are visible:
   - Dashboard shows revenue statistics
   - Order management shows payment columns
   - Customer list shows invoice fields
   - Financial dashboard is accessible

## Data Recovery

All existing payment and invoice data has been preserved. If you ran the backup migration:

### Check Backup Tables
```sql
-- List backup tables
SELECT table_name 
FROM information_schema.tables 
WHERE table_name LIKE '%_backup_20250806';

-- Check backup data
SELECT COUNT(*) FROM invoices_backup_20250806;
SELECT COUNT(*) FROM payments_backup_20250806;
```

### Restore from Backup (if needed)
```bash
python migrations/restore_payment_data.py
```

## Feature Flag Configuration

### Backend Feature Flags
Location: `backend/app/core/config.py`

```python
ENABLE_PAYMENT_SYSTEM: bool = Field(
    False,  # Default disabled
    description="Enable payment processing features",
    env="ENABLE_PAYMENT_SYSTEM"
)
ENABLE_INVOICE_SYSTEM: bool = Field(
    False,  # Default disabled
    description="Enable invoice generation and management",
    env="ENABLE_INVOICE_SYSTEM"
)
ENABLE_BANKING_SYSTEM: bool = Field(
    False,  # Default disabled
    description="Enable banking integration and transfers",
    env="ENABLE_BANKING_SYSTEM"
)
ENABLE_FINANCIAL_REPORTS: bool = Field(
    False,  # Default disabled
    description="Enable financial reporting features",
    env="ENABLE_FINANCIAL_REPORTS"
)
```

### Frontend Feature Flags
Location: `frontend/src/config/features.ts`

```typescript
export const features = {
  payments: import.meta.env.VITE_ENABLE_PAYMENTS === 'true',
  invoices: import.meta.env.VITE_ENABLE_INVOICES === 'true',
  banking: import.meta.env.VITE_ENABLE_BANKING === 'true',
  financialReports: import.meta.env.VITE_ENABLE_FINANCIAL_REPORTS === 'true',
  
  // Helper properties
  get anyPaymentFeature() {
    return this.payments || this.invoices || this.banking || this.financialReports;
  },
  get allPaymentFeatures() {
    return this.payments && this.invoices && this.banking && this.financialReports;
  }
};
```

## Affected Code Locations

### Backend
- `app/main.py` - Conditional route registration
- `app/api/v1/invoices.py` - Invoice endpoints
- `app/api/v1/payments.py` - Payment endpoints
- `app/api/v1/banking.py` - Banking endpoints
- `app/api/v1/financial_reports.py` - Report endpoints

### Frontend
- `src/components/dashboard/Dashboard.tsx` - Revenue statistics
- `src/pages/office/OrderManagement.tsx` - Payment fields and columns
- `src/components/office/CustomerList.tsx` - Invoice fields
- `src/components/office/CustomerDetail.tsx` - Order amount display
- `src/App.tsx` - Financial dashboard route

## Testing After Re-enabling

### Backend Tests
```bash
# Run payment-specific tests
pytest tests/test_payments.py -v
pytest tests/test_invoices.py -v
pytest tests/test_banking.py -v
```

### Frontend Tests
```bash
# Run component tests
npm test -- --testPathPattern="payment|invoice|financial"
```

### E2E Tests
```bash
# Run E2E tests with payment features
VITE_ENABLE_PAYMENTS=true npm run test:e2e
```

## Troubleshooting

### Issue: API endpoints still return 404
**Solution**: Ensure environment variables are set and services are restarted. Check logs for feature flag values.

### Issue: UI elements not showing
**Solution**: Clear browser cache and ensure frontend environment variables start with `VITE_`.

### Issue: Data missing after re-enabling
**Solution**: Check if backup tables exist and run restoration script if needed.

### Issue: Tests failing
**Solution**: Update test configuration to enable feature flags in test environment.

## Partial Re-enabling

You can enable features selectively:

- **Invoices only**: Set only `ENABLE_INVOICE_SYSTEM=true`
- **Payments only**: Set only `ENABLE_PAYMENT_SYSTEM=true`
- **Reports only**: Set only `ENABLE_FINANCIAL_REPORTS=true`

The system is designed to work with any combination of enabled features.

## Contact

For assistance with re-enabling payment/invoice features, contact the development team.

---

Last updated: August 6, 2025