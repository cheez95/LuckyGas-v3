#!/bin/bash

# LuckyGas Blue-Green Deployment Script
# Zero-downtime deployment using blue-green strategy

set -euo pipefail

# Configuration
DEPLOYMENT_ID="${1:-$(date +%Y%m%d_%H%M%S)}"
NAMESPACE="${NAMESPACE:-default}"
DOCKER_REGISTRY="${DOCKER_REGISTRY:-gcr.io/lucky-gas-prod}"
VERSION=$(git describe --tags --abbrev=0 2>/dev/null || echo "v1.0.0")

# Deployment configuration
FRONTEND_REPLICAS=3
BACKEND_REPLICAS=3
HEALTH_CHECK_RETRIES=30
HEALTH_CHECK_DELAY=10

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log() {
    echo -e "${2:-}[$(date +'%Y-%m-%d %H:%M:%S')] $1${NC}"
}

# Check current environment
check_current_environment() {
    log "Checking current environment..." "$BLUE"
    
    # Determine which environment is currently live
    local frontend_selector=$(kubectl get service luckygas-frontend -o jsonpath='{.spec.selector.deployment}' 2>/dev/null || echo "none")
    local backend_selector=$(kubectl get service luckygas-backend -o jsonpath='{.spec.selector.deployment}' 2>/dev/null || echo "none")
    
    if [ "$frontend_selector" = "blue" ] && [ "$backend_selector" = "blue" ]; then
        export CURRENT_ENV="blue"
        export TARGET_ENV="green"
    elif [ "$frontend_selector" = "green" ] && [ "$backend_selector" = "green" ]; then
        export CURRENT_ENV="green"
        export TARGET_ENV="blue"
    else
        log "Warning: Mixed or unknown environment state. Defaulting to blue as current." "$YELLOW"
        export CURRENT_ENV="blue"
        export TARGET_ENV="green"
    fi
    
    log "Current environment: $CURRENT_ENV" "$YELLOW"
    log "Target environment: $TARGET_ENV" "$YELLOW"
}

# Create Kubernetes manifests for green environment
create_green_manifests() {
    log "Creating deployment manifests for $TARGET_ENV environment..." "$BLUE"
    
    # Frontend deployment
    cat > "/tmp/frontend-${TARGET_ENV}.yaml" <<EOF
apiVersion: apps/v1
kind: Deployment
metadata:
  name: luckygas-frontend-${TARGET_ENV}
  labels:
    app: luckygas-frontend
    deployment: ${TARGET_ENV}
    version: ${VERSION}
spec:
  replicas: ${FRONTEND_REPLICAS}
  selector:
    matchLabels:
      app: luckygas-frontend
      deployment: ${TARGET_ENV}
  template:
    metadata:
      labels:
        app: luckygas-frontend
        deployment: ${TARGET_ENV}
        version: ${VERSION}
    spec:
      containers:
      - name: frontend
        image: ${DOCKER_REGISTRY}/frontend:${VERSION}
        ports:
        - containerPort: 3000
        env:
        - name: REACT_APP_API_URL
          value: "https://api.luckygas.com.tw"
        - name: DEPLOYMENT_ENV
          value: "${TARGET_ENV}"
        - name: TZ
          value: "Asia/Taipei"
        resources:
          requests:
            memory: "256Mi"
            cpu: "100m"
          limits:
            memory: "512Mi"
            cpu: "500m"
        livenessProbe:
          httpGet:
            path: /health
            port: 3000
          initialDelaySeconds: 30
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /health
            port: 3000
          initialDelaySeconds: 5
          periodSeconds: 5
---
apiVersion: v1
kind: Service
metadata:
  name: luckygas-frontend-${TARGET_ENV}
spec:
  selector:
    app: luckygas-frontend
    deployment: ${TARGET_ENV}
  ports:
  - port: 80
    targetPort: 3000
EOF

    # Backend deployment
    cat > "/tmp/backend-${TARGET_ENV}.yaml" <<EOF
apiVersion: apps/v1
kind: Deployment
metadata:
  name: luckygas-backend-${TARGET_ENV}
  labels:
    app: luckygas-backend
    deployment: ${TARGET_ENV}
    version: ${VERSION}
spec:
  replicas: ${BACKEND_REPLICAS}
  selector:
    matchLabels:
      app: luckygas-backend
      deployment: ${TARGET_ENV}
  template:
    metadata:
      labels:
        app: luckygas-backend
        deployment: ${TARGET_ENV}
        version: ${VERSION}
    spec:
      containers:
      - name: backend
        image: ${DOCKER_REGISTRY}/backend:${VERSION}
        ports:
        - containerPort: 8000
        env:
        - name: DATABASE_URL
          valueFrom:
            secretKeyRef:
              name: database-credentials
              key: url
        - name: GOOGLE_MAPS_API_KEY
          valueFrom:
            secretKeyRef:
              name: google-api-keys
              key: maps-api-key
        - name: VERTEX_AI_PROJECT
          value: "lucky-gas-prod"
        - name: TZ
          value: "Asia/Taipei"
        - name: DEPLOYMENT_ENV
          value: "${TARGET_ENV}"
        resources:
          requests:
            memory: "512Mi"
            cpu: "200m"
          limits:
            memory: "1Gi"
            cpu: "1000m"
        livenessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 30
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /health/ready
            port: 8000
          initialDelaySeconds: 10
          periodSeconds: 5
---
apiVersion: v1
kind: Service
metadata:
  name: luckygas-backend-${TARGET_ENV}
spec:
  selector:
    app: luckygas-backend
    deployment: ${TARGET_ENV}
  ports:
  - port: 80
    targetPort: 8000
EOF
    
    log "Manifests created for $TARGET_ENV environment ✓" "$GREEN"
}

