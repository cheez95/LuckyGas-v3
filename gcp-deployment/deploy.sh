#!/bin/bash

# LuckyGas v3.0 GCP Production Deployment Script
# Automated deployment to Google Cloud Platform

set -e  # Exit on error

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
PROJECT_ID="vast-tributary-466619-m8"
REGION="asia-east1"
ZONE="asia-east1-a"
SERVICE_NAME="luckygas-backend"
DB_INSTANCE="luckygas-prod-db"
REDIS_INSTANCE="luckygas-cache"

# Function to print colored output
print_status() {
    echo -e "${BLUE}[$(date +'%Y-%m-%d %H:%M:%S')]${NC} $1"
}

print_success() {
    echo -e "${GREEN}✓${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}⚠${NC} $1"
}

print_error() {
    echo -e "${RED}✗${NC} $1"
}

# Check prerequisites
check_prerequisites() {
    print_status "Checking prerequisites..."
    
    # Check gcloud
    if ! command -v gcloud &> /dev/null; then
        print_error "gcloud CLI not found. Please install Google Cloud SDK."
        exit 1
    fi
    
    # Check Docker
    if ! command -v docker &> /dev/null; then
        print_error "Docker not found. Please install Docker."
        exit 1
    fi
    
    # Check authentication
    if ! gcloud auth list --filter=status:ACTIVE --format="value(account)" | grep -q .; then
        print_error "Not authenticated. Please run: gcloud auth login"
        exit 1
    fi
    
    print_success "Prerequisites check passed"
}

# Enable required APIs
enable_apis() {
    print_status "Enabling required Google Cloud APIs..."
    
    gcloud services enable \
        run.googleapis.com \
        sqladmin.googleapis.com \
        compute.googleapis.com \
        redis.googleapis.com \
        secretmanager.googleapis.com \
        cloudbuild.googleapis.com \
        monitoring.googleapis.com \
        logging.googleapis.com \
        storage.googleapis.com \
        artifactregistry.googleapis.com \
        aiplatform.googleapis.com \
        --project=$PROJECT_ID
    
    print_success "APIs enabled"
}

# Create Artifact Registry repository
create_artifact_registry() {
    print_status "Creating Artifact Registry repository..."
    
    if ! gcloud artifacts repositories describe luckygas --location=$REGION --project=$PROJECT_ID &>/dev/null; then
        gcloud artifacts repositories create luckygas \
            --repository-format=docker \
            --location=$REGION \
            --description="LuckyGas Docker images" \
            --project=$PROJECT_ID
        print_success "Artifact Registry created"
    else
        print_warning "Artifact Registry already exists"
    fi
}

# Set up Cloud SQL
setup_cloud_sql() {
    print_status "Setting up Cloud SQL PostgreSQL instance..."
    
    # Check if instance exists
    if ! gcloud sql instances describe $DB_INSTANCE --project=$PROJECT_ID &>/dev/null; then
        print_status "Creating Cloud SQL instance (this may take 10-15 minutes)..."
        
        gcloud sql instances create $DB_INSTANCE \
            --database-version=POSTGRES_15 \
            --tier=db-n1-standard-2 \
            --region=$REGION \
            --network=default \
            --storage-size=100GB \
            --storage-type=SSD \
            --storage-auto-increase \
            --storage-auto-increase-limit=500 \
            --backup \
            --backup-start-time=03:00 \
            --maintenance-window-day=SUN \
            --maintenance-window-hour=4 \
            --maintenance-release-channel=production \
            --database-flags=max_connections=200,shared_buffers=256MB \
            --project=$PROJECT_ID
        
        print_success "Cloud SQL instance created"
    else
        print_warning "Cloud SQL instance already exists"
    fi
    
    # Create database
    if ! gcloud sql databases describe luckygas --instance=$DB_INSTANCE --project=$PROJECT_ID &>/dev/null; then
        gcloud sql databases create luckygas \
            --instance=$DB_INSTANCE \
            --project=$PROJECT_ID
        print_success "Database created"
    fi
    
    # Set root password
    DB_PASSWORD=$(openssl rand -base64 32)
    gcloud sql users set-password postgres \
        --instance=$DB_INSTANCE \
        --password=$DB_PASSWORD \
        --project=$PROJECT_ID
    
    # Store password in Secret Manager
    echo -n "$DB_PASSWORD" | gcloud secrets create database-password \
        --data-file=- \
        --replication-policy=user-managed \
        --locations=$REGION \
        --project=$PROJECT_ID 2>/dev/null || \
    echo -n "$DB_PASSWORD" | gcloud secrets versions add database-password \
        --data-file=- \
        --project=$PROJECT_ID
    
    print_success "Database password stored in Secret Manager"
}

