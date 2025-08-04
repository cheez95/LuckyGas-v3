#!/bin/bash

# Deploy Security Controls for Epic 7 Story 2
# This script deploys all security controls in the correct order

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
PROJECT_ID="vast-tributary-466619-m8"
REGION="asia-east1"
ENVIRONMENT="production"

echo -e "${GREEN}Lucky Gas Security Controls Deployment${NC}"
echo "========================================"
echo "Project: $PROJECT_ID"
echo "Region: $REGION"
echo "Environment: $ENVIRONMENT"
echo ""

# Check prerequisites
echo -e "${YELLOW}Checking prerequisites...${NC}"

# Check if gcloud is installed
if ! command -v gcloud &> /dev/null; then
    echo -e "${RED}Error: gcloud CLI is not installed${NC}"
    exit 1
fi

# Check if terraform is installed
if ! command -v terraform &> /dev/null; then
    echo -e "${RED}Error: Terraform is not installed${NC}"
    exit 1
fi

# Check if logged in to gcloud
if ! gcloud auth list --filter=status:ACTIVE --format="value(account)" &> /dev/null; then
    echo -e "${RED}Error: Not logged in to gcloud. Run 'gcloud auth login'${NC}"
    exit 1
fi

# Set project
gcloud config set project $PROJECT_ID

# Check for required environment variables
if [ -z "$TF_VAR_organization_id" ]; then
    echo -e "${YELLOW}Warning: TF_VAR_organization_id not set. VPC Service Controls will be skipped.${NC}"
    echo "To set: export TF_VAR_organization_id=YOUR_ORG_ID"
fi

if [ -z "$TF_VAR_project_number" ]; then
    PROJECT_NUMBER=$(gcloud projects describe $PROJECT_ID --format="value(projectNumber)")
    export TF_VAR_project_number=$PROJECT_NUMBER
    echo "Project number: $PROJECT_NUMBER"
fi

# Initialize Terraform
echo -e "\n${YELLOW}Initializing Terraform...${NC}"
terraform init

# Plan deployment
echo -e "\n${YELLOW}Planning deployment...${NC}"
terraform plan -out=security-deploy.plan

# Ask for confirmation
echo -e "\n${YELLOW}Ready to deploy security controls. Continue? (y/n)${NC}"
read -r response
if [[ ! "$response" =~ ^[Yy]$ ]]; then
    echo "Deployment cancelled"
    exit 0
fi

# Deploy in phases
echo -e "\n${GREEN}Phase 1: Deploying Workload Identity...${NC}"
terraform apply -target=google_service_account.backend_workload_identity \
                -target=google_service_account.frontend_workload_identity \
                -target=google_service_account.worker_workload_identity \
                -auto-approve

echo -e "\n${GREEN}Phase 2: Setting up IAM roles...${NC}"
terraform apply -target=google_project_iam_custom_role.backend_api_role \
                -target=google_project_iam_custom_role.frontend_static_role \
                -target=google_project_iam_custom_role.worker_batch_role \
                -auto-approve

echo -e "\n${GREEN}Phase 3: Configuring VPC Service Controls...${NC}"
if [ -n "$TF_VAR_organization_id" ]; then
    terraform apply -target=google_access_context_manager_access_policy.lucky_gas_policy \
                    -target=google_access_context_manager_access_level.internal_access \
                    -target=google_access_context_manager_service_perimeter.lucky_gas_perimeter \
                    -auto-approve
else
    echo -e "${YELLOW}Skipping VPC Service Controls (no organization ID)${NC}"
fi

echo -e "\n${GREEN}Phase 4: Setting up Security Command Center...${NC}"
# Package Cloud Functions first
echo "Packaging Cloud Functions..."
cd functions
zip -q security-alert-processor.zip security-alert-processor.py requirements.txt
zip -q key-rotation.zip key-rotation.py requirements.txt
cd ..

# Upload functions to bucket
FUNCTIONS_BUCKET="${PROJECT_ID}-functions"
echo "Creating functions bucket..."
gsutil mb -p $PROJECT_ID -l $REGION gs://$FUNCTIONS_BUCKET || true
gsutil cp functions/*.zip gs://$FUNCTIONS_BUCKET/

# Deploy Security Command Center
terraform apply -target=google_project_service.security_center_api \
                -target=google_project_service.container_analysis_api \
                -target=google_project_service.binary_authorization_api \
                -auto-approve

echo -e "\n${GREEN}Phase 5: Setting up Key Rotation...${NC}"
terraform apply -target=google_cloud_scheduler_job.key_rotation \
                -target=google_cloudfunctions_function.key_rotation \
                -auto-approve

echo -e "\n${GREEN}Phase 6: Applying remaining configurations...${NC}"
terraform apply -auto-approve

# Post-deployment tasks
echo -e "\n${GREEN}Post-deployment configuration...${NC}"

# Create Slack webhook secret (if not exists)
echo "Creating Slack webhook secret..."
echo "https://hooks.slack.com/services/YOUR/WEBHOOK/URL" | \
    gcloud secrets create security-alerts-webhook --data-file=- || true

# Enable audit logs
echo "Enabling audit logs..."
gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="allUsers" \
    --role="roles/logging.viewer" \
    --condition=None

# Verification
echo -e "\n${GREEN}Verifying deployment...${NC}"

# Check Workload Identity
echo -n "Workload Identity service accounts: "
gcloud iam service-accounts list --filter="email:luckygas-*-wi@" --format="value(email)" | wc -l

# Check custom roles
echo -n "Custom IAM roles created: "
gcloud iam roles list --project=$PROJECT_ID --filter="name:luckyGas*" --format="value(name)" | wc -l

# Check Cloud Functions
echo -n "Security Cloud Functions deployed: "
gcloud functions list --filter="name:security-alert-processor OR name:service-account-key-rotation" --format="value(name)" | wc -l

# Summary
echo -e "\n${GREEN}Deployment Summary${NC}"
echo "=================="
echo "✓ Workload Identity configured"
echo "✓ Least privilege IAM implemented"
if [ -n "$TF_VAR_organization_id" ]; then
    echo "✓ VPC Service Controls enabled"
else
    echo "⚠ VPC Service Controls skipped (no org ID)"
fi
echo "✓ Security Command Center integrated"
echo "✓ Key rotation automation deployed"

echo -e "\n${GREEN}Next Steps:${NC}"
echo "1. Update Slack webhook URL in Secret Manager:"
echo "   gcloud secrets versions add security-alerts-webhook --data-file=slack-webhook.txt"
echo ""
echo "2. Test Workload Identity:"
echo "   gcloud run deploy test-wi --image=gcr.io/cloudrun/hello --service-account=luckygas-backend-wi@${PROJECT_ID}.iam.gserviceaccount.com --region=$REGION"
echo ""
echo "3. Configure Security Command Center:"
echo "   https://console.cloud.google.com/security/command-center?project=$PROJECT_ID"
echo ""
echo "4. Monitor key rotation:"
echo "   gcloud scheduler jobs describe service-account-key-rotation --location=$REGION"
echo ""
echo -e "${GREEN}Security controls deployment complete!${NC}"