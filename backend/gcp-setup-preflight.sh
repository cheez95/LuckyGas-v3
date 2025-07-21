#!/bin/bash
# GCP Setup Pre-flight Validation Script
# This script validates all prerequisites before executing GCP setup

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
PROJECT_ID="vast-tributary-466619-m8"
PROJECT_NAME="Lucky Gas Prod"
BILLING_ACCOUNT="011479-B04C2D-B0F925"
REGION="asia-east1"
LOG_FILE="gcp-setup-preflight.log"

# Initialize log
echo "GCP Setup Pre-flight Check - $(date)" | tee $LOG_FILE

# Function to print colored output
print_status() {
    local status=$1
    local message=$2
    
    case $status in
        "success")
            echo -e "${GREEN}✓${NC} $message" | tee -a $LOG_FILE
            ;;
        "error")
            echo -e "${RED}✗${NC} $message" | tee -a $LOG_FILE
            ;;
        "warning")
            echo -e "${YELLOW}⚠${NC} $message" | tee -a $LOG_FILE
            ;;
        "info")
            echo -e "${BLUE}ℹ${NC} $message" | tee -a $LOG_FILE
            ;;
    esac
}

# Function to check command exists
check_command() {
    local cmd=$1
    if command -v $cmd &> /dev/null; then
        print_status "success" "$cmd is installed"
        return 0
    else
        print_status "error" "$cmd is not installed"
        return 1
    fi
}

# Function to validate gcloud authentication
check_gcloud_auth() {
    print_status "info" "Checking gcloud authentication..."
    
    if gcloud auth list --filter=status:ACTIVE --format="value(account)" | grep -q .; then
        local account=$(gcloud auth list --filter=status:ACTIVE --format="value(account)")
        print_status "success" "Authenticated as: $account"
        return 0
    else
        print_status "error" "Not authenticated with gcloud"
        return 1
    fi
}

# Function to check if project exists
check_project_exists() {
    print_status "info" "Checking if project $PROJECT_ID exists..."
    
    if gcloud projects describe $PROJECT_ID &> /dev/null; then
        print_status "warning" "Project $PROJECT_ID already exists"
        
        # Check if we have access
        if gcloud projects get-iam-policy $PROJECT_ID &> /dev/null; then
            print_status "success" "Have access to project $PROJECT_ID"
            return 0
        else
            print_status "error" "No access to project $PROJECT_ID"
            return 1
        fi
    else
        print_status "info" "Project $PROJECT_ID does not exist (will be created)"
        return 0
    fi
}

# Function to validate billing account
check_billing_account() {
    print_status "info" "Checking billing account $BILLING_ACCOUNT..."
    
    if gcloud beta billing accounts describe $BILLING_ACCOUNT &> /dev/null; then
        print_status "success" "Billing account $BILLING_ACCOUNT is valid"
        
        # Check if account is open
        local is_open=$(gcloud beta billing accounts describe $BILLING_ACCOUNT --format="value(open)")
        if [ "$is_open" = "True" ]; then
            print_status "success" "Billing account is open and active"
            return 0
        else
            print_status "error" "Billing account is closed"
            return 1
        fi
    else
        print_status "error" "Cannot access billing account $BILLING_ACCOUNT"
        return 1
    fi
}

# Function to check user permissions
check_permissions() {
    print_status "info" "Checking user permissions..."
    
    local account=$(gcloud auth list --filter=status:ACTIVE --format="value(account)")
    
    # Check organization permissions if needed
    local org_id=$(gcloud organizations list --format="value(name)" 2>/dev/null | head -1)
    
    if [ -n "$org_id" ]; then
        print_status "info" "Organization found: $org_id"
        
        # Check if user can create projects
        if gcloud organizations get-iam-policy $org_id --flatten="bindings[].members" \
           --filter="bindings.members:user:$account" \
           --format="value(bindings.role)" | grep -q "roles/resourcemanager.projectCreator"; then
            print_status "success" "User has project creation permissions"
        else
            print_status "warning" "User may not have project creation permissions"
        fi
    else
        print_status "info" "No organization found (using personal account)"
    fi
    
    return 0
}

