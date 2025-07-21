# 🚀 Lucky Gas Production Google Cloud Platform Setup Guide

This guide provides comprehensive step-by-step instructions for setting up Google Cloud Platform services for Lucky Gas production deployment. Follow these instructions carefully to ensure a secure and properly configured environment.

## 📋 Prerequisites

Before starting, ensure you have:
- Google Cloud account with billing enabled
- `gcloud` CLI installed and configured
- Project Owner or Editor role in GCP
- Access to Lucky Gas GitHub repository
- Terminal/command line access

## 🏗️ Project Setup

### 1. Create New GCP Project

```bash
# Set project name variable
export PROJECT_ID="vast-tributary-466619-m8"
export PROJECT_NAME="Lucky Gas Prod"

# Create the project
gcloud projects create $PROJECT_ID --name="$PROJECT_NAME"

# Set as current project
gcloud config set project $PROJECT_ID

# Link billing account (replace with your billing account ID)
gcloud beta billing projects link $PROJECT_ID --billing-account=011479-B04C2D-B0F925

# Enable required APIs upfront
gcloud services enable \
    compute.googleapis.com \
    cloudresourcemanager.googleapis.com \
    iam.googleapis.com
```

## 📑 Story 1: Service Account Configuration [GCP-SETUP-01]

### 1.1 Create Production Service Account

```bash
# Create service account
gcloud iam service-accounts create lucky-gas-prod \
    --display-name="Lucky Gas Production Service Account" \
    --description="Service account for Lucky Gas production services"

# Set service account email variable
export SERVICE_ACCOUNT_EMAIL="lucky-gas-prod@${PROJECT_ID}.iam.gserviceaccount.com"
```

### 1.2 Assign Minimal IAM Roles

Following the principle of least privilege, assign only necessary roles:

```bash
# Routes API Viewer (for route optimization)
gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="serviceAccount:${SERVICE_ACCOUNT_EMAIL}" \
    --role="roles/routes.viewer"

# Vertex AI User (for predictions)
gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="serviceAccount:${SERVICE_ACCOUNT_EMAIL}" \
    --role="roles/aiplatform.user"

# Storage Object Admin (bucket-specific, will be refined later)
# Note: This will be scoped to specific bucket only
gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="serviceAccount:${SERVICE_ACCOUNT_EMAIL}" \
    --role="roles/storage.objectAdmin" \
    --condition="expression=resource.name.startsWith('projects/_/buckets/lucky-gas-storage/'),title=lucky-gas-bucket-only,description=Access only to lucky-gas-storage bucket"

# Secret Manager Secret Accessor
gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="serviceAccount:${SERVICE_ACCOUNT_EMAIL}" \
    --role="roles/secretmanager.secretAccessor"

# Cloud SQL Client (for database access)
gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="serviceAccount:${SERVICE_ACCOUNT_EMAIL}" \
    --role="roles/cloudsql.client"
```

### 1.3 Generate and Secure Service Account Key

```bash
# Create keys directory
mkdir -p ~/.gcp/lucky-gas

# Generate key
gcloud iam service-accounts keys create \
    ~/.gcp/lucky-gas/lucky-gas-prod-key.json \
    --iam-account=$SERVICE_ACCOUNT_EMAIL

# Set restrictive permissions
chmod 600 ~/.gcp/lucky-gas/lucky-gas-prod-key.json

# Create backup
cp ~/.gcp/lucky-gas/lucky-gas-prod-key.json \
   ~/.gcp/lucky-gas/lucky-gas-prod-key-backup-$(date +%Y%m%d).json
```

### 1.4 Configure Workload Identity (Optional - for GKE)

If using Google Kubernetes Engine:

```bash
# Enable Workload Identity on cluster
gcloud container clusters update lucky-gas-cluster \
    --workload-pool=${PROJECT_ID}.svc.id.goog

# Create Kubernetes service account
kubectl create serviceaccount lucky-gas-ksa \
    --namespace default

# Bind to GCP service account
gcloud iam service-accounts add-iam-policy-binding \
    $SERVICE_ACCOUNT_EMAIL \
    --role roles/iam.workloadIdentityUser \
    --member "serviceAccount:${PROJECT_ID}.svc.id.goog[default/lucky-gas-ksa]"

# Annotate Kubernetes service account
kubectl annotate serviceaccount lucky-gas-ksa \
    --namespace default \
    iam.gke.io/gcp-service-account=$SERVICE_ACCOUNT_EMAIL
```

