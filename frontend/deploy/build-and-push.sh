#!/bin/bash

# Build and push Docker image for Lucky Gas Frontend
# Usage: ./build-and-push.sh [environment] [version]
# Example: ./build-and-push.sh production v1.0.0

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
ENVIRONMENT=${1:-production}
VERSION=${2:-latest}
REGISTRY=${DOCKER_REGISTRY:-"gcr.io/luckygas-project"}
IMAGE_NAME="luckygas-frontend"

# Load environment-specific variables
ENV_FILE=".env.${ENVIRONMENT}"
if [ ! -f "$ENV_FILE" ]; then
    echo -e "${RED}Error: Environment file ${ENV_FILE} not found${NC}"
    exit 1
fi

echo -e "${GREEN}Building Lucky Gas Frontend for ${ENVIRONMENT}${NC}"
echo "Version: ${VERSION}"
echo "Registry: ${REGISTRY}"
echo ""

# Source environment variables
export $(cat $ENV_FILE | grep -v '^#' | xargs)

# Build Docker image
echo -e "${YELLOW}Building Docker image...${NC}"
docker build \
    --build-arg VITE_API_URL="${VITE_API_URL}" \
    --build-arg VITE_WS_URL="${VITE_WS_URL}" \
    --build-arg VITE_ENV="${VITE_ENV}" \
    --build-arg VITE_GOOGLE_MAPS_API_KEY="${VITE_GOOGLE_MAPS_API_KEY:-}" \
    --build-arg VITE_SENTRY_DSN="${VITE_SENTRY_DSN:-}" \
    -t "${IMAGE_NAME}:${VERSION}" \
    -t "${IMAGE_NAME}:${ENVIRONMENT}-latest" \
    .

# Tag for registry
docker tag "${IMAGE_NAME}:${VERSION}" "${REGISTRY}/${IMAGE_NAME}:${VERSION}"
docker tag "${IMAGE_NAME}:${VERSION}" "${REGISTRY}/${IMAGE_NAME}:${ENVIRONMENT}-latest"

# Push to registry
echo -e "${YELLOW}Pushing to registry...${NC}"
docker push "${REGISTRY}/${IMAGE_NAME}:${VERSION}"
docker push "${REGISTRY}/${IMAGE_NAME}:${ENVIRONMENT}-latest"

echo -e "${GREEN}Build and push completed successfully!${NC}"
echo ""
echo "Images pushed:"
echo "  - ${REGISTRY}/${IMAGE_NAME}:${VERSION}"
echo "  - ${REGISTRY}/${IMAGE_NAME}:${ENVIRONMENT}-latest"