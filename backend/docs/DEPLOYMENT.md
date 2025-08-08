# LuckyGas Deployment Guide

## Overview
Complete deployment guide for the LuckyGas gas delivery management system on Google Cloud Platform.

## Table of Contents
1. [Prerequisites](#prerequisites)
2. [Environment Setup](#environment-setup)
3. [Backend Deployment](#backend-deployment)
4. [Frontend Deployment](#frontend-deployment)
5. [Database Migration](#database-migration)
6. [Environment Variables](#environment-variables)
7. [Health Checks](#health-checks)
8. [Monitoring](#monitoring)
9. [Rollback Procedures](#rollback-procedures)
10. [Troubleshooting](#troubleshooting)

## Prerequisites

### Required Tools
```bash
# Install Google Cloud SDK
curl https://sdk.cloud.google.com | bash

# Install Docker
# Visit https://docs.docker.com/get-docker/

# Install Python with uv
curl -LsSf https://astral.sh/uv/install.sh | sh

# Install Node.js
curl -fsSL https://deb.nodesource.com/setup_18.x | sudo -E bash -
sudo apt-get install -y nodejs
```

### GCP Services Required
- Cloud Run (Backend API)
- Cloud SQL (PostgreSQL)
- Cloud Storage (Static files)
- Cloud CDN (Frontend)
- Vertex AI (ML predictions)
- Secret Manager (Sensitive configs)

## Environment Setup

### 1. Project Configuration
```bash
# Set project ID
export PROJECT_ID="vast-tributary-466619-m8"
gcloud config set project $PROJECT_ID

# Enable required APIs
gcloud services enable \
  run.googleapis.com \
  cloudsql.googleapis.com \
  storage.googleapis.com \
  secretmanager.googleapis.com \
  aiplatform.googleapis.com
```

### 2. Service Account Setup
```bash
# Create service account
gcloud iam service-accounts create luckygas-backend \
  --display-name="LuckyGas Backend Service"

# Grant permissions
gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:luckygas-backend@$PROJECT_ID.iam.gserviceaccount.com" \
  --role="roles/cloudsql.client"

gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:luckygas-backend@$PROJECT_ID.iam.gserviceaccount.com" \
  --role="roles/storage.objectAdmin"
```

## Backend Deployment

### 1. Build Docker Image
```bash
cd backend

# Build image
docker build -t asia-east1-docker.pkg.dev/$PROJECT_ID/luckygas/backend:latest .

# Push to Artifact Registry
docker push asia-east1-docker.pkg.dev/$PROJECT_ID/luckygas/backend:latest
```

### 2. Deploy to Cloud Run
```bash
gcloud run deploy luckygas-backend \
  --image asia-east1-docker.pkg.dev/$PROJECT_ID/luckygas/backend:latest \
  --region asia-east1 \
  --platform managed \
  --allow-unauthenticated \
  --set-env-vars="ENVIRONMENT=production" \
  --set-env-vars="DATABASE_URL=postgresql+asyncpg://user:pass@/luckygas?host=/cloudsql/$PROJECT_ID:asia-east1:luckygas-db" \
  --add-cloudsql-instances $PROJECT_ID:asia-east1:luckygas-db \
  --service-account luckygas-backend@$PROJECT_ID.iam.gserviceaccount.com \
  --memory 2Gi \
  --cpu 2 \
  --min-instances 1 \
  --max-instances 10 \
  --concurrency 100
```

### 3. Configure Backend Environment
```bash
# Create .env.production
cat > .env.production << EOF
ENVIRONMENT=production
DATABASE_URL=postgresql+asyncpg://luckygas:password@/luckygas?host=/cloudsql/$PROJECT_ID:asia-east1:luckygas-db
SECRET_KEY=$(openssl rand -hex 32)
FIRST_SUPERUSER=admin@luckygas.com
FIRST_SUPERUSER_PASSWORD=$(openssl rand -base64 12)
REDIS_URL=redis://redis:6379
VERTEX_AI_PROJECT=$PROJECT_ID
VERTEX_AI_LOCATION=asia-east1
EOF

# Store secrets in Secret Manager
gcloud secrets create backend-env --data-file=.env.production
```

## Frontend Deployment

### 1. Build Frontend
```bash
cd frontend

# Set production environment
export VITE_API_URL=https://luckygas-backend-xxxxx-de.a.run.app
export VITE_WS_URL=wss://luckygas-backend-xxxxx-de.a.run.app
export VITE_ENV=production

# Build
npm install
npm run build
```

### 2. Deploy to Cloud Storage
```bash
# Create bucket
gsutil mb -l asia-east1 gs://luckygas-frontend-prod

# Upload files
gsutil -m cp -r dist/* gs://luckygas-frontend-prod/

# Set public access
gsutil iam ch allUsers:objectViewer gs://luckygas-frontend-prod

# Configure as website
gsutil web set -m index.html -e 404.html gs://luckygas-frontend-prod
```

### 3. Setup Cloud CDN
```bash
# Create backend bucket
gcloud compute backend-buckets create luckygas-frontend-bucket \
  --gcs-bucket-name=luckygas-frontend-prod

# Create URL map
gcloud compute url-maps create luckygas-frontend-lb \
  --default-backend-bucket=luckygas-frontend-bucket

# Create HTTPS proxy
gcloud compute target-https-proxies create luckygas-frontend-proxy \
  --url-map=luckygas-frontend-lb \
  --ssl-certificates=luckygas-ssl-cert

# Create forwarding rule
gcloud compute forwarding-rules create luckygas-frontend-https \
  --global \
  --target-https-proxy=luckygas-frontend-proxy \
  --ports=443
```

## Database Migration

### 1. Create Cloud SQL Instance
```bash
gcloud sql instances create luckygas-db \
  --database-version=POSTGRES_15 \
  --tier=db-n1-standard-2 \
  --region=asia-east1 \
  --network=default \
  --no-assign-ip \
  --database-flags=max_connections=200 \
  --storage-size=100GB \
  --storage-type=SSD \
  --backup-start-time=03:00
```

### 2. Create Database
```bash
# Create database
gcloud sql databases create luckygas \
  --instance=luckygas-db

# Create user
gcloud sql users create luckygas \
  --instance=luckygas-db \
  --password=secure-password-here
```

### 3. Run Migrations
```bash
# Connect to Cloud SQL proxy
cloud_sql_proxy -instances=$PROJECT_ID:asia-east1:luckygas-db=tcp:5432 &

# Run migrations
cd backend
DATABASE_URL=postgresql://luckygas:password@localhost:5432/luckygas \
  uv run alembic upgrade head

# Import initial data
DATABASE_URL=postgresql://luckygas:password@localhost:5432/luckygas \
  uv run python scripts/import_data.py
```

## Environment Variables

### Backend Environment Variables
```bash
# Required
ENVIRONMENT=production|staging|development
DATABASE_URL=postgresql+asyncpg://...
SECRET_KEY=<32-character-secret>
FIRST_SUPERUSER=admin@luckygas.com
FIRST_SUPERUSER_PASSWORD=<secure-password>

# Google Cloud
VERTEX_AI_PROJECT=vast-tributary-466619-m8
VERTEX_AI_LOCATION=asia-east1
GCS_BUCKET=luckygas-storage

# Redis (for WebSocket)
REDIS_URL=redis://redis:6379

# Optional
CORS_ORIGINS=["https://luckygas.com.tw"]
LOG_LEVEL=INFO
SENTRY_DSN=<sentry-dsn>
```

### Frontend Environment Variables
```bash
# Required
VITE_API_URL=https://api.luckygas.com.tw
VITE_WS_URL=wss://api.luckygas.com.tw
VITE_ENV=production

# Optional
VITE_SENTRY_DSN=<sentry-dsn>
VITE_GA_ID=<google-analytics-id>
```

## Health Checks

### Backend Health Endpoints
```bash
# Basic health check
curl https://api.luckygas.com.tw/api/v1/health

# Readiness check (with dependencies)
curl https://api.luckygas.com.tw/api/v1/health/ready

# Detailed health (requires auth)
curl -H "Authorization: Bearer $TOKEN" \
  https://api.luckygas.com.tw/api/v1/health/detailed
```

### Expected Responses
```json
// Healthy
{
  "status": "healthy",
  "timestamp": "2025-08-08T10:00:00Z",
  "service": "LuckyGas Backend",
  "version": "1.0.0"
}

// Ready
{
  "ready": true,
  "checks": {
    "database": true,
    "redis": true
  }
}
```

## Monitoring

### 1. Cloud Monitoring Setup
```bash
# Create uptime checks
gcloud monitoring uptime-check-configs create luckygas-backend \
  --display-name="LuckyGas Backend Health" \
  --uri="https://api.luckygas.com.tw/api/v1/health" \
  --check-interval=60
```

### 2. Alert Policies
```yaml
# alert-policy.yaml
displayName: "LuckyGas Backend Down"
conditions:
  - displayName: "Uptime check failure"
    conditionThreshold:
      filter: 'metric.type="monitoring.googleapis.com/uptime_check/check_passed"'
      comparison: COMPARISON_LT
      thresholdValue: 1
      duration: 300s
notificationChannels:
  - projects/$PROJECT_ID/notificationChannels/12345
```

### 3. Logging
```bash
# View backend logs
gcloud logging read "resource.type=cloud_run_revision \
  AND resource.labels.service_name=luckygas-backend" \
  --limit 50

# Stream logs
gcloud logging tail "resource.type=cloud_run_revision" \
  --filter="severity>=ERROR"
```

## Rollback Procedures

### 1. Backend Rollback
```bash
# List revisions
gcloud run revisions list --service luckygas-backend

# Rollback to previous revision
gcloud run services update-traffic luckygas-backend \
  --to-revisions=luckygas-backend-00002-abc=100

# Or deploy previous image
gcloud run deploy luckygas-backend \
  --image asia-east1-docker.pkg.dev/$PROJECT_ID/luckygas/backend:v1.0.0
```

### 2. Database Rollback
```bash
# Restore from backup
gcloud sql backups restore BACKUP_ID \
  --restore-instance=luckygas-db

# Or run migration rollback
DATABASE_URL=... uv run alembic downgrade -1
```

### 3. Frontend Rollback
```bash
# Restore previous version
gsutil -m rsync -r -d gs://luckygas-frontend-backup/ gs://luckygas-frontend-prod/

# Clear CDN cache
gcloud compute url-maps invalidate-cdn-cache luckygas-frontend-lb \
  --path="/*"
```

## Troubleshooting

### Common Issues

#### 1. Database Connection Error
```bash
# Check Cloud SQL proxy
gcloud sql instances describe luckygas-db

# Test connection
psql "host=/cloudsql/$PROJECT_ID:asia-east1:luckygas-db dbname=luckygas user=luckygas"
```

#### 2. Cloud Run Deployment Failure
```bash
# Check build logs
gcloud builds list --limit=5

# Check service logs
gcloud run services describe luckygas-backend
```

#### 3. Frontend 404 Errors
```bash
# Check bucket permissions
gsutil iam get gs://luckygas-frontend-prod

# Verify index.html exists
gsutil ls gs://luckygas-frontend-prod/index.html
```

#### 4. WebSocket Connection Issues
```bash
# Check Redis connection
redis-cli -h redis-host ping

# Check WebSocket upgrade headers
curl -i -N -H "Connection: Upgrade" \
  -H "Upgrade: websocket" \
  -H "Sec-WebSocket-Version: 13" \
  -H "Sec-WebSocket-Key: test" \
  https://api.luckygas.com.tw/ws/test
```

## Performance Optimization

### 1. Cloud Run Optimization
```yaml
# Optimal settings
minInstances: 1  # Avoid cold starts
maxInstances: 10  # Scale as needed
cpu: 2
memory: 2Gi
concurrency: 100  # Requests per instance
```

### 2. Database Optimization
```sql
-- Add indexes for common queries
CREATE INDEX idx_orders_scheduled_date ON orders(scheduled_date);
CREATE INDEX idx_orders_status ON orders(status);
CREATE INDEX idx_customers_phone ON customers(phone);

-- Analyze tables
ANALYZE orders;
ANALYZE customers;
```

### 3. Frontend Optimization
```javascript
// vite.config.js
export default {
  build: {
    rollupOptions: {
      output: {
        manualChunks: {
          vendor: ['react', 'react-dom'],
          ui: ['antd'],
          utils: ['lodash', 'moment']
        }
      }
    },
    minify: 'terser',
    terserOptions: {
      compress: {
        drop_console: true
      }
    }
  }
}
```

## Security Checklist

- [ ] All secrets in Secret Manager
- [ ] HTTPS enforced
- [ ] CORS properly configured
- [ ] Authentication required for admin endpoints
- [ ] SQL injection prevention (using ORM)
- [ ] XSS protection (React default)
- [ ] Rate limiting configured
- [ ] Security headers set
- [ ] Regular dependency updates
- [ ] Backup strategy in place

## Deployment Scripts

### Complete Deployment Script
```bash
#!/bin/bash
# deploy.sh

set -e

echo "🚀 Starting LuckyGas deployment..."

# Build and deploy backend
echo "📦 Building backend..."
cd backend
docker build -t asia-east1-docker.pkg.dev/$PROJECT_ID/luckygas/backend:latest .
docker push asia-east1-docker.pkg.dev/$PROJECT_ID/luckygas/backend:latest

echo "☁️ Deploying to Cloud Run..."
gcloud run deploy luckygas-backend \
  --image asia-east1-docker.pkg.dev/$PROJECT_ID/luckygas/backend:latest \
  --region asia-east1

# Build and deploy frontend
echo "🎨 Building frontend..."
cd ../frontend
npm run build

echo "📤 Uploading to Cloud Storage..."
gsutil -m rsync -r -d dist/ gs://luckygas-frontend-prod/

echo "🔄 Invalidating CDN cache..."
gcloud compute url-maps invalidate-cdn-cache luckygas-frontend-lb --path="/*"

echo "✅ Deployment complete!"
```

## Maintenance

### Regular Tasks
1. **Daily**: Check health endpoints, review error logs
2. **Weekly**: Review performance metrics, check backup status
3. **Monthly**: Update dependencies, review security alerts
4. **Quarterly**: Load testing, disaster recovery drill

### Update Procedure
1. Deploy to staging environment first
2. Run integration tests
3. Deploy to production during low-traffic hours
4. Monitor for 30 minutes post-deployment
5. Be ready to rollback if issues arise

## Support

For deployment issues:
1. Check logs in Cloud Console
2. Review this documentation
3. Contact DevOps team
4. Create issue in GitHub repository

---

*Last Updated: 2025-08-08*
*Version: 1.0.0*