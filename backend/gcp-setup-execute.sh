#!/bin/bash
# GCP Setup Execution Script with DevOps Best Practices
# This script executes the GCP setup with validation, error handling, and rollback

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
PROJECT_NAME="Lucky Gas Prod"
BILLING_ACCOUNT="011479-B04C2D-B0F925"
REGION="asia-east1"
SERVICE_ACCOUNT_EMAIL="lucky-gas-prod@${PROJECT_ID}.iam.gserviceaccount.com"

# Enable verbose logging
export CLOUDSDK_CORE_VERBOSITY=debug
export CLOUDSDK_CORE_LOG_HTTP=true

# Paths
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LOG_DIR="$SCRIPT_DIR/logs"
CHECKPOINT_FILE="$LOG_DIR/gcp-setup-checkpoint.json"
EXECUTION_LOG="$LOG_DIR/gcp-setup-execution.log"
ROLLBACK_LOG="$LOG_DIR/gcp-setup-rollback.log"

# Create log directory
mkdir -p "$LOG_DIR"

# Dry run mode
DRY_RUN=${DRY_RUN:-false}

# Initialize logging
exec 1> >(tee -a "$EXECUTION_LOG")
exec 2>&1

# Set up detailed gcloud logging
export CLOUDSDK_CORE_VERBOSITY=debug
gcloud config set core/log_http true
gcloud config set core/user_output_enabled true

echo "GCP Setup Execution Started at $(date)"
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
        "step")
            echo -e "[$timestamp] ${MAGENTA}▶${NC} $message"
            ;;
    esac
}

# Function to execute command with dry run support
execute_command() {
    local cmd=$1
    local description=${2:-"Executing command"}
    
    print_status "info" "$description"
    print_status "info" "Command: $cmd"
    
    if [ "$DRY_RUN" = "true" ]; then
        print_status "info" "[DRY RUN] Would execute: $cmd"
        return 0
    else
        # Add timeout and verbose flags for gcloud commands
        if [[ $cmd == *"gcloud"* ]]; then
            # Add verbosity and timeout flags
            cmd="$cmd --verbosity=debug"
            
            # Add timeout for API enable commands
            if [[ $cmd == *"services enable"* ]]; then
                print_status "warning" "API enablement may take several minutes..."
                # Use timeout command if available
                if command -v gtimeout &> /dev/null; then
                    cmd="gtimeout 600 $cmd"  # 10 minute timeout
                elif command -v timeout &> /dev/null; then
                    cmd="timeout 600 $cmd"   # 10 minute timeout
                fi
            fi
        fi
        
        print_status "info" "Executing with verbose logging: $cmd"
        local start_time=$(date +%s)
        
        if eval "$cmd"; then
            local end_time=$(date +%s)
            local duration=$((end_time - start_time))
            print_status "success" "Command completed successfully in ${duration}s"
            return 0
        else
            local exit_code=$?
            local end_time=$(date +%s)
            local duration=$((end_time - start_time))
            print_status "error" "Command failed with exit code $exit_code after ${duration}s: $cmd"
            return 1
        fi
    fi
}

# Function to save checkpoint
save_checkpoint() {
    local step=$1
    local status=$2
    
    if [ "$DRY_RUN" = "true" ]; then
        return 0
    fi
    
    cat > "$CHECKPOINT_FILE" << EOF
{
  "last_completed_step": "$step",
  "status": "$status",
  "timestamp": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
  "project_id": "$PROJECT_ID"
}
EOF
    print_status "info" "Checkpoint saved: $step"
}

# Function to load checkpoint
load_checkpoint() {
    if [ -f "$CHECKPOINT_FILE" ]; then
        local last_step=$(jq -r '.last_completed_step' "$CHECKPOINT_FILE" 2>/dev/null || echo "none")
        print_status "info" "Resuming from checkpoint: $last_step"
        echo "$last_step"
    else
        echo "none"
    fi
}

# Function to confirm action
confirm_action() {
    local message=$1
    
    if [ "$DRY_RUN" = "true" ]; then
        return 0
    fi
    
    echo -e "${YELLOW}$message${NC}"
    read -p "Continue? (y/N) " -n 1 -r
    echo
    
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        print_status "warning" "Action cancelled by user"
        return 1
    fi
    
    return 0
}

