#!/bin/bash

# Test Cloud Run deployment
echo "Testing simple Cloud Run deployment..."

# Deploy a simple test service
gcloud run deploy luckygas-test \
  --image=gcr.io/cloudrun/hello \
  --region=asia-east1 \
  --platform=managed \
  --allow-unauthenticated \
  --port=8080

echo "Test deployment complete. Check if this works first."