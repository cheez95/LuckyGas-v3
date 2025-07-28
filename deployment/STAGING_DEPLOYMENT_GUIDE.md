# LuckyGas Staging Deployment Guide

## Overview

This guide provides step-by-step instructions for deploying LuckyGas to a staging environment on Google Cloud Platform (GCP). The staging environment mirrors production infrastructure while allowing for safe testing and validation before the pilot launch.

## Prerequisites

### Required Tools
- Google Cloud SDK (`gcloud`) installed and configured
- `kubectl` (v1.25+) installed
- Docker installed and running
- `kustomize` (v4.5+) installed
- `helm` (v3.10+) installed
- `uv` for Python dependency management
- Node.js (v18+) and npm

### GCP Resources Required
- GCP Project with billing enabled
- Service Account with appropriate permissions
- APIs enabled:
  - Kubernetes Engine API
  - Cloud SQL Admin API
  - Cloud Build API
  - Container Registry API
  - Secret Manager API
  - Cloud Run API
  - Memorystore Redis API
  - Cloud Storage API
  - Vertex AI API
  - Routes API

### Access Requirements
- Project Editor or Owner role in GCP project
- Access to staging domain DNS configuration
- SSL certificates for staging domain

## Architecture Overview

### Staging Environment Components
```
┌─────────────────────────────────────────────────────────────┐
│                     Google Cloud Platform                      │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  ┌─────────────┐     ┌─────────────┐     ┌─────────────┐   │
│  │    GKE      │     │  Cloud SQL  │     │   Redis     │   │
│  │  Cluster    │────▶│ PostgreSQL  │     │ Memorystore │   │
│  └─────────────┘     └─────────────┘     └─────────────┘   │
│         │                                         ▲           │
│         ▼                                         │           │
│  ┌─────────────┐                                │           │
│  │   Ingress   │                                │           │
│  │    NGINX    │                                │           │
│  └─────────────┘                                │           │
│         │                                         │           │
│    ┌────┴────┐                                  │           │
│    ▼         ▼                                  │           │
│  ┌─────┐  ┌─────┐                              │           │
│  │ FE  │  │ BE  │◀─────────────────────────────┘           │
│  │Pods │  │Pods │                                           │
│  └─────┘  └─────┘                                           │
│                                                               │
│  ┌─────────────┐     ┌─────────────┐     ┌─────────────┐   │
│  │   Secret    │     │   Cloud     │     │  Vertex AI  │   │
│  │  Manager    │     │  Storage    │     │   & Maps    │   │
│  └─────────────┘     └─────────────┘     └─────────────┘   │
└─────────────────────────────────────────────────────────────┘
```

## Step 1: Initial Setup

### 1.1 Configure GCP Project
```bash
# Set project ID
export PROJECT_ID="luckygas-staging"
export REGION="asia-east1"  # Taiwan region
export ZONE="${REGION}-a"

# Configure gcloud
gcloud config set project ${PROJECT_ID}
gcloud config set compute/region ${REGION}
gcloud config set compute/zone ${ZONE}

# Enable required APIs
gcloud services enable compute.googleapis.com
gcloud services enable container.googleapis.com
gcloud services enable sqladmin.googleapis.com
gcloud services enable redis.googleapis.com
gcloud services enable secretmanager.googleapis.com
gcloud services enable cloudbuild.googleapis.com
gcloud services enable containerregistry.googleapis.com
gcloud services enable storage-api.googleapis.com
gcloud services enable aiplatform.googleapis.com
gcloud services enable routes.googleapis.com
```

### 1.2 Create Service Account
```bash
# Create service account for staging
gcloud iam service-accounts create luckygas-staging \
    --display-name="LuckyGas Staging Service Account"

# Grant necessary permissions
gcloud projects add-iam-policy-binding ${PROJECT_ID} \
    --member="serviceAccount:luckygas-staging@${PROJECT_ID}.iam.gserviceaccount.com" \
    --role="roles/cloudsql.client"

gcloud projects add-iam-policy-binding ${PROJECT_ID} \
    --member="serviceAccount:luckygas-staging@${PROJECT_ID}.iam.gserviceaccount.com" \
    --role="roles/redis.editor"

gcloud projects add-iam-policy-binding ${PROJECT_ID} \
    --member="serviceAccount:luckygas-staging@${PROJECT_ID}.iam.gserviceaccount.com" \
    --role="roles/secretmanager.secretAccessor"

gcloud projects add-iam-policy-binding ${PROJECT_ID} \
    --member="serviceAccount:luckygas-staging@${PROJECT_ID}.iam.gserviceaccount.com" \
    --role="roles/storage.objectAdmin"

gcloud projects add-iam-policy-binding ${PROJECT_ID} \
    --member="serviceAccount:luckygas-staging@${PROJECT_ID}.iam.gserviceaccount.com" \
    --role="roles/aiplatform.user"
```