# Deploy to target environment
deploy_green_environment() {
    log "Deploying to $TARGET_ENV environment..." "$BLUE"
    
    # Apply frontend deployment
    kubectl apply -f "/tmp/frontend-${TARGET_ENV}.yaml"
    
    # Apply backend deployment
    kubectl apply -f "/tmp/backend-${TARGET_ENV}.yaml"
    
    # Wait for rollout
    log "Waiting for $TARGET_ENV deployments to roll out..." "$YELLOW"
    
    kubectl rollout status deployment/luckygas-frontend-${TARGET_ENV} --timeout=300s
    kubectl rollout status deployment/luckygas-backend-${TARGET_ENV} --timeout=300s
    
    log "$TARGET_ENV environment deployed successfully ✓" "$GREEN"
}

# Health check for green environment
health_check_green() {
    log "Running health checks on $TARGET_ENV environment..." "$BLUE"
    
    local frontend_service="luckygas-frontend-${TARGET_ENV}"
    local backend_service="luckygas-backend-${TARGET_ENV}"
    
    # Get service IPs
    local frontend_ip=$(kubectl get service $frontend_service -o jsonpath='{.spec.clusterIP}')
    local backend_ip=$(kubectl get service $backend_service -o jsonpath='{.spec.clusterIP}')
    
    # Check frontend health
    for i in $(seq 1 $HEALTH_CHECK_RETRIES); do
        if kubectl run health-check-frontend-${DEPLOYMENT_ID} --rm -i --restart=Never --image=curlimages/curl -- \
            curl -s -f "http://${frontend_ip}/health" > /dev/null 2>&1; then
            log "Frontend health check passed ✓" "$GREEN"
            break
        else
            if [ $i -eq $HEALTH_CHECK_RETRIES ]; then
                log "Frontend health check failed!" "$RED"
                return 1
            fi
            log "Frontend not ready yet, retrying in ${HEALTH_CHECK_DELAY}s..." "$YELLOW"
            sleep $HEALTH_CHECK_DELAY
        fi
    done
    
    # Check backend health
    for i in $(seq 1 $HEALTH_CHECK_RETRIES); do
        if kubectl run health-check-backend-${DEPLOYMENT_ID} --rm -i --restart=Never --image=curlimages/curl -- \
            curl -s -f "http://${backend_ip}/health" > /dev/null 2>&1; then
            log "Backend health check passed ✓" "$GREEN"
            break
        else
            if [ $i -eq $HEALTH_CHECK_RETRIES ]; then
                log "Backend health check failed!" "$RED"
                return 1
            fi
            log "Backend not ready yet, retrying in ${HEALTH_CHECK_DELAY}s..." "$YELLOW"
            sleep $HEALTH_CHECK_DELAY
        fi
    done
    
    # Check critical endpoints
    log "Checking critical endpoints..." "$BLUE"
    
    # Test authentication endpoint
    kubectl run test-auth-${DEPLOYMENT_ID} --rm -i --restart=Never --image=curlimages/curl -- \
        curl -s -f "http://${backend_ip}/api/v1/auth/health" > /dev/null 2>&1
    
    # Test analytics endpoints
    local analytics_endpoints=("executive" "operations" "financial" "performance")
    for endpoint in "${analytics_endpoints[@]}"; do
        kubectl run test-analytics-${endpoint}-${DEPLOYMENT_ID} --rm -i --restart=Never --image=curlimages/curl -- \
            curl -s -o /dev/null -w "%{http_code}" "http://${backend_ip}/api/v1/analytics/${endpoint}" | grep -E "401|403" > /dev/null 2>&1
        if [ $? -eq 0 ]; then
            log "Analytics endpoint /${endpoint} responding correctly ✓" "$GREEN"
        else
            log "Analytics endpoint /${endpoint} not responding correctly!" "$RED"
            return 1
        fi
    done
    
    log "All health checks passed ✓" "$GREEN"
    return 0
}

