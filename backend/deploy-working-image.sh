#!/bin/bash

# Deploy the WORKING Lucky Gas Backend with PORT fix to Cloud Run
set -e

echo "🚀 Deploying Lucky Gas Backend (PORT FIXED) to Cloud Run..."

# Build info
BUILD_ID="3c03550b-81a0-44dd-968a-73eddf802c12"
IMAGE="asia-east1-docker.pkg.dev/vast-tributary-466619-m8/cloud-run-source-deploy/luckygas-backend-working:latest"

# Check build status
echo "Checking build status for ${BUILD_ID}..."
BUILD_STATUS=$(gcloud builds describe ${BUILD_ID} --region=asia-east1 --format="value(status)" 2>/dev/null || echo "UNKNOWN")

if [ "$BUILD_STATUS" == "WORKING" ]; then
    echo "⏳ Build still in progress. Waiting for completion..."
    gcloud builds log ${BUILD_ID} --region=asia-east1 --stream
elif [ "$BUILD_STATUS" == "FAILURE" ]; then
    echo "❌ Build failed! Check logs:"
    gcloud builds log ${BUILD_ID} --region=asia-east1 | tail -50
    exit 1
elif [ "$BUILD_STATUS" != "SUCCESS" ]; then
    echo "⚠️ Build status: ${BUILD_STATUS}"
fi

# Deploy the fixed image
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
  --set-env-vars "LOG_LEVEL=INFO" \
  --set-env-vars "USE_ASYNC_DB=true"

echo "✅ Deployment complete!"

# Test the deployment
SERVICE_URL=$(gcloud run services describe luckygas-backend-production --region asia-east1 --format "value(status.url)")
echo "🌐 Service URL: ${SERVICE_URL}"

echo "🧪 Testing endpoints..."
echo ""
echo "1. Health check:"
curl -s "${SERVICE_URL}/health" | python3 -m json.tool || echo "Health check failed"

echo ""
echo "2. API health:"
curl -s "${SERVICE_URL}/api/v1/health" | python3 -m json.tool || echo "API health check failed"

echo ""
echo "3. Login test:"
curl -X POST "${SERVICE_URL}/api/v1/auth/login" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=admin@luckygas.com&password=admin-password-2025" \
  -s | python3 -c "import sys, json; data = json.load(sys.stdin); print('✅ Login successful!' if 'access_token' in data else '❌ Login failed: ' + str(data))" || echo "Login test failed"

echo ""
echo "4. Optimized login test:"
curl -X POST "${SERVICE_URL}/api/v1/auth/login-optimized" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=admin@luckygas.com&password=admin-password-2025" \
  -s | python3 -c "import sys, json; data = json.load(sys.stdin); print('✅ Optimized login successful!' if 'access_token' in data else '❌ Optimized login failed: ' + str(data))" || echo "Optimized login test failed"

echo ""
echo "🎉 Lucky Gas Backend with PORT fix is now running!"
echo ""
echo "Key fix applied:"
echo "✅ run.py now reads PORT environment variable (was hardcoded to 8000)"
echo "✅ Dockerfile uses Python script that properly handles PORT"
echo "✅ Backend will listen on port 8080 as Cloud Run requires"