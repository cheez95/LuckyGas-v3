# Epic 7 Story 2: Security & Access Controls Implementation

This directory contains the implementation of advanced security controls for the Lucky Gas Google Cloud Platform infrastructure.

## Overview

The security controls implemented in this story include:

1. **Workload Identity for Cloud Run** - Eliminates the need for service account keys
2. **VPC Service Controls** - Restricts API access to authorized networks and services
3. **Cloud Security Command Center Integration** - Provides security monitoring and vulnerability scanning
4. **Service Account Key Rotation Automation** - Automatically rotates keys every 30 days
5. **Least Privilege IAM Implementation** - Implements fine-grained permissions

## Prerequisites

- Google Cloud Project: `vast-tributary-466619-m8`
- Terraform >= 1.0
- Google Cloud SDK (gcloud) configured
- Organization ID and Project Number for VPC Service Controls
- Existing service account: `lucky-gas-prod@vast-tributary-466619-m8.iam.gserviceaccount.com`

## Implementation Guide

### 1. Workload Identity Setup

Workload Identity allows Cloud Run services to authenticate as Google Service Accounts without managing keys.

```bash
# Apply Workload Identity configuration
cd infrastructure/security/epic-7-story-2
terraform apply -target=module.workload_identity -var-file=../../environments/production.tfvars
```

Key features:
- Separate service accounts for backend, frontend, and worker services
- No service account keys stored in the application
- Automatic credential management by Google Cloud

### 2. VPC Service Controls

VPC Service Controls create a security perimeter around your Google Cloud resources.

```bash
# Set required variables
export TF_VAR_organization_id="YOUR_ORG_ID"
export TF_VAR_project_number="YOUR_PROJECT_NUMBER"

# Apply VPC Service Controls
terraform apply -target=module.vpc_service_controls -var-file=../../environments/production.tfvars
```

Configuration includes:
- Access levels based on IP ranges, service accounts, and regions
- Service perimeter protecting sensitive APIs
- Private Google Access for all subnets
- Cloud NAT for secure egress

### 3. Security Command Center Integration

Enables comprehensive security monitoring and vulnerability scanning.

```bash
# Apply Security Command Center configuration
terraform apply -target=module.security_command_center -var-file=../../environments/production.tfvars

# Package Cloud Functions
cd functions
zip security-alert-processor.zip security-alert-processor.py requirements.txt
zip key-rotation.zip key-rotation.py requirements.txt
cd ..
```

Features:
- Binary Authorization for container security
- Vulnerability scanning for all containers
- Custom security alerts via Pub/Sub
- Automated remediation for common issues

### 4. Key Rotation Automation

Automatically rotates service account keys based on age.

```bash
# Deploy key rotation automation
terraform apply -target=module.key_rotation -var-file=../../environments/production.tfvars

# Manually trigger rotation (for testing)
gcloud scheduler jobs run service-account-key-rotation --location=asia-east1
```

Rotation process:
1. Checks key age (default: 30 days)
2. Creates new key
3. Stores in Secret Manager
4. Updates applications
5. Deletes old keys after verification

### 5. Least Privilege IAM

Implements custom IAM roles with minimal required permissions.

```bash
# Apply least privilege IAM configuration
terraform apply -target=module.least_privilege_iam -var-file=../../environments/production.tfvars
```

Custom roles created:
- `luckyGasBackendAPI` - Backend service permissions
- `luckyGasFrontendStatic` - Frontend service permissions
- `luckyGasWorkerBatch` - Worker service permissions
- `luckyGasCICDDeploy` - CI/CD deployment permissions

## Configuration Files

### terraform.tfvars Example

```hcl
project_id      = "vast-tributary-466619-m8"
region          = "asia-east1"
environment     = "production"
organization_id = "123456789012"
project_number  = "123456789012"
```

### Environment Variables for Cloud Functions

```bash
# Security Alert Processor
PROJECT_ID=vast-tributary-466619-m8
SLACK_WEBHOOK_SECRET=security-alerts-webhook

# Key Rotation
PROJECT_ID=vast-tributary-466619-m8
KEY_AGE_DAYS=30
NOTIFICATION_TOPIC=projects/vast-tributary-466619-m8/topics/key-rotation-notifications
```

## Security Best Practices

### 1. Service Account Management

- Use Workload Identity instead of service account keys where possible
- If keys are required, use the automated rotation system
- Never commit service account keys to version control
- Use Secret Manager for all sensitive credentials

### 2. Network Security

- All services run within VPC Service Controls perimeter
- Private Google Access enabled for all subnets
- Cloud NAT for controlled egress
- Firewall rules follow least privilege principle

### 3. Monitoring and Alerting

