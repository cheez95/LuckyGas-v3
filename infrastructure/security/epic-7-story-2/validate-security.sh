#!/bin/bash

# Validate Security Controls Implementation
# This script checks that all security controls are properly configured

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
PROJECT_ID="vast-tributary-466619-m8"
REGION="asia-east1"
SERVICE_ACCOUNT="lucky-gas-prod@vast-tributary-466619-m8.iam.gserviceaccount.com"

echo -e "${GREEN}Security Controls Validation${NC}"
echo "============================"
echo "Project: $PROJECT_ID"
echo "Region: $REGION"
echo ""

# Track validation results
PASSED=0
FAILED=0
WARNINGS=0

# Function to check a validation
check() {
    local description=$1
    local command=$2
    local expected=$3
    
    echo -n "Checking $description... "
    
    if eval "$command" &> /dev/null; then
        echo -e "${GREEN}✓ PASSED${NC}"
        ((PASSED++))
    else
        if [ -n "$expected" ]; then
            echo -e "${YELLOW}⚠ WARNING${NC} - $expected"
            ((WARNINGS++))
        else
            echo -e "${RED}✗ FAILED${NC}"
            ((FAILED++))
        fi
    fi
}

# Function to check with output comparison
check_output() {
    local description=$1
    local command=$2
    local expected=$3
    
    echo -n "Checking $description... "
    
    local output=$(eval "$command" 2>/dev/null || echo "ERROR")
    
    if [[ "$output" == *"$expected"* ]]; then
        echo -e "${GREEN}✓ PASSED${NC}"
        ((PASSED++))
    else
        echo -e "${RED}✗ FAILED${NC} (expected: $expected, got: $output)"
        ((FAILED++))
    fi
}

echo -e "\n${YELLOW}1. Workload Identity Validation${NC}"
echo "--------------------------------"

# Check Workload Identity service accounts
check "Backend Workload Identity SA exists" \
      "gcloud iam service-accounts describe luckygas-backend-wi@${PROJECT_ID}.iam.gserviceaccount.com" \
      ""

check "Frontend Workload Identity SA exists" \
      "gcloud iam service-accounts describe luckygas-frontend-wi@${PROJECT_ID}.iam.gserviceaccount.com" \
      ""

check "Worker Workload Identity SA exists" \
      "gcloud iam service-accounts describe luckygas-worker-wi@${PROJECT_ID}.iam.gserviceaccount.com" \
      ""

# Check Workload Identity bindings
check "Backend WI binding configured" \
      "gcloud iam service-accounts get-iam-policy luckygas-backend-wi@${PROJECT_ID}.iam.gserviceaccount.com --flatten='bindings[].members' --filter='bindings.role:roles/iam.workloadIdentityUser' | grep -q serviceAccount:${PROJECT_ID}.svc.id.goog" \
      ""

echo -e "\n${YELLOW}2. VPC Service Controls Validation${NC}"
echo "-----------------------------------"

# Check Private Google Access
check "Private Google Access enabled" \
      "gcloud compute networks subnets describe luckygas-subnet-${REGION} --region=$REGION --format='value(privateIpGoogleAccess)' | grep -q True" \
      "May need to be configured if using original subnet"

# Check Cloud NAT
check "Cloud NAT configured" \
      "gcloud compute routers nats list --router=luckygas-router --region=$REGION" \
      "Optional but recommended"

# Check firewall rules
check "Deny all ingress rule exists" \
      "gcloud compute firewall-rules describe luckygas-deny-all-ingress" \
      "Recommended for defense in depth"

echo -e "\n${YELLOW}3. Security Command Center Validation${NC}"
echo "--------------------------------------"

# Check APIs enabled
check "Security Command Center API enabled" \
      "gcloud services list --enabled --filter='name:securitycenter.googleapis.com' | grep -q securitycenter" \
      ""

check "Container Analysis API enabled" \
      "gcloud services list --enabled --filter='name:containeranalysis.googleapis.com' | grep -q containeranalysis" \
      ""

check "Binary Authorization API enabled" \
      "gcloud services list --enabled --filter='name:binaryauthorization.googleapis.com' | grep -q binaryauthorization" \
      ""

# Check Binary Authorization policy
check "Binary Authorization policy exists" \
      "gcloud container binauthz policy export --format='value(name)' | grep -q projects/${PROJECT_ID}/policy" \
      "Required for container security"

echo -e "\n${YELLOW}4. Key Rotation Validation${NC}"
echo "--------------------------"

# Check Cloud Scheduler job
check "Key rotation scheduler job exists" \
      "gcloud scheduler jobs describe service-account-key-rotation --location=$REGION" \
      ""

# Check Cloud Function
check "Key rotation function deployed" \
      "gcloud functions describe service-account-key-rotation --region=$REGION" \
      ""

# Check key age
echo -n "Checking service account key age... "
KEY_COUNT=$(gcloud iam service-accounts keys list --iam-account=$SERVICE_ACCOUNT --filter="keyType:USER_MANAGED" --format="value(name)" | wc -l)
if [ "$KEY_COUNT" -gt 0 ]; then
    OLDEST_KEY_AGE=$(gcloud iam service-accounts keys list --iam-account=$SERVICE_ACCOUNT --filter="keyType:USER_MANAGED" --format="value(validAfterTime)" | xargs -I {} date -d {} +%s | sort -n | head -1)
    CURRENT_TIME=$(date +%s)
    AGE_DAYS=$(( ($CURRENT_TIME - $OLDEST_KEY_AGE) / 86400 ))
    
    if [ "$AGE_DAYS" -gt 30 ]; then
        echo -e "${YELLOW}⚠ WARNING${NC} - Keys older than 30 days found ($AGE_DAYS days)"
        ((WARNINGS++))
    else
        echo -e "${GREEN}✓ PASSED${NC} - All keys within rotation period"
        ((PASSED++))
    fi