### 1.5 Set Up Key Rotation Policy

Create a rotation script:

```bash
cat > ~/rotate-service-key.sh << 'EOF'
#!/bin/bash
# Service Account Key Rotation Script

PROJECT_ID="lucky-gas-prod"
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

chmod +x ~/rotate-service-key.sh

# Schedule rotation (add to crontab for 90-day rotation)
echo "0 0 1 */3 * $HOME/rotate-service-key.sh" | crontab -
```

## 🔧 Story 2: API Services Setup [GCP-SETUP-02]

### 2.1 Enable Required APIs and Set Quotas

```bash
# Enable all required APIs
gcloud services enable \
    routes.googleapis.com \
    aiplatform.googleapis.com \
    storage-component.googleapis.com \
    secretmanager.googleapis.com \
    cloudresourcemanager.googleapis.com \
    monitoring.googleapis.com \
    logging.googleapis.com \
    cloudbilling.googleapis.com

# Configure Routes API quota (via console as quotas need approval)
echo "Manual step required:"
echo "1. Go to https://console.cloud.google.com/apis/api/routes.googleapis.com/quotas"
echo "2. Set 'Requests per minute' to 600 (10 requests/second)"
echo "3. Submit quota increase request if needed"

# Note: Vertex AI quotas are managed automatically based on usage
```

### 2.2 Configure Vertex AI Endpoint

```bash
# Set up Vertex AI
export REGION="asia-east1"  # Taiwan region

# Create Vertex AI dataset (if needed for custom models)
# For now, we'll use pre-built models

# Initialize Vertex AI
gcloud ai platform operations list --region=$REGION
```

### 2.3 Set Up Cloud Storage Buckets

```bash
# Create main storage bucket
gsutil mb -p $PROJECT_ID -c STANDARD -l $REGION gs://lucky-gas-storage/

# Create folders structure
gsutil -m mkdir -p \
    gs://lucky-gas-storage/uploads/ \
    gs://lucky-gas-storage/exports/ \
    gs://lucky-gas-storage/backups/ \
    gs://lucky-gas-storage/ml-models/

# Set bucket-level IAM policy
gsutil iam ch serviceAccount:${SERVICE_ACCOUNT_EMAIL}:objectAdmin gs://lucky-gas-storage

# Enable versioning for backups
gsutil versioning set on gs://lucky-gas-storage

# Set lifecycle rules
cat > lifecycle.json << 'EOF'
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

gsutil lifecycle set lifecycle.json gs://lucky-gas-storage
```

### 2.4 Configure API Key Restrictions

```bash
# Create API key for frontend (restricted)
gcloud alpha services api-keys create lucky-gas-web-key \
    --display-name="Lucky Gas Web Application" \
    --restrictions="browserKeyRestrictions={allowedReferrers=['https://luckygas.com/*','https://*.luckygas.com/*']}" \
    --allowed-ips="0.0.0.0/0" \
    --api-target="service=routes.googleapis.com"

# Store API key securely
echo "Store the generated API key in Secret Manager:"
gcloud secrets create lucky-gas-web-api-key --data-file=- # Paste key and press Ctrl+D
```

### 2.5 Set Up Cost Alerts and Budgets

```bash
# Create budget alert
gcloud billing budgets create \
    --billing-account=XXXXXX-XXXXXX-XXXXXX \
    --display-name="Lucky Gas Production Budget" \
    --budget-amount=100USD \
    --threshold-rule=percent=50 \
    --threshold-rule=percent=90 \
    --threshold-rule=percent=100 \
    --all-updates-rule \
    --project=$PROJECT_ID

# Create notification channel
cat > notification-channel.json << EOF
{
  "type": "email",
  "displayName": "Lucky Gas Alerts",
  "description": "Budget alerts for Lucky Gas",
  "labels": {
    "email_address": "admin@luckygas.com"
  },
  "enabled": true
}
EOF

# Note: Use Cloud Console to complete notification setup
echo "Complete budget notification setup in Cloud Console:"
echo "https://console.cloud.google.com/billing/budgets"
```

## 🔒 Story 3: Security Configuration [GCP-SETUP-03]

### 3.1 Enable Security Command Center

```bash
# Enable Security Command Center API
gcloud services enable securitycenter.googleapis.com

# Note: Full setup requires Organization-level access
echo "For full Security Command Center setup:"
echo "1. Go to https://console.cloud.google.com/security/command-center"
echo "2. Enable asset discovery"
echo "3. Configure finding notifications"
echo "4. Set up security marks"
```

