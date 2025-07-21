# 🚀 Lucky Gas GCP Infrastructure Setup - DevOps Guide

This directory contains a complete DevOps automation framework for setting up Lucky Gas production infrastructure on Google Cloud Platform.

## 📁 File Structure

```
backend/
├── GCP_SETUP_GUIDE.md          # Original setup guide with manual steps
├── GCP_SETUP_README.md         # This file - DevOps automation guide
├── gcp-setup-preflight.sh      # Pre-flight validation script
├── gcp-setup-execute.sh        # Main automated setup script
├── gcp-setup-rollback.sh       # Rollback script for safe cleanup
├── gcp-monitor.sh              # Infrastructure monitoring script
└── logs/                       # Execution logs and checkpoints
```

## 🎯 Quick Start

### 1. Run Pre-flight Checks

```bash
cd backend
./gcp-setup-preflight.sh
```

This validates:
- ✅ gcloud CLI installation
- ✅ Authentication status
- ✅ Project permissions
- ✅ Billing account access
- ✅ Existing resources

### 2. Execute Setup

```bash
# Dry run first (recommended)
./gcp-setup-execute.sh --dry-run

# Execute for real
./gcp-setup-execute.sh
```

The setup script features:
- 🔄 Checkpoint system (resume from failures)
- 📝 Comprehensive logging
- ❓ Interactive confirmations
- 🛡️ Error handling
- 📊 Progress tracking

### 3. Monitor Infrastructure

```bash
# One-time check
./gcp-monitor.sh

# Continuous monitoring (every hour)
./gcp-monitor.sh --continuous
```

### 4. Rollback (if needed)

```bash
./gcp-setup-rollback.sh
```

Interactive menu for:
- 🗑️ Selective component removal
- 💾 Backup before deletion
- ⚠️ Confirmation prompts
- 📋 Rollback reports

## 📋 Setup Checklist

- [ ] **Prerequisites**
  - [ ] Install gcloud CLI
  - [ ] Authenticate: `gcloud auth login`
  - [ ] Verify billing account access
  - [ ] Review project ID and configuration

- [ ] **Pre-flight**
  - [ ] Run `./gcp-setup-preflight.sh`
  - [ ] Review warnings and recommendations
  - [ ] Fix any blocking issues

- [ ] **Execution**
  - [ ] Run dry-run: `./gcp-setup-execute.sh --dry-run`
  - [ ] Review planned changes
  - [ ] Execute: `./gcp-setup-execute.sh`
  - [ ] Note any manual steps required

- [ ] **Post-Setup**
  - [ ] Run validation: `./gcp-monitor.sh`
  - [ ] Configure manual items in console
  - [ ] Update application configuration
  - [ ] Test GCP integration

## 🔧 Configuration

### Environment Variables

```bash
# Project Configuration
export PROJECT_ID="vast-tributary-466619-m8"
export PROJECT_NAME="Lucky Gas Prod"
export BILLING_ACCOUNT="011479-B04C2D-B0F925"
export REGION="asia-east1"

# Service Account
export SERVICE_ACCOUNT_EMAIL="lucky-gas-prod@${PROJECT_ID}.iam.gserviceaccount.com"
```

### Application Configuration

After setup, update `backend/.env`:

```env
# Google Cloud Configuration
GOOGLE_APPLICATION_CREDENTIALS=/path/to/lucky-gas-prod-key.json
GCP_PROJECT_ID=vast-tributary-466619-m8
GCP_REGION=asia-east1
GCS_BUCKET=lucky-gas-storage

# API Keys (get from console after setup)
GOOGLE_MAPS_API_KEY=your-api-key-here
```

## 📊 What Gets Created

### 1. **Service Account** (Story 1)
- ✅ `lucky-gas-prod` service account
- ✅ Minimal IAM roles (least privilege)
- ✅ Service account key (stored securely)
- ✅ Key rotation script

### 2. **APIs & Services** (Story 2)
- ✅ Routes API (for optimization)
- ✅ Vertex AI (for predictions)
- ✅ Cloud Storage (for files)
- ✅ Secret Manager (for credentials)
- ✅ Monitoring & Logging

### 3. **Storage**
- ✅ `gs://lucky-gas-storage` bucket
- ✅ Folder structure (uploads, exports, backups, ml-models)
- ✅ Lifecycle policies (90-day cleanup)
- ✅ Versioning enabled

### 4. **Security** (Story 3)
- ✅ Cloud Armor policy
- ✅ Rate limiting (50 req/min)
- ✅ Geo-blocking (Taiwan + US only)
- ✅ OWASP protection (XSS, SQLi)
- ✅ Audit logging

## 🔍 Monitoring & Maintenance

### Regular Checks

Run monitoring script regularly:

```bash
# Manual check
./gcp-monitor.sh

# Automated (add to cron)
0 * * * * /path/to/backend/gcp-monitor.sh >> /var/log/gcp-monitor.log 2>&1
```

### Key Metrics Monitored

- 🏥 Service health status
- 💰 Cost tracking and alerts
- 📊 API quota usage
- 🔒 Security events
- ⚡ Performance metrics

