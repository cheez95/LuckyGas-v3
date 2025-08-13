#!/bin/bash

# Deploy the FIXED Lucky Gas Backend to Cloud Run
set -e

echo "🚀 Deploying Fixed Lucky Gas Backend to Cloud Run..."

# Check build status
BUILD_ID="130b41c6-032a-4203-b928-f1a2e42afc90"
echo "Checking build status for ${BUILD_ID}..."
BUILD_STATUS=$(gcloud builds describe ${BUILD_ID} --region=asia-east1 --format="value(status)")

if [ "$BUILD_STATUS" != "SUCCESS" ]; then
    echo "⏳ Build status: ${BUILD_STATUS}"
    echo "Waiting for build to complete..."
    gcloud builds log ${BUILD_ID} --region=asia-east1 --stream
fi

# Deploy the fixed image
IMAGE="asia-east1-docker.pkg.dev/vast-tributary-466619-m8/cloud-run-source-deploy/luckygas-backend-fixed:latest"

echo "📦 Deploying image: ${IMAGE}"

gcloud run deploy luckygas-backend-production \
  --image ${IMAGE} \
  --region asia-east1 \
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
  --set-env-vars "LOG_LEVEL=INFO"

echo "✅ Deployment complete!"

# Test the deployment
SERVICE_URL=$(gcloud run services describe luckygas-backend-production --region asia-east1 --format "value(status.url)")
echo "🌐 Service URL: ${SERVICE_URL}"

echo "🧪 Testing endpoints..."
curl -s "${SERVICE_URL}/health" | python3 -m json.tool

echo "🎉 Fixed backend is now running!"