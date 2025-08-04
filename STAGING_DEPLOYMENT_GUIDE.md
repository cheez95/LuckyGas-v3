# Lucky Gas V3 Staging Deployment Guide

## Overview

This guide provides comprehensive instructions for deploying Lucky Gas V3 to the Google Cloud Platform staging environment. The staging environment is designed to mirror production as closely as possible while providing a safe space for testing and validation before the pilot launch.

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                    Google Cloud Platform (Staging)                │
├─────────────────────────────────────────────────────────────────┤
│                                                                   │
│  ┌──────────────┐      ┌──────────────┐      ┌──────────────┐  │
│  │  Cloud Run   │      │  Cloud SQL   │      │  Memorystore │  │
│  │  Services    │◀────▶│  PostgreSQL  │      │    Redis     │  │
│  └──────────────┘      └──────────────┘      └──────────────┘  │
│         │                                              ▲          │
│         │                                              │          │
│  ┌──────────────┐                                    │          │
│  │ Load Balancer│                                    │          │
│  │   + CDN      │                                    │          │
│  └──────────────┘                                    │          │
│         │                                              │          │
│    ┌────┴────┐                                        │          │
│    ▼         ▼                                        │          │
│  ┌────┐   ┌────┐                                     │          │
│  │ FE │   │ BE │◀────────────────────────────────────┘          │
│  └────┘   └────┘                                                 │
│                                                                   │
│  ┌──────────────┐      ┌──────────────┐      ┌──────────────┐  │
│  │   Secret     │      │   Storage    │      │  Vertex AI   │  │
│  │   Manager    │      │   Buckets    │      │   & Maps     │  │
│  └──────────────┘      └──────────────┘      └──────────────┘  │
└─────────────────────────────────────────────────────────────────┘
```

## Prerequisites

### 1. Required Tools
- **Google Cloud SDK** (`gcloud`) - [Install Guide](https://cloud.google.com/sdk/docs/install)
- **Docker** - [Install Guide](https://docs.docker.com/get-docker/)
- **Git** - For version control
- **Node.js** (v20+) - For frontend builds
- **Python** (3.11+) with `uv` - For backend

### 2. Access Requirements
- GCP Project Editor or Owner role
- Access to `luckygas-staging` GCP project
- GitHub repository access
- Domain DNS management access (for luckygas.tw)

### 3. Environment Setup
```bash
# Install gcloud if not already installed
curl https://sdk.cloud.google.com | bash
exec -l $SHELL

# Authenticate with Google Cloud
gcloud auth login
gcloud auth application-default login

# Set default project
export GCP_PROJECT_ID=luckygas-staging
gcloud config set project ${GCP_PROJECT_ID}
```

## Pre-Deployment Checklist

- [ ] All tools installed and configured
- [ ] GCP project access verified
- [ ] Domain DNS access available
- [ ] Latest code pulled from repository
- [ ] Environment variables prepared
- [ ] Backup of any existing staging data

## Step 1: Infrastructure Setup

### 1.1 Enable Required APIs
```bash
# Enable all required Google Cloud APIs
gcloud services enable \
    compute.googleapis.com \
    container.googleapis.com \
    sqladmin.googleapis.com \
    redis.googleapis.com \
    secretmanager.googleapis.com \
    cloudbuild.googleapis.com \
    artifactregistry.googleapis.com \
    run.googleapis.com \
    vpcaccess.googleapis.com \
    servicenetworking.googleapis.com \
    dns.googleapis.com \
    monitoring.googleapis.com \
    logging.googleapis.com \
    aiplatform.googleapis.com \
    routes.googleapis.com
```

### 1.2 Create Artifact Registry Repository
```bash
# Create repository for Docker images
gcloud artifacts repositories create luckygas \
    --repository-format=docker \
    --location=asia-east1 \
    --description="Lucky Gas container images"

# Configure Docker authentication
gcloud auth configure-docker asia-east1-docker.pkg.dev
```

### 1.3 Set Up VPC and Networking
```bash
# Create VPC network
gcloud compute networks create luckygas-staging-vpc \
    --subnet-mode=custom \
    --bgp-routing-mode=regional

# Create subnet
gcloud compute networks subnets create luckygas-staging-subnet \
    --network=luckygas-staging-vpc \
    --region=asia-east1 \
    --range=10.0.0.0/24

# Create VPC connector for Cloud Run
gcloud compute networks vpc-access connectors create luckygas-staging-connector \
    --region=asia-east1 \
    --subnet=luckygas-staging-subnet \
    --min-instances=2 \
    --max-instances=10
```

### 1.4 Create Cloud SQL Instance
```bash
# Create Cloud SQL instance
gcloud sql instances create luckygas-staging-db \
    --database-version=POSTGRES_15 \
    --tier=db-g1-small \
    --region=asia-east1 \
    --network=projects/${GCP_PROJECT_ID}/global/networks/luckygas-staging-vpc \
    --no-assign-ip \
    --backup-start-time=03:00 \
    --backup-location=asia-east1 \
    --maintenance-window-day=SUN \
    --maintenance-window-hour=04