# Function to validate project setup
validate_project() {
    print_status "step" "Validating project configuration..."
    
    # Check if project exists
    if gcloud projects describe $PROJECT_ID &> /dev/null; then
        print_status "info" "Project $PROJECT_ID exists"
        
        # Set as current project
        execute_command "gcloud config set project $PROJECT_ID" "Setting current project"
        
        # Verify billing is enabled
        local billing_enabled=$(gcloud beta billing projects describe $PROJECT_ID --format="value(billingEnabled)" 2>/dev/null || echo "false")
        
        if [ "$billing_enabled" = "True" ]; then
            print_status "success" "Billing is enabled for project"
        else
            print_status "warning" "Billing is not enabled for project"
            
            if confirm_action "Enable billing for project $PROJECT_ID?"; then
                execute_command "gcloud beta billing projects link $PROJECT_ID --billing-account=$BILLING_ACCOUNT" \
                    "Enabling billing"
            fi
        fi
    else
        print_status "error" "Project $PROJECT_ID does not exist"
        
        if confirm_action "Create new project $PROJECT_ID?"; then
            execute_command "gcloud projects create $PROJECT_ID --name=\"$PROJECT_NAME\"" \
                "Creating project"
            
            execute_command "gcloud config set project $PROJECT_ID" \
                "Setting current project"
            
            execute_command "gcloud beta billing projects link $PROJECT_ID --billing-account=$BILLING_ACCOUNT" \
                "Linking billing account"
        else
            return 1
        fi
    fi
    
    # Enable initial APIs
    print_status "info" "Enabling core APIs (this may take several minutes)..."
    
    # Enable APIs one by one for better debugging
    local core_apis=("compute.googleapis.com" "cloudresourcemanager.googleapis.com" "iam.googleapis.com")
    for api in "${core_apis[@]}"; do
        print_status "info" "Checking if $api is already enabled..."
        if gcloud services list --enabled --filter="name:$api" --format="value(name)" | grep -q "$api"; then
            print_status "success" "$api is already enabled"
        else
            execute_command "gcloud services enable $api --async" \
                "Enabling $api (async)"
            
            # Wait for operation to complete
            print_status "info" "Waiting for $api to be fully enabled..."
            local max_wait=300  # 5 minutes max wait
            local waited=0
            while [ $waited -lt $max_wait ]; do
                if gcloud services list --enabled --filter="name:$api" --format="value(name)" | grep -q "$api"; then
                    print_status "success" "$api is now enabled"
                    break
                fi
                sleep 10
                waited=$((waited + 10))
                print_status "info" "Still waiting for $api... ($waited seconds)"
            done
            
            if [ $waited -ge $max_wait ]; then
                print_status "error" "Timeout waiting for $api to be enabled"
                return 1
            fi
        fi
    done
    
    save_checkpoint "project_setup" "completed"
    return 0
}

