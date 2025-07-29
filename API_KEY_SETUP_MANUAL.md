# 🔑 LuckyGas v3 API Key Setup Manual

**IMPORTANT**: This manual contains sensitive security information. Handle with care.

## 🚨 Step 1: Immediate Actions Required

### 1.1 Revoke Exposed Google Maps API Key
1. Go to [Google Cloud Console](https://console.cloud.google.com)
2. Navigate to **APIs & Services** → **Credentials**
3. Find and DELETE this key: `AIzaSyDPHBiMtFoSAmd12SbbQU5gZYMQdF6DOcY`
4. Check **Metrics** to see if there was any unauthorized usage

## 📋 Step 2: Create Environment Files

### 2.1 Backend Environment Files

Create these files in the `backend/` directory:

#### `.env.development`
```bash
# Database
DATABASE_URL=postgresql+asyncpg://luckygas:your_dev_password@localhost:5432/luckygas_dev
POSTGRES_USER=luckygas
POSTGRES_PASSWORD=your_dev_password
POSTGRES_DB=luckygas_dev

# Redis
REDIS_URL=redis://localhost:6379/0

# Security
SECRET_KEY=generate_32_char_random_string_for_dev
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_DAYS=7

# CORS
BACKEND_CORS_ORIGINS=["http://localhost:3000","http://localhost:5173"]

# Google Cloud (Development)
GOOGLE_CLOUD_PROJECT=your-project-id
GOOGLE_APPLICATION_CREDENTIALS=/path/to/dev-service-account.json
GOOGLE_MAPS_API_KEY=your_dev_maps_key_with_localhost_restriction

# Vertex AI (Optional - see note below)
VERTEX_AI_LOCATION=asia-east1
VERTEX_AI_MODEL_NAME=lucky-gas-demand-prediction

# SMS - Twilio (Test Credentials)
TWILIO_ACCOUNT_SID=your_test_account_sid
TWILIO_AUTH_TOKEN=your_test_auth_token
TWILIO_FROM_NUMBER=+1234567890

# SMS - Chunghwa Telecom
CHT_SMS_ACCOUNT_ID=your_test_account
CHT_SMS_PASSWORD=your_test_password
CHT_SMS_WEBHOOK_SECRET=generate_random_secret

# Email
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your-email@gmail.com
SMTP_PASSWORD=your-app-specific-password

# Admin
FIRST_SUPERUSER=admin@luckygas.tw
FIRST_SUPERUSER_PASSWORD=strong_admin_password
```

#### `.env.staging`
```bash
# Similar to development but with:
BACKEND_CORS_ORIGINS=["https://staging.luckygas.com.tw"]
GOOGLE_MAPS_API_KEY=staging_key_with_domain_restriction
# Use staging database credentials
# Use staging SMS credentials
```

#### `.env.production`
```bash
# Production values with maximum security
BACKEND_CORS_ORIGINS=["https://luckygas.com.tw","https://www.luckygas.com.tw"]
# Production database with strong passwords
# Production API keys with strict restrictions
# Remove all debug flags
```

### 2.2 Frontend Environment Files

Create these files in the `frontend/` directory:

#### `.env.development`
```bash
VITE_API_URL=http://localhost:8000
VITE_WS_URL=ws://localhost:8000
VITE_ENVIRONMENT=development
```

#### `.env.staging`
```bash
VITE_API_URL=https://api-staging.luckygas.com.tw
VITE_WS_URL=wss://api-staging.luckygas.com.tw
VITE_ENVIRONMENT=staging
```

#### `.env.production`
```bash
VITE_API_URL=https://api.luckygas.com.tw
VITE_WS_URL=wss://api.luckygas.com.tw
VITE_ENVIRONMENT=production
```

## 🔐 Step 3: Google Cloud Setup

### 3.1 Create Service Account
1. Go to **IAM & Admin** → **Service Accounts**
2. Create new service account: `luckygas-backend-dev`
3. Grant roles:
   - `Vertex AI User` (if using AI features)
   - `Storage Object Admin` (for photo uploads)
4. Create and download JSON key
5. Save as `backend/credentials/dev-service-account.json`

### 3.2 Create Google Maps API Keys

For each environment, create a separate key:

#### Development Key
- Name: `luckygas-maps-dev`
- Application restrictions: **HTTP referrers**
- Website restrictions:
  ```
  http://localhost:3000/*
  http://localhost:5173/*
  http://127.0.0.1:*/*
  ```
- API restrictions: 
  - Maps JavaScript API
  - Places API
  - Geocoding API
  - Directions API
- Quotas: 100 requests/day

#### Staging Key
- Name: `luckygas-maps-staging`
- Website restrictions:
  ```
  https://staging.luckygas.com.tw/*
  https://*.staging.luckygas.com.tw/*
  ```
- Quotas: 1,000 requests/day

#### Production Key
- Name: `luckygas-maps-prod`
- Website restrictions:
  ```
  https://luckygas.com.tw/*
  https://www.luckygas.com.tw/*
  ```
- Quotas: 50,000 requests/day

## 🤖 Step 4: Vertex AI Decision

### Is Vertex AI Needed?

Based on the codebase analysis, Vertex AI is **OPTIONAL** but recommended for:

1. **Demand Prediction** - Predict gas cylinder orders by area
2. **Route Optimization** - Optimize delivery routes
3. **Customer Churn Prediction** - Identify at-risk customers

**Current Status**: The code has Vertex AI integration but also includes mock services for development without it.

### If YES - Using Vertex AI:
1. Enable Vertex AI API in Google Cloud Console
2. The service account created above already has permissions
3. No additional API key needed (uses service account)

### If NO - Skip Vertex AI:
1. The system will use mock predictions
2. Set these to empty in `.env`:
   ```bash
   VERTEX_AI_LOCATION=
   VERTEX_AI_MODEL_NAME=
   ```

## 📱 Step 5: SMS Gateway Setup

### 5.1 Twilio Setup
1. Create account at [twilio.com](https://www.twilio.com)
2. Get credentials from Console:
   - Account SID
   - Auth Token
   - Phone Number
3. For development, use test credentials
4. Configure webhook URL: `https://your-domain/api/v1/webhooks/sms/twilio`

### 5.2 Chunghwa Telecom Setup
1. Contact business support for API access
2. Get credentials:
   - Account ID
   - Password
   - API Endpoint
3. Configure webhook URL: `https://your-domain/api/v1/webhooks/sms/cht`

## 💰 Step 6: Banking SFTP (Production Only)

### For Each Bank Partner:
1. **E.Sun Bank (玉山銀行)**:
   ```bash
   ESUN_SFTP_HOST=sftp.esunbank.com.tw
   ESUN_SFTP_PORT=22
   ESUN_SFTP_USERNAME=lucky_gas_prod
   ESUN_SFTP_PRIVATE_KEY_PATH=/secure/keys/esun_rsa
   ```

2. **Generate PGP Keys**:
   ```bash
   # Generate key pair for each bank
   gpg --gen-key
   # Export public key for bank
   gpg --export -a "Lucky Gas" > luckygas_public.asc
   ```

## 🚀 Step 7: Secret Manager Setup

### 7.1 Google Secret Manager (Recommended)
```bash
# Enable Secret Manager API
gcloud services enable secretmanager.googleapis.com

# Create secrets
gcloud secrets create google-maps-api-key-dev --data-file=-
gcloud secrets create twilio-auth-token-prod --data-file=-

# Grant access to service account
gcloud secrets add-iam-policy-binding google-maps-api-key-dev \
    --member="serviceAccount:luckygas-backend-dev@PROJECT_ID.iam.gserviceaccount.com" \
    --role="roles/secretmanager.secretAccessor"
```

### 7.2 Update Code to Use Secret Manager
The code already has Secret Manager integration. Just ensure:
```python
# backend/app/core/config.py
USE_SECRET_MANAGER = True  # Enable in staging/production
```

## ✅ Step 8: Validation Checklist

### Development Environment
- [ ] All `.env.development` files created
- [ ] Google Maps key works on localhost
- [ ] Can send test SMS (Twilio test credentials)
- [ ] Database connection successful
- [ ] Frontend can connect to backend API

### Before Staging Deployment
- [ ] All staging API keys created with domain restrictions
- [ ] Secret Manager configured
- [ ] Webhook URLs configured for SMS providers
- [ ] SSL certificates ready

### Before Production
- [ ] All production keys have maximum restrictions
- [ ] Banking SFTP credentials secured
- [ ] Key rotation schedule documented
- [ ] Monitoring alerts configured
- [ ] Security audit completed

## 🔄 Step 9: Key Rotation Schedule

Set calendar reminders for:
- **Monthly**: Review API usage and anomalies
- **Quarterly**: Rotate Google Maps, SMS, JWT keys
- **Semi-Annually**: Rotate Vertex AI service account
- **Annually**: Rotate banking SFTP credentials

## 📞 Step 10: Emergency Contacts

Keep these contacts ready:
- Google Cloud Support: [Your support plan]
- Twilio Support: support@twilio.com
- Banking Technical Contacts: [Per bank]
- Your Security Team: [Internal contacts]

## 🎯 Quick Start Commands

```bash
# 1. Clone and setup
cd backend
cp .env.example .env.development
# Edit with your keys

# 2. Test connection
python -c "from app.core.config import settings; print(settings.GOOGLE_MAPS_API_KEY[:10] + '...')"

# 3. Start development
docker-compose up -d
cd backend && uvicorn app.main:app --reload
cd frontend && npm run dev

# 4. Verify API proxy works (no keys in frontend)
# Open browser DevTools Network tab
# Check that map requests go through /api/v1/maps/
```

## ⚠️ Security Reminders

1. **NEVER** commit `.env` files to git
2. **NEVER** expose API keys in frontend code
3. **ALWAYS** use the backend proxy for external APIs
4. **ALWAYS** restrict API keys by domain/IP
5. **MONITOR** API usage for anomalies
6. **ROTATE** keys regularly
7. **USE** Secret Manager in production

---

**Next Step**: After setting up all keys, run the security validation:
```bash
cd backend
python security_scan.py
```

This will verify no keys are exposed in the codebase.