# Production API Integration Deployment Guide

This guide covers the deployment and configuration of production-ready API integrations for LuckyGas, including E-Invoice, Banking SFTP, and SMS gateways.

## Prerequisites

1. **Google Cloud Project** with the following APIs enabled:
   - Secret Manager API
   - Cloud SQL API
   - Cloud Storage API
   - Vertex AI API

2. **Service Account** with permissions:
   - Secret Manager Secret Accessor
   - Cloud SQL Client
   - Storage Object Admin
   - Vertex AI User

3. **Production Credentials** from:
   - Taiwan E-Invoice platform
   - Banking partners (SFTP access)
   - SMS providers (Every8d, Mitake, or Twilio)

## 1. Initialize Production Secrets

First, set up all production secrets using the initialization script:

```bash
cd backend
python scripts/init_production_secrets.py --project-id YOUR_PROJECT_ID
```

This will prompt you to enter credentials for:
- Database passwords
- JWT secret keys
- E-Invoice API credentials
- Banking SFTP credentials (per bank)
- SMS provider credentials

### Manual Secret Creation (Alternative)

If you prefer to create secrets manually:

```bash
# Core secrets
gcloud secrets create database-password --data-file=- < password.txt
gcloud secrets create jwt-secret-key --data-file=- < jwt-secret.txt
gcloud secrets create first-superuser-password --data-file=- < admin-password.txt

# E-Invoice secrets
echo '{"app_id": "YOUR_APP_ID", "api_key": "YOUR_API_KEY"}' | \
  gcloud secrets create einvoice-api-credentials --data-file=-

# Banking secrets (repeat for each bank)
echo '{
  "sftp_username": "username",
  "sftp_password": "password",
  "sftp_host": "sftp.bank.com.tw",
  "sftp_port": 22,
  "sftp_private_key": "-----BEGIN RSA PRIVATE KEY-----..."
}' | gcloud secrets create banking-mega-credentials --data-file=-

# SMS provider secrets
echo '{
  "username": "your_username",
  "password": "your_password",
  "api_url": "https://api.every8d.com/..."
}' | gcloud secrets create sms-every8d-credentials --data-file=-
```

## 2. E-Invoice API Configuration

### Production Endpoints

The E-Invoice service automatically uses production endpoints when `ENVIRONMENT=production`:

- B2B API: `https://einvoice.nat.gov.tw/B2BInvoice`
- B2C API: `https://einvoice.nat.gov.tw/Invoice`

### Certificate Setup

If using certificate-based authentication:

1. Upload certificates to Secret Manager:
```bash
gcloud secrets create einvoice-certificate --data-file=cert.pem
gcloud secrets create einvoice-private-key --data-file=key.pem
```

2. The service will automatically load these in production.

### Circuit Breaker Configuration

Default settings:
- Failure threshold: 5 failures
- Recovery timeout: 300 seconds (5 minutes)
- Request timeout: 30 seconds

Customize in `app/core/einvoice_config.py` if needed.

## 3. Banking SFTP Configuration

### Supported Banks

The system supports SFTP integration with:
- Mega Bank (兆豐銀行)
- CTBC (中國信託)
- E.SUN Bank (玉山銀行)
- First Bank (第一銀行)
- Taishin Bank (台新銀行)

### Connection Pooling

Each bank maintains a connection pool with:
- Max connections: 5
- Keepalive interval: 30 seconds
- Connection timeout: 30 seconds

### File Transfer Features

- **Atomic uploads**: Files are uploaded with `.tmp` extension then renamed
- **Checksum verification**: SHA-256 checksums for file integrity
- **Automatic retry**: 3 attempts with exponential backoff
- **Circuit breaker**: Per-bank circuit breakers (3 failures = 10 minute cooldown)

### File Formats

Supports both fixed-width and CSV formats per Taiwan banking standards:
- Fixed-width: 200 character records with specific field positions
- CSV: BIG5 or UTF-8 encoding with configurable delimiters