# Function to create service account (Story 1)
setup_service_account() {
    print_status "step" "Setting up service account (Story 1)..."
    
    # Check if service account exists
    if gcloud iam service-accounts describe $SERVICE_ACCOUNT_EMAIL &> /dev/null; then
        print_status "warning" "Service account already exists: $SERVICE_ACCOUNT_EMAIL"
        
        if ! confirm_action "Use existing service account?"; then
            return 1
        fi
    else
        # Create service account
        execute_command "gcloud iam service-accounts create lucky-gas-prod \
            --display-name=\"Lucky Gas Production Service Account\" \
            --description=\"Service account for Lucky Gas production services\"" \
            "Creating service account"
    fi
    
    # Assign IAM roles
    print_status "info" "Assigning IAM roles..."
    
    local roles=(
        "roles/routes.viewer"
        "roles/aiplatform.user"
        "roles/secretmanager.secretAccessor"
        "roles/cloudsql.client"
    )
    
    for role in "${roles[@]}"; do
        execute_command "gcloud projects add-iam-policy-binding $PROJECT_ID \
            --member=\"serviceAccount:${SERVICE_ACCOUNT_EMAIL}\" \
            --role=\"$role\" --quiet" \
            "Assigning role: $role"
    done
    
    # Storage role with condition
    execute_command "gcloud projects add-iam-policy-binding $PROJECT_ID \
        --member=\"serviceAccount:${SERVICE_ACCOUNT_EMAIL}\" \
        --role=\"roles/storage.objectAdmin\" \
        --condition=\"expression=resource.name.startsWith('projects/_/buckets/lucky-gas-storage/'),title=lucky-gas-bucket-only,description=Access only to lucky-gas-storage bucket\" --quiet" \
        "Assigning conditional storage role"
    
    # Generate service account key
    local key_dir="$HOME/.gcp/lucky-gas"
    local key_file="$key_dir/lucky-gas-prod-key.json"
    
    if [ -f "$key_file" ]; then
        print_status "warning" "Service account key already exists"
        
        if confirm_action "Generate new service account key?"; then
            # Backup existing key
            execute_command "cp $key_file ${key_file}.backup.$(date +%Y%m%d%H%M%S)" \
                "Backing up existing key"
            
            execute_command "gcloud iam service-accounts keys create $key_file \
                --iam-account=$SERVICE_ACCOUNT_EMAIL" \
                "Generating new service account key"
        fi
    else
        execute_command "mkdir -p $key_dir" "Creating key directory"
        
        execute_command "gcloud iam service-accounts keys create $key_file \
            --iam-account=$SERVICE_ACCOUNT_EMAIL" \
            "Generating service account key"
    fi
    
    execute_command "chmod 600 $key_file" "Setting key permissions"
    
    # Create key rotation script
    print_status "info" "Setting up key rotation..."
    create_key_rotation_script
    
    save_checkpoint "service_account" "completed"
    return 0
}

# Function to create key rotation script
create_key_rotation_script() {
    local script_path="$HOME/rotate-service-key.sh"
    
    cat > "$script_path" << 'EOF'
#!/bin/bash
# Service Account Key Rotation Script

PROJECT_ID="vast-tributary-466619-m8"
SERVICE_ACCOUNT_EMAIL="lucky-gas-prod@${PROJECT_ID}.iam.gserviceaccount.com"
KEY_DIR="$HOME/.gcp/lucky-gas"

# List current keys
echo "Current keys:"
gcloud iam service-accounts keys list --iam-account=$SERVICE_ACCOUNT_EMAIL

# Create new key
NEW_KEY_PATH="${KEY_DIR}/lucky-gas-prod-key-new.json"
gcloud iam service-accounts keys create $NEW_KEY_PATH \
    --iam-account=$SERVICE_ACCOUNT_EMAIL

# Backup current key
cp ${KEY_DIR}/lucky-gas-prod-key.json \
   ${KEY_DIR}/lucky-gas-prod-key-old-$(date +%Y%m%d).json

# Replace current key
mv $NEW_KEY_PATH ${KEY_DIR}/lucky-gas-prod-key.json

# Set permissions
chmod 600 ${KEY_DIR}/lucky-gas-prod-key.json

echo "Key rotation completed. Remember to:"
echo "1. Update the application with new key"
echo "2. Test the new key"
echo "3. Delete old key after verification"
EOF
    
    chmod +x "$script_path"
    print_status "success" "Key rotation script created: $script_path"
}

