# Taiwan Government E-Invoice API Integration Requirements

## Overview
This document outlines the requirements for integrating with the Taiwan Government E-Invoice Platform (財政部電子發票整合服務平台).

## API Access Requirements

### 1. Business Registration
- **Requirement**: Valid Taiwan Business Registration (統一編號)
- **Process**: Register company with Ministry of Finance
- **Documents Needed**:
  - Business Registration Certificate
  - Tax Registration Certificate
  - Company Seal

### 2. E-Invoice Platform Registration
- **Website**: https://www.einvoice.nat.gov.tw/
- **Steps**:
  1. Apply for B2B Turnkey Service Account
  2. Complete identity verification
  3. Sign service agreement
  4. Receive APP_ID and API_KEY

### 3. Technical Requirements

#### API Credentials
```bash
# Test Environment
EINVOICE_TEST_APP_ID=<provided_by_ministry>
EINVOICE_TEST_API_KEY=<provided_by_ministry>

# Production Environment
EINVOICE_PROD_APP_ID=<provided_by_ministry>
EINVOICE_PROD_API_KEY=<provided_by_ministry>
```

#### Certificate Requirements (if applicable)
- **Mutual TLS**: Some APIs require client certificates
- **Certificate Path**: Store certificates securely
```bash
EINVOICE_TEST_CERT_PATH=/path/to/test/cert.pem
EINVOICE_TEST_KEY_PATH=/path/to/test/key.pem
EINVOICE_PROD_CERT_PATH=/path/to/prod/cert.pem
EINVOICE_PROD_KEY_PATH=/path/to/prod/key.pem
```

#### QR Code Encryption Key
- **Purpose**: For generating QR codes on invoices
- **Format**: 32-byte AES key
```bash
EINVOICE_QRCODE_AES_KEY=<32_byte_key_from_ministry>
```

### 4. Company Information
Required company information for invoice issuance:
```bash
COMPANY_TAX_ID=<8_digit_tax_id>
COMPANY_NAME=幸福氣有限公司
COMPANY_ADDRESS=<registered_address>
COMPANY_PHONE=<company_phone>
COMPANY_EMAIL=<company_email>
```

## API Endpoints

### Test Environment
- Base URL: `https://wwwtest.einvoice.nat.gov.tw`
- B2B API: `https://wwwtest.einvoice.nat.gov.tw/BIZAPIVAN/biz`
- B2C API: `https://wwwtest.einvoice.nat.gov.tw/INVAPIVAN/invapp`

### Production Environment
- Base URL: `https://www.einvoice.nat.gov.tw`
- B2B API: `https://www.einvoice.nat.gov.tw/BIZAPIVAN/biz`
- B2C API: `https://www.einvoice.nat.gov.tw/INVAPIVAN/invapp`

## Implementation Status

### Current Implementation
- ✅ Complete E-Invoice service with all core functionality
- ✅ Circuit breaker pattern for fault tolerance
- ✅ Automatic retry with exponential backoff
- ✅ Request/response logging for audit trail
- ✅ Mock mode for testing without credentials
- ✅ Traditional Chinese error messages
- ✅ Comprehensive unit tests

### Features Implemented
1. **Invoice Operations**:
   - Submit B2B invoices
   - Submit B2C invoices
   - Void invoices
   - Issue allowances (credit notes)
   - Query invoice status

2. **Validation**:
   - Taiwan tax ID validation
   - Carrier format validation
   - Invoice data validation

3. **Resilience**:
   - Circuit breaker pattern
   - Retry logic with exponential backoff
   - Graceful degradation to mock mode

4. **Security**:
   - HMAC-SHA256 signature generation
   - Certificate support for mutual TLS
   - Sensitive data masking in logs

## Testing

### Mock Mode
The service automatically runs in mock mode when:
- Environment is not "production"
- API credentials are not configured
- Placeholder values are detected

### Test Credentials
For development and testing:
```python
# Mock mode will be activated with these placeholder values
EINVOICE_TEST_APP_ID=PLACEHOLDER_TEST_APP_ID
EINVOICE_TEST_API_KEY=PLACEHOLDER_TEST_API_KEY
```

### Running Tests
```bash
cd backend
pytest tests/services/test_einvoice_service.py -v
```

## Production Deployment Checklist

1. **Obtain Credentials**:
   - [ ] Register with E-Invoice platform
   - [ ] Receive APP_ID and API_KEY
   - [ ] Obtain certificates (if required)
   - [ ] Get QR code encryption key

2. **Configure Environment**:
   - [ ] Set all required environment variables
   - [ ] Store certificates securely
   - [ ] Configure company information

3. **Test Integration**:
   - [ ] Test in sandbox environment
   - [ ] Verify invoice submission
   - [ ] Test error handling
   - [ ] Confirm audit logging

4. **Production Readiness**:
   - [ ] Enable production mode
   - [ ] Configure monitoring
   - [ ] Set up alerts for circuit breaker
   - [ ] Implement backup procedures

## Support and Documentation

### Official Resources
- **Developer Portal**: https://www.einvoice.nat.gov.tw/ein_upload/html/ESQ/ESQ101W.html
- **API Documentation**: Available after registration
- **Technical Support**: 0800-521-988

### Common Issues
1. **Certificate Errors**: Ensure certificates are in PEM format
2. **Signature Failures**: Check API_KEY and parameter ordering
3. **Character Encoding**: Use UTF-8 for Traditional Chinese
4. **Network Timeouts**: Adjust timeout settings if needed

## Compliance Notes

### Legal Requirements
- All B2B transactions must issue e-invoices
- B2C transactions can use paper or e-invoices
- Invoices must be submitted within 7 days
- Keep records for 5 years

### Data Privacy
- Customer data must be protected
- Follow Personal Information Protection Act
- Implement access controls
- Regular security audits