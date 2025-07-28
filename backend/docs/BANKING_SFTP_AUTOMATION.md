# Banking SFTP Automation System

## Overview

The Banking SFTP automation system provides secure, reliable file transfers for Taiwan banking operations including payment processing and reconciliation. The system implements production-grade features including circuit breakers, connection pooling, PGP encryption, and comprehensive monitoring.

## Architecture Components

### 1. Enhanced SFTP Service (`banking_sftp.py`)

#### Features:
- **Connection Pooling**: Maintains reusable SFTP connections with health monitoring
- **Circuit Breaker Pattern**: Prevents cascading failures with automatic recovery
- **Retry Mechanism**: Exponential backoff with configurable retry limits
- **Transfer Queue**: Failed transfers automatically queued for later processing
- **Metrics Collection**: Prometheus metrics for monitoring and alerting

#### Key Classes:
- `BankingSFTPService`: Main service class for SFTP operations
- `CircuitBreaker`: Implements circuit breaker pattern for fault tolerance
- `ConnectionPool`: Manages SFTP connection lifecycle and health
- `TransferResult`: Data class for transfer operation results

### 2. Taiwan ACH Format Generator (`ach_format.py`)

#### Supported Formats:
- **Fixed-Width Format**: Taiwan banking standard with Big5 encoding support
- **CSV Format**: Alternative format for some banks
- **Reconciliation Parsing**: Handles return files from banks

#### Features:
- Automatic encoding conversion (UTF-8/Big5)
- Taiwan-specific field formatting (dates, amounts, IDs)
- Batch validation before file generation
- Support for all major Taiwan banks

### 3. PGP Encryption Handler (`pgp_handler.py`)

#### Security Features:
- **Dual Implementation**: GPG and native Python cryptography
- **Key Management**: Secure storage via Google Secret Manager
- **Digital Signatures**: File integrity verification
- **Bank-Specific Keys**: Each bank has unique encryption keys

### 4. Scheduled Tasks (`banking_transfers.py`)

#### Automated Tasks:
1. **Daily Payment Generation** (6 AM Taiwan time)
   - Queries pending invoices
   - Creates payment batches
   - Generates ACH files
   - Uploads via SFTP

2. **Reconciliation Checks** (Every 30 minutes during business hours)
   - Checks for new reconciliation files
   - Downloads and processes files
   - Updates transaction statuses
   - Sends notifications for exceptions

3. **Retry Queue Processing** (Hourly)
   - Processes failed transfers
   - Implements intelligent retry strategies

4. **Health Monitoring** (Every 5 minutes)
   - Tests SFTP connections
   - Monitors circuit breaker states
   - Tracks connection pool health

### 5. Banking Monitor API (`banking_monitor.py`)

#### Endpoints:
- `GET /api/v1/banking-monitor/health` - System health status
- `GET /api/v1/banking-monitor/dashboard` - Operations dashboard
- `GET /api/v1/banking-monitor/transfer-history` - Recent transfers
- `GET /api/v1/banking-monitor/batches/{batch_id}` - Batch details
- `POST /api/v1/banking-monitor/test-connection` - Test bank connection
- `POST /api/v1/banking-monitor/batches/generate` - Manual batch generation

## Configuration

### Bank Configuration Model
```python
{
    "bank_code": "ctbc",
    "bank_name": "中國信託",
    "sftp_host": "sftp.ctbcbank.com",
    "sftp_port": 22,
    "upload_path": "/incoming/payments",
    "download_path": "/outgoing/reconciliation",
    "file_format": "fixed_width",
    "encoding": "Big5",
    "payment_file_pattern": "PAY_{YYYYMMDD}_{BATCH}.txt",
    "reconciliation_file_pattern": "REC_{YYYYMMDD}*.txt",
    "cutoff_time": "15:30"
}
```

### Supported Banks
- **mega** (017) - 兆豐銀行
- **ctbc** (822) - 中國信託
- **esun** (808) - 玉山銀行
- **first** (007) - 第一銀行
- **taishin** (812) - 台新銀行

## Security Implementation

### Authentication Methods
1. **Password Authentication**: Basic SFTP authentication
2. **Key-Based Authentication**: RSA/Ed25519 private keys
3. **PGP Encryption**: All files encrypted before transfer

### Credential Management
- Production credentials stored in Google Secret Manager
- Automatic credential rotation support
- Audit logging for all access

