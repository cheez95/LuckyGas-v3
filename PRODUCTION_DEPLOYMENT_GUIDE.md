# 🚀 Lucky Gas Production Deployment Guide

## 📋 Overview

This guide covers the complete production deployment process for Lucky Gas on Google Cloud Platform, including:
- Infrastructure setup
- Security configuration
- Application deployment
- Monitoring setup
- Disaster recovery

## 🏗️ Infrastructure Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        Google Cloud Platform                      │
├─────────────────────────────────────────────────────────────────┤
│                                                                   │
│  ┌─────────────┐     ┌──────────────┐     ┌─────────────────┐  │
│  │   Cloud     │     │    Cloud     │     │     Cloud       │  │
│  │   Load      │────▶│     Run      │────▶│      SQL        │  │
│  │  Balancer   │     │  (Backend)   │     │  (PostgreSQL)   │  │
│  └─────────────┘     └──────────────┘     └─────────────────┘  │
│         │                    │                      │            │
│         │            ┌──────────────┐              │            │
│         │            │   Cloud      │              │            │
│         └───────────▶│   Storage    │              │            │
│                      │  (Frontend)  │              │            │
│                      └──────────────┘              │            │
│                                                    │            │
│  ┌─────────────┐     ┌──────────────┐     ┌──────────────┐    │
│  │  Memorystore│     │   Vertex     │     │   BigQuery   │    │
│  │   (Redis)   │     │     AI       │     │ (Analytics)  │    │
│  └─────────────┘     └──────────────┘     └──────────────┘    │
│                                                                   │
└─────────────────────────────────────────────────────────────────┘
```

## 🔧 Pre-Deployment Checklist

### 1. Google Cloud Setup
- [ ] GCP Project created
- [ ] Billing account configured
- [ ] Required APIs enabled:
  - [ ] Cloud Run API
  - [ ] Cloud SQL Admin API
  - [ ] Cloud Storage API
  - [ ] Vertex AI API
  - [ ] Container Registry API
  - [ ] Cloud Build API
  - [ ] Secret Manager API

### 2. Service Accounts
- [ ] Backend service account created
- [ ] Appropriate IAM roles assigned
- [ ] Service account keys generated (if needed)

### 3. Domain & SSL
- [ ] Domain registered
- [ ] DNS configured
- [ ] SSL certificates ready

### 4. Environment Variables
- [ ] Production secrets configured in Secret Manager
- [ ] Environment-specific configurations ready

## 📦 Backend Deployment

### Step 1: Database Setup

```bash
# Create Cloud SQL instance
gcloud sql instances create luckygas-prod \
  --database-version=POSTGRES_15 \
  --tier=db-n1-standard-2 \
  --region=asia-east1 \
  --network=default \
  --backup \
  --backup-start-time=03:00 \
  --maintenance-window-day=SUN \
  --maintenance-window-hour=4

# Create database
gcloud sql databases create luckygas \
  --instance=luckygas-prod

# Create user
gcloud sql users create luckygas \
  --instance=luckygas-prod \
  --password=[SECURE_PASSWORD]

# Get connection string
gcloud sql instances describe luckygas-prod --format="value(connectionName)"
```

### Step 2: Redis Setup

```bash
# Create Memorystore Redis instance
gcloud redis instances create luckygas-cache \
  --size=2 \
  --region=asia-east1 \
  --redis-version=redis_7_0 \
  --tier=standard
```

### Step 3: Build and Push Docker Image

```bash
cd backend

# Build image
docker build -t gcr.io/[PROJECT_ID]/luckygas-backend:latest .

# Push to Container Registry
docker push gcr.io/[PROJECT_ID]/luckygas-backend:latest
```

### Step 4: Deploy to Cloud Run

Create `cloud-run-deploy.yaml`:
```yaml
apiVersion: serving.knative.dev/v1
kind: Service
metadata:
  name: luckygas-backend
  annotations:
    run.googleapis.com/ingress: all