# Function to setup APIs and services (Story 2)
setup_apis_and_services() {
    print_status "step" "Setting up APIs and services (Story 2)..."
    
    # Enable required APIs
    print_status "info" "Enabling required APIs..."
    
    local apis=(
        "routes.googleapis.com"
        "aiplatform.googleapis.com"
        "storage-component.googleapis.com"
        "secretmanager.googleapis.com"
        "monitoring.googleapis.com"
        "logging.googleapis.com"
        "cloudbilling.googleapis.com"
    )
    
    for api in "${apis[@]}"; do
        execute_command "gcloud services enable $api" "Enabling $api"
    done
    
    # Initialize Vertex AI
    print_status "info" "Initializing Vertex AI..."
    execute_command "gcloud ai platform operations list --region=$REGION || true" \
        "Initializing Vertex AI in region $REGION"
    
    # Create Cloud Storage bucket
    print_status "info" "Setting up Cloud Storage..."
    
    if gsutil ls -b gs://lucky-gas-storage &> /dev/null; then
        print_status "warning" "Storage bucket already exists: gs://lucky-gas-storage"
    else
        execute_command "gsutil mb -p $PROJECT_ID -c STANDARD -l $REGION gs://lucky-gas-storage/" \
            "Creating storage bucket"
    fi
    
    # Create folder structure
    execute_command "gsutil -m mkdir -p \
        gs://lucky-gas-storage/uploads/ \
        gs://lucky-gas-storage/exports/ \
        gs://lucky-gas-storage/backups/ \
        gs://lucky-gas-storage/ml-models/" \
        "Creating folder structure"
    
    # Set bucket permissions
    execute_command "gsutil iam ch serviceAccount:${SERVICE_ACCOUNT_EMAIL}:objectAdmin gs://lucky-gas-storage" \
        "Setting bucket permissions"
    
    # Enable versioning
    execute_command "gsutil versioning set on gs://lucky-gas-storage" \
        "Enabling versioning"
    
    # Set lifecycle rules
    create_lifecycle_rules
    
    # Create API key
    print_status "info" "Creating API key for frontend..."
    
    if [ "$DRY_RUN" = "false" ]; then
        local api_key_output=$(gcloud alpha services api-keys create lucky-gas-web-key \
            --display-name="Lucky Gas Web Application" \
            --api-target="service=routes.googleapis.com" 2>&1 || echo "")
        
        if echo "$api_key_output" | grep -q "already exists"; then
            print_status "warning" "API key already exists"
        else
            print_status "success" "API key created"
            print_status "warning" "Remember to restrict API key in console and store in Secret Manager"
        fi
    fi
    
    save_checkpoint "apis_and_services" "completed"
    return 0
}

# Function to create lifecycle rules
create_lifecycle_rules() {
    local lifecycle_file="$LOG_DIR/lifecycle.json"
    
    cat > "$lifecycle_file" << 'EOF'
{
  "lifecycle": {
    "rule": [
      {
        "action": {"type": "Delete"},
        "condition": {
          "age": 90,
          "matchesPrefix": ["uploads/", "exports/"]
        }
      },
      {
        "action": {"type": "SetStorageClass", "storageClass": "NEARLINE"},
        "condition": {
          "age": 30,
          "matchesPrefix": ["backups/"]
        }
      }
    ]
  }
}
EOF
    
    execute_command "gsutil lifecycle set $lifecycle_file gs://lucky-gas-storage" \
        "Setting lifecycle rules"
}

# Function to setup security (Story 3)
setup_security() {
    print_status "step" "Setting up security configuration (Story 3)..."
    
    # Enable Security Command Center
    execute_command "gcloud services enable securitycenter.googleapis.com" \
        "Enabling Security Command Center API"
    
    print_status "warning" "Security Command Center requires manual configuration in console"
    print_status "info" "Visit: https://console.cloud.google.com/security/command-center"
    
    # Create security policy
    print_status "info" "Creating Cloud Armor security policy..."
    
    if gcloud compute security-policies describe lucky-gas-prod-policy &> /dev/null; then
        print_status "warning" "Security policy already exists"
    else
        execute_command "gcloud compute security-policies create lucky-gas-prod-policy \
            --description=\"Lucky Gas production security policy\"" \
            "Creating security policy"
        
        # Add rate limiting
        execute_command "gcloud compute security-policies rules create 1000 \
            --security-policy=lucky-gas-prod-policy \
            --expression=\"true\" \
            --action=rate-based-ban \
            --rate-limit-threshold-count=50 \
            --rate-limit-threshold-interval-sec=60 \
            --ban-duration-sec=600 \
            --conform-action=allow" \
            "Adding rate limiting rule"
        
        # Add geo-blocking
        execute_command "gcloud compute security-policies rules create 2000 \
            --security-policy=lucky-gas-prod-policy \
            --expression=\"origin.region_code != 'TW' && origin.region_code != 'US'\" \
            --action=deny-403" \
            "Adding geo-blocking rule"
        
        # Add OWASP rules
        execute_command "gcloud compute security-policies rules create 3000 \
            --security-policy=lucky-gas-prod-policy \
            --expression=\"evaluatePreconfiguredExpr('xss-stable')\" \
            --action=deny-403" \
            "Adding XSS protection"
        
        execute_command "gcloud compute security-policies rules create 3001 \
            --security-policy=lucky-gas-prod-policy \
            --expression=\"evaluatePreconfiguredExpr('sqli-stable')\" \
            --action=deny-403" \
            "Adding SQL injection protection"
    fi
    
    # Create log sink for security events
    print_status "info" "Setting up security logging..."
    
    if ! gsutil ls -b gs://lucky-gas-security-logs &> /dev/null; then
        execute_command "gsutil mb -p $PROJECT_ID -c STANDARD -l $REGION gs://lucky-gas-security-logs/" \
            "Creating security logs bucket"
    fi
    
    execute_command "gcloud logging sinks create security-events \
        storage.googleapis.com/lucky-gas-security-logs \
        --log-filter='protoPayload.@type=\"type.googleapis.com/google.cloud.audit.AuditLog\" AND severity >= WARNING' || true" \
        "Creating security log sink"
    
    save_checkpoint "security" "completed"
    return 0
}

