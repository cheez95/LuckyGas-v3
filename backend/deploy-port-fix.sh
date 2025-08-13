#!/bin/bash

# Deploy script for Lucky Gas Backend with PORT fix
set -e

echo "🚀 Deploying Lucky Gas Backend with PORT fix to Cloud Run..."

# Configuration
PROJECT_ID="vast-tributary-466619-m8"
REGION="asia-east1"
SERVICE_NAME="luckygas-backend-production"
IMAGE_NAME="asia-east1-docker.pkg.dev/${PROJECT_ID}/cloud-run-source-deploy/luckygas-backend-port-fix:latest"

# Deploy to Cloud Run
echo "📦 Deploying to Cloud Run..."
gcloud run deploy ${SERVICE_NAME} \
  --image ${IMAGE_NAME} \
  --region ${REGION} \
  --platform managed \
  --allow-unauthenticated \
  --port 8080 \
  --timeout 300 \
  --memory 1Gi \
  --cpu 2 \
  --min-instances 1 \
  --max-instances 10 \
  --set-env-vars "ENVIRONMENT=production" \
  --set-env-vars "DATABASE_URL=postgresql+asyncpg://luckygas:staging-password-2025@35.194.143.37/luckygas" \
  --set-env-vars "FIRST_SUPERUSER=admin@luckygas.com" \
  --set-env-vars "FIRST_SUPERUSER_PASSWORD=admin-password-2025" \
  --set-env-vars "SECRET_KEY=production-secret-key-very-long-and-secure-2025" \
  --set-env-vars "LOG_LEVEL=INFO" \
  --set-env-vars "USE_ASYNC_DB=true" \
  --set-env-vars "REDIS_URL=redis://localhost:6379" \
  --update-annotations "run.googleapis.com/cpu-throttling=false"

echo "✅ Deployment complete!"

# Get service URL
SERVICE_URL=$(gcloud run services describe ${SERVICE_NAME} --region ${REGION} --format "value(status.url)")
echo "🌐 Service URL: ${SERVICE_URL}"

# Test the deployment
echo "🧪 Testing deployment..."
echo "Testing health endpoint..."
curl -s "${SERVICE_URL}/health" | python3 -m json.tool || echo "Health check failed"

echo "Testing API health..."
curl -s "${SERVICE_URL}/api/v1/health" | python3 -m json.tool || echo "API health check failed"

echo "Testing login endpoint..."
curl -X POST "${SERVICE_URL}/api/v1/auth/login" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=admin@luckygas.com&password=admin-password-2025" \
  -s | python3 -c "import sys, json; data = json.load(sys.stdin); print('✅ Login successful!' if 'access_token' in data else '❌ Login failed')" || echo "Login test failed"

echo "Testing optimized login endpoint..."
curl -X POST "${SERVICE_URL}/api/v1/auth/login-optimized" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=admin@luckygas.com&password=admin-password-2025" \
  -s | python3 -c "import sys, json; data = json.load(sys.stdin); print('✅ Optimized login successful!' if 'access_token' in data else '❌ Optimized login failed')" || echo "Optimized login test failed"

echo "🎉 Deployment and testing complete!"