spec:
  template:
    metadata:
      annotations:
        run.googleapis.com/cloudsql-instances: [PROJECT_ID]:[REGION]:luckygas-prod
        run.googleapis.com/execution-environment: gen2
        autoscaling.knative.dev/minScale: "2"
        autoscaling.knative.dev/maxScale: "100"
    spec:
      serviceAccountName: luckygas-backend@[PROJECT_ID].iam.gserviceaccount.com
      containers:
      - image: gcr.io/[PROJECT_ID]/luckygas-backend:latest
        ports:
        - containerPort: 8000
        resources:
          limits:
            cpu: "2"
            memory: "2Gi"
        env:
        - name: DATABASE_URL
          valueFrom:
            secretKeyRef:
              name: database-url
              key: latest
        - name: REDIS_URL
          valueFrom:
            secretKeyRef:
              name: redis-url
              key: latest
        - name: SECRET_KEY
          valueFrom:
            secretKeyRef:
              name: secret-key
              key: latest
        - name: ENVIRONMENT
          value: "production"
        - name: CORS_ORIGINS
          value: '["https://luckygas.com.tw","https://www.luckygas.com.tw"]'
```

Deploy:
```bash
gcloud run services replace cloud-run-deploy.yaml --region=asia-east1
```

### Step 5: Configure Secrets

```bash
# Create secrets in Secret Manager
echo -n "postgresql+asyncpg://luckygas:[PASSWORD]@/luckygas?host=/cloudsql/[CONNECTION_NAME]" | \
  gcloud secrets create database-url --data-file=-

echo -n "redis://[REDIS_IP]:6379" | \
  gcloud secrets create redis-url --data-file=-

echo -n "[GENERATE_SECURE_SECRET_KEY]" | \
  gcloud secrets create secret-key --data-file=-

# Grant access to service account
gcloud secrets add-iam-policy-binding database-url \
  --member="serviceAccount:luckygas-backend@[PROJECT_ID].iam.gserviceaccount.com" \
  --role="roles/secretmanager.secretAccessor"
```

## 🎨 Frontend Deployment

### Step 1: Build Frontend

```bash
cd frontend

# Create production environment file
cat > .env.production << EOF
VITE_API_URL=https://api.luckygas.com.tw
VITE_WS_URL=wss://api.luckygas.com.tw
VITE_GOOGLE_MAPS_API_KEY=[YOUR_API_KEY]
VITE_ENVIRONMENT=production
EOF

# Build for production
npm run build
```

### Step 2: Deploy to Cloud Storage

```bash
# Create bucket
gsutil mb -p [PROJECT_ID] -c standard -l asia-east1 gs://luckygas-frontend

# Enable website configuration
gsutil web set -m index.html -e 404.html gs://luckygas-frontend

# Upload files
gsutil -m rsync -r -d dist/ gs://luckygas-frontend/

# Set public access
gsutil iam ch allUsers:objectViewer gs://luckygas-frontend
```

### Step 3: Configure CDN

```bash
# Create backend bucket
gcloud compute backend-buckets create luckygas-frontend-backend \
  --gcs-bucket-name=luckygas-frontend

# Create URL map
gcloud compute url-maps create luckygas-lb \
  --default-backend-bucket=luckygas-frontend-backend

# Create HTTPS proxy
gcloud compute target-https-proxies create luckygas-https-proxy \
  --url-map=luckygas-lb \
  --ssl-certificates=luckygas-ssl-cert

# Create forwarding rule
gcloud compute forwarding-rules create luckygas-https-rule \
  --global \
  --target-https-proxy=luckygas-https-proxy \
  --ports=443
```

## 🔒 Security Configuration

### 1. Cloud Armor Setup

```bash
# Create security policy
gcloud compute security-policies create luckygas-security-policy \
  --description="Lucky Gas security policy"

# Add rate limiting rule
gcloud compute security-policies rules create 1000 \
  --security-policy=luckygas-security-policy \
  --expression="true" \
  --action=rate-based-ban \
  --rate-limit-threshold-count=100 \
  --rate-limit-threshold-interval-sec=60 \
  --ban-duration-sec=600

# Add country blocking (if needed)
gcloud compute security-policies rules create 2000 \
  --security-policy=luckygas-security-policy \
  --expression="origin.region_code != 'TW'" \
  --action=deny-403

