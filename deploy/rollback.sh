#!/bin/bash

# LuckyGas Emergency Rollback Script
# Quickly rollback to previous stable deployment

set -euo pipefail

# Configuration
DEPLOYMENT_ID="${1:-}"
ROLLBACK_LOG="rollback_$(date +%Y%m%d_%H%M%S).log"
SLACK_WEBHOOK="${SLACK_WEBHOOK:-}"
MAX_ROLLBACK_TIME=120  # 2 minutes max

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Start timer
START_TIME=$(date +%s)

log() {
    echo -e "${2:-}[$(date +'%Y-%m-%d %H:%M:%S')] $1${NC}" | tee -a "$ROLLBACK_LOG"
}

send_notification() {
    local message="$1"
    local status="${2:-info}"
    
    if [ -n "$SLACK_WEBHOOK" ]; then
        curl -X POST "$SLACK_WEBHOOK" \
            -H 'Content-Type: application/json' \
            -d "{\"text\":\"🔄 LuckyGas Rollback: ${message}\"}" \
            >/dev/null 2>&1 || true
    fi
}

check_rollback_prerequisites() {
    log "Checking rollback prerequisites..." "$BLUE"
    
    # Verify we have a blue deployment to rollback to
    local blue_deployment=$(kubectl get deployment luckygas-blue -o name 2>/dev/null || echo "")
    
    if [ -z "$blue_deployment" ]; then
        log "Error: No blue deployment found to rollback to!" "$RED"
        exit 1
    fi
    
    log "Blue deployment found ✓" "$GREEN"
}

switch_traffic_to_blue() {
    log "Switching traffic back to blue environment..." "$BLUE"
    
    # Update service selectors to point to blue
    kubectl patch service luckygas-frontend -p '{"spec":{"selector":{"deployment":"blue"}}}'
    kubectl patch service luckygas-backend -p '{"spec":{"selector":{"deployment":"blue"}}}'
    
    # Update ingress to blue
    kubectl patch ingress luckygas-ingress --type='json' \
        -p='[{"op": "replace", "path": "/spec/rules/0/http/paths/0/backend/service/name", "value":"luckygas-frontend-blue"}]'
    
    log "Traffic switched to blue ✓" "$GREEN"
}

verify_blue_health() {
    log "Verifying blue environment health..." "$BLUE"
    
    # Wait for blue pods to be ready
    kubectl wait --for=condition=ready pod -l app=luckygas,deployment=blue --timeout=60s
    
    # Quick health check
    local frontend_ready=$(kubectl get pods -l app=luckygas-frontend,deployment=blue -o json | \
        jq '[.items[].status.conditions[] | select(.type=="Ready" and .status=="True")] | length')
    local backend_ready=$(kubectl get pods -l app=luckygas-backend,deployment=blue -o json | \
        jq '[.items[].status.conditions[] | select(.type=="Ready" and .status=="True")] | length')
    
    if [ "$frontend_ready" -ge 1 ] && [ "$backend_ready" -ge 1 ]; then
        log "Blue environment is healthy ✓" "$GREEN"
        return 0
    else
        log "Blue environment health check failed!" "$RED"
        return 1
    fi
}

rollback_database() {
    log "Checking if database rollback is needed..." "$BLUE"
    
    # Check if migrations were applied in this deployment
    local migration_log="migrations_${DEPLOYMENT_ID}.log"
    
    if [ -f "$migration_log" ]; then
        log "Database migrations were applied, initiating rollback..." "$YELLOW"
        
        # Get the previous migration version
        local previous_version=$(grep "Previous version:" "$migration_log" | cut -d: -f2 | tr -d ' ')
        
        if [ -n "$previous_version" ]; then
            # Rollback to previous migration
            cd /Users/lgee258/Desktop/LuckyGas-v3/backend
            alembic downgrade "$previous_version"
            
            if [ $? -eq 0 ]; then
                log "Database rolled back to version $previous_version ✓" "$GREEN"
            else
                log "Database rollback failed! Manual intervention required!" "$RED"
                send_notification "Database rollback failed! Manual intervention required!" "error"
            fi
        fi
    else
        log "No database migrations to rollback" "$YELLOW"
    fi
}

scale_down_green() {
    log "Scaling down green deployment..." "$BLUE"
    
    # Scale green deployments to 0
    kubectl scale deployment luckygas-frontend-green --replicas=0
    kubectl scale deployment luckygas-backend-green --replicas=0
    
    log "Green deployment scaled down ✓" "$GREEN"
}

