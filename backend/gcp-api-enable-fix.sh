#!/bin/bash
# Fixed API Enablement Script with Reliability Improvements
# This script demonstrates proper API enablement with checks and timeouts

set -euo pipefail

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Configuration
PROJECT_ID="${PROJECT_ID:-vast-tributary-466619-m8}"
MAX_WAIT_TIME=300  # 5 minutes max wait per API
CHECK_INTERVAL=5   # Check every 5 seconds

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

# Function to check if API is already enabled
is_api_enabled() {
    local api=$1
    
    if gcloud services list --enabled --filter="name:$api" --format="value(name)" 2>/dev/null | grep -q "$api"; then
        return 0  # API is enabled
    else
        return 1  # API is not enabled
    fi
}

# Function to enable API with proper checks and timeout
enable_api_safe() {
    local api=$1
    local description=${2:-"API"}
    
    print_status "info" "Processing $description ($api)..."
    
    # First check if already enabled
    if is_api_enabled "$api"; then
        print_status "success" "$description is already enabled"
        return 0
    fi
    
    # Try to enable the API asynchronously
    print_status "info" "Enabling $description..."
    
    # Start the enable operation
    local operation_name=""
    local enable_output=""
    
    # Capture the operation details
    enable_output=$(gcloud services enable "$api" --async --format="value(name)" 2>&1) || {
        local exit_code=$?
        print_status "error" "Failed to start enable operation for $api: $enable_output"
        return $exit_code
    }
    
    # Extract operation name if available
    if [[ "$enable_output" =~ operations/([a-zA-Z0-9._-]+) ]]; then
        operation_name="${BASH_REMATCH[1]}"
        print_status "info" "Operation started: $operation_name"
    else
        # If no operation returned, it might have completed immediately
        print_status "info" "Checking if API was enabled immediately..."
        sleep 2
        
        if is_api_enabled "$api"; then
            print_status "success" "$description enabled successfully"
            return 0
        else
            print_status "warning" "No operation ID returned, but API not yet enabled"
        fi
    fi
    
    # Wait for the API to be enabled
    local waited=0
    while [ $waited -lt $MAX_WAIT_TIME ]; do
        if is_api_enabled "$api"; then
            print_status "success" "$description enabled successfully after ${waited}s"
            return 0
        fi
        
        # Check operation status if we have an operation name
        if [ -n "$operation_name" ]; then
            local op_status=$(gcloud services operations describe "$operation_name" --format="value(done)" 2>/dev/null || echo "unknown")
            
            if [ "$op_status" = "True" ]; then
                # Operation completed, double-check if API is enabled
                if is_api_enabled "$api"; then
                    print_status "success" "$description enabled successfully"
                    return 0
                else
                    print_status "error" "Operation completed but API still not enabled"
                    return 1
                fi
            elif [ "$op_status" = "unknown" ]; then
                print_status "warning" "Cannot check operation status, continuing to poll API state..."
            fi
        fi
        
        sleep $CHECK_INTERVAL
        waited=$((waited + CHECK_INTERVAL))
        
        # Progress indicator
        if [ $((waited % 30)) -eq 0 ]; then
            print_status "info" "Still waiting for $api... (${waited}s elapsed)"
        fi
    done
    
    print_status "error" "Timeout waiting for $api to be enabled after ${MAX_WAIT_TIME}s"
    return 1
}

# Function to enable multiple APIs safely
enable_apis_batch() {
    local apis=("$@")
    local failed_apis=()
    
    print_status "info" "Enabling ${#apis[@]} APIs..."
    
    for api in "${apis[@]}"; do
        if ! enable_api_safe "$api" "$api"; then
            failed_apis+=("$api")
        fi
        echo  # Add spacing between APIs
    done
    
    if [ ${#failed_apis[@]} -gt 0 ]; then
        print_status "error" "Failed to enable the following APIs:"
        for api in "${failed_apis[@]}"; do
            echo "  - $api"
        done
        return 1
    else
        print_status "success" "All APIs enabled successfully!"
        return 0
    fi
}

# Main execution
main() {
    print_status "info" "Starting fixed API enablement process..."
    print_status "info" "Project: $PROJECT_ID"
    echo
    
    # Set the project
    gcloud config set project "$PROJECT_ID" >/dev/null 2>&1
    
    # Define APIs to enable
    local core_apis=(
        "compute.googleapis.com"
        "cloudresourcemanager.googleapis.com"
        "iam.googleapis.com"
    )
    
    local app_apis=(
        "routes.googleapis.com"
        "aiplatform.googleapis.com"
        "storage-component.googleapis.com"
        "secretmanager.googleapis.com"
        "monitoring.googleapis.com"
        "logging.googleapis.com"
        "cloudbilling.googleapis.com"
    )
    
    # Enable core APIs first
    print_status "info" "=== Enabling Core APIs ==="
    enable_apis_batch "${core_apis[@]}"
    echo
    
    # Enable application APIs
    print_status "info" "=== Enabling Application APIs ==="
    enable_apis_batch "${app_apis[@]}"
    echo
    
    # Final verification
    print_status "info" "=== Final Verification ==="
    local all_apis=("${core_apis[@]}" "${app_apis[@]}")
    local all_enabled=true
    
    for api in "${all_apis[@]}"; do
        if is_api_enabled "$api"; then
            print_status "success" "$api: Enabled"
        else
            print_status "error" "$api: Not enabled"
            all_enabled=false
        fi
    done
    
    echo
    if $all_enabled; then
        print_status "success" "All APIs are enabled and ready!"
        return 0
    else
        print_status "error" "Some APIs failed to enable. Please check the errors above."
        return 1
    fi
}

# Run if executed directly
if [ "${BASH_SOURCE[0]}" = "${0}" ]; then
    main "$@"
fi