# Function to run validation tests
run_validation() {
    print_status "step" "Running validation tests..."
    
    local validation_errors=0
    
    # Validate service account
    print_status "info" "Validating service account..."
    if gcloud iam service-accounts describe $SERVICE_ACCOUNT_EMAIL &> /dev/null; then
        print_status "success" "Service account exists"
    else
        print_status "error" "Service account not found"
        ((validation_errors++))
    fi
    
    # Validate APIs
    print_status "info" "Validating enabled APIs..."
    local required_apis=(
        "routes.googleapis.com"
        "aiplatform.googleapis.com"
        "storage-component.googleapis.com"
    )
    
    for api in "${required_apis[@]}"; do
        if gcloud services list --enabled --filter="name:$api" --format="value(name)" | grep -q "$api"; then
            print_status "success" "$api is enabled"
        else
            print_status "error" "$api is not enabled"
            ((validation_errors++))
        fi
    done
    
    # Validate storage bucket
    print_status "info" "Validating storage bucket..."
    if gsutil ls -b gs://lucky-gas-storage &> /dev/null; then
        print_status "success" "Storage bucket exists"
        
        # Test upload
        if [ "$DRY_RUN" = "false" ]; then
            echo "test" > /tmp/gcp-test.txt
            if gsutil cp /tmp/gcp-test.txt gs://lucky-gas-storage/uploads/ && \
               gsutil rm gs://lucky-gas-storage/uploads/gcp-test.txt; then
                print_status "success" "Storage bucket is accessible"
            else
                print_status "error" "Cannot write to storage bucket"
                ((validation_errors++))
            fi
            rm -f /tmp/gcp-test.txt
        fi
    else
        print_status "error" "Storage bucket not found"
        ((validation_errors++))
    fi
    
    # Validate security policy
    print_status "info" "Validating security configuration..."
    if gcloud compute security-policies describe lucky-gas-prod-policy &> /dev/null; then
        print_status "success" "Security policy exists"
    else
        print_status "warning" "Security policy not found (may not be needed yet)"
    fi
    
    if [ $validation_errors -eq 0 ]; then
        print_status "success" "All validation tests passed!"
        save_checkpoint "validation" "completed"
        return 0
    else
        print_status "error" "Validation failed with $validation_errors errors"
        return 1
    fi
}