### 3.2 Configure VPC Service Controls

```bash
# Create VPC Service Perimeter
gcloud access-context-manager perimeters create lucky-gas-prod \
    --title="Lucky Gas Production Perimeter" \
    --resources=projects/$(gcloud config get-value project) \
    --restricted-services=storage.googleapis.com,aiplatform.googleapis.com \
    --access-level=CORP_NETWORK \
    --perimeter-type=regular

# Define access levels
cat > access-level.yaml << EOF
name: accessPolicies/POLICY_ID/accessLevels/CORP_NETWORK
title: Corporate Network Access
basic:
  conditions:
  - ipSubnetworks:
    - "203.0.113.0/24"  # Replace with your corporate IP range
  - devicePolicy:
      requireScreenlock: true
      allowedEncryptionStatuses:
      - ENCRYPTED
EOF

# Apply access level
gcloud access-context-manager levels create CORP_NETWORK \
    --title="Corporate Network Access" \
    --basic-level-spec=access-level.yaml
```

### 3.3 Set Up Cloud Armor Rules

```bash
# Create security policy
gcloud compute security-policies create lucky-gas-prod-policy \
    --description="Lucky Gas production security policy"

# Add rate limiting rule
gcloud compute security-policies rules create 1000 \
    --security-policy=lucky-gas-prod-policy \
    --expression="true" \
    --action=rate-based-ban \
    --rate-limit-threshold-count=50 \
    --rate-limit-threshold-interval-sec=60 \
    --ban-duration-sec=600 \
    --conform-action=allow

# Add geo-blocking rule (allow only from Taiwan and admin countries)
gcloud compute security-policies rules create 2000 \
    --security-policy=lucky-gas-prod-policy \
    --expression="origin.region_code != 'TW' && origin.region_code != 'US'" \
    --action=deny-403

# Add OWASP rules
gcloud compute security-policies rules create 3000 \
    --security-policy=lucky-gas-prod-policy \
    --expression="evaluatePreconfiguredExpr('xss-stable')" \
    --action=deny-403

gcloud compute security-policies rules create 3001 \
    --security-policy=lucky-gas-prod-policy \
    --expression="evaluatePreconfiguredExpr('sqli-stable')" \
    --action=deny-403
```

### 3.4 Enable Audit Logging

```bash
# Create audit config file
cat > audit-config.yaml << EOF
auditConfigs:
- service: allServices
  auditLogConfigs:
  - logType: ADMIN_READ
  - logType: DATA_READ
  - logType: DATA_WRITE
  exemptedMembers:
  - serviceAccount:$SERVICE_ACCOUNT_EMAIL
- service: storage.googleapis.com
  auditLogConfigs:
  - logType: ADMIN_READ
  - logType: DATA_READ
  - logType: DATA_WRITE
- service: secretmanager.googleapis.com
  auditLogConfigs:
  - logType: ADMIN_READ
  - logType: DATA_READ
  - logType: DATA_WRITE
EOF

# Apply audit configuration
gcloud projects set-iam-policy $PROJECT_ID audit-config.yaml

# Create log sink for security events
gcloud logging sinks create security-events \
    storage.googleapis.com/lucky-gas-security-logs \
    --log-filter='protoPayload.@type="type.googleapis.com/google.cloud.audit.AuditLog" AND severity >= WARNING'
```

### 3.5 Configure DLP Policies

