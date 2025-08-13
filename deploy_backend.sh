#!/bin/bash
# Deploy Lucky Gas Simplified Backend to Google Cloud Run

set -e

# Configuration
PROJECT_ID="vast-tributary-466619-m8"  # Your actual GCP project ID
REGION="asia-east1"
SERVICE_NAME="luckygas-backend-production"
IMAGE_NAME="luckygas-backend-simplified"

echo "================================================"
echo "   Lucky Gas Backend Deployment to Cloud Run"
echo "================================================"
echo ""

# Check if gcloud is installed
if ! command -v gcloud &> /dev/null; then
    echo "❌ gcloud CLI is not installed. Please install it first."
    exit 1
fi

# Check current project
CURRENT_PROJECT=$(gcloud config get-value project 2>/dev/null)
if [ "$CURRENT_PROJECT" != "$PROJECT_ID" ]; then
    echo "Setting GCP project to $PROJECT_ID..."
    gcloud config set project $PROJECT_ID
fi

# Build the Docker image
echo "📦 Building Docker image..."
cd backend
docker build -f Dockerfile.production -t gcr.io/$PROJECT_ID/$IMAGE_NAME:latest .
docker tag gcr.io/$PROJECT_ID/$IMAGE_NAME:latest gcr.io/$PROJECT_ID/$IMAGE_NAME:$(date +%Y%m%d-%H%M%S)

# Push to Google Container Registry
echo "⬆️ Pushing image to GCR..."
docker push gcr.io/$PROJECT_ID/$IMAGE_NAME:latest

# Deploy to Cloud Run
echo "🚀 Deploying to Cloud Run..."
gcloud run deploy $SERVICE_NAME \
    --image gcr.io/$PROJECT_ID/$IMAGE_NAME:latest \
    --region $REGION \
    --platform managed \
    --allow-unauthenticated \
    --memory 512Mi \
    --cpu 1 \
    --timeout 60 \
    --min-instances 0 \
    --max-instances 5 \
    --set-env-vars "ENVIRONMENT=production" \
    --set-env-vars "DATABASE_URL=$DATABASE_URL" \
    --set-env-vars "SECRET_KEY=$SECRET_KEY" \
    --set-env-vars "FIRST_SUPERUSER=admin@luckygas.com" \
    --set-env-vars "FIRST_SUPERUSER_PASSWORD=$ADMIN_PASSWORD"

# Get the service URL
SERVICE_URL=$(gcloud run services describe $SERVICE_NAME --region $REGION --format 'value(status.url)')

echo ""
echo "================================================"
echo "✅ Deployment Complete!"
echo "================================================"
echo ""
echo "Service URL: $SERVICE_URL"
echo "Health Check: $SERVICE_URL/health"
echo "API Docs: $SERVICE_URL/docs"
echo ""
echo "To view logs:"
echo "  gcloud run logs read --service $SERVICE_NAME --region $REGION"
echo ""
echo "To check service status:"
echo "  gcloud run services describe $SERVICE_NAME --region $REGION"
echo ""

# Test the deployment
echo "Testing deployment..."
if curl -s "$SERVICE_URL/health" | grep -q "healthy"; then
    echo "✅ Health check passed!"
else
    echo "⚠️ Health check failed or service is still starting..."
    echo "Please check logs for details."
fi