# Run smoke tests on green environment
run_smoke_tests() {
    log "Running smoke tests on $TARGET_ENV environment..." "$BLUE"
    
    # Create test job
    cat > "/tmp/smoke-test-${DEPLOYMENT_ID}.yaml" <<EOF
apiVersion: batch/v1
kind: Job
metadata:
  name: smoke-test-${DEPLOYMENT_ID}
spec:
  template:
    spec:
      containers:
      - name: smoke-test
        image: ${DOCKER_REGISTRY}/test-runner:latest
        env:
        - name: API_URL
          value: "http://luckygas-backend-${TARGET_ENV}"
        - name: FRONTEND_URL
          value: "http://luckygas-frontend-${TARGET_ENV}"
        command: ["/bin/sh", "-c"]
        args:
          - |
            echo "Running smoke tests..."
            
            # Test login
            curl -X POST \${API_URL}/api/v1/auth/login \
              -H "Content-Type: application/json" \
              -d '{"username":"testuser","password":"testpass"}' \
              -f || exit 1
            
            # Test 預定配送日期 field
            curl -X GET \${API_URL}/api/v1/orders/schema \
              -f | grep "預定配送日期" || exit 1
            
            # Test Google Maps integration
            curl -X GET \${API_URL}/api/v1/maps/test \
              -f || exit 1
            
            echo "Smoke tests passed!"
      restartPolicy: Never
  backoffLimit: 1
EOF
    
    kubectl apply -f "/tmp/smoke-test-${DEPLOYMENT_ID}.yaml"
    
    # Wait for job to complete
    if kubectl wait --for=condition=complete job/smoke-test-${DEPLOYMENT_ID} --timeout=120s; then
        log "Smoke tests passed ✓" "$GREEN"
        kubectl delete job smoke-test-${DEPLOYMENT_ID}
        return 0
    else
        log "Smoke tests failed!" "$RED"
        kubectl logs job/smoke-test-${DEPLOYMENT_ID}
        kubectl delete job smoke-test-${DEPLOYMENT_ID}
        return 1
    fi
}

