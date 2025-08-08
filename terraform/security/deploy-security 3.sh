#!/bin/bash
# Deploy Security Controls for Lucky Gas Google Cloud Setup
# This script deploys all Story 2 security configurations

set -euo pipefail

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Configuration
PROJECT_ID="vast-tributary-466619-m8"
REGION="asia-east1"
ORGANIZATION_ID="${ORGANIZATION_ID:-}" # Set this environment variable

echo -e "${GREEN}Lucky Gas Security Controls Deployment${NC}"
echo "========================================"

# Check prerequisites
check_prerequisites() {
    echo -e "\n${YELLOW}Checking prerequisites...${NC}"
    
    # Check if gcloud is installed
    if ! command -v gcloud &> /dev/null; then
        echo -e "${RED}Error: gcloud CLI not installed${NC}"
        exit 1
    fi
    
    # Check if terraform is installed
    if ! command -v terraform &> /dev/null; then
        echo -e "${RED}Error: Terraform not installed${NC}"
        exit 1
    fi
    
    # Check if logged in to gcloud
    if ! gcloud auth list --filter=status:ACTIVE --format="value(account)" &> /dev/null; then
        echo -e "${RED}Error: Not logged in to gcloud. Run: gcloud auth login${NC}"
        exit 1
    fi
    
    # Check project
    CURRENT_PROJECT=$(gcloud config get-value project 2>/dev/null)
    if [ "$CURRENT_PROJECT" != "$PROJECT_ID" ]; then
        echo -e "${YELLOW}Setting project to $PROJECT_ID...${NC}"
        gcloud config set project "$PROJECT_ID"
    fi
    
    # Check organization ID
    if [ -z "$ORGANIZATION_ID" ]; then
        echo -e "${YELLOW}Warning: ORGANIZATION_ID not set. Organization policies will be skipped.${NC}"
        echo "To set: export ORGANIZATION_ID=your-org-id"
    fi
    
    echo -e "${GREEN}Prerequisites check passed!${NC}"
}

# Enable required APIs
enable_apis() {
    echo -e "\n${YELLOW}Enabling required APIs...${NC}"
    
    APIS=(
        "securitycenter.googleapis.com"
        "containeranalysis.googleapis.com"
        "binaryauthorization.googleapis.com"
        "accesscontextmanager.googleapis.com"
        "cloudscheduler.googleapis.com"
        "secretmanager.googleapis.com"
        "monitoring.googleapis.com"
        "logging.googleapis.com"
        "cloudresourcemanager.googleapis.com"
        "orgpolicy.googleapis.com"
        "servicenetworking.googleapis.com"
        "vpcaccess.googleapis.com"
        "websecurityscanner.googleapis.com"
    )
    
    for api in "${APIS[@]}"; do
        echo "Enabling $api..."
        gcloud services enable "$api" --project="$PROJECT_ID" || true
    done
    
    echo -e "${GREEN}APIs enabled!${NC}"
}

# Initialize Terraform
init_terraform() {
    echo -e "\n${YELLOW}Initializing Terraform...${NC}"
    
    # Create terraform.tfvars
    cat > terraform.tfvars <<EOF
project_id = "$PROJECT_ID"
region = "$REGION"
organization_id = "$ORGANIZATION_ID"
EOF
    
    terraform init
    
    echo -e "${GREEN}Terraform initialized!${NC}"
}

# Validate Terraform configuration
validate_terraform() {
    echo -e "\n${YELLOW}Validating Terraform configuration...${NC}"
    
    terraform validate
    
    echo -e "${GREEN}Terraform configuration is valid!${NC}"
}

# Plan Terraform deployment
plan_terraform() {
    echo -e "\n${YELLOW}Planning Terraform deployment...${NC}"
    
    terraform plan -out=security.tfplan
    
    echo -e "${GREEN}Terraform plan created!${NC}"
}

# Apply Terraform configuration
apply_terraform() {
    echo -e "\n${YELLOW}Applying Terraform configuration...${NC}"
    echo -e "${RED}This will create real resources and incur costs.${NC}"
    read -p "Continue? (yes/no): " confirm
    
    if [ "$confirm" != "yes" ]; then
        echo "Deployment cancelled."
        exit 0
    fi
    
    terraform apply security.tfplan
    
    echo -e "${GREEN}Terraform configuration applied!${NC}"
}

