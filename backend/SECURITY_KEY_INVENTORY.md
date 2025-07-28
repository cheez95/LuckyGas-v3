# LuckyGas v3 Security Key Inventory

**Generated**: 2025-01-28
**Classification**: CONFIDENTIAL
**Purpose**: Complete inventory of all API keys, credentials, and secrets required for the system

## 🚨 CRITICAL SECURITY FINDINGS

### 1. Previously Exposed Keys
- **Google Maps API Key**: `AIzaSyDPHBiMtFoSAmd12SbbQU5gZYMQdF6DOcY`
  - **Status**: EXPOSED in commit 5427d04
  - **Action Required**: 🔑 KEY REQUIRED: Google Cloud Console - Please IMMEDIATELY revoke this key
  - **Files Affected**: Removed 20 HTML files in scripts/ directory

### 2. Current Test Credentials in .env
- **Database Password**: `luckygas123` (test environment)
- **JWT Secret**: `test-secret-key-for-testing-only`
- **Superuser Password**: `TestAdmin123!`
- **Risk**: LOW (test environment only)

## 📋 Complete Key Requirements Matrix

### A. Google Cloud Services

#### 1. Google Maps Platform
- **Service**: Maps JavaScript API, Places API, Geocoding API, Directions API
- **Key Name**: `GOOGLE_MAPS_API_KEY`
- **Environments**: Dev, Staging, Production
- **Restrictions Required**:
  - HTTP referrer restrictions (domain whitelist)
  - API restrictions (specific APIs only)
  - Quota limits per API
- **Rotation Schedule**: Quarterly
- **Risk Level**: HIGH (public exposure risk)
- **🔑 KEY REQUIRED**: Google Cloud - Dev/Staging/Prod - Please provide restricted API keys

#### 2. Vertex AI
- **Service**: AI/ML predictions for demand forecasting
- **Key Name**: `GOOGLE_APPLICATION_CREDENTIALS` (Service Account)
- **Environments**: Staging, Production
- **Restrictions Required**:
  - Service account with minimal permissions
  - Vertex AI User role only
  - Resource-specific bindings
- **Rotation Schedule**: Semi-annually
- **Risk Level**: HIGH
- **🔑 KEY REQUIRED**: Google Cloud - Staging/Prod - Please provide service account JSON

#### 3. Cloud Storage
- **Service**: Photo storage for delivery confirmations
- **Key Name**: Uses same `GOOGLE_APPLICATION_CREDENTIALS`
- **Bucket**: `lucky-gas-storage`
- **Permissions**: Storage Object Admin on specific bucket only

### B. SMS Gateway Services

#### 1. Twilio
- **Service**: International SMS delivery
- **Key Names**: 
  - `TWILIO_ACCOUNT_SID`
  - `TWILIO_AUTH_TOKEN`
  - `TWILIO_FROM_NUMBER`
- **Environments**: All
- **Restrictions Required**:
  - Geo-permissions (Taiwan only)
  - Verified phone numbers only
  - Rate limiting
- **Rotation Schedule**: Quarterly
- **Risk Level**: MEDIUM
- **🔑 KEY REQUIRED**: Twilio - All Environments - Please provide credentials

#### 2. Chunghwa Telecom (中華電信)
- **Service**: Local Taiwan SMS delivery
- **Key Names**:
  - `CHT_SMS_ACCOUNT_ID`
  - `CHT_SMS_PASSWORD`
  - `CHT_SMS_WEBHOOK_SECRET`
- **Environments**: All
- **Restrictions Required**:
  - IP whitelist
  - Taiwan numbers only
- **Rotation Schedule**: Semi-annually
- **Risk Level**: MEDIUM
- **🔑 KEY REQUIRED**: Chunghwa Telecom - All Environments - Please provide credentials

### C. Banking Integration

#### 1. SFTP Credentials (Per Bank)
- **Banks**: E.Sun (玉山), Cathay (國泰), First Bank (第一)
- **Key Names per bank**:
  - `{BANK}_SFTP_HOST`
  - `{BANK}_SFTP_PORT`
  - `{BANK}_SFTP_USERNAME`
  - `{BANK}_SFTP_PASSWORD` or SSH Private Key
  - `{BANK}_SFTP_PRIVATE_KEY`
  - `{BANK}_PGP_PUBLIC_KEY`
  - `{BANK}_PGP_PRIVATE_KEY`
  - `{BANK}_PGP_PASSPHRASE`
- **Environments**: Production only
- **Restrictions Required**:
  - IP whitelist (production server only)
  - Certificate-based auth where possible
  - File encryption required