```

### 1.5 Create Redis Instance
```bash
# Create Redis instance
gcloud redis instances create luckygas-staging-redis \
    --size=1 \
    --region=asia-east1 \
    --network=projects/${GCP_PROJECT_ID}/global/networks/luckygas-staging-vpc \
    --redis-version=redis_7_0
```

### 1.6 Create Storage Buckets
```bash
# Create main storage bucket
gsutil mb -p ${GCP_PROJECT_ID} -c standard -l asia-east1 \
    gs://luckygas-staging-storage/

# Create backup bucket
gsutil mb -p ${GCP_PROJECT_ID} -c nearline -l asia-east1 \
    gs://luckygas-staging-backups/

# Set lifecycle rules for backup bucket
cat > /tmp/lifecycle.json <<EOF
{
  "lifecycle": {
    "rule": [
      {
        "action": {"type": "SetStorageClass", "storageClass": "COLDLINE"},
        "condition": {"age": 30}
      },
      {
        "action": {"type": "Delete"},
        "condition": {"age": 90}
      }
    ]
  }
}
EOF

gsutil lifecycle set /tmp/lifecycle.json gs://luckygas-staging-backups/
```

## Step 2: Secrets Configuration

### 2.1 Create Service Account
```bash
# Create service account for workload identity
gcloud iam service-accounts create luckygas-staging-workload \
    --display-name="Lucky Gas Staging Workload"

# Grant necessary permissions
export SA_EMAIL=luckygas-staging-workload@${GCP_PROJECT_ID}.iam.gserviceaccount.com

# Add IAM bindings
gcloud projects add-iam-policy-binding ${GCP_PROJECT_ID} \
    --member="serviceAccount:${SA_EMAIL}" \
    --role="roles/cloudsql.client"

gcloud projects add-iam-policy-binding ${GCP_PROJECT_ID} \
    --member="serviceAccount:${SA_EMAIL}" \
    --role="roles/secretmanager.secretAccessor"

gcloud projects add-iam-policy-binding ${GCP_PROJECT_ID} \
    --member="serviceAccount:${SA_EMAIL}" \
    --role="roles/storage.objectAdmin"

gcloud projects add-iam-policy-binding ${GCP_PROJECT_ID} \
    --member="serviceAccount:${SA_EMAIL}" \
    --role="roles/redis.editor"

gcloud projects add-iam-policy-binding ${GCP_PROJECT_ID} \
    --member="serviceAccount:${SA_EMAIL}" \
    --role="roles/aiplatform.user"
```

### 2.2 Create Secrets in Secret Manager
```bash
# Database password
echo -n "$(openssl rand -base64 32)" | \
    gcloud secrets create database-password --data-file=-

# JWT secret key
echo -n "$(openssl rand -base64 64)" | \
    gcloud secrets create jwt-secret-key --data-file=-

# Redis password
echo -n "$(openssl rand -base64 32)" | \
    gcloud secrets create redis-password --data-file=-

# Admin password
echo -n "LuckyGas@Staging2024!" | \
    gcloud secrets create admin-password --data-file=-

# Google Maps API Key (replace with actual key)
echo -n "your-google-maps-api-key" | \
    gcloud secrets create google-maps-api-key --data-file=-

# SMS API credentials (if available)
echo -n "your-sms-api-key" | \
    gcloud secrets create sms-api-key --data-file=-

# E-Invoice credentials (if available)
echo -n "your-einvoice-app-id" | \
    gcloud secrets create einvoice-app-id --data-file=-

echo -n "your-einvoice-api-key" | \
    gcloud secrets create einvoice-api-key --data-file=-
```

## Step 3: Build and Push Docker Images

### 3.1 Build Images
```bash
# Navigate to project root
cd /path/to/LuckyGas-v3

# Make build script executable
chmod +x deployment/scripts/build-staging-images.sh

# Run build script
./deployment/scripts/build-staging-images.sh
```

### 3.2 Verify Images
```bash
# List images in Artifact Registry
gcloud artifacts docker images list \
    asia-east1-docker.pkg.dev/${GCP_PROJECT_ID}/luckygas
```

## Step 4: Database Setup

### 4.1 Initialize Database
```bash
# Make migration script executable
chmod +x deployment/scripts/migrate-staging-database.sh

# Run database migration
./deployment/scripts/migrate-staging-database.sh
```

### 4.2 Verify Database Setup
```bash
# Connect to Cloud SQL instance
gcloud sql connect luckygas-staging-db --user=luckygas_staging

# In psql, verify tables
\dt
\q
```

## Step 5: Deploy Services

### 5.1 Deploy to Cloud Run
```bash
# Make deployment script executable
chmod +x deployment/scripts/deploy-staging-cloudrun.sh

# Deploy services
./deployment/scripts/deploy-staging-cloudrun.sh
```

### 5.2 Configure Domain Mapping
```bash
# The deployment script will output DNS records to configure
# Update your DNS provider with:
# - staging.luckygas.tw → [Cloud Run Frontend IP]
# - staging-api.luckygas.tw → [Cloud Run Backend IP]
```

## Step 6: Post-Deployment Validation

### 6.1 Run Health Checks
```bash
# Make validation script executable
chmod +x deployment/scripts/validate-staging-health.sh