## 4. SMS Gateway Configuration

### Provider Priority

The system automatically selects providers based on:
1. Priority setting in database
2. Success rate (historical performance)
3. Circuit breaker state
4. Rate limits

### Rate Limiting

Default rate limits (per minute):
- Every8d: 100 messages
- Mitake: 200 messages
- Twilio: 100 messages

### Delivery Tracking

The service supports:
- Webhook callbacks for delivery status
- Polling-based status checks
- Automatic failover between providers
- A/B testing for message templates

### Circuit Breakers

Per-provider circuit breakers:
- Failure threshold: 5 failures
- Recovery timeout: 180 seconds (3 minutes)
- Half-open testing period: 30 seconds

## 5. Monitoring and Alerting

### Prometheus Metrics

All services expose metrics on `/metrics` endpoint:

```yaml
# E-Invoice metrics
einvoice_requests_total{endpoint, status}
einvoice_request_duration_seconds{endpoint}
einvoice_circuit_breaker_state
einvoice_success_rate

# Banking metrics
banking_sftp_connections{bank_code}
banking_sftp_failures_total{bank_code, error_type}
banking_file_transfers_total{bank_code, direction, status}
banking_transfer_duration_seconds{bank_code, direction}
banking_reconciliation_accuracy{bank_code}

# SMS metrics
sms_messages_sent_total{provider, status, message_type}
sms_messages_delivered_total{provider, message_type}
sms_message_cost_twd{provider}
sms_provider_latency_seconds{provider, operation}
sms_provider_health{provider}
```

### Health Checks

Access health status at `/api/v1/health/`:

```json
{
  "status": "healthy",
  "services": {
    "einvoice": {
      "status": "healthy",
      "response_time": 0.234,
      "circuit_breaker": "closed"
    },
    "banking_mega": {
      "status": "healthy",
      "active_connections": 2,
      "circuit_breaker": "closed"
    },
    "sms_every8d": {
      "status": "healthy",
      "rate_limit_remaining": 87,
      "circuit_breaker": "closed"
    }
  }
}
```

### Alerting Rules

Recommended Prometheus alerting rules:

```yaml
groups:
  - name: api_integration_alerts
    rules:
      - alert: EInvoiceAPIDown
        expr: einvoice_circuit_breaker_state > 0
        for: 5m
        annotations:
          summary: "E-Invoice API circuit breaker is open"
          
      - alert: BankingSFTPFailureRate
        expr: rate(banking_sftp_failures_total[5m]) > 0.1
        annotations:
          summary: "High SFTP failure rate for {{ $labels.bank_code }}"
          
      - alert: SMSProviderUnhealthy
        expr: sms_provider_health == 0
        for: 10m
        annotations:
          summary: "SMS provider {{ $labels.provider }} is unhealthy"
```

## 6. Deployment Steps

### 1. Set Environment Variables

```bash
export GOOGLE_APPLICATION_CREDENTIALS=/path/to/service-account.json
export GCP_PROJECT_ID=your-project-id
export ENVIRONMENT=production
```

### 2. Database Migrations

```bash
cd backend
alembic upgrade head
```

### 3. Initialize Invoice Sequences

```sql
-- Run in production database
INSERT INTO invoice_sequences (year_month, prefix, range_start, range_end, current_number, is_active)
VALUES 
  ('202501', 'AA', 10000000, 19999999, 10000000, true),
  ('202501', 'AB', 20000000, 29999999, 20000000, true);
```

### 4. Configure Bank Connections

```sql
-- Insert bank configurations
INSERT INTO bank_configurations (
  bank_code, bank_name, sftp_host, sftp_port, 
  upload_path, download_path, file_format, 
  encoding, is_active
) VALUES 
  ('mega', '兆豐銀行', 'sftp.megabank.com.tw', 22, 
   '/upload', '/download', 'fixed_width', 'BIG5', true),
  ('ctbc', '中國信託', 'sftp.ctbc.com.tw', 22,
   '/payment/upload', '/payment/download', 'csv', 'UTF-8', true);
```

