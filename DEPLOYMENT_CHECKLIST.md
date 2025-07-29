# Lucky Gas Production Deployment Checklist

## 🎯 Deployment Overview

This checklist ensures a smooth deployment of the Lucky Gas delivery management system to production. Follow each step carefully and check off completed items.

## 📋 Pre-Deployment Checklist

### 1. Environment Preparation

- [ ] **Google Cloud Project Setup**
  - [ ] Create production GCP project
  - [ ] Enable required APIs:
    - [ ] Cloud Run API
    - [ ] Cloud SQL API
    - [ ] Cloud Storage API
    - [ ] Vertex AI API
    - [ ] Cloud Build API
    - [ ] Secret Manager API
    - [ ] Cloud Monitoring API

- [ ] **Service Accounts**
  - [ ] Create service account for Cloud Run
  - [ ] Create service account for Cloud SQL
  - [ ] Assign appropriate IAM roles:
    - [ ] Cloud SQL Client
    - [ ] Storage Object Admin
    - [ ] Vertex AI User
    - [ ] Secret Manager Secret Accessor

### 2. Infrastructure Setup

- [ ] **Database**
  - [ ] Create Cloud SQL PostgreSQL instance
  - [ ] Configure connection pooling
  - [ ] Set up automated backups
  - [ ] Create production database
  - [ ] Configure SSL connections

- [ ] **Redis**
  - [ ] Deploy Redis (Memorystore or Cloud Run)
  - [ ] Configure persistence
  - [ ] Set up connection limits

- [ ] **Storage**
  - [ ] Create GCS buckets:
    - [ ] `lucky-gas-uploads` - User uploads
    - [ ] `lucky-gas-backups` - Database backups
    - [ ] `lucky-gas-exports` - Report exports
    - [ ] `lucky-gas-models` - ML models
  - [ ] Configure lifecycle policies
  - [ ] Set up CORS policies

### 3. Security Configuration

- [ ] **Secrets Management**
  ```bash
  # Create secrets in Secret Manager
  gcloud secrets create database-url --data-file=-
  gcloud secrets create jwt-secret --data-file=-
  gcloud secrets create google-maps-api-key --data-file=-
  gcloud secrets create vertex-ai-credentials --data-file=-
  gcloud secrets create twilio-credentials --data-file=-
  gcloud secrets create encryption-key --data-file=-
  ```

- [ ] **SSL Certificates**
  - [ ] Generate SSL certificates for domain
  - [ ] Configure Cloud Load Balancer
  - [ ] Set up domain DNS records

- [ ] **API Keys**
  - [ ] Create production Google Maps API key (server-side)
  - [ ] Create production Google Maps API key (client-side)
  - [ ] Configure API key restrictions
  - [ ] Set up usage quotas

### 4. Application Configuration

- [ ] **Environment Variables**
  ```bash
  # Production .env configuration
  ENVIRONMENT=production
  DEBUG=false
  DATABASE_URL=postgresql+asyncpg://user:pass@/dbname?host=/cloudsql/project:region:instance
  REDIS_URL=redis://redis-host:6379
  SECRET_KEY=[generate-strong-key]
  ALLOWED_HOSTS=luckygas.com.tw,api.luckygas.com.tw
  CORS_ORIGINS=https://luckygas.com.tw
  ```

- [ ] **Google Cloud Integration**
  - [ ] Configure Vertex AI endpoint
  - [ ] Set up Cloud Storage integration
  - [ ] Configure Cloud Logging

## 🚀 Deployment Process

### 1. Database Migration

```bash
# Connect to production database
gcloud sql connect luckygas-prod --user=postgres

# Run migrations
cd backend
uv run alembic upgrade head

# Import initial data
uv run python scripts/import_production_data.py
```

### 2. Build and Deploy Backend

```bash
# Build and push Docker image
docker build -t gcr.io/lucky-gas-prod/backend:latest ./backend
docker push gcr.io/lucky-gas-prod/backend:latest

# Deploy to Cloud Run
gcloud run deploy lucky-gas-backend \
  --image gcr.io/lucky-gas-prod/backend:latest \
  --platform managed \
  --region asia-east1 \
  --allow-unauthenticated \
  --set-env-vars-from-file=.env.production \
  --add-cloudsql-instances=lucky-gas-prod:asia-east1:postgres \
  --memory=2Gi \
  --cpu=2 \
  --min-instances=2 \
  --max-instances=100 \
  --concurrency=100
```

### 3. Build and Deploy Frontend

