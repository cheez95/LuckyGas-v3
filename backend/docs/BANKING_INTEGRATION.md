# Banking System Integration Documentation

## Overview

The LuckyGas Banking System Integration provides automated payment processing and reconciliation via bank SFTP connections. This system handles automatic payment collection (自動扣款) from customers using Taiwan banking standards.

## Features

- **Multi-Bank Support**: Configurable for multiple Taiwan banks
- **SFTP File Exchange**: Secure file transfer for payment and reconciliation files
- **Taiwan Banking Formats**: Support for fixed-width and CSV formats used by Taiwan banks
- **Automatic Reconciliation**: Process bank response files and update payment statuses
- **Circuit Breaker**: Resilient connection handling with automatic recovery
- **Traditional Chinese Support**: Big5 and UTF-8 encoding support
- **Comprehensive Reporting**: Payment status tracking and failed transaction reports

## Architecture

### Database Models

1. **BankConfiguration**: Stores bank-specific SFTP and file format settings
2. **PaymentBatch**: Tracks payment file uploads
3. **PaymentTransaction**: Individual payment records
4. **ReconciliationLog**: Reconciliation file processing results

### Service Layer

The `BankingService` provides:
- SFTP connection management with pooling
- Payment file generation (fixed-width and CSV)
- File upload/download operations
- Reconciliation processing
- Payment status reporting

### API Endpoints

- `POST /api/v1/banking/payment-batches`: Create payment batch
- `POST /api/v1/banking/generate-payment-file`: Generate payment file
- `POST /api/v1/banking/upload-file/{bank_code}`: Upload to bank
- `GET /api/v1/banking/check-reconciliation`: Check for new files
- `POST /api/v1/banking/process-reconciliation`: Process reconciliation
- `GET /api/v1/banking/payment-status/{batch_id}`: Get status report

## Configuration

### Bank Setup

Each bank requires configuration in the database:

```python
{
    "bank_code": "CTBC",
    "bank_name": "中國信託商業銀行",
    "sftp_host": "sftp.ctbcbank.com",
    "sftp_port": 22,
    "sftp_username": "your_username",
    "sftp_password": "encrypted_password",
    "upload_path": "/upload/",
    "download_path": "/download/",
    "file_format": "fixed_width",
    "encoding": "Big5"
}
```

### File Formats

#### Fixed-Width Format (Most Banks)
```
H[Batch Number    ][Date    ][Bank][Version]...
D[Seq][Transaction ID      ][Account    ][Name    ][Amount    ][Date    ]...
T[Count][Total Amount      ]...
```

#### CSV Format (Some Banks)
```csv
交易序號,扣款帳號,戶名,扣款金額,扣款日期,備註
000001,12345678901234,張三,3000,2024/01/20,Invoice: 1
```

## Usage

### 1. Initialize Bank Configurations

```bash
cd backend
python scripts/init_bank_configs.py
```

### 2. Create Payment Batch

```python
# Via API
POST /api/v1/banking/payment-batches
{
    "bank_code": "CTBC",
    "processing_date": "2024-01-20T00:00:00",
    "invoice_ids": [1, 2, 3]  // Optional: specific invoices
}
```

### 3. Generate and Upload Payment File

```python
# Generate file
POST /api/v1/banking/generate-payment-file
{
    "batch_id": 1
}

# Upload to bank
POST /api/v1/banking/upload-file/CTBC
{
    "batch_id": 1
}
```

### 4. Process Reconciliation

```python
# Check for new files
GET /api/v1/banking/check-reconciliation?bank_codes=CTBC

# Process file
POST /api/v1/banking/process-reconciliation
{
    "bank_code": "CTBC",
    "file_name": "REC_20240120.txt"
}
```

### 5. Check Payment Status

```python
GET /api/v1/banking/payment-status/1
```

## File Exchange Process

### Daily Workflow

1. **Morning (08:00)**: 
   - Create payment batch for pending invoices
   - Generate payment files
   - Upload to banks before cutoff time

2. **Afternoon (15:00)**: 
   - Check for reconciliation files
   - Process responses
   - Update payment statuses
   - Handle failed payments

3. **End of Day**:
   - Generate payment reports
   - Notify customers of failed payments

### Error Handling

- **Connection Failures**: Circuit breaker prevents repeated attempts
- **File Format Errors**: Logged with detailed error messages
- **Payment Failures**: Tracked with bank response codes

## Security Considerations

1. **SFTP Authentication**:
   - Support for password and SSH key authentication
   - Credentials should be encrypted in database
   - Use environment variables for sensitive data

2. **File Validation**:
   - Verify file checksums when available
   - Validate record counts and amounts
   - Archive processed files

3. **Access Control**:
   - Only admin/manager roles can process payments
   - Audit logging for all operations
   - Transaction-level tracking

## Testing

### Unit Tests
```bash
pytest tests/services/test_banking_service.py
```

### Integration Tests (with mocked SFTP)
```bash
pytest tests/integration/test_banking_integration.py
```

### Manual Testing
1. Use test bank configurations
2. Generate sample payment files
3. Verify file formats
4. Test reconciliation processing

## Common Bank Response Codes

| Code | Description (繁體中文) | Action Required |
|------|----------------------|-----------------|
| 000  | 交易成功 | None |
| 001  | 餘額不足 | Notify customer |
| 002  | 帳號錯誤 | Verify account |
| 003  | 帳戶已結清 | Update records |
| 004  | 帳戶凍結 | Contact customer |
| 005  | 無此帳號 | Verify with customer |

## Troubleshooting

### SFTP Connection Issues
- Check firewall settings
- Verify credentials
- Test with command line SFTP client
- Check circuit breaker status

### File Format Errors
- Verify encoding (Big5 vs UTF-8)
- Check field lengths for fixed-width
- Validate delimiter for CSV
- Review bank specifications

### Reconciliation Mismatches
- Compare transaction IDs
- Verify amounts match
- Check date formats
- Review bank response codes

## Future Enhancements

1. **Real-time Status Updates**: WebSocket notifications
2. **Batch Scheduling**: Automated daily batch creation
3. **Multi-Currency Support**: For international transactions
4. **API Integration**: Direct API connections for supported banks
5. **Enhanced Reporting**: Business intelligence dashboards