## File Formats

### Payment File (Fixed-Width)
```
H[Batch Number    ][Date    ][Bank][Version]...
D[Seq][Transaction ID      ][Account      ][Name          ][Amount      ]...
T[Count][Total Amount      ]...
```

### Reconciliation File
```
D[Seq][Transaction ID      ][Bank Ref    ][Code][Message][Date    ]...
R[Seq][Transaction ID      ][Reason][Date    ][Amount      ]...
```

## Monitoring & Alerting

### Metrics Collected
- SFTP connection success/failure rates
- Transfer duration histograms
- Active connections gauge
- Retry queue size
- Circuit breaker states

### Alerts
- Connection failures > 3 consecutive
- Retry queue size > 100
- Reconciliation mismatches > 5%
- Processing delays > 30 minutes

## Error Handling

### Retry Strategy
1. **Immediate Retry**: Network timeouts
2. **Exponential Backoff**: Connection failures (2^n seconds)
3. **Queue for Later**: After max retries exceeded
4. **Manual Intervention**: Critical failures

### Circuit Breaker States
- **Closed**: Normal operation
- **Open**: Failures exceeded threshold (3 failures)
- **Half-Open**: Testing recovery (after 5 minutes)

## Daily Operations Workflow

### Morning (6:00 AM)
1. Generate payment batches for all active banks
2. Create ACH files with proper encoding
3. Encrypt files using bank PGP keys
4. Upload to bank SFTP servers
5. Send confirmation emails

### Business Hours (8:00 AM - 6:00 PM)
1. Check for reconciliation files every 30 minutes
2. Download and decrypt files
3. Process reconciliation records
4. Update transaction statuses
5. Alert on unmatched transactions

### Evening (7:00 PM)
1. Generate daily summary report
2. Email report to stakeholders
3. Archive processed files

## API Usage Examples

### Test Bank Connection
```bash
curl -X POST http://localhost:8000/api/v1/banking-monitor/test-connection \
  -H "Authorization: Bearer {token}" \
  -H "Content-Type: application/json" \
  -d '{"bank_code": "ctbc"}'
```

### Get Banking Dashboard
```bash
curl http://localhost:8000/api/v1/banking-monitor/dashboard?days=7 \
  -H "Authorization: Bearer {token}"
```

### Trigger Manual Payment Generation
```bash
curl -X POST http://localhost:8000/api/v1/banking-monitor/batches/generate \
  -H "Authorization: Bearer {token}"
```

## Troubleshooting

### Common Issues

1. **Connection Timeout**
   - Check firewall rules
   - Verify SFTP credentials
   - Test network connectivity

2. **Encoding Errors**
   - Verify bank encoding settings
   - Check for special characters in data
   - Use proper Big5 compatible fonts

3. **File Format Rejection**
   - Validate against bank specifications
   - Check field widths and padding
   - Verify checksum calculations

### Debug Commands

```python
# Test SFTP connection
from app.tasks.banking_transfers import test_bank_connection
result = test_bank_connection.delay("ctbc")

# Check retry queue
from app.services.banking_sftp import BankingSFTPService
service = BankingSFTPService(db)
queue_size = service._retry_queue.qsize()

# Manual file upload
result = await service.transfer_file_with_retry(
    bank_config, local_path, remote_path, "upload", encrypt=True
)
```

## Performance Optimization

### Connection Pool Tuning
- Max connections per bank: 5
- Connection timeout: 30 seconds
- Keep-alive interval: 30 seconds
- Health check interval: 60 seconds

### Batch Processing
- Max transactions per batch: 5000
- File size limit: 10 MB
- Concurrent bank processing: 3
- Memory usage optimization for large files

## Compliance & Audit

### Audit Trail
- All file transfers logged with checksums
- User actions tracked with timestamps
- Failed attempts recorded with reasons
- Reconciliation history maintained

### Regulatory Compliance
- Taiwan banking regulations
- PCI DSS for payment data
- GDPR for customer information
- Financial data retention policies

## Future Enhancements

1. **Real-time Notifications**: WebSocket updates for transfer status
2. **Multi-Bank Aggregation**: Consolidated reporting across banks
3. **AI Anomaly Detection**: Identify unusual patterns in reconciliation
4. **Mobile App Integration**: Transfer monitoring on mobile devices
5. **Blockchain Audit Trail**: Immutable transfer history