#\!/bin/bash
# Lucky Gas Rollback Script

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
PROJECT_ID="${GCP_PROJECT_ID:-luckygas-production}"
REGION="${GCP_REGION:-asia-east1}"
BACKEND_SERVICE="luckygas-backend"
FRONTEND_SERVICE="luckygas-frontend"

echo -e "${RED}🔄 Lucky Gas Rollback Script${NC}"
echo ""

# Function to list recent revisions
list_revisions() {
    echo -e "${YELLOW}Recent backend revisions:${NC}"
    gcloud run revisions list --service $BACKEND_SERVICE --region $REGION --limit 5
    echo ""
    echo -e "${YELLOW}Recent frontend revisions:${NC}"
    gcloud run revisions list --service $FRONTEND_SERVICE --region $REGION --limit 5
}

# Function to rollback service
rollback_service() {
    local service=$1
    local revision=$2
    
    echo -e "${YELLOW}Rolling back $service to revision $revision...${NC}"
    gcloud run services update-traffic $service --region $REGION --to-revisions=$revision=100
    echo -e "${GREEN}✓ $service rolled back to $revision${NC}"
}

# Function to get previous revision
get_previous_revision() {
    local service=$1
    gcloud run revisions list --service $service --region $REGION --limit 2 --format='value(name)' | tail -n 1
}

# Main rollback flow
main() {
    echo -e "${YELLOW}Starting rollback process...${NC}"
    
    if [ $# -eq 0 ]; then
        # Auto rollback to previous revision
        echo -e "${YELLOW}No revision specified, rolling back to previous revision...${NC}"
        
        BACKEND_PREV=$(get_previous_revision $BACKEND_SERVICE)
        FRONTEND_PREV=$(get_previous_revision $FRONTEND_SERVICE)
        
        rollback_service $BACKEND_SERVICE $BACKEND_PREV
        rollback_service $FRONTEND_SERVICE $FRONTEND_PREV
    elif [ $# -eq 1 ]; then
        # Rollback to specific revision
        REVISION=$1
        rollback_service $BACKEND_SERVICE "$BACKEND_SERVICE-$REVISION"
        rollback_service $FRONTEND_SERVICE "$FRONTEND_SERVICE-$REVISION"
    else
        echo -e "${RED}Usage: $0 [revision]${NC}"
        echo -e "If no revision is specified, will rollback to previous revision"
        echo ""
        list_revisions
        exit 1
    fi
    
    # Run health checks
    echo -e "${YELLOW}Running health checks...${NC}"
    sleep 10  # Wait for rollback to take effect
    
    BACKEND_URL=$(gcloud run services describe $BACKEND_SERVICE --region $REGION --format 'value(status.url)')
    FRONTEND_URL=$(gcloud run services describe $FRONTEND_SERVICE --region $REGION --format 'value(status.url)')
    
    if curl -f "$BACKEND_URL/health" > /dev/null 2>&1; then
        echo -e "${GREEN}✓ Backend health check passed${NC}"
    else
        echo -e "${RED}✗ Backend health check failed${NC}"
    fi
    
    if curl -f "$FRONTEND_URL" > /dev/null 2>&1; then
        echo -e "${GREEN}✓ Frontend health check passed${NC}"
    else
        echo -e "${RED}✗ Frontend health check failed${NC}"
    fi
    
    echo -e "${GREEN}🎉 Rollback completed\!${NC}"
}

# Show help if requested
if [ "${1:-}" = "--help" ] || [ "${1:-}" = "-h" ]; then
    echo "Lucky Gas Rollback Script"
    echo ""
    echo "Usage: $0 [revision]"
    echo ""
    echo "Examples:"
    echo "  $0                    # Rollback to previous revision"
    echo "  $0 abc123            # Rollback to specific revision"
    echo "  $0 --list            # List recent revisions"
    exit 0
fi

# List revisions if requested
if [ "${1:-}" = "--list" ] || [ "${1:-}" = "-l" ]; then
    list_revisions
    exit 0
fi

# Run main function
main "$@"