# Attach to backend service
gcloud compute backend-services update luckygas-backend \
  --security-policy=luckygas-security-policy --global
```

### 2. Identity-Aware Proxy (Optional)

```bash
# Enable IAP for Cloud Run
gcloud iap web enable --resource-type=backend-services \
  --service=luckygas-backend

# Add authorized users
gcloud iap web add-iam-policy-binding \
  --resource-type=backend-services \
  --service=luckygas-backend \
  --member="user:admin@luckygas.com.tw" \
  --role="roles/iap.httpsResourceAccessor"
```

### 3. API Key Restrictions

```bash
# Restrict Google Maps API key
gcloud alpha services api-keys update [KEY_ID] \
  --allowed-referrers="https://luckygas.com.tw/*,https://www.luckygas.com.tw/*" \
  --api-target=service=maps-backend.googleapis.com
```

## 📊 Monitoring Setup

### 1. Cloud Monitoring

```bash
# Create uptime checks
gcloud monitoring uptime-checks create luckygas-api \
  --display-name="Lucky Gas API Health" \
  --resource-type=uptime-url \
  --hostname=api.luckygas.com.tw \
  --path=/api/v1/health \
  --check-interval=60s

# Create alerting policy
gcloud alpha monitoring policies create \
  --notification-channels=[CHANNEL_ID] \
  --display-name="API Down Alert" \
  --condition-display-name="API Uptime Check Failed" \
  --condition-type=uptime_check \
  --uptime-check=luckygas-api
```

### 2. Log-Based Metrics

```bash
# Create error rate metric
gcloud logging metrics create api_error_rate \
  --description="API error rate" \
  --log-filter='resource.type="cloud_run_revision"
    resource.labels.service_name="luckygas-backend"
    jsonPayload.status>=500'
```

### 3. Custom Dashboards

Create monitoring dashboard via Console or API:
- API response times
- Error rates
- Active users
- Order volume
- Database performance
- Redis hit rate

## 🔄 CI/CD Pipeline

### GitHub Actions Deployment

`.github/workflows/deploy-production.yml`:
```yaml
name: Deploy to Production

on:
  push:
    tags:
      - 'v*'

env:
  PROJECT_ID: ${{ secrets.GCP_PROJECT_ID }}
  SERVICE: luckygas-backend
  REGION: asia-east1

jobs:
  deploy:
    runs-on: ubuntu-latest
    
    steps:
    - uses: actions/checkout@v3
    
    - id: 'auth'
      uses: 'google-github-actions/auth@v1'
      with:
        credentials_json: '${{ secrets.GCP_SA_KEY }}'
    
    - name: 'Set up Cloud SDK'
      uses: 'google-github-actions/setup-gcloud@v1'
    
    - name: 'Configure Docker'
      run: gcloud auth configure-docker
    
    - name: 'Build and Push Backend'
      working-directory: backend
      run: |
        docker build -t gcr.io/$PROJECT_ID/$SERVICE:${{ github.sha }} .
        docker push gcr.io/$PROJECT_ID/$SERVICE:${{ github.sha }}
    
    - name: 'Deploy to Cloud Run'
      run: |
        gcloud run deploy $SERVICE \
          --image gcr.io/$PROJECT_ID/$SERVICE:${{ github.sha }} \
          --region $REGION \
          --platform managed \
          --allow-unauthenticated
    
    - name: 'Build and Deploy Frontend'
      working-directory: frontend
      run: |
        npm ci
        npm run build
        gsutil -m rsync -r -d dist/ gs://luckygas-frontend/
```

## 🔥 Disaster Recovery

### 1. Backup Strategy

```bash
# Automated Cloud SQL backups (configured during setup)
# Additional manual backup
gcloud sql backups create --instance=luckygas-prod

# Export to Cloud Storage
gcloud sql export sql luckygas-prod \
  gs://luckygas-backups/backup-$(date +%Y%m%d-%H%M%S).sql \
  --database=luckygas
```

### 2. Recovery Procedures

```bash
# Restore from backup
gcloud sql backups restore [BACKUP_ID] \
  --restore-instance=luckygas-prod