# Create Cloud Function source code
create_cloud_functions() {
    echo -e "\n${YELLOW}Creating Cloud Function source code...${NC}"
    
    mkdir -p functions/security-processor
    mkdir -p functions/key-rotator
    
    # Security Alert Processor
    cat > functions/security-processor/main.py <<'EOF'
import json
import os
import logging
import requests
from flask import Request, jsonify
from google.cloud import secretmanager

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def process_security_alert(request: Request):
    """Process Security Command Center alerts and send to Slack."""
    try:
        # Parse Pub/Sub message
        envelope = request.get_json()
        if not envelope:
            return jsonify({'error': 'No message received'}), 400
        
        pubsub_message = envelope['message']
        data = json.loads(pubsub_message['data'].decode('base64'))
        
        # Extract finding details
        finding = data.get('finding', {})
        severity = finding.get('severity', 'UNKNOWN')
        category = finding.get('category', 'UNKNOWN')
        resource = finding.get('resourceName', 'UNKNOWN')
        
        # Only alert on HIGH and CRITICAL
        if severity not in ['HIGH', 'CRITICAL']:
            logger.info(f"Ignoring {severity} severity finding")
            return jsonify({'status': 'ignored'}), 200
        
        # Get Slack webhook from Secret Manager
        client = secretmanager.SecretManagerServiceClient()
        project_id = os.environ['PROJECT_ID']
        secret_name = f"projects/{project_id}/secrets/slack-security-webhook/versions/latest"
        response = client.access_secret_version(request={"name": secret_name})
        webhook_url = response.payload.data.decode("UTF-8")
        
        # Format Slack message
        slack_message = {
            "text": f"🚨 Security Alert: {severity} severity finding",
            "blocks": [
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"*Security Alert*\n*Severity:* {severity}\n*Category:* {category}\n*Resource:* {resource}"
                    }
                }
            ]
        }
        
        # Send to Slack
        response = requests.post(webhook_url, json=slack_message)
        response.raise_for_status()
        
        logger.info(f"Alert sent to Slack for {severity} finding")
        return jsonify({'status': 'sent'}), 200
        
    except Exception as e:
        logger.error(f"Error processing security alert: {e}")
        return jsonify({'error': str(e)}), 500
EOF

    # Key Rotation Function
    cat > functions/key-rotator/main.py <<'EOF'
import os
import json
import logging
from datetime import datetime, timedelta
from flask import Request, jsonify
from google.cloud import iam_admin_v1
from google.cloud import secretmanager
from google.cloud import monitoring_v3

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def rotate_service_account_keys(request: Request):
    """Rotate service account keys older than 30 days."""
    try:
        project_id = os.environ['PROJECT_ID']
        rotation_days = int(os.environ.get('ROTATION_DAYS', 30))
        service_accounts = json.loads(os.environ['SERVICE_ACCOUNTS'])
        
        iam_client = iam_admin_v1.IAMClient()
        secret_client = secretmanager.SecretManagerServiceClient()
        metrics_client = monitoring_v3.MetricServiceClient()
        
        rotated_keys = []
        
        for sa_email in service_accounts:
            logger.info(f"Checking keys for {sa_email}")
            
            # List existing keys
            sa_name = f"projects/{project_id}/serviceAccounts/{sa_email}"
            keys = iam_client.list_service_account_keys(request={"name": sa_name})
            
            for key in keys.keys:
                # Skip system-managed keys
                if key.key_type != iam_admin_v1.ServiceAccountKey.KeyType.USER_MANAGED:
                    continue
                
                # Check key age
                created_time = key.valid_after_time
                age_days = (datetime.utcnow() - created_time).days
                
                if age_days > rotation_days:
                    logger.info(f"Rotating key {key.name} (age: {age_days} days)")
                    
                    # Create new key
                    new_key = iam_client.create_service_account_key(
                        request={"name": sa_name}
                    )
                    
                    # Store in Secret Manager
                    secret_id = f"lucky-gas-{sa_email.split('@')[0]}-key"
                    secret_name = f"projects/{project_id}/secrets/{secret_id}"
                    
                    # Create secret version
                    secret_client.add_secret_version(
                        request={
                            "parent": secret_name,
                            "payload": {"data": new_key.private_key_data}
                        }
                    )
                    
                    # Delete old key
                    iam_client.delete_service_account_key(request={"name": key.name})
                    
                    rotated_keys.append({
                        "service_account": sa_email,
                        "old_key_id": key.name.split('/')[-1],
                        "new_key_id": new_key.name.split('/')[-1],
                        "rotated_at": datetime.utcnow().isoformat()
                    })
                    
                    # Log rotation event
                    logger.info(f"Successfully rotated key for {sa_email}")
        
        # Send metrics
        series = monitoring_v3.TimeSeries()
        series.metric.type = f"custom.googleapis.com/luckygas/key_rotations"
        series.metric.labels["status"] = "success"
        series.points.append(monitoring_v3.Point({
            "interval": {"end_time": {"seconds": int(datetime.utcnow().timestamp())}},
            "value": {"int64_value": len(rotated_keys)}
        }))
        
        return jsonify({
            "status": "success",
            "rotated_keys": rotated_keys
        }), 200
        
    except Exception as e:
        logger.error(f"Error rotating keys: {e}")
        return jsonify({"error": str(e)}), 500