```bash
# Build frontend with production config
cd frontend
npm run build

# Deploy to Cloud Storage + CDN
gsutil -m rsync -r dist/ gs://lucky-gas-frontend/
gsutil -m setmeta -h "Cache-Control:public, max-age=3600" gs://lucky-gas-frontend/**

# Configure Cloud CDN
gcloud compute backend-buckets create lucky-gas-frontend-bucket \
  --gcs-bucket-name=lucky-gas-frontend
```

### 4. Configure Load Balancer

```bash
# Create backend service
gcloud compute backend-services create lucky-gas-api \
  --global \
  --protocol=HTTPS \
  --port-name=https \
  --timeout=30s

# Create URL map
gcloud compute url-maps create lucky-gas-lb \
  --default-service=lucky-gas-api
```

## ✅ Post-Deployment Verification

### 1. Health Checks

- [ ] **API Health**
  ```bash
  curl https://api.luckygas.com.tw/health
  # Expected: {"status": "healthy", "timestamp": "..."}
  ```

- [ ] **Database Connection**
  ```bash
  curl https://api.luckygas.com.tw/api/v1/health/db
  # Expected: {"database": "connected", "migrations": "up-to-date"}
  ```

- [ ] **Redis Connection**
  ```bash
  curl https://api.luckygas.com.tw/api/v1/health/cache
  # Expected: {"cache": "connected", "memory_usage": "..."}
  ```

### 2. Feature Testing

- [ ] **Authentication**
  - [ ] Admin login works
  - [ ] JWT tokens are valid
  - [ ] Role-based access control

- [ ] **Core Features**
  - [ ] Customer management
  - [ ] Order creation
  - [ ] Route optimization
  - [ ] Driver mobile app
  - [ ] Real-time tracking

- [ ] **Integrations**
  - [ ] Google Maps geocoding
  - [ ] SMS notifications
  - [ ] AI predictions
  - [ ] Payment processing

### 3. Performance Testing

```bash
# Load test with k6
k6 run --vus 100 --duration 30s load-test.js
```

- [ ] Response time < 200ms (p95)
- [ ] Error rate < 0.1%
- [ ] Concurrent users > 500

### 4. Security Verification

- [ ] SSL certificate valid
- [ ] CORS properly configured
- [ ] Rate limiting active
- [ ] SQL injection protection
- [ ] XSS protection headers

## 📊 Monitoring Setup

### 1. Configure Alerts

```yaml
# alerting-policy.yaml
displayName: "Lucky Gas Production Alerts"
conditions:
  - displayName: "High Error Rate"
    conditionThreshold:
      filter: 'resource.type="cloud_run_revision" AND severity="ERROR"'
      comparison: COMPARISON_GT
      thresholdValue: 10
      duration: 300s
```

### 2. Dashboard Creation

- [ ] Create Cloud Monitoring dashboard
- [ ] Add key metrics:
  - [ ] Request rate
  - [ ] Error rate
  - [ ] Response time
  - [ ] Active users
  - [ ] Database connections
  - [ ] Cache hit rate

## 🔄 Rollback Plan

### If Issues Occur:

1. **Immediate Rollback**
   ```bash
   # Rollback Cloud Run to previous revision
   gcloud run services update-traffic lucky-gas-backend \
     --to-revisions=lucky-gas-backend-00001-abc=100
   ```

2. **Database Rollback**
   ```bash
   # Restore from backup
   gcloud sql backups restore [BACKUP_ID] \
     --restore-instance=lucky-gas-prod
   ```

3. **Frontend Rollback**
   ```bash
   # Restore previous frontend version
   gsutil -m rsync -r gs://lucky-gas-frontend-backup/ gs://lucky-gas-frontend/
   ```

## 📱 Mobile App Deployment

### Android (Google Play)

- [ ] Build release APK
- [ ] Sign with production keystore
- [ ] Upload to Play Console
- [ ] Complete store listing
- [ ] Submit for review

### iOS (App Store)

- [ ] Build release IPA
- [ ] Upload to App Store Connect
- [ ] Complete metadata
- [ ] Submit for review

## 📝 Final Checklist

- [ ] All tests passing
- [ ] Documentation updated
- [ ] Team training completed
- [ ] Support contacts configured
- [ ] Backup procedures tested
- [ ] Monitoring alerts configured
- [ ] Customer communication sent
- [ ] Go-live schedule confirmed

## 🎉 Go-Live

**Target Date**: _________________

**Responsible Team Members**:
- Technical Lead: _________________
- DevOps Engineer: _________________
- QA Lead: _________________
- Product Manager: _________________

## 📞 Emergency Contacts

- **On-Call Engineer**: +886-9XX-XXX-XXX
- **Database Admin**: +886-9XX-XXX-XXX
- **Google Cloud Support**: [Case Number]
- **Domain Registrar**: [Support Contact]

---

**Remember**: Take backups before any major changes and test thoroughly in staging first!