```bash
# Enable DLP API
gcloud services enable dlp.googleapis.com

# Create DLP inspection template
cat > dlp-inspect-template.json << EOF
{
  "displayName": "Lucky Gas PII Detection",
  "description": "Detect PII in Lucky Gas data",
  "inspectConfig": {
    "infoTypes": [
      {"name": "TAIWAN_NATIONAL_ID"},
      {"name": "PHONE_NUMBER"},
      {"name": "EMAIL_ADDRESS"},
      {"name": "CREDIT_CARD_NUMBER"},
      {"name": "PERSON_NAME"}
    ],
    "minLikelihood": "POSSIBLE",
    "customInfoTypes": [
      {
        "infoType": {"name": "TAIWAN_PHONE"},
        "regex": {"pattern": "09\\d{2}-?\\d{3}-?\\d{3}|0[2-8]-?\\d{4}-?\\d{4}"}
      }
    ]
  }
}
EOF

# Create inspection template
curl -X POST \
  -H "Authorization: Bearer $(gcloud auth print-access-token)" \
  -H "Content-Type: application/json" \
  -d @dlp-inspect-template.json \
  "https://dlp.googleapis.com/v2/projects/$PROJECT_ID/inspectTemplates"

# Create de-identification template
cat > dlp-deidentify-template.json << EOF
{
  "displayName": "Lucky Gas PII Masking",
  "description": "Mask PII in Lucky Gas data",
  "deidentifyConfig": {
    "infoTypeTransformations": {
      "transformations": [
        {
          "primitiveTransformation": {
            "replaceConfig": {
              "newValue": {"stringValue": "[REDACTED]"}
            }
          },
          "infoTypes": [
            {"name": "TAIWAN_NATIONAL_ID"},
            {"name": "CREDIT_CARD_NUMBER"}
          ]
        },
        {
          "primitiveTransformation": {
            "characterMaskConfig": {
              "maskingCharacter": "*",
              "numberToMask": 4
            }
          },
          "infoTypes": [
            {"name": "PHONE_NUMBER"},
            {"name": "TAIWAN_PHONE"}
          ]
        }
      ]
    }
  }
}
EOF

# Create de-identification template
curl -X POST \
  -H "Authorization: Bearer $(gcloud auth print-access-token)" \
  -H "Content-Type: application/json" \
  -d @dlp-deidentify-template.json \
  "https://dlp.googleapis.com/v2/projects/$PROJECT_ID/deidentifyTemplates"
```

## 📊 Verification Steps

### Verify Service Account

```bash
# Check service account
gcloud iam service-accounts describe $SERVICE_ACCOUNT_EMAIL

# List service account keys
gcloud iam service-accounts keys list --iam-account=$SERVICE_ACCOUNT_EMAIL

# Test authentication
export GOOGLE_APPLICATION_CREDENTIALS="$HOME/.gcp/lucky-gas/lucky-gas-prod-key.json"
gcloud auth application-default print-access-token
```

### Verify API Enablement

```bash
# List enabled APIs
gcloud services list --enabled

# Check specific APIs
gcloud services list --enabled --filter="name:routes.googleapis.com"
gcloud services list --enabled --filter="name:aiplatform.googleapis.com"
```

### Verify Storage Bucket

```bash
# List buckets
gsutil ls

# Check bucket permissions
gsutil iam get gs://lucky-gas-storage

# Test upload
echo "test" > test.txt
gsutil cp test.txt gs://lucky-gas-storage/uploads/
gsutil rm gs://lucky-gas-storage/uploads/test.txt
```

### Verify Security Settings

```bash
# Check audit logs
gcloud logging read "protoPayload.serviceName='storage.googleapis.com'" --limit 10

# List security policies
gcloud compute security-policies list

# Check VPC service controls
gcloud access-context-manager perimeters list
```

## 🔄 Next Steps

1. **Store Credentials Securely**:
   ```bash
   # Upload service account key to Secret Manager
   gcloud secrets create lucky-gas-service-key \
       --data-file=$HOME/.gcp/lucky-gas/lucky-gas-prod-key.json
   ```

2. **Update Application Configuration**:
   ```python
   # backend/.env
   GOOGLE_APPLICATION_CREDENTIALS=/app/secrets/lucky-gas-prod-key.json
   GCP_PROJECT_ID=lucky-gas-prod
   GCP_REGION=asia-east1
   GCS_BUCKET=lucky-gas-storage
   ```

3. **Test Integration**:
   ```bash
   cd backend
   uv run python -c "from google.cloud import storage; client = storage.Client(); print('GCS Connected!')"
   ```

4. **Monitor Usage**:
   - Check billing dashboard: https://console.cloud.google.com/billing
   - Review API usage: https://console.cloud.google.com/apis/dashboard
   - Monitor security: https://console.cloud.google.com/security/command-center

## 🚨 Important Security Notes

1. **Never commit service account keys to Git**
2. **Rotate keys every 90 days**
3. **Use Workload Identity in production Kubernetes**
4. **Enable 2FA for all Google Cloud accounts**
5. **Review IAM permissions quarterly**
6. **Monitor audit logs for suspicious activity**
7. **Use VPN or Cloud Interconnect for production access**

## 📞 Support Contacts

- GCP Support: https://cloud.google.com/support
- Lucky Gas DevOps Team: devops@luckygas.com
- Security Issues: security@luckygas.com

---

**Document Version**: 1.0  
**Last Updated**: 2025-07-22  
**Author**: Lucky Gas DevOps Team