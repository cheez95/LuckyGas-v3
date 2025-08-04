# Manual Staging Deployment Guide - Lucky Gas v3

## 🚨 URGENT: UAT Starts Monday - Deploy Now!

### Current Status
- **Deployment Scripts**: Ready ✅
- **Docker Configs**: Fixed ✅
- **GCP Project**: `vast-tributary-466619-m8` ✅
- **Services**: NOT DEPLOYED ❌

## Step 1: Build Docker Images Locally

```bash
# Navigate to project root
cd /Users/lgee258/Desktop/LuckyGas-v3

# Build backend image
docker build -t gcr.io/vast-tributary-466619-m8/luckygas-backend:staging -f backend/Dockerfile ./backend

# Build frontend image
docker build -t gcr.io/vast-tributary-466619-m8/luckygas-frontend:staging -f frontend/Dockerfile ./frontend
```

## Step 2: Push Images to Google Container Registry

```bash
# Configure Docker for GCR
gcloud auth configure-docker

# Push backend
docker push gcr.io/vast-tributary-466619-m8/luckygas-backend:staging

# Push frontend
docker push gcr.io/vast-tributary-466619-m8/luckygas-frontend:staging
```

## Step 3: Deploy Backend to Cloud Run

```bash
gcloud run deploy luckygas-backend-staging \
  --image gcr.io/vast-tributary-466619-m8/luckygas-backend:staging \
  --platform managed \
  --region asia-east1 \
  --allow-unauthenticated \
  --port 8000 \
  --memory 2Gi \
  --cpu 2 \
  --min-instances 1 \
  --max-instances 10 \
  --set-env-vars "ENVIRONMENT=staging,CORS_ALLOWED_ORIGINS=https://luckygas-frontend-staging-*.asia-east1.run.app" \
  --set-secrets "DATABASE_URL=DATABASE_URL_STAGING:latest,SECRET_KEY=SECRET_KEY_STAGING:latest"
```

## Step 4: Deploy Frontend to Cloud Run

```bash
gcloud run deploy luckygas-frontend-staging \
  --image gcr.io/vast-tributary-466619-m8/luckygas-frontend:staging \
  --platform managed \
  --region asia-east1 \
  --allow-unauthenticated \
  --port 80 \
  --memory 512Mi \
  --cpu 1 \
  --min-instances 1 \
  --max-instances 5
```

## Step 5: Run Database Migrations

```bash
# Get backend service URL
BACKEND_URL=$(gcloud run services describe luckygas-backend-staging --region asia-east1 --format 'value(status.url)')

# SSH into Cloud SQL proxy or use Cloud Shell
gcloud sql connect luckygas-staging-db --user=luckygas_staging

# Run migrations via backend endpoint
curl -X POST "$BACKEND_URL/api/v1/admin/migrate" \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "Content-Type: application/json"
```

## Step 6: Configure Domain Mapping (Optional)

```bash
# Map custom domain to frontend
gcloud run domain-mappings create \
  --service luckygas-frontend-staging \
  --domain staging.luckygas.com.tw \
  --region asia-east1

# Map API subdomain to backend
gcloud run domain-mappings create \
  --service luckygas-backend-staging \
  --domain api-staging.luckygas.com.tw \
  --region asia-east1
```

## Step 7: Validate Deployment

```bash
# Get service URLs
FRONTEND_URL=$(gcloud run services describe luckygas-frontend-staging --region asia-east1 --format 'value(status.url)')
BACKEND_URL=$(gcloud run services describe luckygas-backend-staging --region asia-east1 --format 'value(status.url)')

echo "Frontend URL: $FRONTEND_URL"
echo "Backend URL: $BACKEND_URL"

# Test backend health
curl "$BACKEND_URL/health"

# Test frontend
curl "$FRONTEND_URL"
```

## Quick Validation Checklist

- [ ] Backend responds to /health endpoint
- [ ] Frontend loads without errors
- [ ] Can login with test credentials
- [ ] WebSocket connection establishes
- [ ] Database queries work
- [ ] External APIs accessible

## Service URLs (Update After Deployment)

- **Frontend**: https://luckygas-frontend-staging-[HASH].asia-east1.run.app
- **Backend**: https://luckygas-backend-staging-[HASH].asia-east1.run.app
- **Database**: luckygas-staging-db (internal)

## Test Credentials

```
Manager: manager@luckygas.tw / TestPass123!
Staff: staff@luckygas.tw / TestPass123!
Driver: driver@luckygas.tw / TestPass123!
```

## Troubleshooting

### Build Fails
- Ensure Docker daemon is running
- Check Docker has enough disk space
- Verify package.json dependencies

### Push Fails
- Run `gcloud auth login`
- Ensure you have push permissions to GCR

### Deploy Fails
- Check Cloud Run quotas
- Verify secrets exist in Secret Manager
- Check service account permissions

### Health Check Fails
- Check Cloud SQL is accessible
- Verify environment variables
- Check application logs: `gcloud run logs read`

## Next Steps After Deployment

1. Load UAT test data
2. Send UAT participants the staging URLs
3. Set up monitoring alerts
4. Prepare support channels

---

**CRITICAL**: Complete deployment by end of day to allow testing before Monday UAT!