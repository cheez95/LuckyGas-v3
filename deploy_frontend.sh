#!/bin/bash
# Deploy Lucky Gas Frontend to Google Cloud Storage

set -e

# Configuration
BUCKET_NAME="luckygas-frontend-production"
STAGING_BUCKET="luckygas-frontend-staging-2025"
ENVIRONMENT=${1:-production}  # Default to production

echo "================================================"
echo "   Lucky Gas Frontend Deployment to GCS"
echo "   Environment: $ENVIRONMENT"
echo "================================================"
echo ""

# Determine which bucket to use
if [ "$ENVIRONMENT" = "staging" ]; then
    TARGET_BUCKET=$STAGING_BUCKET
else
    TARGET_BUCKET=$BUCKET_NAME
fi

# Check if gsutil is installed
if ! command -v gsutil &> /dev/null; then
    echo "❌ gsutil is not installed. Please install Google Cloud SDK first."
    exit 1
fi

# Move to frontend directory
cd frontend

# Install dependencies if needed
if [ ! -d "node_modules" ]; then
    echo "📦 Installing dependencies..."
    npm install
fi

# Build the frontend
echo "🔨 Building frontend for $ENVIRONMENT..."
if [ "$ENVIRONMENT" = "production" ]; then
    npm run build
else
    npm run build -- --mode staging
fi

# Check if build was successful
if [ ! -d "dist" ]; then
    echo "❌ Build failed! No dist directory found."
    exit 1
fi

# Create bucket if it doesn't exist
echo "🪣 Checking bucket gs://$TARGET_BUCKET..."
if ! gsutil ls -b gs://$TARGET_BUCKET &> /dev/null; then
    echo "Creating bucket gs://$TARGET_BUCKET..."
    gsutil mb -l asia-east1 gs://$TARGET_BUCKET
fi

# Upload files to GCS
echo "⬆️ Uploading files to gs://$TARGET_BUCKET..."
gsutil -m rsync -r -d dist/ gs://$TARGET_BUCKET/

# Set proper content types
echo "🔧 Setting content types..."
gsutil -m setmeta -h "Content-Type:text/html" gs://$TARGET_BUCKET/**/*.html 2>/dev/null || true
gsutil -m setmeta -h "Content-Type:text/css" gs://$TARGET_BUCKET/**/*.css 2>/dev/null || true
gsutil -m setmeta -h "Content-Type:application/javascript" gs://$TARGET_BUCKET/**/*.js 2>/dev/null || true
gsutil -m setmeta -h "Content-Type:application/json" gs://$TARGET_BUCKET/**/*.json 2>/dev/null || true

# Set cache control for static assets
echo "⚡ Setting cache control..."
gsutil -m setmeta -h "Cache-Control:public, max-age=31536000" gs://$TARGET_BUCKET/js/*.js 2>/dev/null || true
gsutil -m setmeta -h "Cache-Control:public, max-age=31536000" gs://$TARGET_BUCKET/css/*.css 2>/dev/null || true
gsutil -m setmeta -h "Cache-Control:public, max-age=3600" gs://$TARGET_BUCKET/index.html 2>/dev/null || true

# Configure bucket as a website
echo "🌐 Configuring bucket for web hosting..."
gsutil web set -m index.html -e 404.html gs://$TARGET_BUCKET

# Make bucket publicly readable
echo "🔓 Setting public access..."
gsutil iam ch allUsers:objectViewer gs://$TARGET_BUCKET

echo ""
echo "================================================"
echo "✅ Frontend Deployment Complete!"
echo "================================================"
echo ""
echo "Frontend URL: https://storage.googleapis.com/$TARGET_BUCKET/index.html"
echo ""
echo "To set up custom domain:"
echo "  1. Add CNAME record pointing to: c.storage.googleapis.com"
echo "  2. Verify domain ownership in Google Search Console"
echo "  3. Configure bucket name to match domain"
echo ""

# Test the deployment
echo "Testing deployment..."
FRONTEND_URL="https://storage.googleapis.com/$TARGET_BUCKET/index.html"
if curl -s "$FRONTEND_URL" | grep -q "Lucky Gas"; then
    echo "✅ Frontend is accessible!"
    echo ""
    echo "🌐 Open in browser: $FRONTEND_URL"
else
    echo "⚠️ Frontend might still be propagating..."
    echo "Please wait a few minutes and try again."
fi