## Step 2: Infrastructure Setup

### 2.1 Run GCP Setup Script
```bash
# Make script executable
chmod +x deployment/scripts/setup-gcp-staging.sh

# Run setup script
./deployment/scripts/setup-gcp-staging.sh
```

### 2.2 Verify Infrastructure
```bash
# Check GKE cluster
gcloud container clusters describe luckygas-staging-cluster --region=${REGION}

# Check Cloud SQL instance
gcloud sql instances describe luckygas-staging-db

# Check Redis instance
gcloud redis instances describe luckygas-staging-redis --region=${REGION}

# List secrets
gcloud secrets list
```

## Step 3: Configure Secrets

### 3.1 Create Secrets in Secret Manager
```bash
# Database password
echo -n "$(openssl rand -base64 32)" | \
  gcloud secrets create database-password --data-file=-

# JWT secret key
echo -n "$(openssl rand -base64 64)" | \
  gcloud secrets create jwt-secret-key --data-file=-

# Redis password
echo -n "$(openssl rand -base64 32)" | \
  gcloud secrets create redis-password --data-file=-

# Admin password
echo -n "LuckyGas@Staging2024!" | \
  gcloud secrets create admin-password --data-file=-

# SMS Gateway API Key (placeholder)
echo -n "your-sms-api-key" | \
  gcloud secrets create sms-api-key --data-file=-

# E-Invoice credentials (placeholder)
echo -n "your-einvoice-app-id" | \
  gcloud secrets create einvoice-app-id --data-file=-

echo -n "your-einvoice-api-key" | \
  gcloud secrets create einvoice-api-key --data-file=-

# Banking API credentials (placeholder)
echo -n "your-banking-api-key" | \
  gcloud secrets create banking-api-key --data-file=-

echo -n "your-banking-api-secret" | \
  gcloud secrets create banking-api-secret --data-file=-
```

### 3.2 Create Kubernetes Secrets
```bash
# Get cluster credentials
gcloud container clusters get-credentials luckygas-staging-cluster --region=${REGION}

# Create namespace
kubectl create namespace luckygas-staging

# Create secrets from Secret Manager
kubectl create secret generic luckygas-backend-secrets \
  --from-literal=DATABASE_PASSWORD=$(gcloud secrets versions access latest --secret=database-password) \
  --from-literal=SECRET_KEY=$(gcloud secrets versions access latest --secret=jwt-secret-key) \
  --from-literal=REDIS_PASSWORD=$(gcloud secrets versions access latest --secret=redis-password) \
  --from-literal=FIRST_SUPERUSER_PASSWORD=$(gcloud secrets versions access latest --secret=admin-password) \
  --from-literal=SMS_API_KEY=$(gcloud secrets versions access latest --secret=sms-api-key) \
  --from-literal=EINVOICE_APP_ID=$(gcloud secrets versions access latest --secret=einvoice-app-id) \
  --from-literal=EINVOICE_API_KEY=$(gcloud secrets versions access latest --secret=einvoice-api-key) \
  --from-literal=BANKING_API_KEY=$(gcloud secrets versions access latest --secret=banking-api-key) \
  --from-literal=BANKING_API_SECRET=$(gcloud secrets versions access latest --secret=banking-api-secret) \
  -n luckygas-staging
```

## Step 4: Build and Deploy Application

### 4.1 Build Docker Images
```bash
# Set image registry
export REGISTRY="gcr.io/${PROJECT_ID}"

# Build backend image
cd backend
docker build -t ${REGISTRY}/luckygas-backend:staging-latest \
  --build-arg BUILD_ENV=staging \
  --build-arg VERSION=$(git describe --tags --always) \
  -f Dockerfile .

# Build frontend image
cd ../frontend
docker build -t ${REGISTRY}/luckygas-frontend:staging-latest \
  --build-arg VITE_API_URL=https://staging-api.luckygas.tw \
  --build-arg VITE_WS_URL=wss://staging-api.luckygas.tw \
  --build-arg VITE_ENV=staging \
  -f Dockerfile .

# Push images to registry
docker push ${REGISTRY}/luckygas-backend:staging-latest
docker push ${REGISTRY}/luckygas-frontend:staging-latest
```