restore_monitoring() {
    log "Restoring monitoring configuration..." "$BLUE"
    
    # Revert Prometheus config if backup exists
    if kubectl get configmap prometheus-config-backup &>/dev/null; then
        kubectl delete configmap prometheus-config
        kubectl create configmap prometheus-config --from-literal=config="$(kubectl get configmap prometheus-config-backup -o jsonpath='{.data.config}')"
        kubectl rollout restart deployment prometheus -n monitoring
    fi
    
    log "Monitoring configuration restored ✓" "$GREEN"
}

cleanup_failed_deployment() {
    log "Cleaning up failed deployment artifacts..." "$BLUE"
    
    # Remove green services if they exist
    kubectl delete service luckygas-frontend-green --ignore-not-found=true
    kubectl delete service luckygas-backend-green --ignore-not-found=true
    
    # Remove any temporary resources
    kubectl delete configmap "deployment-${DEPLOYMENT_ID}" --ignore-not-found=true
    
    log "Cleanup completed ✓" "$GREEN"
}

verify_rollback_success() {
    log "Verifying rollback success..." "$BLUE"
    
    # Run basic health check
    sleep 10  # Allow services to stabilize
    
    # Check critical endpoints
    local api_health=$(curl -s -o /dev/null -w "%{http_code}" https://api.luckygas.com.tw/health || echo "000")
    local frontend_health=$(curl -s -o /dev/null -w "%{http_code}" https://app.luckygas.com.tw || echo "000")
    
    if [ "$api_health" = "200" ] && [ "$frontend_health" = "200" ]; then
        log "Rollback verification successful ✓" "$GREEN"
        return 0
    else
        log "Rollback verification failed! API: $api_health, Frontend: $frontend_health" "$RED"
        return 1
    fi
}

generate_rollback_report() {
    local end_time=$(date +%s)
    local duration=$((end_time - START_TIME))
    
    cat > "rollback_report_$(date +%Y%m%d_%H%M%S).txt" <<EOF
LuckyGas Emergency Rollback Report
==================================
Deployment ID: $DEPLOYMENT_ID
Date: $(date)
Duration: ${duration} seconds
Status: $([ $? -eq 0 ] && echo "SUCCESS" || echo "FAILED")

Actions Taken:
- Traffic switched to blue environment
- Green deployment scaled down
- Database rollback: $([ -f "migrations_${DEPLOYMENT_ID}.log" ] && echo "PERFORMED" || echo "NOT NEEDED")
- Monitoring configuration restored
- Failed deployment artifacts cleaned up

Rollback Log: $ROLLBACK_LOG
==================================
EOF
    
    log "Rollback report generated" "$BLUE"
}

# Main rollback flow
main() {
    log "=== Starting Emergency Rollback ===" "$RED"
    send_notification "Emergency rollback initiated for deployment $DEPLOYMENT_ID" "error"
    
    # Quick rollback actions
    check_rollback_prerequisites
    switch_traffic_to_blue
    
    # Verify blue is handling traffic
    if verify_blue_health; then
        log "Traffic successfully restored to blue environment ✓" "$GREEN"
        send_notification "Traffic restored to previous stable version"
        
        # Cleanup actions (can be done async)
        rollback_database
        scale_down_green
        restore_monitoring
        cleanup_failed_deployment
        
        # Final verification
        if verify_rollback_success; then
            log "=== Rollback Completed Successfully ===" "$GREEN"
            send_notification "Rollback completed successfully. System is stable."
        else
            log "=== Rollback Completed with Warnings ===" "$YELLOW"
            send_notification "Rollback completed but verification failed. Manual check required!" "warning"
        fi
    else
        log "=== CRITICAL: Rollback Failed ===" "$RED"
        send_notification "CRITICAL: Rollback failed! Manual intervention required!" "error"
        
        # Last resort: scale up both blue and green
        log "Attempting to scale up all deployments..." "$RED"
        kubectl scale deployment luckygas-frontend-blue --replicas=3
        kubectl scale deployment luckygas-backend-blue --replicas=3
        kubectl scale deployment luckygas-frontend-green --replicas=3
        kubectl scale deployment luckygas-backend-green --replicas=3
        
        exit 1
    fi
    
    generate_rollback_report
    
    # Check rollback time
    local end_time=$(date +%s)
    local duration=$((end_time - START_TIME))
    
    if [ $duration -le $MAX_ROLLBACK_TIME ]; then
        log "Rollback completed in ${duration} seconds (under 2 minute target) ✓" "$GREEN"
    else
        log "Rollback took ${duration} seconds (exceeded 2 minute target)" "$YELLOW"
    fi
}

# Validate deployment ID
if [ -z "$DEPLOYMENT_ID" ]; then
    log "Error: Deployment ID required!" "$RED"
    echo "Usage: $0 <deployment_id>"
    exit 1
fi

# Execute main function
main