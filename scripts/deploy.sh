#\!/bin/bash
# Lucky Gas Deployment Script

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
PROJECT_ID="${GCP_PROJECT_ID:-luckygas-production}"
REGION="${GCP_REGION:-asia-east1}"
ENVIRONMENT="${ENVIRONMENT:-production}"
VERSION="${VERSION:-$(git rev-parse --short HEAD)}"

# Services
BACKEND_SERVICE="luckygas-backend"
FRONTEND_SERVICE="luckygas-frontend"
ARTIFACT_REGISTRY="asia-east1-docker.pkg.dev"

echo -e "${GREEN}🚀 Lucky Gas Deployment Script${NC}"
echo -e "Environment: ${YELLOW}$ENVIRONMENT${NC}"
echo -e "Version: ${YELLOW}$VERSION${NC}"
echo ""

# Function to check prerequisites
check_prerequisites() {
    echo -e "${YELLOW}Checking prerequisites...${NC}"
    
    if \! command -v gcloud &> /dev/null; then
        echo -e "${RED}Error: gcloud CLI not found${NC}"
        exit 1
    fi
    
    if \! command -v docker &> /dev/null; then
        echo -e "${RED}Error: Docker not found${NC}"
        exit 1
    fi
    
    echo -e "${GREEN}✓ Prerequisites checked${NC}"
}

# Function to run tests
run_tests() {
    echo -e "${YELLOW}Running tests...${NC}"
    
    # Frontend tests
    cd frontend
    npm test -- --watchAll=false
    cd ..
    
    # Backend tests
    cd backend
    uv run pytest
    cd ..
    
    echo -e "${GREEN}✓ Tests passed${NC}"
}

# Function to build and push images
build_and_push_images() {
    echo -e "${YELLOW}Building and pushing Docker images...${NC}"
    
    # Configure Docker for Artifact Registry
    gcloud auth configure-docker $ARTIFACT_REGISTRY
    
    # Build and push backend
    echo -e "${YELLOW}Building backend image...${NC}"
    docker build -t $ARTIFACT_REGISTRY/$PROJECT_ID/luckygas/$BACKEND_SERVICE:$VERSION ./backend
    docker tag $ARTIFACT_REGISTRY/$PROJECT_ID/luckygas/$BACKEND_SERVICE:$VERSION \
               $ARTIFACT_REGISTRY/$PROJECT_ID/luckygas/$BACKEND_SERVICE:latest
    docker push $ARTIFACT_REGISTRY/$PROJECT_ID/luckygas/$BACKEND_SERVICE:$VERSION
    docker push $ARTIFACT_REGISTRY/$PROJECT_ID/luckygas/$BACKEND_SERVICE:latest
    
    # Build and push frontend
    echo -e "${YELLOW}Building frontend image...${NC}"
    docker build -t $ARTIFACT_REGISTRY/$PROJECT_ID/luckygas/$FRONTEND_SERVICE:$VERSION ./frontend
    docker tag $ARTIFACT_REGISTRY/$PROJECT_ID/luckygas/$FRONTEND_SERVICE:$VERSION \
               $ARTIFACT_REGISTRY/$PROJECT_ID/luckygas/$FRONTEND_SERVICE:latest
    docker push $ARTIFACT_REGISTRY/$PROJECT_ID/luckygas/$FRONTEND_SERVICE:$VERSION
    docker push $ARTIFACT_REGISTRY/$PROJECT_ID/luckygas/$FRONTEND_SERVICE:latest
    
    echo -e "${GREEN}✓ Images built and pushed${NC}"
}