### 5. Configure SMS Providers

```sql
-- Insert SMS provider configurations
INSERT INTO provider_configs (
  provider, config, priority, rate_limit, is_active
) VALUES 
  ('every8d', '{}', 100, 100, true),
  ('mitake', '{}', 90, 200, true),
  ('twilio', '{}', 80, 100, false);
```

### 6. Deploy Application

Using Cloud Run:

```bash
# Build and push image
docker build -t gcr.io/$PROJECT_ID/luckygas-backend:latest .
docker push gcr.io/$PROJECT_ID/luckygas-backend:latest

# Deploy
gcloud run deploy luckygas-backend \
  --image gcr.io/$PROJECT_ID/luckygas-backend:latest \
  --platform managed \
  --region asia-east1 \
  --allow-unauthenticated \
  --set-env-vars ENVIRONMENT=production \
  --set-secrets DATABASE_PASSWORD=database-password:latest \
  --set-secrets JWT_SECRET_KEY=jwt-secret-key:latest
```

## 7. Post-Deployment Verification

### 1. Test E-Invoice Integration

```bash
# Health check
curl https://your-app.run.app/api/v1/einvoice/health

# Test invoice submission (use test endpoint first)
curl -X POST https://your-app.run.app/api/v1/einvoice/test \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"invoice_number": "AA10000001", "amount": 1000}'
```

### 2. Test Banking SFTP

```bash
# Check connection status
curl https://your-app.run.app/api/v1/banking/mega/status \
  -H "Authorization: Bearer $TOKEN"

# Test file upload
curl -X POST https://your-app.run.app/api/v1/banking/mega/test-upload \
  -H "Authorization: Bearer $TOKEN"
```

### 3. Test SMS Gateway

```bash
# Send test SMS
curl -X POST https://your-app.run.app/api/v1/sms/test \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"phone": "0912345678", "message": "Test message"}'
```

## 8. Troubleshooting

### Common Issues

1. **Secret Manager Access Denied**
   - Ensure service account has `Secret Manager Secret Accessor` role
   - Check `GOOGLE_APPLICATION_CREDENTIALS` is set correctly

2. **SFTP Connection Timeout**
   - Verify firewall rules allow outbound connections
   - Check if bank requires IP whitelisting
   - Test with manual SFTP client first

3. **E-Invoice API Errors**
   - Verify certificate files are correctly formatted
   - Check API credentials in Secret Manager
   - Review audit logs in Cloud Logging

4. **SMS Delivery Failures**
   - Check provider rate limits
   - Verify phone number format (Taiwan mobile)
   - Review circuit breaker states

### Debug Mode

Enable debug logging for detailed troubleshooting:

```python
# In production config
LOG_LEVEL=DEBUG  # Temporary for debugging
```

### Log Queries

Useful Cloud Logging queries:

```
# E-Invoice errors
resource.type="cloud_run_revision"
jsonPayload.service="einvoice"
severity>=ERROR

# SFTP failures
resource.type="cloud_run_revision"
jsonPayload.bank_code="mega"
jsonPayload.error_type="SFTPConnectionError"

# SMS circuit breaker events
resource.type="cloud_run_revision"
textPayload=~"Circuit breaker opened for SMS provider"
```

## Security Considerations

1. **Never commit credentials** to version control
2. **Use Secret Manager** for all sensitive data
3. **Enable audit logging** for compliance
4. **Implement IP whitelisting** where supported
5. **Regular credential rotation** (quarterly recommended)
6. **Monitor for anomalies** in API usage patterns

## Support Contacts

- **E-Invoice Platform**: support@einvoice.nat.gov.tw
- **Banking Integration**: Contact your bank's IT department
- **SMS Providers**: 
  - Every8d: support@every8d.com
  - Mitake: service@mitake.com.tw
  - Twilio: support@twilio.com