# Run health check validation
./deployment/scripts/validate-staging-health.sh
```

### 6.2 Manual Verification
1. **Frontend Access**: Visit https://staging.luckygas.tw
2. **API Documentation**: Visit https://staging-api.luckygas.tw/docs
3. **Login Test**: Use admin@staging.luckygas.tw with the admin password
4. **Create Test Order**: Verify order creation workflow
5. **Check Maps Integration**: Verify Google Maps loads correctly

## Step 7: Monitoring Setup

### 7.1 Configure Uptime Checks
```bash
# Create uptime checks
gcloud monitoring uptime create https \
    --display-name="Lucky Gas Staging API" \
    --uri="https://staging-api.luckygas.tw/health"

gcloud monitoring uptime create https \
    --display-name="Lucky Gas Staging Frontend" \
    --uri="https://staging.luckygas.tw"
```

### 7.2 Set Up Alerts
```bash
# Create notification channel
gcloud alpha monitoring channels create \
    --display-name="Lucky Gas Staging Alerts" \
    --type=email \
    --channel-labels=email_address=devops@luckygas.tw

# Create alert policies (example for API availability)
gcloud alpha monitoring policies create \
    --notification-channels=[CHANNEL_ID] \
    --display-name="Staging API Unavailable" \
    --condition-display-name="API Health Check Failed" \
    --condition-metric-type="monitoring.googleapis.com/uptime_check/check_passed" \
    --condition-resource-type="uptime_url"
```

## Rollback Procedures

### Emergency Rollback
```bash
# 1. Revert to previous image version
gcloud run services update luckygas-backend-staging \
    --image asia-east1-docker.pkg.dev/${GCP_PROJECT_ID}/luckygas/luckygas-backend:previous-version \
    --region asia-east1

gcloud run services update luckygas-frontend-staging \
    --image asia-east1-docker.pkg.dev/${GCP_PROJECT_ID}/luckygas/luckygas-frontend:previous-version \
    --region asia-east1

# 2. Restore database from backup
gcloud sql backups restore [BACKUP_ID] \
    --restore-instance=luckygas-staging-db
```

### Partial Rollback
```bash
# Roll back only backend
gcloud run services update-traffic luckygas-backend-staging \
    --to-revisions=previous-revision=100 \
    --region asia-east1
```

## Troubleshooting

### Common Issues and Solutions

#### 1. Service Not Starting
```bash
# Check logs
gcloud run logs read --service=luckygas-backend-staging --region=asia-east1

# Check service details
gcloud run services describe luckygas-backend-staging --region=asia-east1
```

#### 2. Database Connection Issues
```bash
# Verify Cloud SQL proxy sidecar
gcloud run revisions describe [REVISION] --region=asia-east1

# Check VPC connector
gcloud compute networks vpc-access connectors describe luckygas-staging-connector \
    --region=asia-east1
```

#### 3. Permission Errors
```bash
# Verify service account permissions
gcloud projects get-iam-policy ${GCP_PROJECT_ID} \
    --flatten="bindings[].members" \
    --filter="bindings.members:luckygas-staging-workload"
```

## Security Checklist

- [ ] All secrets stored in Secret Manager
- [ ] Service accounts use least privilege principle
- [ ] VPC connector configured for private communication
- [ ] SSL/TLS enabled on all endpoints
- [ ] CORS configured correctly
- [ ] Authentication required for admin endpoints
- [ ] Monitoring and alerting configured
- [ ] Backup retention policies set

## Maintenance Tasks

### Daily
- Monitor application logs
- Check uptime status
- Review error rates
- Verify backup completion

### Weekly
- Review resource utilization
- Check for security updates
- Test backup restoration
- Review cost optimization opportunities

### Monthly
- Full security audit
- Performance analysis
- Update dependencies
- Disaster recovery drill

## Support Information

### Internal Contacts
- **DevOps Team**: devops@luckygas.tw
- **Development Team**: dev@luckygas.tw
- **Security Team**: security@luckygas.tw

### External Resources
- [Google Cloud Console](https://console.cloud.google.com)
- [Cloud Run Documentation](https://cloud.google.com/run/docs)
- [Cloud SQL Documentation](https://cloud.google.com/sql/docs)

## Appendix

### Useful Commands
```bash
# View all Cloud Run services
gcloud run services list --region=asia-east1

# Stream logs
gcloud alpha run services logs tail luckygas-backend-staging --region=asia-east1

# Check current traffic allocation
gcloud run services describe luckygas-backend-staging \
    --region=asia-east1 \
    --format="value(spec.traffic)"

# Export environment configuration
gcloud run services export luckygas-backend-staging \
    --region=asia-east1 \
    --format=export > backend-config.yaml
```

### Environment URLs
- **Frontend**: https://staging.luckygas.tw
- **API**: https://staging-api.luckygas.tw
- **API Docs**: https://staging-api.luckygas.tw/docs
- **Health Check**: https://staging-api.luckygas.tw/health

---

**Document Version**: 1.0.0  
**Last Updated**: 2024-01-30  
**Next Review**: 2024-02-30