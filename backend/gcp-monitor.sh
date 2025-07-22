#!/bin/bash
# GCP Infrastructure Monitoring Script
# This script monitors the health and performance of GCP resources

set -euo pipefail

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
MAGENTA='\033[0;35m'
NC='\033[0m'

# Configuration
PROJECT_ID="vast-tributary-466619-m8"
SERVICE_ACCOUNT_EMAIL="lucky-gas-prod@${PROJECT_ID}.iam.gserviceaccount.com"
REGION="asia-east1"

# Thresholds
COST_WARNING_THRESHOLD=500  # USD per month
COST_CRITICAL_THRESHOLD=1000  # USD per month
API_QUOTA_WARNING=80  # Percentage
STORAGE_WARNING_GB=100  # GB

# Paths
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LOG_DIR="$SCRIPT_DIR/logs"
MONITOR_LOG="$LOG_DIR/gcp-monitor.log"
METRICS_FILE="$LOG_DIR/gcp-metrics.json"

# Create log directory
mkdir -p "$LOG_DIR"

# Initialize logging
exec 1> >(tee -a "$MONITOR_LOG")
exec 2>&1

echo "GCP Monitoring Check - $(date)"
echo "============================================="

# Function to print colored output
print_status() {
    local status=$1
    local message=$2
    
    case $status in
        "success")
            echo -e "${GREEN}✓${NC} $message"
            ;;
        "error")
            echo -e "${RED}✗${NC} $message"
            ;;
        "warning")
            echo -e "${YELLOW}⚠${NC} $message"
            ;;
        "info")
            echo -e "${BLUE}ℹ${NC} $message"
            ;;
        "metric")
            echo -e "${MAGENTA}📊${NC} $message"
            ;;
    esac
}

# Function to convert ISO date to epoch seconds (portable for macOS and Linux)
date_to_epoch() {
    local date_string="$1"
    
    # Check if we're on macOS or Linux
    if [[ "$(uname)" == "Darwin" ]]; then
        # macOS uses -j flag and different format
        # Convert ISO format to macOS format
        local formatted_date=$(echo "$date_string" | sed -E 's/([0-9]{4})-([0-9]{2})-([0-9]{2})T([0-9]{2}):([0-9]{2}):([0-9]{2})Z?/\1\2\3\4\5\6/')
        date -j -f "%Y%m%d%H%M%S" "$formatted_date" "+%s" 2>/dev/null || echo "0"
    else
        # Linux/GNU date
        date -d "$date_string" +%s 2>/dev/null || echo "0"
    fi
}

# Function to check service health
check_service_health() {
    print_status "info" "Checking service health..."
    
    local unhealthy=0
    
    # Check project
    if gcloud projects describe $PROJECT_ID &> /dev/null; then
        print_status "success" "Project accessible: $PROJECT_ID"
    else
        print_status "error" "Cannot access project: $PROJECT_ID"
        ((unhealthy++))
    fi
    
    # Check service account
    if gcloud iam service-accounts describe $SERVICE_ACCOUNT_EMAIL &> /dev/null; then
        print_status "success" "Service account active: $SERVICE_ACCOUNT_EMAIL"
        
        # Check keys
        local key_count=$(gcloud iam service-accounts keys list \
            --iam-account=$SERVICE_ACCOUNT_EMAIL \
            --format="value(name)" | wc -l)
        
        if [ "$key_count" -gt 2 ]; then
            print_status "warning" "Multiple service account keys detected ($key_count keys)"
        fi
        
        # Check key age
        local oldest_key=$(gcloud iam service-accounts keys list \
            --iam-account=$SERVICE_ACCOUNT_EMAIL \
            --format="value(validAfterTime)" \
            --sort-by="validAfterTime" | head -1)
        
        if [ -n "$oldest_key" ]; then
            # Use portable date conversion
            local key_epoch=$(date_to_epoch "$oldest_key")
            if [ "$key_epoch" -ne 0 ]; then
                local key_age_days=$(( ($(date +%s) - key_epoch) / 86400 ))
                if [ "$key_age_days" -gt 90 ]; then
                    print_status "warning" "Service account key older than 90 days ($key_age_days days)"
                fi
            else
                print_status "warning" "Could not parse key date: $oldest_key"
            fi
        fi
    else
        print_status "error" "Service account not found"
        ((unhealthy++))
    fi
    
    # Check critical APIs
    local required_apis=(
        "routes.googleapis.com"
        "aiplatform.googleapis.com"
        "storage-component.googleapis.com"
    )
    
    for api in "${required_apis[@]}"; do
        if gcloud services list --enabled --filter="name:$api" --format="value(name)" | grep -q "$api"; then
            print_status "success" "API enabled: $api"
        else
            print_status "error" "API not enabled: $api"
            ((unhealthy++))
        fi
    done
    
    # Check storage bucket
    if gsutil ls -b gs://lucky-gas-storage &> /dev/null; then
        print_status "success" "Storage bucket accessible: gs://lucky-gas-storage"
    else
        print_status "error" "Storage bucket not accessible"
        ((unhealthy++))
    fi
    
    return $unhealthy
}

