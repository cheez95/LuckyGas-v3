#!/bin/bash

# Lucky Gas Frontend Deployment Script for Google Cloud Platform

set -e

echo "🚀 Lucky Gas Frontend Deployment to GCP"
echo "========================================"

# Configuration
PROJECT_ID=${GCP_PROJECT_ID:-"lucky-gas-production"}
BUCKET_NAME=${GCP_BUCKET_NAME:-"lucky-gas-frontend"}
REGION=${GCP_REGION:-"asia-east1"}
CDN_NAME="lucky-gas-cdn"

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

# Check if gcloud is installed
if ! command -v gcloud &> /dev/null; then
    print_error "gcloud CLI is not installed. Please install it first."
    echo "Visit: https://cloud.google.com/sdk/docs/install"
    exit 1
fi

# Check if logged in to gcloud
if ! gcloud auth list --filter=status:ACTIVE --format="value(account)" | grep -q .; then
    print_error "Not authenticated with gcloud. Please run: gcloud auth login"
    exit 1
fi

# Set the project
echo "Setting GCP project to: $PROJECT_ID"
gcloud config set project $PROJECT_ID

# Build the production version
echo ""
echo "📦 Building production version..."
echo "--------------------------------"
npm run build

if [ ! -d "dist" ]; then
    print_error "Build failed - dist directory not found"
    exit 1
fi

print_status "Build completed successfully"

# Check if bucket exists, create if not
echo ""
echo "☁️  Checking Cloud Storage bucket..."
echo "-----------------------------------"
if ! gsutil ls -b gs://$BUCKET_NAME &> /dev/null; then
    echo "Creating bucket: gs://$BUCKET_NAME"
    gsutil mb -p $PROJECT_ID -c STANDARD -l $REGION gs://$BUCKET_NAME
    
    # Enable public access
    gsutil iam ch allUsers:objectViewer gs://$BUCKET_NAME
    
    # Set up website configuration
    gsutil web set -m index.html -e index.html gs://$BUCKET_NAME
    
    print_status "Bucket created and configured"
else
    print_status "Bucket already exists"
fi

# Upload files to Cloud Storage
echo ""
echo "📤 Uploading files to Cloud Storage..."
echo "--------------------------------------"

# Clear existing files (optional - comment out if you want to keep old versions)
print_warning "Clearing existing files in bucket..."
gsutil -m rm -r gs://$BUCKET_NAME/** 2>/dev/null || true

# Upload new files with proper cache headers
echo "Uploading static assets..."

# HTML files - no cache
gsutil -m -h "Cache-Control:no-cache, no-store, must-revalidate" \
       -h "Content-Type:text/html; charset=utf-8" \
       cp dist/*.html gs://$BUCKET_NAME/

# JS files - cache for 1 year (they have hash in filename)
gsutil -m -h "Cache-Control:public, max-age=31536000, immutable" \
       -h "Content-Type:application/javascript; charset=utf-8" \
       cp -r dist/js gs://$BUCKET_NAME/

# CSS files - cache for 1 year (they have hash in filename)
gsutil -m -h "Cache-Control:public, max-age=31536000, immutable" \
       -h "Content-Type:text/css; charset=utf-8" \
       cp -r dist/css gs://$BUCKET_NAME/

# Images and other assets - cache for 1 month
if [ -d "dist/images" ]; then
    gsutil -m -h "Cache-Control:public, max-age=2592000" \
           cp -r dist/images gs://$BUCKET_NAME/
fi

# Service worker and manifest - short cache
for file in dist/service-worker.js dist/sw.js dist/manifest.json; do
    if [ -f "$file" ]; then
        gsutil -h "Cache-Control:public, max-age=3600" \
               cp "$file" gs://$BUCKET_NAME/
    fi
done

# Upload compressed versions if they exist
if ls dist/*.gz 1> /dev/null 2>&1; then
    echo "Uploading gzipped files..."
    gsutil -m -h "Content-Encoding:gzip" \
           cp dist/**/*.gz gs://$BUCKET_NAME/
fi

if ls dist/*.br 1> /dev/null 2>&1; then
    echo "Uploading brotli compressed files..."
    gsutil -m -h "Content-Encoding:br" \
           cp dist/**/*.br gs://$BUCKET_NAME/
fi

print_status "Files uploaded successfully"

# Set up Cloud CDN (optional)
echo ""
echo "🌐 Setting up Cloud CDN..."
echo "--------------------------"

# Check if load balancer exists
if gcloud compute url-maps list --format="value(name)" | grep -q "$CDN_NAME"; then
    print_warning "CDN already configured"
else
    echo "Would you like to set up Cloud CDN? (y/n)"
    read -r setup_cdn
    
    if [ "$setup_cdn" = "y" ]; then
        # Create backend bucket
        gcloud compute backend-buckets create $CDN_NAME-backend \
            --gcs-bucket-name=$BUCKET_NAME \
            --enable-cdn \
            --cache-mode=CACHE_ALL_STATIC \
            --default-ttl=3600 \
            --max-ttl=86400 \
            --negative-caching
        
        # Create URL map
        gcloud compute url-maps create $CDN_NAME \
            --default-backend-bucket=$CDN_NAME-backend
        
        # Create HTTPS proxy
        gcloud compute target-https-proxies create $CDN_NAME-https-proxy \
            --url-map=$CDN_NAME \
            --ssl-certificates=$CDN_NAME-cert
        
        print_status "Cloud CDN configured"
    fi
fi

# Print deployment information
echo ""
echo "======================================"
echo -e "${GREEN}✅ Deployment Complete!${NC}"
echo "======================================"
echo ""
echo "📍 Your frontend is deployed at:"
echo "   https://storage.googleapis.com/$BUCKET_NAME/index.html"
echo ""
echo "🌐 If using custom domain:"
echo "   1. Set up Cloud Load Balancing"
echo "   2. Configure SSL certificate"
echo "   3. Update DNS records"
echo ""
echo "📊 View in GCP Console:"
echo "   https://console.cloud.google.com/storage/browser/$BUCKET_NAME?project=$PROJECT_ID"
echo ""

# Invalidate CDN cache if needed
echo "💡 To invalidate CDN cache, run:"
echo "   gcloud compute url-maps invalidate-cdn-cache $CDN_NAME --path='/*'"

echo ""
print_status "Deployment script completed!"