#!/bin/bash

# Emergency deployment script for database initialization fix
set -e

echo "🚨 Deploying emergency database initialization fix..."

# Build and deploy directly to Cloud Run
echo "📦 Building and deploying to Cloud Run..."

gcloud run deploy luckygas-backend-production \
  --source . \
  --region asia-east1 \
  --platform managed \
  --allow-unauthenticated \
  --timeout 60 \
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
  --set-env-vars "USE_ASYNC_DB=true"

echo "✅ Deployment complete!"

# Test the health endpoints
echo "🔍 Testing health endpoints..."

# Test basic health
echo "Testing /health endpoint..."
curl -s https://luckygas-backend-production-154687573210.asia-east1.run.app/health | jq

# Test debug health
echo "Testing /api/v1/health/debug endpoint..."
curl -s https://luckygas-backend-production-154687573210.asia-east1.run.app/api/v1/health/debug | jq

# Test database health
echo "Testing /api/v1/health/db-test endpoint..."
curl -s https://luckygas-backend-production-154687573210.asia-east1.run.app/api/v1/health/db-test | jq

echo "🎉 Emergency fix deployed successfully!"