- Security Command Center findings automatically processed
- Critical alerts sent to Slack with @channel mention
- All security events logged to Cloud Logging
- Custom metrics for security KPIs

### 4. Compliance

- Binary Authorization ensures only approved containers run
- Organization policies enforce security standards
- Audit logs capture all IAM and data access
- Asset inventory exported to BigQuery for analysis

## Testing

### Test Workload Identity

```bash
# Deploy a test Cloud Run service
gcloud run deploy test-workload-identity \
  --image=gcr.io/cloudrun/hello \
  --service-account=luckygas-backend-wi@vast-tributary-466619-m8.iam.gserviceaccount.com \
  --region=asia-east1

# Verify no keys are used
gcloud run services describe test-workload-identity --region=asia-east1
```

### Test VPC Service Controls

```bash
# Try to access protected API from outside the perimeter
gsutil ls gs://lucky-gas-storage
# Should fail with "VPC Service Controls" error

# Access from within the perimeter (e.g., from Cloud Run)
# Should succeed
```

### Test Security Alerts

```bash
# Create a test finding
gcloud alpha scc findings create test-finding-001 \
  --organization=$ORGANIZATION_ID \
  --source=$SCC_SOURCE_ID \
  --category=PUBLIC_BUCKET_ACL \
  --resource-name=//storage.googleapis.com/test-bucket

# Check Slack for alert notification
```

### Test Key Rotation

```bash
# List current keys
gcloud iam service-accounts keys list \
  --iam-account=lucky-gas-prod@vast-tributary-466619-m8.iam.gserviceaccount.com

# Trigger rotation
gcloud pubsub topics publish service-account-key-rotation \
  --message='{"service_accounts":["lucky-gas-prod@vast-tributary-466619-m8.iam.gserviceaccount.com"]}'

# Verify new key created and old keys deleted
```

## Monitoring

### Security Dashboards

1. **Service Account Key Age Dashboard**
   - Shows age of all service account keys
   - Alerts when keys approach rotation threshold
   - Tracks rotation success/failure rates

2. **Security Alerts Dashboard**
   - Real-time security findings from Security Command Center
   - Categorized by severity and type
   - Shows remediation status

3. **VPC Service Controls Dashboard**
   - Access attempts blocked by perimeter
   - Authorized access patterns
   - Potential security anomalies

### Alerts

- **Critical Security Finding**: Immediate Slack notification
- **Key Rotation Failure**: Email to security team
- **Privilege Escalation Attempt**: Immediate investigation required
- **VPC Perimeter Violation**: Security team notification

## Troubleshooting

### Workload Identity Issues

```bash
# Check service account binding
gcloud iam service-accounts get-iam-policy luckygas-backend-wi@vast-tributary-466619-m8.iam.gserviceaccount.com

# Verify Cloud Run service account
gcloud run services describe luckygas-backend --region=asia-east1 --format="value(spec.template.spec.serviceAccountName)"
```

### VPC Service Controls Issues

```bash
# Check perimeter configuration
gcloud access-context-manager perimeters describe lucky_gas_perimeter

# Test access levels
gcloud access-context-manager access-levels test-iam-permissions internal_access
```

### Key Rotation Issues

```bash
# Check Cloud Function logs
gcloud functions logs read service-account-key-rotation --limit=50

# Verify Secret Manager access
gcloud secrets versions list sa-key-lucky-gas-prod
```

## Rollback Procedures

### Disable VPC Service Controls

```bash
# Remove resources from perimeter
gcloud access-context-manager perimeters update lucky_gas_perimeter \
  --remove-resources=projects/YOUR_PROJECT_NUMBER
```

### Revert to Service Account Keys

```bash
# Create new key
gcloud iam service-accounts keys create key.json \
  --iam-account=lucky-gas-prod@vast-tributary-466619-m8.iam.gserviceaccount.com

# Update application to use key file
# Update GOOGLE_APPLICATION_CREDENTIALS environment variable
```

### Disable Security Command Center

```bash
# Disable notifications
gcloud scc notification-configs delete high-severity-findings \
  --organization=$ORGANIZATION_ID
```

## Cost Optimization

- VPC Service Controls: No additional cost
- Security Command Center: Free tier available
- Cloud Functions: ~$5/month for rotation and alert processing
- Secret Manager: $0.06 per secret version per month
- Monitoring: Included in free tier for most metrics

## Next Steps

1. Enable additional Security Command Center detectors
2. Implement automated compliance reporting
3. Add more automated remediation rules
4. Integrate with SIEM system
5. Implement security training based on findings

## Support

For issues or questions:
- Create an issue in the repository
- Contact the security team at security@luckygas.tw
- Check Cloud Console logs and monitoring dashboards