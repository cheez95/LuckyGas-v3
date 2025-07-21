#!/bin/bash
# GCP Setup Rollback Script
# This script safely rolls back GCP setup changes

set -euo pipefail

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Configuration
PROJECT_ID="vast-tributary-466619-m8"
SERVICE_ACCOUNT_EMAIL="lucky-gas-prod@${PROJECT_ID}.iam.gserviceaccount.com"
REGION="asia-east1"

# Paths
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LOG_DIR="$SCRIPT_DIR/logs"
ROLLBACK_LOG="$LOG_DIR/gcp-setup-rollback.log"
BACKUP_DIR="$LOG_DIR/rollback-backups"

# Create directories
mkdir -p "$LOG_DIR" "$BACKUP_DIR"

# Initialize logging
exec 1> >(tee -a "$ROLLBACK_LOG")
exec 2>&1

echo "GCP Setup Rollback Started at $(date)"
echo "============================================="

# Function to print colored output
print_status() {
    local status=$1
    local message=$2
    local timestamp=$(date '+%Y-%m-%d %H:%M:%S')
    
    case $status in
        "success")
            echo -e "[$timestamp] ${GREEN}✓${NC} $message"
            ;;
        "error")
            echo -e "[$timestamp] ${RED}✗${NC} $message"
            ;;
        "warning")
            echo -e "[$timestamp] ${YELLOW}⚠${NC} $message"
            ;;
        "info")
            echo -e "[$timestamp] ${BLUE}ℹ${NC} $message"
            ;;
    esac
}

# Function to confirm action
confirm_action() {
    local message=$1
    local default=${2:-n}
    
    echo -e "${YELLOW}$message${NC}"
    
    if [ "$default" = "y" ]; then
        read -p "Continue? (Y/n) " -n 1 -r
    else
        read -p "Continue? (y/N) " -n 1 -r
    fi
    echo
    
    if [ "$default" = "y" ]; then
        [[ ! $REPLY =~ ^[Nn]$ ]]
    else
        [[ $REPLY =~ ^[Yy]$ ]]
    fi
}

# Function to backup current state
backup_current_state() {
    print_status "info" "Backing up current state..."
    
    local backup_file="$BACKUP_DIR/gcp-state-$(date +%Y%m%d-%H%M%S).json"
    
    {
        echo "{"
        echo "  \"timestamp\": \"$(date -u +%Y-%m-%dT%H:%M:%SZ)\","
        echo "  \"project_id\": \"$PROJECT_ID\","
        echo "  \"service_accounts\": ["
        gcloud iam service-accounts list --format=json 2>/dev/null || echo "[]"
        echo "  ],"
        echo "  \"enabled_apis\": ["
        gcloud services list --enabled --format=json 2>/dev/null || echo "[]"
        echo "  ],"
        echo "  \"storage_buckets\": ["
        gsutil ls -p $PROJECT_ID 2>/dev/null | jq -R . | jq -s . || echo "[]"
        echo "  ]"
        echo "}"
    } > "$backup_file"
    
    print_status "success" "State backed up to: $backup_file"
}

# Function to rollback security configuration
rollback_security() {
    print_status "warning" "Rolling back security configuration..."
    
    # Remove security policy
    if gcloud compute security-policies describe lucky-gas-prod-policy &> /dev/null; then
        if confirm_action "Delete security policy 'lucky-gas-prod-policy'?"; then
            gcloud compute security-policies delete lucky-gas-prod-policy --quiet
            print_status "success" "Security policy deleted"
        fi
    fi
    
    # Remove log sink
    if gcloud logging sinks describe security-events &> /dev/null; then
        if confirm_action "Delete log sink 'security-events'?"; then
            gcloud logging sinks delete security-events --quiet
            print_status "success" "Log sink deleted"
        fi
    fi
    
    # Remove security logs bucket
    if gsutil ls -b gs://lucky-gas-security-logs &> /dev/null; then
        if confirm_action "Delete security logs bucket 'gs://lucky-gas-security-logs'?"; then
            gsutil -m rm -r gs://lucky-gas-security-logs
            print_status "success" "Security logs bucket deleted"
        fi
    fi
}