# Switch traffic to green environment
switch_traffic() {
    log "Switching traffic to $TARGET_ENV environment..." "$BLUE"
    
    # Update main services to point to green
    kubectl patch service luckygas-frontend -p '{"spec":{"selector":{"deployment":"'${TARGET_ENV}'"}}}'
    kubectl patch service luckygas-backend -p '{"spec":{"selector":{"deployment":"'${TARGET_ENV}'"}}}'
    
    # Update ingress if exists
    if kubectl get ingress luckygas-ingress &>/dev/null; then
        kubectl patch ingress luckygas-ingress --type='json' \
            -p='[
                {"op": "replace", "path": "/spec/rules/0/http/paths/0/backend/service/name", "value":"luckygas-frontend"},
                {"op": "replace", "path": "/spec/rules/0/http/paths/1/backend/service/name", "value":"luckygas-backend"}
            ]'
    fi
    
    log "Traffic switched to $TARGET_ENV ✓" "$GREEN"
    
    # Label the deployments
    kubectl label deployment luckygas-frontend-${TARGET_ENV} live=true --overwrite
    kubectl label deployment luckygas-backend-${TARGET_ENV} live=true --overwrite
    kubectl label deployment luckygas-frontend-${CURRENT_ENV} live=false --overwrite 2>/dev/null || true
    kubectl label deployment luckygas-backend-${CURRENT_ENV} live=false --overwrite 2>/dev/null || true
}

# Verify production traffic
verify_production() {
    log "Verifying production traffic..." "$BLUE"
    
    sleep 10  # Allow time for traffic to stabilize
    
    # Check external endpoints
    local api_status=$(curl -s -o /dev/null -w "%{http_code}" https://api.luckygas.com.tw/health || echo "000")
    local app_status=$(curl -s -o /dev/null -w "%{http_code}" https://app.luckygas.com.tw || echo "000")
    
    if [ "$api_status" = "200" ] && [ "$app_status" = "200" ]; then
        log "Production endpoints responding correctly ✓" "$GREEN"
        
        # Check version
        local api_version=$(curl -s https://api.luckygas.com.tw/version | jq -r '.version' || echo "unknown")
        log "API version: $api_version" "$YELLOW"
        
        return 0
    else
        log "Production verification failed! API: $api_status, App: $app_status" "$RED"
        return 1
    fi
}

# Keep blue environment for rollback
preserve_blue_environment() {
    log "Preserving $CURRENT_ENV environment for rollback..." "$BLUE"
    
    # Scale down but don't delete
    kubectl scale deployment luckygas-frontend-${CURRENT_ENV} --replicas=1
    kubectl scale deployment luckygas-backend-${CURRENT_ENV} --replicas=1
    
    # Add labels for identification
    kubectl label deployment luckygas-frontend-${CURRENT_ENV} rollback-available=true --overwrite
    kubectl label deployment luckygas-backend-${CURRENT_ENV} rollback-available=true --overwrite
    kubectl label deployment luckygas-frontend-${CURRENT_ENV} deployment-id=${DEPLOYMENT_ID} --overwrite
    kubectl label deployment luckygas-backend-${CURRENT_ENV} deployment-id=${DEPLOYMENT_ID} --overwrite
    
    log "$CURRENT_ENV environment preserved for rollback ✓" "$GREEN"
}

# Main deployment flow
main() {
    log "=== Starting Blue-Green Deployment ===" "$BLUE"
    log "Deployment ID: $DEPLOYMENT_ID" "$YELLOW"
    log "Version: $VERSION" "$YELLOW"
    
    check_current_environment
    create_green_manifests
    deploy_green_environment
    
    if health_check_green; then
        if run_smoke_tests; then
            switch_traffic
            
            if verify_production; then
                preserve_blue_environment
                log "=== Blue-Green Deployment Successful ===" "$GREEN"
                log "Traffic is now served by $TARGET_ENV environment" "$YELLOW"
                log "$CURRENT_ENV environment preserved for rollback" "$YELLOW"
                exit 0
            else
                log "Production verification failed!" "$RED"
                exit 1
            fi
        else
            log "Smoke tests failed!" "$RED"
            kubectl delete deployment luckygas-frontend-${TARGET_ENV}
            kubectl delete deployment luckygas-backend-${TARGET_ENV}
            kubectl delete service luckygas-frontend-${TARGET_ENV}
            kubectl delete service luckygas-backend-${TARGET_ENV}
            exit 1
        fi
    else
        log "Health checks failed!" "$RED"
        kubectl delete deployment luckygas-frontend-${TARGET_ENV}
        kubectl delete deployment luckygas-backend-${TARGET_ENV}
        kubectl delete service luckygas-frontend-${TARGET_ENV}
        kubectl delete service luckygas-backend-${TARGET_ENV}
        exit 1
    fi
}

# Execute main function
main