### 4.2 Deploy to Kubernetes
```bash
# Run deployment script
cd ..
./deployment/scripts/deploy-staging.sh
```

### 4.3 Verify Deployment
```bash
# Check pod status
kubectl get pods -n luckygas-staging

# Check services
kubectl get svc -n luckygas-staging

# Check ingress
kubectl get ingress -n luckygas-staging

# View logs
kubectl logs -n luckygas-staging -l app=luckygas-backend --tail=100
kubectl logs -n luckygas-staging -l app=luckygas-frontend --tail=100
```

## Step 5: Database Setup and Migration

### 5.1 Run Database Migrations
```bash
# Get backend pod name
BACKEND_POD=$(kubectl get pods -n luckygas-staging -l app=luckygas-backend -o jsonpath='{.items[0].metadata.name}')

# Run migrations
kubectl exec -n luckygas-staging ${BACKEND_POD} -- python -m alembic upgrade head

# Seed initial data
kubectl exec -n luckygas-staging ${BACKEND_POD} -- python app/scripts/seed_gas_products.py
kubectl exec -n luckygas-staging ${BACKEND_POD} -- python app/scripts/init_test_users.py
```

### 5.2 Import Historical Data
```bash
# Copy data files to pod
kubectl cp raw/2025-05\ commercial\ client\ list.xlsx luckygas-staging/${BACKEND_POD}:/tmp/
kubectl cp raw/2025-05\ commercial\ deliver\ history.xlsx luckygas-staging/${BACKEND_POD}:/tmp/

# Run import scripts
kubectl exec -n luckygas-staging ${BACKEND_POD} -- python app/scripts/import_excel_data.py
kubectl exec -n luckygas-staging ${BACKEND_POD} -- python app/scripts/import_delivery_history_v2.py
```

## Step 6: Configure Monitoring

### 6.1 Deploy Monitoring Stack
```bash
# Install Prometheus and Grafana
./k8s/scripts/setup-monitoring.sh staging

# Verify monitoring deployment
kubectl get pods -n monitoring
```

### 6.2 Configure Alerts
```bash
# Apply alert rules
kubectl apply -f k8s/overlays/staging/monitoring/alerts.yaml
```

## Step 7: SSL Certificate Setup

### 7.1 Install Cert Manager
```bash
# Install cert-manager
kubectl apply -f https://github.com/cert-manager/cert-manager/releases/download/v1.13.0/cert-manager.yaml

# Wait for cert-manager to be ready
kubectl wait --for=condition=ready pod -l app.kubernetes.io/instance=cert-manager -n cert-manager
```

### 7.2 Create Certificate
```bash
# Apply certificate configuration
kubectl apply -f - <<EOF
apiVersion: cert-manager.io/v1
kind: Certificate
metadata:
  name: luckygas-staging-tls
  namespace: luckygas-staging
spec:
  secretName: luckygas-staging-tls
  issuerRef:
    name: letsencrypt-staging
    kind: ClusterIssuer
  dnsNames:
  - staging.luckygas.tw
  - staging-api.luckygas.tw
EOF
```

## Step 8: Health Check Validation

### 8.1 API Health Check
```bash
# Check backend health
curl -k https://staging-api.luckygas.tw/health

# Check frontend health
curl -k https://staging.luckygas.tw/health

# Check database connectivity
kubectl exec -n luckygas-staging ${BACKEND_POD} -- python -c "
from app.core.database import SessionLocal
db = SessionLocal()
print('Database connection: OK')
db.close()
"

# Check Redis connectivity
kubectl exec -n luckygas-staging ${BACKEND_POD} -- python -c "
import redis
r = redis.from_url('redis://redis-service:6379')
r.ping()
print('Redis connection: OK')
"
```

### 8.2 Run Integration Tests
```bash
# Run E2E tests against staging
cd frontend/e2e
npm install
PLAYWRIGHT_BASE_URL=https://staging.luckygas.tw npm run test
```

## Step 9: Backup Configuration