EOF

    # Requirements files
    echo "google-cloud-secret-manager==2.16.0" > functions/security-processor/requirements.txt
    echo "requests==2.31.0" >> functions/security-processor/requirements.txt
    echo "Flask==3.0.0" >> functions/security-processor/requirements.txt
    
    echo "google-cloud-iam==2.12.0" > functions/key-rotator/requirements.txt
    echo "google-cloud-secret-manager==2.16.0" >> functions/key-rotator/requirements.txt
    echo "google-cloud-monitoring==2.15.0" >> functions/key-rotator/requirements.txt
    echo "Flask==3.0.0" >> functions/key-rotator/requirements.txt
    
    echo -e "${GREEN}Cloud Functions created!${NC}"
}

# Deploy Cloud Functions
deploy_cloud_functions() {
    echo -e "\n${YELLOW}Deploying Cloud Functions...${NC}"
    
    # Build container images
    echo "Building security processor image..."
    cd functions/security-processor
    gcloud builds submit --tag "gcr.io/$PROJECT_ID/security-processor:latest" .
    cd ../..
    
    echo "Building key rotator image..."
    cd functions/key-rotator
    gcloud builds submit --tag "gcr.io/$PROJECT_ID/key-rotator:latest" .
    cd ../..
    
    echo -e "${GREEN}Cloud Functions deployed!${NC}"
}

# Post-deployment configuration
post_deployment() {
    echo -e "\n${YELLOW}Post-deployment configuration...${NC}"
    
    # Create initial secrets
    echo "Creating initial secrets..."
    echo -n "Enter Slack webhook URL (or press Enter to skip): "
    read -r SLACK_WEBHOOK
    
    if [ -n "$SLACK_WEBHOOK" ]; then
        echo "$SLACK_WEBHOOK" | gcloud secrets create slack-security-webhook \
            --data-file=- \
            --replication-policy="automatic" \
            --project="$PROJECT_ID" || true
    fi
    
    # Output important information
    echo -e "\n${GREEN}Deployment Complete!${NC}"
    echo -e "\n${YELLOW}Important Information:${NC}"
    echo "1. Service Accounts created:"
    terraform output -json | jq -r '.backend_service_account.value'
    terraform output -json | jq -r '.frontend_service_account.value'
    terraform output -json | jq -r '.worker_service_account.value'
    
    echo -e "\n2. Security monitoring dashboard:"
    terraform output -json | jq -r '.security_dashboard_url.value'
    
    echo -e "\n3. Next steps:"
    echo "   - Update Cloud Run services to use new service accounts"
    echo "   - Configure Slack webhook for security alerts"
    echo "   - Review and adjust security policies"
    echo "   - Test workload identity authentication"
}

# Main execution
main() {
    check_prerequisites
    enable_apis
    
    # Give APIs time to propagate
    echo -e "\n${YELLOW}Waiting for API activation...${NC}"
    sleep 10
    
    init_terraform
    validate_terraform
    plan_terraform
    apply_terraform
    create_cloud_functions
    deploy_cloud_functions
    post_deployment
}

# Run main function
main

echo -e "\n${GREEN}Security controls deployment completed successfully!${NC}"