# Set up Redis (Memorystore)
setup_redis() {
    print_status "Setting up Redis Memorystore instance..."
    
    # Check if instance exists
    if ! gcloud redis instances describe $REDIS_INSTANCE --region=$REGION --project=$PROJECT_ID &>/dev/null; then
        print_status "Creating Redis instance (this may take 5-10 minutes)..."
        
        gcloud redis instances create $REDIS_INSTANCE \
            --size=1 \
            --region=$REGION \
            --redis-version=redis_6_x \
            --display-name="LuckyGas Cache" \
            --project=$PROJECT_ID
        
        print_success "Redis instance created"
    else
        print_warning "Redis instance already exists"
    fi
}

# Create Cloud Storage buckets
setup_storage() {
    print_status "Setting up Cloud Storage buckets..."
    
    # Frontend bucket
    if ! gsutil ls -b gs://luckygas-frontend-prod &>/dev/null; then
        gsutil mb -p $PROJECT_ID -l $REGION gs://luckygas-frontend-prod
        gsutil iam ch allUsers:objectViewer gs://luckygas-frontend-prod
        print_success "Frontend bucket created"
    fi
    
    # Backup bucket
    if ! gsutil ls -b gs://luckygas-backups-prod &>/dev/null; then
        gsutil mb -p $PROJECT_ID -l $REGION gs://luckygas-backups-prod
        
        # Set lifecycle policy for backup retention
        cat > /tmp/lifecycle.json <<EOF
{
  "lifecycle": {
    "rule": [
      {
        "action": {"type": "Delete"},
        "condition": {"age": 90}
      }
    ]
  }
}
EOF
        gsutil lifecycle set /tmp/lifecycle.json gs://luckygas-backups-prod
        rm /tmp/lifecycle.json
        print_success "Backup bucket created with 90-day retention"
    fi
}

# Store secrets in Secret Manager
setup_secrets() {
    print_status "Setting up Secret Manager..."
    
    # Generate and store JWT secret
    JWT_SECRET=$(openssl rand -hex 32)
    echo -n "$JWT_SECRET" | gcloud secrets create jwt-secret-key \
        --data-file=- \
        --replication-policy=user-managed \
        --locations=$REGION \
        --project=$PROJECT_ID 2>/dev/null || true
    
    # Generate and store superuser password
    SUPERUSER_PASSWORD=$(openssl rand -base64 16)
    echo -n "$SUPERUSER_PASSWORD" | gcloud secrets create first-superuser-password \
        --data-file=- \
        --replication-policy=user-managed \
        --locations=$REGION \
        --project=$PROJECT_ID 2>/dev/null || true
    
    print_success "Secrets configured"
}

# Build and push Docker image
build_and_push_image() {
    print_status "Building and pushing Docker image..."
    
    cd backend
    
    # Configure Docker for Artifact Registry
    gcloud auth configure-docker ${REGION}-docker.pkg.dev --quiet
    
    # Build image
    IMAGE_URL="${REGION}-docker.pkg.dev/${PROJECT_ID}/luckygas/${SERVICE_NAME}:latest"
    docker build -f Dockerfile.production -t $IMAGE_URL .
    
    # Push image
    docker push $IMAGE_URL
    
    cd ..
    print_success "Docker image pushed to Artifact Registry"
}