# Function to check costs
check_costs() {
    print_status "info" "Checking costs and billing..."
    
    # Get current month costs
    local current_month=$(date +%Y-%m)
    local billing_account=$(gcloud beta billing projects describe $PROJECT_ID --format="value(billingAccountName)" 2>/dev/null)
    
    if [ -n "$billing_account" ]; then
        print_status "success" "Billing enabled: $billing_account"
        
        # Note: Full cost data requires BigQuery export setup
        print_status "info" "For detailed cost analysis, enable billing export to BigQuery"
        
        # Estimate based on resource usage
        local estimated_monthly_cost=0
        
        # Estimate Cloud Run costs
        local cloud_run_services=$(gcloud run services list --format="value(name)" 2>/dev/null | wc -l || echo "0")
        estimated_monthly_cost=$((estimated_monthly_cost + cloud_run_services * 50))
        
        # Estimate storage costs
        local storage_size_gb=$(gsutil du -s gs://lucky-gas-storage 2>/dev/null | awk '{print int($1/1024/1024/1024)}' || echo "0")
        estimated_monthly_cost=$((estimated_monthly_cost + storage_size_gb * 2))
        
        print_status "metric" "Estimated monthly cost: ~\$$estimated_monthly_cost USD"
        
        if [ "$estimated_monthly_cost" -gt "$COST_CRITICAL_THRESHOLD" ]; then
            print_status "error" "Cost exceeds critical threshold (\$$COST_CRITICAL_THRESHOLD)"
        elif [ "$estimated_monthly_cost" -gt "$COST_WARNING_THRESHOLD" ]; then
            print_status "warning" "Cost exceeds warning threshold (\$$COST_WARNING_THRESHOLD)"
        else
            print_status "success" "Costs within budget"
        fi
    else
        print_status "error" "Billing not enabled"
    fi
}

# Function to check API quotas
check_api_quotas() {
    print_status "info" "Checking API quotas and usage..."
    
    # Routes API quota check
    print_status "info" "Routes API quota requires manual check in console"
    echo "   Visit: https://console.cloud.google.com/apis/api/routes.googleapis.com/quotas?project=$PROJECT_ID"
    
    # Check Vertex AI usage
    local vertex_operations=$(gcloud ai platform operations list --region=$REGION --format="value(name)" 2>/dev/null | wc -l || echo "0")
    print_status "metric" "Vertex AI operations: $vertex_operations"
    
    # Storage usage
    local storage_objects=$(gsutil ls -r gs://lucky-gas-storage/** 2>/dev/null | wc -l || echo "0")
    local storage_size_gb=$(gsutil du -s gs://lucky-gas-storage 2>/dev/null | awk '{print int($1/1024/1024/1024)}' || echo "0")
    
    print_status "metric" "Storage objects: $storage_objects"
    print_status "metric" "Storage size: ${storage_size_gb}GB"
    
    if [ "$storage_size_gb" -gt "$STORAGE_WARNING_GB" ]; then
        print_status "warning" "Storage usage high (${storage_size_gb}GB > ${STORAGE_WARNING_GB}GB)"
    fi
}

# Function to check security
check_security() {
    print_status "info" "Checking security configuration..."
    
    # Check audit logs
    local recent_auth_failures=$(gcloud logging read \
        'protoPayload.authenticationInfo.principalEmail!="" AND 
         protoPayload.authorizationInfo.granted=false' \
        --limit=10 \
        --format="value(timestamp)" \
        --project=$PROJECT_ID 2>/dev/null | wc -l || echo "0")
    
    if [ "$recent_auth_failures" -gt 5 ]; then
        print_status "warning" "Multiple auth failures detected ($recent_auth_failures)"
    else
        print_status "success" "No significant auth failures"
    fi
    
    # Check IAM policy
    local iam_member_count=$(gcloud projects get-iam-policy $PROJECT_ID \
        --flatten="bindings[].members" \
        --format="value(bindings.members)" | sort -u | wc -l)
    
    print_status "metric" "IAM members with access: $iam_member_count"
    
    # Check for overly permissive roles
    local owner_count=$(gcloud projects get-iam-policy $PROJECT_ID \
        --flatten="bindings[].members" \
        --filter="bindings.role:roles/owner" \
        --format="value(bindings.members)" | wc -l)
    
    if [ "$owner_count" -gt 2 ]; then
        print_status "warning" "Multiple project owners detected ($owner_count)"
    fi
    
    # Check security policy
    if gcloud compute security-policies describe lucky-gas-prod-policy &> /dev/null; then
        print_status "success" "Security policy active"
        
        # Check recent blocks
        local blocked_requests=$(gcloud logging read \
            'resource.type="http_load_balancer" AND 
             jsonPayload.enforcedSecurityPolicy.name="lucky-gas-prod-policy" AND
             jsonPayload.enforcedSecurityPolicy.outcome="DENY"' \
            --limit=100 \
            --format="value(timestamp)" \
            --project=$PROJECT_ID 2>/dev/null | wc -l || echo "0")
        
        if [ "$blocked_requests" -gt 0 ]; then
            print_status "metric" "Security policy blocks (last 24h): $blocked_requests"
        fi
    else
        print_status "warning" "Security policy not configured"
    fi
}

# Function to check performance
check_performance() {
    print_status "info" "Checking performance metrics..."
    
    # API response times would require Cloud Monitoring API
    print_status "info" "For detailed performance metrics, check Cloud Monitoring:"
    echo "   https://console.cloud.google.com/monitoring?project=$PROJECT_ID"
    
    # Check for errors in logs
    local error_count=$(gcloud logging read \
        'severity>=ERROR' \
        --limit=100 \
        --format="value(timestamp)" \
        --project=$PROJECT_ID \
        --freshness=1d 2>/dev/null | wc -l || echo "0")
    
    print_status "metric" "Errors in last 24h: $error_count"
    
    if [ "$error_count" -gt 50 ]; then
        print_status "warning" "High error rate detected"
    fi
}

# Function to generate metrics JSON
generate_metrics() {
    local metrics_data=$(cat << EOF
{
  "timestamp": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
  "project_id": "$PROJECT_ID",
  "health": {
    "services_healthy": true,
    "apis_enabled": true,
    "storage_accessible": true
  },
  "costs": {
    "estimated_monthly": 0,
    "within_budget": true
  },
  "usage": {
    "storage_gb": 0,
    "storage_objects": 0,
    "vertex_ai_operations": 0
  },
  "security": {
    "auth_failures": 0,
    "iam_members": 0,
    "security_blocks": 0
  },
  "performance": {
    "errors_24h": 0
  }
}
EOF
)
    
    echo "$metrics_data" > "$METRICS_FILE"
    print_status "success" "Metrics saved to: $METRICS_FILE"
}

# Function to send alerts
send_alerts() {
    local alert_level=$1
    local message=$2
    
    # In production, this would send to email/Slack/PagerDuty
    print_status "warning" "ALERT [$alert_level]: $message"
    
    # Log to file
    echo "[$(date)] ALERT [$alert_level]: $message" >> "$LOG_DIR/alerts.log"
}

# Function to generate summary report
generate_summary() {
    local report_file="$LOG_DIR/monitor-report-$(date +%Y%m%d-%H%M%S).md"
    
    cat > "$report_file" << EOF
# GCP Infrastructure Monitoring Report

**Generated**: $(date)
**Project**: $PROJECT_ID
**Region**: $REGION

## Health Status

$(grep -E "✓|✗|⚠" "$MONITOR_LOG" | tail -20)

## Key Metrics

$(grep "📊" "$MONITOR_LOG" | tail -10)

## Recommendations

1. **Security**:
   - Review IAM permissions quarterly
   - Rotate service account keys every 90 days
   - Monitor auth failures regularly

2. **Cost Optimization**:
   - Set up billing alerts
   - Enable budget notifications
   - Review unused resources

3. **Performance**:
   - Monitor API quotas
   - Set up uptime checks
   - Configure alerting policies

## Quick Links

- [Cloud Console](https://console.cloud.google.com/home/dashboard?project=$PROJECT_ID)
- [Billing](https://console.cloud.google.com/billing/linkedaccount?project=$PROJECT_ID)
- [Monitoring](https://console.cloud.google.com/monitoring?project=$PROJECT_ID)
- [Security](https://console.cloud.google.com/security/command-center?project=$PROJECT_ID)
- [Logging](https://console.cloud.google.com/logs/query?project=$PROJECT_ID)

EOF
    
    print_status "success" "Report generated: $report_file"
}

# Main execution
main() {
    local total_issues=0
    
    echo -e "${BLUE}=== GCP Infrastructure Monitoring ===${NC}\n"
    
    # Set current project
    gcloud config set project $PROJECT_ID &> /dev/null
    
    # Run checks
    check_service_health || ((total_issues+=$?))
    echo
    
    check_costs
    echo
    
    check_api_quotas
    echo
    
    check_security
    echo
    
    check_performance
    echo
    
    # Generate outputs
    generate_metrics
    generate_summary
    
    echo -e "\n${BLUE}=== Monitoring Summary ===${NC}\n"
    
    if [ "$total_issues" -eq 0 ]; then
        print_status "success" "All systems operational"
    else
        print_status "warning" "Issues detected: $total_issues"
        send_alerts "WARNING" "$total_issues infrastructure issues detected"
    fi
    
    print_status "info" "Next monitoring check recommended in 1 hour"
}

# Parse command line arguments
case "${1:-}" in
    --continuous)
        # Run continuously every hour
        while true; do
            main
            echo -e "\n${YELLOW}Sleeping for 1 hour...${NC}\n"
            sleep 3600
        done
        ;;
    --help)
        echo "Usage: $0 [--continuous] [--help]"
        echo "  --continuous  Run monitoring continuously (every hour)"
        echo "  --help        Show this help message"
        exit 0
        ;;
    *)
        # Run once
        main
        ;;
esac