else
    echo -e "${GREEN}✓ PASSED${NC} - No user-managed keys (using Workload Identity)"
    ((PASSED++))
fi

echo -e "\n${YELLOW}5. Least Privilege IAM Validation${NC}"
echo "---------------------------------"

# Check custom roles
check "Backend custom role exists" \
      "gcloud iam roles describe luckyGasBackendAPI --project=$PROJECT_ID" \
      ""

check "Frontend custom role exists" \
      "gcloud iam roles describe luckyGasFrontendStatic --project=$PROJECT_ID" \
      ""

check "Worker custom role exists" \
      "gcloud iam roles describe luckyGasWorkerBatch --project=$PROJECT_ID" \
      ""

# Check organization policies
check "Service account key creation restricted" \
      "gcloud resource-manager org-policies describe iam.disableServiceAccountKeyCreation --project=$PROJECT_ID | grep -q enforced" \
      "Recommended for production"

# Check for overly permissive roles
echo -n "Checking for overly permissive roles... "
OWNER_COUNT=$(gcloud projects get-iam-policy $PROJECT_ID --flatten="bindings[].members" --filter="bindings.role:roles/owner" --format="value(bindings.members)" | grep -v "projectOwner" | wc -l)
EDITOR_COUNT=$(gcloud projects get-iam-policy $PROJECT_ID --flatten="bindings[].members" --filter="bindings.role:roles/editor" --format="value(bindings.members)" | grep -v "projectEditor" | wc -l)

if [ "$OWNER_COUNT" -gt 1 ] || [ "$EDITOR_COUNT" -gt 0 ]; then
    echo -e "${YELLOW}⚠ WARNING${NC} - Found overly permissive roles (Owners: $OWNER_COUNT, Editors: $EDITOR_COUNT)"
    ((WARNINGS++))
else
    echo -e "${GREEN}✓ PASSED${NC}"
    ((PASSED++))
fi

echo -e "\n${YELLOW}6. Monitoring & Alerting Validation${NC}"
echo "-----------------------------------"

# Check notification channels
check "Security notification channel exists" \
      "gcloud alpha monitoring channels list --filter='displayName:\"Security Team\"' | grep -q 'Security Team'" \
      "Configure in Cloud Console if needed"

# Check alert policies
check "Key rotation failure alert exists" \
      "gcloud alpha monitoring policies list --filter='displayName:\"Service Account Key Rotation Failure\"' | grep -q 'Key Rotation'" \
      ""

check "Privilege escalation alert exists" \
      "gcloud alpha monitoring policies list --filter='displayName:\"IAM Privilege Escalation Attempt\"' | grep -q 'Privilege'" \
      ""

echo -e "\n${YELLOW}7. Secret Manager Validation${NC}"
echo "----------------------------"

# Check secrets exist
check "Database password secret exists" \
      "gcloud secrets describe database-password" \
      ""

check "JWT secret exists" \
      "gcloud secrets describe jwt-secret-key" \
      ""

# Check secret access
check "Backend SA has secret access" \
      "gcloud secrets get-iam-policy database-password --flatten='bindings[].members' --filter='bindings.role:roles/secretmanager.secretAccessor' | grep -q luckygas-backend" \
      ""

echo -e "\n${YELLOW}8. Additional Security Checks${NC}"
echo "-----------------------------"

# Check for default service account usage
echo -n "Checking for default service account usage... "
DEFAULT_SA_USAGE=$(gcloud run services list --region=$REGION --format="value(spec.template.spec.serviceAccountName)" | grep -c "compute@developer.gserviceaccount.com" || true)
if [ "$DEFAULT_SA_USAGE" -gt 0 ]; then
    echo -e "${YELLOW}⚠ WARNING${NC} - Found $DEFAULT_SA_USAGE services using default service account"
    ((WARNINGS++))
else
    echo -e "${GREEN}✓ PASSED${NC}"
    ((PASSED++))
fi

# Check audit logging
check "Audit logging configured" \
      "gcloud projects get-iam-policy $PROJECT_ID --format=json | jq -e '.auditConfigs | length > 0'" \
      "Recommended for compliance"

# Summary
echo -e "\n${GREEN}Validation Summary${NC}"
echo "=================="
echo -e "Passed:   ${GREEN}$PASSED${NC}"
echo -e "Failed:   ${RED}$FAILED${NC}"
echo -e "Warnings: ${YELLOW}$WARNINGS${NC}"

if [ $FAILED -eq 0 ]; then
    echo -e "\n${GREEN}All critical security controls are properly configured!${NC}"
    
    if [ $WARNINGS -gt 0 ]; then
        echo -e "${YELLOW}Some optional security enhancements are recommended.${NC}"
    fi
else
    echo -e "\n${RED}Some security controls need attention. Please review the failed checks.${NC}"
fi

# Recommendations
echo -e "\n${YELLOW}Security Recommendations:${NC}"
echo "1. Enable VPC Service Controls if you have an organization"
echo "2. Configure Security Command Center for vulnerability scanning"
echo "3. Set up proper notification channels for security alerts"
echo "4. Review and minimize the number of project owners/editors"
echo "5. Enable comprehensive audit logging for all services"
echo "6. Regularly review service account permissions"
echo "7. Implement security training based on findings"

exit $FAILED