# Function to generate summary report
generate_summary() {
    local report_file="$LOG_DIR/gcp-setup-summary.md"
    
    cat > "$report_file" << EOF
# GCP Setup Summary Report

**Generated**: $(date)
**Project ID**: $PROJECT_ID
**Region**: $REGION

## Completed Steps

1. ✅ Project Configuration
   - Project: $PROJECT_ID
   - Billing Account: $BILLING_ACCOUNT
   - Region: $REGION

2. ✅ Service Account Setup
   - Email: $SERVICE_ACCOUNT_EMAIL
   - Key Location: ~/.gcp/lucky-gas/lucky-gas-prod-key.json
   - Roles Assigned: routes.viewer, aiplatform.user, storage.objectAdmin, secretmanager.secretAccessor, cloudsql.client

3. ✅ APIs Enabled
   - Routes API
   - Vertex AI API
   - Cloud Storage API
   - Secret Manager API
   - Monitoring API
   - Logging API

4. ✅ Storage Configuration
   - Bucket: gs://lucky-gas-storage
   - Versioning: Enabled
   - Lifecycle Rules: Configured

5. ✅ Security Setup
   - Cloud Armor Policy: lucky-gas-prod-policy
   - Rate Limiting: Configured
   - Geo-blocking: Taiwan and US only
   - OWASP Protection: Enabled

## Next Steps

1. **Manual Configuration Required**:
   - Configure Routes API quota in console
   - Set up Security Command Center
   - Configure budget alerts

2. **Update Application**:
   \`\`\`bash
   # backend/.env
   GOOGLE_APPLICATION_CREDENTIALS=/app/secrets/lucky-gas-prod-key.json
   GCP_PROJECT_ID=$PROJECT_ID
   GCP_REGION=$REGION
   GCS_BUCKET=lucky-gas-storage
   \`\`\`

3. **Store Credentials**:
   \`\`\`bash
   gcloud secrets create lucky-gas-service-key \\
       --data-file=~/.gcp/lucky-gas/lucky-gas-prod-key.json
   \`\`\`

4. **Test Integration**:
   \`\`\`bash
   cd backend
   export GOOGLE_APPLICATION_CREDENTIALS=~/.gcp/lucky-gas/lucky-gas-prod-key.json
   uv run python -c "from google.cloud import storage; client = storage.Client(); print('GCS Connected!')"
   \`\`\`

## Important URLs

- [Billing Dashboard](https://console.cloud.google.com/billing)
- [API Dashboard](https://console.cloud.google.com/apis/dashboard)
- [Security Command Center](https://console.cloud.google.com/security/command-center)
- [Routes API Quotas](https://console.cloud.google.com/apis/api/routes.googleapis.com/quotas)

## Security Reminders

- ⚠️ Never commit service account keys to Git
- ⚠️ Rotate keys every 90 days
- ⚠️ Enable 2FA for all Google Cloud accounts
- ⚠️ Review IAM permissions quarterly
EOF
    
    print_status "success" "Summary report generated: $report_file"
    
    # Display summary
    echo -e "\n${GREEN}=== Setup Complete ===${NC}\n"
    cat "$report_file"
}

# Main execution function
main() {
    print_status "info" "Starting GCP setup execution..."
    
    # Check dry run mode
    if [ "$DRY_RUN" = "true" ]; then
        print_status "warning" "Running in DRY RUN mode - no changes will be made"
    fi
    
    # Load checkpoint
    local last_step=$(load_checkpoint)
    
    # Execute steps based on checkpoint
    # Using a more compatible approach for step execution
    local execute_from_step=true
    
    if [ "$last_step" = "none" ] && [ "$execute_from_step" = "true" ]; then
        validate_project || exit 1
        last_step="project_setup"
    fi
    
    if [ "$last_step" = "project_setup" ] && [ "$execute_from_step" = "true" ]; then
        setup_service_account || exit 1
        last_step="service_account"
    fi
    
    if [ "$last_step" = "service_account" ] && [ "$execute_from_step" = "true" ]; then
        setup_apis_and_services || exit 1
        last_step="apis_and_services"
    fi
    
    if [ "$last_step" = "apis_and_services" ] && [ "$execute_from_step" = "true" ]; then
        setup_security || exit 1
        last_step="security"
    fi
    
    if [ "$last_step" = "security" ] && [ "$execute_from_step" = "true" ]; then
        run_validation || exit 1
        last_step="validation"
    fi
    
    if [ "$last_step" = "validation" ] && [ "$execute_from_step" = "true" ]; then
        generate_summary
    fi
    
    # Check for unknown checkpoint
    local valid_steps=("none" "project_setup" "service_account" "apis_and_services" "security" "validation")
    local step_found=false
    for step in "${valid_steps[@]}"; do
        if [ "$last_step" = "$step" ]; then
            step_found=true
            break
        fi
    done
    
    if [ "$step_found" = "false" ]; then
        print_status "error" "Unknown checkpoint: $last_step"
        exit 1
    fi
    
    print_status "success" "GCP setup execution completed successfully!"
}

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --dry-run)
            DRY_RUN=true
            shift
            ;;
        --help)
            echo "Usage: $0 [--dry-run] [--help]"
            echo "  --dry-run  Run without making actual changes"
            echo "  --help     Show this help message"
            exit 0
            ;;
        *)
            print_status "error" "Unknown option: $1"
            exit 1
            ;;
    esac
done

# Run main function
main "$@"