# Function to rollback storage configuration
rollback_storage() {
    print_status "warning" "Rolling back storage configuration..."
    
    # Check if bucket exists
    if gsutil ls -b gs://lucky-gas-storage &> /dev/null; then
        # Check if bucket has data
        local object_count=$(gsutil ls -r gs://lucky-gas-storage/** 2>/dev/null | wc -l || echo "0")
        
        if [ "$object_count" -gt 0 ]; then
            print_status "warning" "Bucket contains $object_count objects"
            
            if confirm_action "Backup bucket contents before deletion?"; then
                local backup_path="$BACKUP_DIR/lucky-gas-storage-backup-$(date +%Y%m%d-%H%M%S)"
                mkdir -p "$backup_path"
                
                print_status "info" "Backing up bucket contents to: $backup_path"
                gsutil -m cp -r gs://lucky-gas-storage/* "$backup_path/" || true
            fi
        fi
        
        if confirm_action "Delete storage bucket 'gs://lucky-gas-storage' and all contents?" "n"; then
            gsutil -m rm -r gs://lucky-gas-storage
            print_status "success" "Storage bucket deleted"
        fi
    fi
}

# Function to rollback API services
rollback_apis() {
    print_status "warning" "Rolling back API services..."
    
    # List of APIs that were enabled (excluding core APIs)
    local apis_to_disable=(
        "routes.googleapis.com"
        "aiplatform.googleapis.com"
        "storage-component.googleapis.com"
        "secretmanager.googleapis.com"
        "securitycenter.googleapis.com"
    )
    
    print_status "info" "The following APIs will be disabled:"
    printf '%s\n' "${apis_to_disable[@]}"
    
    if confirm_action "Disable these APIs?"; then
        for api in "${apis_to_disable[@]}"; do
            if gcloud services list --enabled --filter="name:$api" --format="value(name)" | grep -q "$api"; then
                gcloud services disable $api --force --quiet || true
                print_status "success" "Disabled $api"
            fi
        done
    fi
}

# Function to rollback service account
rollback_service_account() {
    print_status "warning" "Rolling back service account configuration..."
    
    # List service account keys
    if gcloud iam service-accounts describe $SERVICE_ACCOUNT_EMAIL &> /dev/null; then
        print_status "info" "Service account keys:"
        gcloud iam service-accounts keys list --iam-account=$SERVICE_ACCOUNT_EMAIL
        
        # Remove IAM bindings
        if confirm_action "Remove IAM policy bindings for service account?"; then
            local roles=(
                "roles/routes.viewer"
                "roles/aiplatform.user"
                "roles/storage.objectAdmin"
                "roles/secretmanager.secretAccessor"
                "roles/cloudsql.client"
            )
            
            for role in "${roles[@]}"; do
                gcloud projects remove-iam-policy-binding $PROJECT_ID \
                    --member="serviceAccount:${SERVICE_ACCOUNT_EMAIL}" \
                    --role="$role" --quiet || true
                print_status "success" "Removed binding: $role"
            done
        fi
        
        # Delete service account
        if confirm_action "Delete service account '$SERVICE_ACCOUNT_EMAIL'?" "n"; then
            gcloud iam service-accounts delete $SERVICE_ACCOUNT_EMAIL --quiet
            print_status "success" "Service account deleted"
            
            # Remove local key file
            local key_file="$HOME/.gcp/lucky-gas/lucky-gas-prod-key.json"
            if [ -f "$key_file" ]; then
                if confirm_action "Delete local service account key file?"; then
                    # Backup key first
                    cp "$key_file" "$BACKUP_DIR/lucky-gas-prod-key-backup-$(date +%Y%m%d-%H%M%S).json"
                    rm -f "$key_file"
                    print_status "success" "Local key file deleted (backup saved)"
                fi
            fi
        fi
    fi
}

# Function to rollback project (extreme action)
rollback_project() {
    print_status "error" "PROJECT DELETION - THIS CANNOT BE UNDONE!"
    
    echo -e "${RED}WARNING: This will delete the entire project and ALL resources within it.${NC}"
    echo -e "${RED}This action is PERMANENT and CANNOT be reversed.${NC}"
    
    if confirm_action "Are you ABSOLUTELY SURE you want to delete project '$PROJECT_ID'?" "n"; then
        echo -e "${RED}Type the project ID to confirm deletion: ${NC}"
        read -r confirmation
        
        if [ "$confirmation" = "$PROJECT_ID" ]; then
            gcloud projects delete $PROJECT_ID --quiet
            print_status "success" "Project deletion initiated"
            print_status "warning" "Project will be deleted after 30-day grace period"
        else
            print_status "info" "Project deletion cancelled - confirmation did not match"
        fi
    fi
}

# Function to generate rollback report
generate_rollback_report() {
    local report_file="$LOG_DIR/rollback-report-$(date +%Y%m%d-%H%M%S).md"
    
    cat > "$report_file" << EOF
# GCP Rollback Report

**Generated**: $(date)
**Project ID**: $PROJECT_ID

## Rollback Actions Performed

$(grep "✓" "$ROLLBACK_LOG" | tail -20)

## Remaining Resources

### Service Accounts
$(gcloud iam service-accounts list --format="table(email,disabled)" 2>/dev/null || echo "None")

### Enabled APIs
$(gcloud services list --enabled --format="table(config.name)" 2>/dev/null || echo "None")

### Storage Buckets
$(gsutil ls -p $PROJECT_ID 2>/dev/null || echo "None")

## Backups Created

$(ls -la "$BACKUP_DIR" 2>/dev/null || echo "None")

## Recommendations

1. Review remaining resources above
2. Check billing to ensure no unexpected charges
3. Verify application is updated to remove GCP dependencies
4. Archive backup files for future reference

EOF
    
    print_status "success" "Rollback report generated: $report_file"
    cat "$report_file"
}

# Main menu
show_menu() {
    echo -e "\n${BLUE}=== GCP Setup Rollback Menu ===${NC}\n"
    echo "1. Backup current state"
    echo "2. Rollback security configuration"
    echo "3. Rollback storage configuration"
    echo "4. Rollback API services"
    echo "5. Rollback service account"
    echo "6. Rollback EVERYTHING (except project)"
    echo "7. Delete entire project (DANGEROUS!)"
    echo "8. Generate rollback report"
    echo "9. Exit"
    echo
    read -p "Select an option (1-9): " choice
    
    case $choice in
        1) backup_current_state ;;
        2) rollback_security ;;
        3) rollback_storage ;;
        4) rollback_apis ;;
        5) rollback_service_account ;;
        6) 
            if confirm_action "Rollback ALL configurations (except project)?"; then
                backup_current_state
                rollback_security
                rollback_storage
                rollback_apis
                rollback_service_account
            fi
            ;;
        7) rollback_project ;;
        8) generate_rollback_report ;;
        9) 
            print_status "info" "Exiting rollback script"
            exit 0
            ;;
        *)
            print_status "error" "Invalid option"
            ;;
    esac
}

# Main execution
main() {
    print_status "warning" "GCP Setup Rollback Script"
    print_status "warning" "This script will help you rollback GCP setup changes"
    
    # Verify project
    if ! gcloud projects describe $PROJECT_ID &> /dev/null; then
        print_status "error" "Project $PROJECT_ID not found"
        exit 1
    fi
    
    # Set current project
    gcloud config set project $PROJECT_ID
    
    while true; do
        show_menu
    done
}

# Run main function
main "$@"