# Function to check API quotas
check_api_quotas() {
    print_status "info" "Checking API quotas and limits..."
    
    # This is informational only
    print_status "info" "Routes API quota will need manual configuration"
    print_status "info" "Vertex AI quotas are managed automatically"
    
    return 0
}

# Function to check for existing resources
check_existing_resources() {
    print_status "info" "Checking for existing resources..."
    
    # Check if current project is set
    local current_project=$(gcloud config get-value project 2>/dev/null)
    if [ "$current_project" = "$PROJECT_ID" ]; then
        print_status "info" "Current project is already set to $PROJECT_ID"
        
        # Check for existing service accounts
        if gcloud iam service-accounts list --filter="email:lucky-gas-prod@${PROJECT_ID}.iam.gserviceaccount.com" --format="value(email)" | grep -q .; then
            print_status "warning" "Service account lucky-gas-prod already exists"
        fi
        
        # Check for existing buckets
        if gsutil ls -p $PROJECT_ID 2>/dev/null | grep -q "gs://lucky-gas-storage"; then
            print_status "warning" "Storage bucket lucky-gas-storage already exists"
        fi
    fi
    
    return 0
}

# Function to estimate costs
estimate_costs() {
    print_status "info" "Estimated monthly costs for Lucky Gas production:"
    echo "  - Cloud Run: ~\$50-100 (based on traffic)" | tee -a $LOG_FILE
    echo "  - Cloud SQL: ~\$100-200 (db-f1-micro to db-n1-standard-1)" | tee -a $LOG_FILE
    echo "  - Cloud Storage: ~\$20-50 (based on usage)" | tee -a $LOG_FILE
    echo "  - Routes API: ~\$50-100 (based on requests)" | tee -a $LOG_FILE
    echo "  - Vertex AI: ~\$50-150 (based on predictions)" | tee -a $LOG_FILE
    echo "  - Total estimate: ~\$270-600/month" | tee -a $LOG_FILE
    
    return 0
}

# Main execution
main() {
    echo -e "${BLUE}=== GCP Setup Pre-flight Validation ===${NC}\n"
    
    local errors=0
    
    # Check prerequisites
    print_status "info" "Checking prerequisites..."
    
    check_command "gcloud" || ((errors++))
    check_command "gsutil" || ((errors++))
    check_command "curl" || ((errors++))
    check_command "jq" || ((errors++))
    
    echo ""
    
    # Check authentication
    check_gcloud_auth || ((errors++))
    
    echo ""
    
    # Check project
    check_project_exists || ((errors++))
    
    echo ""
    
    # Check billing
    check_billing_account || ((errors++))
    
    echo ""
    
    # Check permissions
    check_permissions || ((errors++))
    
    echo ""
    
    # Check existing resources
    check_existing_resources
    
    echo ""
    
    # Check quotas
    check_api_quotas
    
    echo ""
    
    # Estimate costs
    estimate_costs
    
    echo -e "\n${BLUE}=== Pre-flight Check Summary ===${NC}\n"
    
    if [ $errors -eq 0 ]; then
        print_status "success" "All pre-flight checks passed!"
        print_status "info" "Ready to proceed with GCP setup"
        
        echo -e "\n${YELLOW}Next steps:${NC}"
        echo "1. Review any warnings above"
        echo "2. Run ./gcp-setup-execute.sh to begin setup"
        echo "3. Monitor progress in gcp-setup-execution.log"
        
        exit 0
    else
        print_status "error" "Pre-flight checks failed with $errors errors"
        print_status "warning" "Please fix the issues above before proceeding"
        
        echo -e "\n${YELLOW}Common fixes:${NC}"
        echo "- Install gcloud: https://cloud.google.com/sdk/docs/install"
        echo "- Authenticate: gcloud auth login"
        echo "- Set project: gcloud config set project PROJECT_ID"
        echo "- Enable billing: https://console.cloud.google.com/billing"
        
        exit 1
    fi
}

# Run main function
main "$@"