- **Rotation Schedule**: Annually or per bank policy
- **Risk Level**: CRITICAL
- **🔑 KEY REQUIRED**: Banking Partners - Production - Please provide SFTP credentials

### D. Taiwan E-Invoice System

#### 1. Ministry of Finance API
- **Service**: Official e-invoice submission
- **Key Names**:
  - `EINVOICE_MERCHANT_ID`
  - `EINVOICE_API_KEY`
  - `EINVOICE_CERTIFICATE` (P12 file)
  - `EINVOICE_CERTIFICATE_PASSWORD`
- **Environments**: Staging (test), Production
- **Restrictions Required**:
  - Certificate-based authentication
  - IP whitelist
  - Valid business registration
- **Rotation Schedule**: Per government requirement
- **Risk Level**: HIGH
- **🔑 KEY REQUIRED**: Ministry of Finance - Staging/Prod - Please provide API credentials

### E. Email Service

#### 1. SMTP Configuration
- **Service**: Transactional emails
- **Key Names**:
  - `SMTP_HOST`
  - `SMTP_PORT`
  - `SMTP_USER`
  - `SMTP_PASSWORD`
- **Current**: Gmail (needs upgrade for production)
- **Environments**: All
- **Risk Level**: LOW
- **🔑 KEY REQUIRED**: Email Service - All Environments - Please provide SMTP credentials

### F. Infrastructure & Monitoring

#### 1. Database
- **Service**: PostgreSQL
- **Key Names**:
  - `POSTGRES_PASSWORD`
  - `POSTGRES_USER`
- **Environments**: All (different per environment)
- **Risk Level**: CRITICAL
- **🔑 KEY REQUIRED**: Database - All Environments - Please provide strong passwords

#### 2. Redis
- **Service**: Cache and session storage
- **Key Name**: `REDIS_PASSWORD` (if configured)
- **Environments**: All
- **Risk Level**: MEDIUM

#### 3. JWT Secret
- **Service**: Authentication tokens
- **Key Name**: `SECRET_KEY`
- **Requirements**: Min 32 characters, cryptographically secure
- **Environments**: All (unique per environment)
- **Risk Level**: CRITICAL
- **🔑 KEY REQUIRED**: Security - All Environments - Please generate secure JWT secrets

#### 4. Monitoring (Future)
- **Service**: Sentry, DataDog, or similar
- **Key Name**: `SENTRY_DSN` or equivalent
- **Environments**: Staging, Production
- **Risk Level**: LOW

### G. Payment Processing (Future)

#### 1. Payment Gateway
- **Service**: TBD (LINE Pay, JKoPay, etc.)
- **Key Names**: TBD based on provider
- **Risk Level**: CRITICAL

## 🔒 Security Implementation Plan

### Phase 1: Immediate Actions (Day 1)
1. **REVOKE** exposed Google Maps key immediately
2. **AUDIT** git history for other exposed secrets
3. **ROTATE** all test environment credentials
4. **IMPLEMENT** Secret Manager integration

### Phase 2: Development Environment (Days 2-3)
1. **CREATE** development-specific API keys with restrictions
2. **IMPLEMENT** backend proxy for Google Maps
3. **SETUP** local secret management
4. **TEST** all integrations with new keys

### Phase 3: Staging Environment (Week 2)
1. **PROVISION** staging-specific credentials
2. **CONFIGURE** Secret Manager for staging
3. **IMPLEMENT** key rotation automation
4. **VALIDATE** all external service integrations

### Phase 4: Production Preparation (Weeks 3-4)
1. **PROVISION** production credentials with maximum restrictions
2. **IMPLEMENT** monitoring and alerting
3. **SETUP** automated rotation schedules
4. **CONDUCT** security audit

## 📊 Risk Assessment Summary

| Service Category | Risk Level | Key Count | Rotation Frequency |
|-----------------|------------|-----------|-------------------|
| Banking SFTP | CRITICAL | 24+ | Annual |
| Google Cloud | HIGH | 3 | Quarterly |
| SMS Gateways | MEDIUM | 5 | Quarterly |
| E-Invoice | HIGH | 4 | Per regulation |
| Infrastructure | CRITICAL | 3 | Quarterly |
| Email | LOW | 2 | Semi-annual |

## 🚦 Next Steps

1. **User Action Required**: Revoke exposed Google Maps API key
2. **User Action Required**: Provide all required API keys per environment
3. **Implementation**: Secret Manager integration
4. **Implementation**: Backend proxy for all external APIs
5. **Validation**: Security audit and penetration testing

---
**Note**: This document contains sensitive security information. Handle with appropriate care.