# Deploy to Cloud Run
deploy_cloud_run() {
    print_status "Deploying to Cloud Run..."
    
    # Get database connection details
    DB_CONNECTION_NAME=$(gcloud sql instances describe $DB_INSTANCE \
        --format="value(connectionName)" \
        --project=$PROJECT_ID)
    
    # Get Redis host
    REDIS_HOST=$(gcloud redis instances describe $REDIS_INSTANCE \
        --region=$REGION \
        --format="value(host)" \
        --project=$PROJECT_ID)
    
    # Deploy service
    IMAGE_URL="${REGION}-docker.pkg.dev/${PROJECT_ID}/luckygas/${SERVICE_NAME}:latest"
    
    gcloud run deploy $SERVICE_NAME \
        --image=$IMAGE_URL \
        --platform=managed \
        --region=$REGION \
        --memory=2Gi \
        --cpu=2 \
        --min-instances=1 \
        --max-instances=10 \
        --concurrency=100 \
        --timeout=300 \
        --port=8080 \
        --allow-unauthenticated \
        --add-cloudsql-instances=$DB_CONNECTION_NAME \
        --set-env-vars="ENVIRONMENT=production" \
        --set-env-vars="DATABASE_URL=postgresql+asyncpg://postgres:$(gcloud secrets versions access latest --secret=database-password)@localhost/luckygas?host=/cloudsql/${DB_CONNECTION_NAME}" \
        --set-env-vars="REDIS_URL=redis://${REDIS_HOST}:6379" \
        --set-env-vars="PROJECT_ID=${PROJECT_ID}" \
        --set-env-vars="SECRET_KEY=$(gcloud secrets versions access latest --secret=jwt-secret-key)" \
        --set-env-vars="FIRST_SUPERUSER=admin@luckygas.com.tw" \
        --set-env-vars="FIRST_SUPERUSER_PASSWORD=$(gcloud secrets versions access latest --secret=first-superuser-password)" \
        --project=$PROJECT_ID
    
    # Get service URL
    SERVICE_URL=$(gcloud run services describe $SERVICE_NAME \
        --platform=managed \
        --region=$REGION \
        --format="value(status.url)" \
        --project=$PROJECT_ID)
    
    print_success "Cloud Run service deployed: $SERVICE_URL"
}

# Set up monitoring
setup_monitoring() {
    print_status "Setting up monitoring and alerting..."
    
    # Create notification channel (email)
    gcloud alpha monitoring channels create \
        --display-name="LuckyGas Alerts" \
        --type=email \
        --channel-labels=email_address=admin@luckygas.com.tw \
        --project=$PROJECT_ID 2>/dev/null || true
    
    # Create uptime check
    cat > /tmp/uptime-check.yaml <<EOF
displayName: LuckyGas Health Check
monitoredResource:
  type: uptime_url
  labels:
    host: ${SERVICE_URL#https://}
    project_id: $PROJECT_ID
httpCheck:
  path: /api/v1/health
  port: 443
  useSsl: true
  validateSsl: true
selectedRegions:
  - ASIA_PACIFIC
  - USA
  - EUROPE
EOF
    
    gcloud monitoring uptime-check-configs create \
        --from-file=/tmp/uptime-check.yaml \
        --project=$PROJECT_ID 2>/dev/null || true
    
    rm /tmp/uptime-check.yaml
    
    print_success "Monitoring configured"
}

# Run deployment
main() {
    echo -e "${BLUE}========================================${NC}"
    echo -e "${BLUE}  LuckyGas v3.0 GCP Deployment Script  ${NC}"
    echo -e "${BLUE}========================================${NC}"
    echo ""
    
    check_prerequisites
    enable_apis
    create_artifact_registry
    setup_cloud_sql
    setup_redis
    setup_storage
    setup_secrets
    build_and_push_image
    deploy_cloud_run
    setup_monitoring
    
    echo ""
    echo -e "${GREEN}========================================${NC}"
    echo -e "${GREEN}     Deployment Completed Successfully!  ${NC}"
    echo -e "${GREEN}========================================${NC}"
    echo ""
    echo -e "${BLUE}Service URL:${NC} $SERVICE_URL"
    echo -e "${BLUE}Health Check:${NC} ${SERVICE_URL}/api/v1/health"
    echo -e "${BLUE}Project:${NC} $PROJECT_ID"
    echo -e "${BLUE}Region:${NC} $REGION"
    echo ""
    echo -e "${YELLOW}Next Steps:${NC}"
    echo "1. Test the health endpoint"
    echo "2. Run database migrations"
    echo "3. Configure custom domain"
    echo "4. Set up CI/CD pipeline"
    echo ""
}

# Run if not sourced
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi