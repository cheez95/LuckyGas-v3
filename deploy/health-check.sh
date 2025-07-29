#!/bin/bash

# LuckyGas System Health Check Script
# Validates all system components are healthy

set -euo pipefail

# Configuration
API_URL="${API_URL:-https://api.luckygas.com.tw}"
FRONTEND_URL="${FRONTEND_URL:-https://app.luckygas.com.tw}"
HEALTH_CHECK_TIMEOUT=30
RETRY_COUNT=3
RETRY_DELAY=5

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

# Health check results
HEALTH_STATUS=0
HEALTH_REPORT=""

log() {
    echo -e "${2:-}[$(date +'%Y-%m-%d %H:%M:%S')] $1${NC}"
}

add_report() {
    HEALTH_REPORT="${HEALTH_REPORT}\n$1"
}

check_endpoint() {
    local endpoint="$1"
    local expected_status="${2:-200}"
    local description="$3"
    
    log "Checking $description..." "$YELLOW"
    
    for i in $(seq 1 $RETRY_COUNT); do
        local response=$(curl -s -o /dev/null -w "%{http_code}" -m $HEALTH_CHECK_TIMEOUT "$endpoint" || echo "000")
        
        if [ "$response" = "$expected_status" ]; then
            log "✓ $description is healthy (HTTP $response)" "$GREEN"
            add_report "✓ $description: HEALTHY"
            return 0
        else
            if [ $i -lt $RETRY_COUNT ]; then
                log "✗ $description returned HTTP $response, retrying in ${RETRY_DELAY}s..." "$RED"
                sleep $RETRY_DELAY
            else
                log "✗ $description is unhealthy (HTTP $response)" "$RED"
                add_report "✗ $description: UNHEALTHY (HTTP $response)"
                HEALTH_STATUS=1
                return 1
            fi
        fi
    done
}

check_api_endpoints() {
    log "=== Checking API Endpoints ===" "$YELLOW"
    
    # Core endpoints
    check_endpoint "${API_URL}/health" "200" "API Health"
    check_endpoint "${API_URL}/api/v1/auth/health" "200" "Auth Service"
    check_endpoint "${API_URL}/api/v1/customers/" "401" "Customers API (Auth Required)"
    check_endpoint "${API_URL}/api/v1/orders/" "401" "Orders API (Auth Required)"
    check_endpoint "${API_URL}/api/v1/routes/" "401" "Routes API (Auth Required)"
    
    # Analytics endpoints - Critical for validation
    check_endpoint "${API_URL}/api/v1/analytics/executive" "401" "Executive Analytics"
    check_endpoint "${API_URL}/api/v1/analytics/operations" "401" "Operations Analytics"
    check_endpoint "${API_URL}/api/v1/analytics/financial" "401" "Financial Analytics"
    check_endpoint "${API_URL}/api/v1/analytics/performance" "401" "Performance Analytics"
    
    # Google Cloud integration endpoints
    check_endpoint "${API_URL}/api/v1/maps/health" "200" "Google Maps Integration"
    check_endpoint "${API_URL}/api/v1/predictions/health" "200" "Vertex AI Integration"
}

check_frontend() {
    log "=== Checking Frontend ===" "$YELLOW"
    
    check_endpoint "${FRONTEND_URL}" "200" "Frontend Home"
    check_endpoint "${FRONTEND_URL}/login" "200" "Login Page"
    
    # Check static assets
    local assets_response=$(curl -s -o /dev/null -w "%{http_code}" "${FRONTEND_URL}/static/js/main.js" || echo "000")
    if [[ "$assets_response" =~ ^(200|304)$ ]]; then
        log "✓ Static assets are being served" "$GREEN"
        add_report "✓ Static Assets: HEALTHY"
    else
        log "✗ Static assets are not accessible" "$RED"
        add_report "✗ Static Assets: UNHEALTHY"
        HEALTH_STATUS=1
    fi
}

check_database() {
    log "=== Checking Database Connectivity ===" "$YELLOW"
    
    # Check database through API health endpoint with detailed check
    local db_health=$(curl -s "${API_URL}/health/db" | jq -r '.status' 2>/dev/null || echo "error")
    
    if [ "$db_health" = "healthy" ]; then
        log "✓ Database connection is healthy" "$GREEN"
        add_report "✓ Database: HEALTHY"
    else
        log "✗ Database connection is unhealthy" "$RED"
        add_report "✗ Database: UNHEALTHY"
        HEALTH_STATUS=1
    fi
}

