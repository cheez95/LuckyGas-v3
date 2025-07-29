#!/bin/bash

# LuckyGas Production Deployment Orchestrator
# Zero-downtime deployment with comprehensive validation

set -euo pipefail

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

# Configuration
DEPLOYMENT_ID=$(date +"%Y%m%d_%H%M%S")
DEPLOY_LOG="deploy_${DEPLOYMENT_ID}.log"
SLACK_WEBHOOK="${SLACK_WEBHOOK:-}"
PROJECT_ROOT="/Users/lgee258/Desktop/LuckyGas-v3"
DEPLOY_DIR="${PROJECT_ROOT}/deploy"

# Docker registry configuration
DOCKER_REGISTRY="${DOCKER_REGISTRY:-gcr.io/lucky-gas-prod}"
FRONTEND_IMAGE="${DOCKER_REGISTRY}/frontend"
BACKEND_IMAGE="${DOCKER_REGISTRY}/backend"

# Deployment functions
log() {
    echo -e "${2:-}[$(date +'%Y-%m-%d %H:%M:%S')] $1${NC}" | tee -a "$DEPLOY_LOG"
}

send_notification() {
    local message="$1"
    local status="${2:-info}"
    
    if [ -n "$SLACK_WEBHOOK" ]; then
        curl -X POST "$SLACK_WEBHOOK" \
            -H 'Content-Type: application/json' \
            -d "{\"text\":\"🚀 LuckyGas Deployment: ${message}\"}" \
            >/dev/null 2>&1 || true
    fi
}

check_prerequisites() {
    log "Checking deployment prerequisites..." "$BLUE"
    
    # Check required tools
    local required_tools=("docker" "kubectl" "gcloud" "npm" "psql")
    for tool in "${required_tools[@]}"; do
        if ! command -v "$tool" &> /dev/null; then
            log "Error: $tool is not installed" "$RED"
            exit 1
        fi
    done
    
    # Check Google Cloud authentication
    if ! gcloud auth list --filter=status:ACTIVE --format="value(account)" | grep -q .; then
        log "Error: Not authenticated with Google Cloud" "$RED"
        exit 1
    fi
    
    # Check kubectl context
    local current_context=$(kubectl config current-context)
    if [[ ! "$current_context" =~ "lucky-gas-prod" ]]; then
        log "Warning: kubectl context is not set to production" "$YELLOW"
        read -p "Continue with context '$current_context'? (y/N) " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            exit 1
        fi
    fi
    
    log "Prerequisites check passed ✓" "$GREEN"
}

run_pre_deployment_tests() {
    log "Running pre-deployment tests..." "$BLUE"
    
    # Run Playwright E2E tests
    cd "${PROJECT_ROOT}/playwright-tests"
    
    if npm test; then
        log "E2E tests passed ✓" "$GREEN"
    else
        log "E2E tests failed ✗" "$RED"
        send_notification "Pre-deployment tests failed! Deployment aborted." "error"
        exit 1
    fi
    
    # Verify test coverage
    local test_count=$(grep -c "✓" reports/test-results.json 2>/dev/null || echo "0")
    if [ "$test_count" -lt 100 ]; then
        log "Warning: Only $test_count tests passed (expected 100+)" "$YELLOW"
    fi
    
    cd "$PROJECT_ROOT"
}

backup_database() {
    log "Backing up production database..." "$BLUE"
    
    "${DEPLOY_DIR}/backup-database.sh" "$DEPLOYMENT_ID"
    
    if [ $? -eq 0 ]; then
        log "Database backup completed ✓" "$GREEN"
    else
        log "Database backup failed ✗" "$RED"
        exit 1
    fi
}

build_docker_images() {
    log "Building Docker images..." "$BLUE"
    
    # Get latest git tag
    local VERSION=$(git describe --tags --abbrev=0 2>/dev/null || echo "v1.0.0")
    
    # Build frontend
    log "Building frontend image..." "$BLUE"
    cd "${PROJECT_ROOT}/frontend"
    docker build -t "${FRONTEND_IMAGE}:${VERSION}" -t "${FRONTEND_IMAGE}:latest" .
    
    # Build backend
    log "Building backend image..." "$BLUE"
    cd "${PROJECT_ROOT}/backend"
    docker build -t "${BACKEND_IMAGE}:${VERSION}" -t "${BACKEND_IMAGE}:latest" .
    
    cd "$PROJECT_ROOT"
    log "Docker images built successfully ✓" "$GREEN"
}