### 9.1 Setup Automated Backups
```bash
# Create backup bucket
gsutil mb -p ${PROJECT_ID} -l ${REGION} gs://luckygas-staging-backups/

# Apply backup CronJob
kubectl apply -f k8s/overlays/staging/backup-cronjob.yaml
```

### 9.2 Test Backup and Restore
```bash
# Trigger manual backup
kubectl create job --from=cronjob/database-backup manual-backup-test -n luckygas-staging

# Verify backup
gsutil ls gs://luckygas-staging-backups/database/
```

## Step 10: Performance Validation

### 10.1 Run Load Tests
```bash
# Install k6
brew install k6

# Run load test
k6 run tests/load/api_load.js --env BASE_URL=https://staging-api.luckygas.tw
```

### 10.2 Check Metrics
```bash
# Access Grafana
kubectl port-forward -n monitoring svc/prometheus-grafana 3000:80

# Open http://localhost:3000
# Default credentials: admin / luckygas-admin
```

## Rollback Procedures

### Emergency Rollback
```bash
# Rollback deployment
kubectl rollout undo deployment/luckygas-backend -n luckygas-staging
kubectl rollout undo deployment/luckygas-frontend -n luckygas-staging

# Check rollback status
kubectl rollout status deployment/luckygas-backend -n luckygas-staging
kubectl rollout status deployment/luckygas-frontend -n luckygas-staging
```

### Database Rollback
```bash
# Connect to Cloud SQL
gcloud sql connect luckygas-staging-db --user=postgres

# Restore from backup
# Use Cloud SQL restore feature in Console or:
gcloud sql backups restore BACKUP_ID --restore-instance=luckygas-staging-db
```

## Troubleshooting

### Common Issues

1. **Pods not starting**
```bash
kubectl describe pod <pod-name> -n luckygas-staging
kubectl logs <pod-name> -n luckygas-staging --previous
```

2. **Database connection errors**
```bash
# Check Cloud SQL proxy
kubectl logs -n luckygas-staging -l app=cloudsql-proxy

# Verify connection string
kubectl get secret luckygas-backend-secrets -n luckygas-staging -o yaml
```

3. **Ingress not accessible**
```bash
# Check ingress status
kubectl describe ingress luckygas-ingress -n luckygas-staging

# Check DNS resolution
nslookup staging.luckygas.tw
```

4. **Performance issues**
```bash
# Check resource usage
kubectl top pods -n luckygas-staging
kubectl top nodes

# Check HPA status
kubectl get hpa -n luckygas-staging
```

## Maintenance Tasks

### Daily Checks
- Monitor application logs in Cloud Logging
- Check error rates in monitoring dashboard
- Verify backup completion
- Review resource utilization

### Weekly Tasks
- Test backup restoration process
- Review and apply security updates
- Check for unused resources
- Review cost optimization opportunities

### Monthly Tasks
- Full system health audit
- Performance baseline comparison
- Security vulnerability scan
- Disaster recovery drill

## Security Checklist

- [ ] All secrets stored in Secret Manager
- [ ] Network policies configured
- [ ] RBAC permissions minimized
- [ ] SSL certificates valid
- [ ] Security scanning enabled on images
- [ ] Audit logging enabled
- [ ] Firewall rules reviewed
- [ ] Service accounts use least privilege

## Support Contacts

### Internal Team
- DevOps Lead: devops@luckygas.tw
- Security Team: security@luckygas.tw
- Database Admin: dba@luckygas.tw

### External Support
- GCP Support: [Support Case Link]
- Domain Registrar: [Contact Info]
- SSL Certificate Provider: [Contact Info]

## Appendix

### Useful Commands
```bash
# Get all resources in namespace
kubectl get all -n luckygas-staging

# Watch pod status
kubectl get pods -n luckygas-staging -w

# Get events
kubectl get events -n luckygas-staging --sort-by='.lastTimestamp'

# Port forward to service
kubectl port-forward -n luckygas-staging svc/luckygas-backend 8000:8000

# Execute shell in pod
kubectl exec -it -n luckygas-staging <pod-name> -- /bin/bash
```

### Environment URLs
- Frontend: https://staging.luckygas.tw
- API: https://staging-api.luckygas.tw
- API Docs: https://staging-api.luckygas.tw/docs
- Monitoring: https://staging-monitoring.luckygas.tw

---

**Last Updated**: 2024-01-20
**Version**: 1.0.0