check_kubernetes_pods() {
    log "=== Checking Kubernetes Pods ===" "$YELLOW"
    
    # Check frontend pods
    local frontend_pods=$(kubectl get pods -l app=luckygas-frontend -o json | jq '.items | length')
    local frontend_ready=$(kubectl get pods -l app=luckygas-frontend -o json | jq '[.items[].status.conditions[] | select(.type=="Ready" and .status=="True")] | length')
    
    if [ "$frontend_ready" -ge 2 ]; then
        log "✓ Frontend pods are healthy ($frontend_ready/$frontend_pods ready)" "$GREEN"
        add_report "✓ Frontend Pods: $frontend_ready/$frontend_pods READY"
    else
        log "✗ Frontend pods are not healthy ($frontend_ready/$frontend_pods ready)" "$RED"
        add_report "✗ Frontend Pods: $frontend_ready/$frontend_pods NOT READY"
        HEALTH_STATUS=1
    fi
    
    # Check backend pods
    local backend_pods=$(kubectl get pods -l app=luckygas-backend -o json | jq '.items | length')
    local backend_ready=$(kubectl get pods -l app=luckygas-backend -o json | jq '[.items[].status.conditions[] | select(.type=="Ready" and .status=="True")] | length')
    
    if [ "$backend_ready" -ge 2 ]; then
        log "✓ Backend pods are healthy ($backend_ready/$backend_pods ready)" "$GREEN"
        add_report "✓ Backend Pods: $backend_ready/$backend_pods READY"
    else
        log "✗ Backend pods are not healthy ($backend_ready/$backend_pods ready)" "$RED"
        add_report "✗ Backend Pods: $backend_ready/$backend_pods NOT READY"
        HEALTH_STATUS=1
    fi
}

check_external_services() {
    log "=== Checking External Services ===" "$YELLOW"
    
    # Check Google Maps API
    local maps_test=$(curl -s "${API_URL}/api/v1/maps/test" | jq -r '.status' 2>/dev/null || echo "error")
    if [ "$maps_test" = "ok" ]; then
        log "✓ Google Maps API is accessible" "$GREEN"
        add_report "✓ Google Maps API: ACCESSIBLE"
    else
        log "✗ Google Maps API is not accessible" "$RED"
        add_report "✗ Google Maps API: NOT ACCESSIBLE"
        HEALTH_STATUS=1
    fi
    
    # Check Vertex AI
    local vertex_test=$(curl -s "${API_URL}/api/v1/predictions/test" | jq -r '.status' 2>/dev/null || echo "error")
    if [ "$vertex_test" = "ok" ]; then
        log "✓ Vertex AI is accessible" "$GREEN"
        add_report "✓ Vertex AI: ACCESSIBLE"
    else
        log "✗ Vertex AI is not accessible" "$RED"
        add_report "✗ Vertex AI: NOT ACCESSIBLE"
        # Don't fail deployment for ML service
    fi
}

check_ssl_certificates() {
    log "=== Checking SSL Certificates ===" "$YELLOW"
    
    # Check API SSL
    local api_cert_expiry=$(echo | openssl s_client -servername api.luckygas.com.tw -connect api.luckygas.com.tw:443 2>/dev/null | openssl x509 -noout -dates | grep notAfter | cut -d= -f2)
    local api_days_left=$(( ($(date -d "$api_cert_expiry" +%s) - $(date +%s)) / 86400 ))
    
    if [ "$api_days_left" -gt 30 ]; then
        log "✓ API SSL certificate valid for $api_days_left days" "$GREEN"
        add_report "✓ API SSL: Valid for $api_days_left days"
    else
        log "⚠ API SSL certificate expires in $api_days_left days" "$YELLOW"
        add_report "⚠ API SSL: Expires in $api_days_left days"
    fi
    
    # Check Frontend SSL
    local frontend_cert_expiry=$(echo | openssl s_client -servername app.luckygas.com.tw -connect app.luckygas.com.tw:443 2>/dev/null | openssl x509 -noout -dates | grep notAfter | cut -d= -f2)
    local frontend_days_left=$(( ($(date -d "$frontend_cert_expiry" +%s) - $(date +%s)) / 86400 ))
    
    if [ "$frontend_days_left" -gt 30 ]; then
        log "✓ Frontend SSL certificate valid for $frontend_days_left days" "$GREEN"
        add_report "✓ Frontend SSL: Valid for $frontend_days_left days"
    else
        log "⚠ Frontend SSL certificate expires in $frontend_days_left days" "$YELLOW"
        add_report "⚠ Frontend SSL: Expires in $frontend_days_left days"
    fi
}

generate_health_report() {
    local report_file="health_check_$(date +%Y%m%d_%H%M%S).txt"
    
    cat > "$report_file" <<EOF
LuckyGas System Health Check Report
===================================
Date: $(date)
Status: $([ $HEALTH_STATUS -eq 0 ] && echo "HEALTHY" || echo "UNHEALTHY")

Health Check Results:
$HEALTH_REPORT

===================================
EOF
    
    log "Health report generated: $report_file" "$YELLOW"
}

# Main health check flow
main() {
    log "=== Starting LuckyGas Health Check ===" "$YELLOW"
    
    check_api_endpoints
    check_frontend
    check_database
    check_kubernetes_pods
    check_external_services
    check_ssl_certificates
    
    generate_health_report
    
    if [ $HEALTH_STATUS -eq 0 ]; then
        log "=== All Health Checks Passed ✓ ===" "$GREEN"
    else
        log "=== Some Health Checks Failed ✗ ===" "$RED"
    fi
    
    exit $HEALTH_STATUS
}

# Execute main function
main "$@"