# Function to deploy to Cloud Run
deploy_to_cloud_run() {
    echo -e "${YELLOW}Deploying to Cloud Run...${NC}"
    
    # Deploy backend
    echo -e "${YELLOW}Deploying backend...${NC}"
    gcloud run deploy $BACKEND_SERVICE \
        --image $ARTIFACT_REGISTRY/$PROJECT_ID/luckygas/$BACKEND_SERVICE:$VERSION \
        --region $REGION \
        --platform managed \
        --allow-unauthenticated \
        --set-env-vars "ENVIRONMENT=$ENVIRONMENT,VERSION=$VERSION" \
        --min-instances 1 \
        --max-instances 10 \
        --cpu 2 \
        --memory 4Gi
    
    # Deploy frontend
    echo -e "${YELLOW}Deploying frontend...${NC}"
    gcloud run deploy $FRONTEND_SERVICE \
        --image $ARTIFACT_REGISTRY/$PROJECT_ID/luckygas/$FRONTEND_SERVICE:$VERSION \
        --region $REGION \
        --platform managed \
        --allow-unauthenticated \
        --set-env-vars "ENVIRONMENT=$ENVIRONMENT,VERSION=$VERSION" \
        --min-instances 1 \
        --max-instances 20
    
    echo -e "${GREEN}✓ Services deployed${NC}"
}

# Function to run health checks
run_health_checks() {
    echo -e "${YELLOW}Running health checks...${NC}"
    
    # Get service URLs
    BACKEND_URL=$(gcloud run services describe $BACKEND_SERVICE --region $REGION --format 'value(status.url)')
    FRONTEND_URL=$(gcloud run services describe $FRONTEND_SERVICE --region $REGION --format 'value(status.url)')
    
    # Check backend health
    if curl -f "$BACKEND_URL/health" > /dev/null 2>&1; then
        echo -e "${GREEN}✓ Backend health check passed${NC}"
    else
        echo -e "${RED}✗ Backend health check failed${NC}"
        exit 1
    fi
    
    # Check frontend health
    if curl -f "$FRONTEND_URL" > /dev/null 2>&1; then
        echo -e "${GREEN}✓ Frontend health check passed${NC}"
    else
        echo -e "${RED}✗ Frontend health check failed${NC}"
        exit 1
    fi
}

# Function to update traffic
update_traffic() {
    echo -e "${YELLOW}Updating traffic split...${NC}"
    
    if [ "$ENVIRONMENT" = "production" ]; then
        # Gradual rollout for production
        echo -e "${YELLOW}Starting gradual rollout...${NC}"
        
        # 10% traffic
        gcloud run services update-traffic $BACKEND_SERVICE --region $REGION --to-revisions=$VERSION=10
        gcloud run services update-traffic $FRONTEND_SERVICE --region $REGION --to-revisions=$VERSION=10
        sleep 300  # Wait 5 minutes
        
        # 50% traffic
        gcloud run services update-traffic $BACKEND_SERVICE --region $REGION --to-revisions=$VERSION=50
        gcloud run services update-traffic $FRONTEND_SERVICE --region $REGION --to-revisions=$VERSION=50
        sleep 300  # Wait 5 minutes
        
        # 100% traffic
        gcloud run services update-traffic $BACKEND_SERVICE --region $REGION --to-revisions=$VERSION=100
        gcloud run services update-traffic $FRONTEND_SERVICE --region $REGION --to-revisions=$VERSION=100
    else
        # Direct cutover for non-production
        gcloud run services update-traffic $BACKEND_SERVICE --region $REGION --to-latest
        gcloud run services update-traffic $FRONTEND_SERVICE --region $REGION --to-latest
    fi
    
    echo -e "${GREEN}✓ Traffic updated${NC}"
}

# Main deployment flow
main() {
    echo -e "${GREEN}Starting deployment process...${NC}"
    
    check_prerequisites
    
    if [ "$SKIP_TESTS" \!= "true" ]; then
        run_tests
    fi
    
    build_and_push_images
    deploy_to_cloud_run
    run_health_checks
    update_traffic
    
    echo -e "${GREEN}🎉 Deployment completed successfully\!${NC}"
    echo -e "Backend URL: $(gcloud run services describe $BACKEND_SERVICE --region $REGION --format 'value(status.url)')"
    echo -e "Frontend URL: $(gcloud run services describe $FRONTEND_SERVICE --region $REGION --format 'value(status.url)')"
}

# Run main function
main