### Alerts

The monitoring script will alert on:
- ❌ Service failures
- 💸 Cost overruns (>$500/month warning, >$1000 critical)
- 🔐 Security incidents (auth failures, policy blocks)
- 📈 High error rates

## 🚨 Troubleshooting

### Common Issues

1. **Project Already Exists**
   ```bash
   # Script handles existing projects
   # Will prompt to use existing or create new
   ```

2. **Permission Denied**
   ```bash
   # Ensure you have Project Owner role
   gcloud projects add-iam-policy-binding $PROJECT_ID \
     --member="user:your-email@domain.com" \
     --role="roles/owner"
   ```

3. **Billing Not Enabled**
   ```bash
   # Link billing account
   gcloud beta billing projects link $PROJECT_ID \
     --billing-account=YOUR-BILLING-ACCOUNT
   ```

4. **API Quota Exceeded**
   - Check quotas in console
   - Request increase if needed
   - Implement rate limiting in app

### Recovery Options

1. **Resume from Checkpoint**
   ```bash
   # Script automatically resumes from last successful step
   ./gcp-setup-execute.sh
   ```

2. **Partial Rollback**
   ```bash
   # Interactive rollback menu
   ./gcp-setup-rollback.sh
   ```

3. **Complete Reset**
   ```bash
   # WARNING: Deletes everything
   ./gcp-setup-rollback.sh
   # Select option 6 or 7
   ```

## 📚 Additional Resources

### Scripts Documentation

1. **gcp-setup-preflight.sh**
   - Validates all prerequisites
   - Estimates costs
   - Non-destructive checks only

2. **gcp-setup-execute.sh**
   - Main setup orchestration
   - Checkpoint system for resumability
   - Dry-run mode for testing

3. **gcp-setup-rollback.sh**
   - Interactive rollback menu
   - Selective component removal
   - Backup before deletion

4. **gcp-monitor.sh**
   - Health and performance monitoring
   - Cost tracking
   - Security monitoring
   - Can run continuously

### Manual Steps Required

After automated setup, complete these in the console:

1. **Routes API Quota**
   - Visit: https://console.cloud.google.com/apis/api/routes.googleapis.com/quotas
   - Set to 600 requests/minute

2. **Security Command Center**
   - Visit: https://console.cloud.google.com/security/command-center
   - Enable asset discovery
   - Configure notifications

3. **Budget Alerts**
   - Visit: https://console.cloud.google.com/billing/budgets
   - Set monthly budget
   - Configure alert thresholds

4. **API Key Restrictions**
   - Visit: https://console.cloud.google.com/apis/credentials
   - Restrict to specific domains
   - Add IP restrictions if needed

## 🔒 Security Best Practices

1. **Service Account Keys**
   - ⚠️ Never commit to Git
   - 🔄 Rotate every 90 days
   - 🔐 Store in Secret Manager
   - 📁 Keep local backups secure

2. **IAM Permissions**
   - ✅ Least privilege principle
   - 🔍 Regular audits
   - 👥 Minimize project owners
   - 📝 Document all access

3. **Network Security**
   - 🌍 Geo-restrictions enabled
   - 🚦 Rate limiting active
   - 🛡️ OWASP protection on
   - 📊 Monitor blocked requests

## 💰 Cost Management

### Estimated Monthly Costs

| Service | Estimate | Notes |
|---------|----------|-------|
| Cloud Run | $50-100 | Based on traffic |
| Cloud SQL | $100-200 | db-f1-micro to db-n1-standard-1 |
| Storage | $20-50 | Based on usage |
| Routes API | $50-100 | Based on requests |
| Vertex AI | $50-150 | Based on predictions |
| **Total** | **$270-600** | Monitor actual usage |

### Cost Optimization Tips

1. **Set Budget Alerts**
   - 50% warning threshold
   - 90% critical threshold
   - 100% hard limit

2. **Review Usage Weekly**
   ```bash
   ./gcp-monitor.sh
   ```

3. **Clean Up Unused Resources**
   - Delete old backups
   - Remove unused API keys
   - Disable unused APIs

## 🎯 Next Steps

1. **Test GCP Integration**
   ```bash
   cd backend
   export GOOGLE_APPLICATION_CREDENTIALS=~/.gcp/lucky-gas/lucky-gas-prod-key.json
   uv run python -c "from google.cloud import storage; client = storage.Client(); print('GCS Connected!')"
   ```

2. **Update Application Code**
   - Configure environment variables
   - Test API connections
   - Verify storage access

3. **Set Up CI/CD**
   - Add GCP credentials to CI
   - Configure deployment pipeline
   - Set up staging environment

4. **Production Readiness**
   - Load testing
   - Security audit
   - Disaster recovery plan
   - Documentation update

---

## 📞 Support

- **GCP Issues**: Check logs in `backend/logs/`
- **Script Problems**: Run with `bash -x` for debug output
- **Emergency**: Use rollback script to revert changes

Remember: Always test in dry-run mode first! 🚀