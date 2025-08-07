# Lucky Gas Google Cloud Security Controls

This directory contains the complete implementation of Epic 7 Story 2: Security & Access Controls for the Lucky Gas delivery management system.

## Overview

The security implementation provides enterprise-grade protection for the Lucky Gas Google Cloud infrastructure through:

1. **Workload Identity** - Eliminates service account keys
2. **VPC Service Controls** - Creates security perimeters around APIs
3. **Security Command Center** - Continuous security monitoring
4. **Automated Key Rotation** - 30-day rotation for remaining keys
5. **Least Privilege IAM** - Minimal permissions for all services

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     Security Architecture                     │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  ┌─────────────┐     ┌──────────────┐    ┌───────────────┐  │
│  │   Cloud     │     │   Workload   │    │     VPC       │  │
│  │    Run      │────▶│   Identity   │────│   Service     │  │
│  │  Services   │     │  (No Keys!)  │    │   Controls    │  │
│  └─────────────┘     └──────────────┘    └───────────────┘  │
│         │                                          │          │
│         ▼                                          ▼          │
│  ┌─────────────┐     ┌──────────────┐    ┌───────────────┐  │
│  │   Security  │     │     Key      │    │     Least     │  │
│  │   Command   │────▶│   Rotation   │────│   Privilege   │  │
│  │   Center    │     │ (Automated)  │    │     IAM       │  │
│  └─────────────┘     └──────────────┘    └───────────────┘  │
│                                                               │
└─────────────────────────────────────────────────────────────┘
```

## Components

### 1. Workload Identity (`workload-identity.tf`)

Provides Google-managed identities for Cloud Run services:

- **Backend Service Account**: `lucky-gas-backend@{project}.iam.gserviceaccount.com`
- **Frontend Service Account**: `lucky-gas-frontend@{project}.iam.gserviceaccount.com`
- **Worker Service Account**: `lucky-gas-worker@{project}.iam.gserviceaccount.com`

Benefits:
- No service account keys to manage
- Automatic credential rotation
- Enhanced security through Google-managed identity

### 2. VPC Service Controls (`vpc-service-controls.tf`)

Creates a security perimeter around sensitive APIs:

- **Protected APIs**: Vertex AI, Cloud Storage, Secret Manager, Cloud SQL, Routes API
- **Access Controls**: IP allowlisting, service account restrictions, regional limits
- **Network Security**: Private Google Access, Cloud NAT, firewall rules
- **Cloud Armor**: DDoS protection, rate limiting, geo-blocking

### 3. Security Command Center (`security-command-center.tf`)

Continuous security monitoring and threat detection:

- **Vulnerability Scanning**: Automatic container and web scanning
- **Security Findings**: Real-time alerts for HIGH/CRITICAL issues
- **Binary Authorization**: Ensures only approved containers run
- **Alert Processing**: Automated Slack notifications for security events

### 4. Key Rotation (`key-rotation.tf`)

Automated rotation for any remaining service account keys:

- **30-Day Rotation**: Automatic monthly key rotation
- **Secret Manager Storage**: Secure key storage with versioning
- **Audit Trail**: Complete history in BigQuery
- **Monitoring**: Alerts for rotation failures or old keys

### 5. Least Privilege IAM (`least-privilege-iam.tf`)

Minimal permissions for maximum security:

- **Custom IAM Roles**: Service-specific minimal permissions
- **Time-Limited Access**: Developer access expires after 8 hours
- **Organization Policies**: Enforced security standards
- **Comprehensive Audit Logging**: All IAM changes logged

## Deployment

### Prerequisites

1. Google Cloud SDK installed and authenticated
2. Terraform installed (version 1.0+)
3. Project Owner permissions
4. Organization ID (for org policies)

### Quick Start

```bash
# Set organization ID (optional but recommended)
export ORGANIZATION_ID=your-org-id

# Run the deployment script
./deploy-security.sh
```

### Manual Deployment

```bash
# 1. Enable required APIs
gcloud services enable \
    securitycenter.googleapis.com \
    containeranalysis.googleapis.com \
    binaryauthorization.googleapis.com \
    accesscontextmanager.googleapis.com \
    cloudscheduler.googleapis.com \
    secretmanager.googleapis.com

# 2. Initialize Terraform
terraform init

# 3. Plan deployment
terraform plan -out=security.tfplan

# 4. Apply configuration
terraform apply security.tfplan

# 5. Deploy Cloud Functions
cd functions/security-processor
gcloud builds submit --tag gcr.io/$PROJECT_ID/security-processor:latest