# Or restore from export
gcloud sql import sql luckygas-prod \
  gs://luckygas-backups/backup-20250120-120000.sql \
  --database=luckygas
```

### 3. Rollback Process

```bash
# Quick rollback to previous version
gcloud run services update-traffic luckygas-backend \
  --to-revisions=luckygas-backend-00001-abc=100 \
  --region=asia-east1
```

## 📈 Performance Optimization

### 1. Cloud Run Optimization

```yaml
# Optimal Cloud Run configuration
spec:
  template:
    metadata:
      annotations:
        autoscaling.knative.dev/minScale: "2"
        autoscaling.knative.dev/maxScale: "100"
        run.googleapis.com/cpu-throttling: "false"
    spec:
      containerConcurrency: 100
      timeoutSeconds: 300
```

### 2. Database Optimization

```sql
-- Create indexes for common queries
CREATE INDEX idx_orders_customer_date ON orders(customer_id, delivery_date);
CREATE INDEX idx_customers_district ON customers(district);
CREATE INDEX idx_routes_date_status ON routes(date, status);

-- Analyze tables
ANALYZE customers;
ANALYZE orders;
ANALYZE routes;
```

### 3. CDN Configuration

```bash
# Enable Cloud CDN for static assets
gcloud compute backend-buckets update luckygas-frontend-backend \
  --enable-cdn \
  --cache-mode=CACHE_ALL_STATIC \
  --default-ttl=3600 \
  --max-ttl=86400
```

## 🔐 Production Secrets

### Required Secrets
1. **DATABASE_URL**: PostgreSQL connection string
2. **REDIS_URL**: Redis connection string
3. **SECRET_KEY**: JWT signing key (min 32 chars)
4. **GOOGLE_CLOUD_PROJECT**: GCP project ID
5. **VERTEX_AI_ENDPOINT**: ML model endpoint
6. **SENTRY_DSN**: Error tracking
7. **SMTP_PASSWORD**: Email service password

### Secret Rotation

```bash
# Rotate secret key monthly
NEW_SECRET=$(openssl rand -base64 32)
echo -n "$NEW_SECRET" | gcloud secrets versions add secret-key --data-file=-

# Update Cloud Run to use new version
gcloud run services update luckygas-backend \
  --update-secrets=SECRET_KEY=secret-key:latest
```

## 📱 Mobile App Deployment (Future)

### iOS App Store
1. Build production IPA
2. Submit via App Store Connect
3. Include Taiwan-specific metadata

### Google Play Store
1. Build production APK/AAB
2. Submit via Play Console
3. Target Taiwan region

## 🚨 Production Monitoring Checklist

### Daily Checks
- [ ] API health status
- [ ] Error rate < 1%
- [ ] Response time < 200ms (p95)
- [ ] Database connections < 80%
- [ ] Redis memory < 80%

### Weekly Checks
- [ ] Security vulnerabilities scan
- [ ] Backup verification
- [ ] Cost analysis
- [ ] Performance trends
- [ ] User feedback review

### Monthly Tasks
- [ ] Security patches
- [ ] Dependency updates
- [ ] Secret rotation
- [ ] Capacity planning
- [ ] Disaster recovery drill

## 📞 Support Contacts

### Google Cloud Support
- Console: https://console.cloud.google.com/support
- Phone: +886-2-2326-1099 (Taiwan)

### Lucky Gas DevOps Team
- Primary: devops@luckygas.com.tw
- Escalation: cto@luckygas.com.tw
- Emergency: [On-call rotation phone]

## 🎯 Launch Checklist

### Pre-Launch (T-7 days)
- [ ] Load testing completed
- [ ] Security audit passed
- [ ] Backup/restore tested
- [ ] Monitoring configured
- [ ] Documentation complete

### Launch Day
- [ ] Database migrated
- [ ] DNS switched
- [ ] SSL verified
- [ ] Health checks passing
- [ ] Team on standby

### Post-Launch (T+1 day)
- [ ] Performance metrics review
- [ ] Error logs analysis
- [ ] User feedback collection
- [ ] Cost monitoring
- [ ] Success celebration! 🎉