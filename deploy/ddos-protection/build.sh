#!/bin/bash
# Build and push DDoS Protection Service container

set -e

# Configuration
PROJECT_ID="lucky-gas-prod"
IMAGE_NAME="ddos-protection"
REGISTRY="gcr.io"
TAG="${1:-latest}"

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${GREEN}Building DDoS Protection Service...${NC}"

# Get script directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

# Build the image
echo -e "${YELLOW}Building Docker image...${NC}"
docker build -t ${IMAGE_NAME}:${TAG} .

# Tag for GCR
echo -e "${YELLOW}Tagging image for Google Container Registry...${NC}"
docker tag ${IMAGE_NAME}:${TAG} ${REGISTRY}/${PROJECT_ID}/${IMAGE_NAME}:${TAG}

# Push to GCR
echo -e "${YELLOW}Pushing image to registry...${NC}"
docker push ${REGISTRY}/${PROJECT_ID}/${IMAGE_NAME}:${TAG}

# Also tag and push as latest if not already
if [ "$TAG" != "latest" ]; then
    docker tag ${IMAGE_NAME}:${TAG} ${REGISTRY}/${PROJECT_ID}/${IMAGE_NAME}:latest
    docker push ${REGISTRY}/${PROJECT_ID}/${IMAGE_NAME}:latest
fi

echo -e "${GREEN}✓ DDoS Protection Service built and pushed successfully!${NC}"
echo -e "${GREEN}  Image: ${REGISTRY}/${PROJECT_ID}/${IMAGE_NAME}:${TAG}${NC}"

# Update deployment if running in CI
if [ "$CI" = "true" ]; then
    echo -e "${YELLOW}Updating Kubernetes deployment...${NC}"
    kubectl set image deployment/ddos-protection ddos-analyzer=${REGISTRY}/${PROJECT_ID}/${IMAGE_NAME}:${TAG} -n ingress-nginx
    kubectl rollout status deployment/ddos-protection -n ingress-nginx
fi