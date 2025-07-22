#!/bin/bash
# API Activation Diagnostic Script
# This script helps diagnose issues with GCP API activation

set -euo pipefail

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}=== GCP API Activation Diagnostic ===${NC}"
echo "Started at: $(date)"
echo

# Check gcloud configuration
echo -e "${YELLOW}1. Checking gcloud configuration...${NC}"
gcloud config list
echo

# Check authentication
echo -e "${YELLOW}2. Checking authentication...${NC}"
gcloud auth list
echo

# Check current project
echo -e "${YELLOW}3. Current project...${NC}"
PROJECT_ID=$(gcloud config get-value project)
echo "Project ID: $PROJECT_ID"
gcloud projects describe $PROJECT_ID || echo -e "${RED}Failed to describe project${NC}"
echo

# Check billing
echo -e "${YELLOW}4. Checking billing status...${NC}"
gcloud beta billing projects describe $PROJECT_ID || echo -e "${RED}Failed to get billing info${NC}"
echo

# Check network connectivity to Google APIs
echo -e "${YELLOW}5. Testing network connectivity...${NC}"
echo -n "Testing servicemanagement.googleapis.com: "
if curl -s -o /dev/null -w "%{http_code}" https://servicemanagement.googleapis.com/ | grep -q "404"; then
    echo -e "${GREEN}OK${NC}"
else
    echo -e "${RED}FAILED${NC}"
fi
echo

# List currently enabled APIs
echo -e "${YELLOW}6. Currently enabled APIs...${NC}"
gcloud services list --enabled --format="table(name,state)" | head -20
echo

# Test enabling a simple API with timeout
echo -e "${YELLOW}7. Testing API enablement with monitoring...${NC}"
echo "Attempting to enable monitoring.googleapis.com (should be quick if already enabled)..."

# Function to monitor API enablement
monitor_api_enable() {
    local api=$1
    local start_time=$(date +%s)
    local timeout=120  # 2 minutes timeout
    
    # Start the enable command in background
    echo "Starting API enablement for $api..."
    gcloud services enable "$api" --verbosity=debug &
    local pid=$!
    
    # Monitor the process
    local elapsed=0
    while kill -0 $pid 2>/dev/null; do
        elapsed=$(($(date +%s) - start_time))
        echo -ne "\rElapsed time: ${elapsed}s (PID: $pid)"
        
        if [ $elapsed -gt $timeout ]; then
            echo -e "\n${RED}Timeout reached! Killing process...${NC}"
            kill -9 $pid 2>/dev/null
            return 1
        fi
        
        sleep 1
    done
    
    # Check exit status
    wait $pid
    local exit_code=$?
    
    if [ $exit_code -eq 0 ]; then
        echo -e "\n${GREEN}API enabled successfully in ${elapsed}s${NC}"
    else
        echo -e "\n${RED}API enablement failed with exit code $exit_code${NC}"
    fi
    
    return $exit_code
}

# Test with monitoring API (usually already enabled)
monitor_api_enable "monitoring.googleapis.com"
echo

# Check for any operations in progress
echo -e "${YELLOW}8. Checking for operations in progress...${NC}"
gcloud services operations list --filter="done:false" --format="table(name,done,error)" || echo "No operations API available"
echo

# Check API restrictions
echo -e "${YELLOW}9. Checking for API restrictions...${NC}"
gcloud services list --available --filter="name:(compute.googleapis.com OR cloudresourcemanager.googleapis.com OR iam.googleapis.com)" \
    --format="table(name,state)" || echo "Failed to list available services"
echo

# Generate recommendations
echo -e "${BLUE}=== Recommendations ===${NC}"
echo
echo "If API activation is hanging, try:"
echo "1. Enable APIs individually with --async flag:"
echo "   ${GREEN}gcloud services enable compute.googleapis.com --async${NC}"
echo
echo "2. Check operation status:"
echo "   ${GREEN}gcloud services operations list --filter='done:false'${NC}"
echo
echo "3. Enable debug logging and try again:"
echo "   ${GREEN}source logs/gcloud-debug-config.sh${NC}"
echo "   ${GREEN}gcloud services enable compute.googleapis.com --verbosity=debug${NC}"
echo
echo "4. Try using the Cloud Console UI instead:"
echo "   ${BLUE}https://console.cloud.google.com/apis/dashboard?project=$PROJECT_ID${NC}"
echo
echo "5. Check if there are organizational policies blocking API enablement:"
echo "   ${GREEN}gcloud resource-manager org-policies list --project=$PROJECT_ID${NC}"
echo

echo -e "${BLUE}Diagnostic complete at: $(date)${NC}"