push_docker_images() {
    log "Pushing Docker images to registry..." "$BLUE"
    
    local VERSION=$(git describe --tags --abbrev=0 2>/dev/null || echo "v1.0.0")
    
    # Configure Docker for GCR
    gcloud auth configure-docker
    
    # Push images
    docker push "${FRONTEND_IMAGE}:${VERSION}"
    docker push "${FRONTEND_IMAGE}:latest"
    docker push "${BACKEND_IMAGE}:${VERSION}"
    docker push "${BACKEND_IMAGE}:latest"
    
    log "Docker images pushed successfully ✓" "$GREEN"
}

run_database_migrations() {
    log "Running database migrations..." "$BLUE"
    
    "${DEPLOY_DIR}/migrate-database.sh"
    
    if [ $? -eq 0 ]; then
        log "Database migrations completed ✓" "$GREEN"
    else
        log "Database migrations failed ✗" "$RED"
        exit 1
    fi
}

perform_blue_green_deployment() {
    log "Starting blue-green deployment..." "$BLUE"
    
    "${DEPLOY_DIR}/blue-green-deploy.sh" "$DEPLOYMENT_ID"
    
    if [ $? -eq 0 ]; then
        log "Blue-green deployment completed ✓" "$GREEN"
    else
        log "Blue-green deployment failed ✗" "$RED"
        exit 1
    fi
}

run_health_checks() {
    log "Running health checks..." "$BLUE"
    
    "${DEPLOY_DIR}/health-check.sh"
    
    if [ $? -eq 0 ]; then
        log "Health checks passed ✓" "$GREEN"
    else
        log "Health checks failed ✗" "$RED"
        return 1
    fi
}

run_post_deployment_validation() {
    log "Running post-deployment validation..." "$BLUE"
    
    "${DEPLOY_DIR}/post-deploy-validation.sh"
    
    if [ $? -eq 0 ]; then
        log "Post-deployment validation passed ✓" "$GREEN"
    else
        log "Post-deployment validation failed ✗" "$RED"
        return 1
    fi
}

update_monitoring() {
    log "Updating monitoring and alerting..." "$BLUE"
    
    # Update Prometheus targets
    kubectl apply -f "${PROJECT_ROOT}/k8s/monitoring/prometheus-config.yaml"
    
    # Reload Grafana dashboards
    kubectl rollout restart deployment/grafana -n monitoring
    
    log "Monitoring updated ✓" "$GREEN"
}

cleanup_old_deployments() {
    log "Cleaning up old deployments..." "$BLUE"
    
    # Keep only last 3 deployments
    local old_deployments=$(kubectl get deployments -l app=luckygas,deployment-type=green \
        --sort-by=.metadata.creationTimestamp -o name | head -n -3)
    
    if [ -n "$old_deployments" ]; then
        echo "$old_deployments" | xargs kubectl delete
    fi
    
    log "Cleanup completed ✓" "$GREEN"
}

# Main deployment flow
main() {
    log "=== LuckyGas Production Deployment Started ===" "$BLUE"
    log "Deployment ID: $DEPLOYMENT_ID" "$BLUE"
    send_notification "Deployment started (ID: $DEPLOYMENT_ID)"
    
    # Pre-deployment phase
    check_prerequisites
    run_pre_deployment_tests
    backup_database
    
    # Build phase
    build_docker_images
    push_docker_images
    
    # Deployment phase
    run_database_migrations
    perform_blue_green_deployment
    
    # Validation phase
    sleep 30  # Wait for services to stabilize
    
    if run_health_checks && run_post_deployment_validation; then
        log "=== Deployment Successful ===" "$GREEN"
        send_notification "Deployment completed successfully! 🎉"
        update_monitoring
        cleanup_old_deployments
    else
        log "=== Deployment Failed - Rolling Back ===" "$RED"
        send_notification "Deployment failed! Rolling back... 🔄" "error"
        "${DEPLOY_DIR}/rollback.sh" "$DEPLOYMENT_ID"
        exit 1
    fi
    
    # Generate deployment report
    cat > "deployment_report_${DEPLOYMENT_ID}.txt" <<EOF
LuckyGas Production Deployment Report
=====================================
Deployment ID: $DEPLOYMENT_ID
Date: $(date)
Version: $(git describe --tags --abbrev=0 2>/dev/null || echo "v1.0.0")
Status: SUCCESS

Pre-deployment Tests: PASSED
Database Backup: COMPLETED
Docker Images: BUILT & PUSHED
Database Migrations: APPLIED
Blue-Green Deploy: SUCCESSFUL
Health Checks: PASSED
Post-Deploy Validation: PASSED

Deployment Log: $DEPLOY_LOG
=====================================
EOF
    
    log "Deployment report generated: deployment_report_${DEPLOYMENT_ID}.txt" "$BLUE"
    log "=== Deployment Complete ===" "$GREEN"
}

# Execute main function
main "$@"