cd ../key-rotator
gcloud builds submit --tag gcr.io/$PROJECT_ID/key-rotator:latest
```

## Configuration

### Required Variables

Create a `terraform.tfvars` file:

```hcl
project_id      = "vast-tributary-466619-m8"
region          = "asia-east1"
organization_id = "your-org-id"  # Optional but recommended
```

### Slack Integration

To receive security alerts in Slack:

1. Create a Slack webhook URL
2. Store it in Secret Manager:
```bash
echo -n "https://hooks.slack.com/services/YOUR/WEBHOOK/URL" | \
  gcloud secrets create slack-security-webhook --data-file=-
```

### Customization

#### Adjust Security Policies

Edit VPC Service Controls in `vpc-service-controls.tf`:
```hcl
# Add your office IP ranges
ip_subnetworks = [
  "203.0.113.0/24",  # Your office IP range
]
```

#### Modify Alert Thresholds

Edit alert policies in `security-command-center.tf`:
```hcl
threshold_value = 5  # Adjust based on your tolerance
```

## Monitoring

### Security Dashboards

1. **Security Command Center**: [Console Link](https://console.cloud.google.com/security/command-center)
2. **IAM Activity Dashboard**: View IAM changes and access patterns
3. **Security Metrics**: Custom dashboard with key security indicators

### Key Metrics

- Failed authentication attempts
- Service account key age
- Security findings by severity
- VPC Service Control violations
- API quota usage

### Alerts

Configured alerts include:
- High/Critical security findings
- Key rotation failures  
- Service account keys older than 45 days
- Multiple unauthorized access attempts
- VPC perimeter violations

## Testing

### Verify Workload Identity

```bash
# Deploy a test Cloud Run service
gcloud run deploy test-workload-identity \
  --image=gcr.io/cloudrun/hello \
  --service-account=lucky-gas-backend@$PROJECT_ID.iam.gserviceaccount.com \
  --region=asia-east1

# Check logs - should see no key-related errors
gcloud run services logs read test-workload-identity
```

### Test VPC Service Controls

```bash
# Try to access protected API from outside perimeter
# This should fail with permission denied
curl -H "Authorization: Bearer $(gcloud auth print-access-token)" \
  https://storage.googleapis.com/storage/v1/b/lucky-gas-storage
```

### Verify Key Rotation

```bash
# Trigger manual key rotation
gcloud scheduler jobs run lucky-gas-key-rotation --location=asia-east1

# Check Secret Manager for new versions
gcloud secrets versions list lucky-gas-backend-service-key
```

## Troubleshooting

### Common Issues

1. **API not enabled error**
   ```bash
   gcloud services enable {api-name}.googleapis.com
   ```

2. **Insufficient permissions**
   - Ensure you have Project Owner role
   - For org policies, need Organization Admin

3. **VPC Service Controls blocking legitimate traffic**
   - Check access levels and add exceptions
   - Review Cloud Logging for detailed errors

4. **Key rotation failing**
   - Check Cloud Run logs for the key-rotator service
   - Verify Secret Manager permissions

### Debug Commands

```bash
# View security findings
gcloud scc findings list $ORGANIZATION_ID --source=$SOURCE_ID

# Check VPC Service Controls
gcloud access-context-manager perimeters list

# View key rotation logs
gcloud logging read "resource.type=cloud_run_revision AND resource.labels.service_name=lucky-gas-key-rotator"

# List service account keys
gcloud iam service-accounts keys list --iam-account=lucky-gas-backend@$PROJECT_ID.iam.gserviceaccount.com
```

## Security Best Practices

1. **Never disable Workload Identity** - It's more secure than keys
2. **Review access logs weekly** - Look for anomalies
3. **Keep VPC Service Controls updated** - Add new services as needed
4. **Respond to security alerts promptly** - High/Critical within 1 hour
5. **Rotate break-glass credentials** - Even if unused

## Compliance

This implementation helps meet:
- **ISO 27001**: Access control, monitoring, audit trails
- **SOC 2**: Security monitoring, least privilege
- **PCI DSS**: Network segmentation, access control
- **GDPR**: Data access logging, security measures

## Cost Estimates

Monthly costs (approximate):
- Security Command Center: $0 (included with GCP)
- VPC Service Controls: $0 (no additional cost)
- Cloud Run (security processors): ~$5-10
- Secret Manager: ~$1-2
- Monitoring/Logging: ~$10-20
- **Total**: ~$20-35/month

## Support

For security issues:
1. Check security alerts in Slack
2. Review Security Command Center console
3. Contact: security@luckygas.com.tw
4. Emergency: Use break-glass procedure

## Next Steps

1. ✅ Deploy security controls
2. ⬜ Configure Slack webhooks
3. ⬜ Test all security features
4. ⬜ Train team on security procedures
5. ⬜ Schedule security review (quarterly)

---

**Last Updated**: 2024-01-22
**Version**: 1.0.0
**Status**: Ready for Deployment