# Lucky Gas Infrastructure Setup Documentation

## Overview

This document outlines the infrastructure setup for Lucky Gas, including staging environment configuration, secrets management, Terraform infrastructure as code, and monitoring with Google Cloud.

## 🔧 Infrastructure Components

### 1. Environment Configuration

#### Staging Environment (`.env.staging`)
- Configured for staging-specific settings
- Uses Cloud SQL and MemoryStore for data persistence
- Reduced resource allocation for cost optimization
- Staging-specific domains and CORS configuration

#### Environment-Based Loading
The application automatically loads the appropriate `.env` file based on the `ENVIRONMENT` variable:
- Development: `.env`
- Staging: `.env.staging`
- Production: `.env.production`

### 2. Secrets Management

#### Google Secret Manager Integration (`app/core/secrets_manager.py`)
- Centralized secrets management using Google Secret Manager
- Automatic fallback to environment variables for local development
- Caching for improved performance
- Support for both string and JSON secrets

#### Key Features:
- **Automatic Loading**: Secrets are loaded from Secret Manager in staging/production
- **Local Development**: Falls back to environment variables
- **Security**: No secrets stored in code or configuration files
- **Audit Trail**: All secret access is logged

#### Managing Secrets:
```bash
# Create default secrets for staging
python infrastructure/scripts/manage_secrets.py create --project luckygas-staging

# Migrate from env file
python infrastructure/scripts/manage_secrets.py migrate --project luckygas-staging --env-file .env.staging

# List all secrets
python infrastructure/scripts/manage_secrets.py list --project luckygas-staging

# Update a specific secret
python infrastructure/scripts/manage_secrets.py update --project luckygas-staging --secret staging-database-password
```

### 3. Terraform Infrastructure as Code

#### Directory Structure:
```
infrastructure/terraform/
├── main.tf                 # Core infrastructure and providers
├── variables.tf            # Variable definitions
├── database.tf             # Cloud SQL and Redis
├── storage.tf              # Cloud Storage buckets
├── monitoring.tf           # Monitoring and alerts
├── outputs.tf              # Output values
├── environments/
│   ├── staging.tfvars      # Staging configuration
│   └── production.tfvars   # Production configuration
```

#### Key Resources:
1. **Networking**
   - Custom VPC with private subnets
   - Cloud NAT for outbound access
   - Firewall rules for security

2. **Database**
   - Cloud SQL PostgreSQL (with automatic backups)
   - Redis for caching
   - Private IP connectivity

3. **Storage**
   - Media bucket for delivery photos
   - Backup bucket for database backups
   - Lifecycle policies for cost optimization

4. **Security**
   - Service accounts with minimal permissions
   - Secrets stored in Secret Manager
   - IAM roles following principle of least privilege

5. **Monitoring**
   - Custom metrics and dashboards
   - Alert policies for critical issues
   - Budget alerts for cost control

#### Deployment:
```bash
# Initialize Terraform
terraform init -backend-config="bucket=luckygas-staging-terraform-state"

# Plan changes
terraform plan -var-file=environments/staging.tfvars

# Apply changes
terraform apply -var-file=environments/staging.tfvars
```

### 4. Google Cloud Monitoring

#### Metrics Collection (`infrastructure/monitoring/metrics_config.py`)
- Integration with Prometheus metrics
- Custom Google Cloud metrics
- Business KPI tracking
- Cost monitoring for Google APIs

#### Key Metrics:
1. **Business Metrics**
   - Orders created
   - Deliveries completed
   - Revenue tracking
   - Route optimization performance

2. **Technical Metrics**
   - API request latency
   - Error rates
   - Cache hit rates
   - Database performance

3. **Cost Metrics**
   - Google API usage and costs
   - Resource utilization
   - Budget tracking

#### Monitoring Setup:
```bash
# Set up monitoring dashboards and alerts
python infrastructure/monitoring/setup_monitoring.py \
  --project luckygas-staging \
  --emails admin@luckygas.tw devops@luckygas.tw
```

#### Dashboards Created:
1. **SLO Dashboard**: Service level objectives and error budgets
2. **Business Metrics**: Orders, revenue, deliveries
3. **Cost Monitoring**: API usage and costs

#### Alert Policies:
- High error rate (>5%)
- High latency (p95 > 1s)
- Database CPU/Memory usage
- Route optimization timeouts
- Low prediction accuracy
- High API costs

## 🚀 Quick Start

### 1. Prerequisites
- Google Cloud SDK installed and authenticated
- Terraform >= 1.0
- Python 3.12+
- Appropriate GCP permissions

### 2. Initial Setup
```bash
# Set up GCP project
export GCP_PROJECT_ID="luckygas-staging"
gcloud config set project $GCP_PROJECT_ID

# Enable required APIs
gcloud services enable compute.googleapis.com \
  sqladmin.googleapis.com \
  redis.googleapis.com \
  secretmanager.googleapis.com \
  monitoring.googleapis.com

# Create Terraform state bucket
gsutil mb -p $GCP_PROJECT_ID gs://$GCP_PROJECT_ID-terraform-state
```

### 3. Deploy Infrastructure
```bash
cd infrastructure/terraform

# Initialize
terraform init -backend-config="bucket=$GCP_PROJECT_ID-terraform-state"

# Deploy
terraform apply -var-file=environments/staging.tfvars
```

### 4. Configure Secrets
```bash
cd ../..

# Create secrets
python infrastructure/scripts/manage_secrets.py create --project $GCP_PROJECT_ID

# Or migrate from env file
python infrastructure/scripts/manage_secrets.py migrate \
  --project $GCP_PROJECT_ID \
  --env-file .env.staging
```

### 5. Set Up Monitoring
```bash
python infrastructure/monitoring/setup_monitoring.py \
  --project $GCP_PROJECT_ID \
  --emails your-email@example.com
```

### 6. Update Application Configuration
After infrastructure deployment, update your application configuration with:
- Database connection string from Terraform outputs
- Redis connection details
- Storage bucket names
- Service account credentials

## 📊 Monitoring and Observability

### Accessing Dashboards
1. Go to [Google Cloud Console](https://console.cloud.google.com)
2. Navigate to Monitoring > Dashboards
3. View custom dashboards:
   - Lucky Gas - SLO Dashboard
   - Lucky Gas - Business Metrics
   - Lucky Gas - Cost Monitoring

### Viewing Metrics
- Prometheus metrics: Available at `/metrics` endpoint
- Cloud Monitoring: Available in GCP Console
- Custom metrics: Under `custom.googleapis.com/luckygas/` namespace

### Alert Management
- Alerts are sent to configured email addresses
- View alert policies in Monitoring > Alerting
- Adjust thresholds in `monitoring.tf` as needed

## 🔒 Security Best Practices

1. **Secrets Management**
   - Never commit secrets to git
   - Use Secret Manager for all sensitive data
   - Rotate secrets regularly
   - Audit secret access

2. **Network Security**
   - Use private IPs for databases
   - Implement least-privilege firewall rules
   - Enable VPC Flow Logs for audit

3. **IAM**
   - Use service accounts for applications
   - Grant minimal required permissions
   - Review IAM policies regularly

4. **Monitoring**
   - Set up alerts for security events
   - Monitor failed authentication attempts
   - Track API usage for anomalies

## 📈 Scaling Considerations

### Staging vs Production
- **Staging**: Optimized for cost (smaller instances, basic tiers)
- **Production**: Optimized for performance (larger instances, HA configurations)

### Resource Scaling
- Cloud SQL: Automatic storage scaling enabled
- Redis: Upgrade tier for more memory/HA
- Cloud Run: Automatic scaling based on load

### Cost Optimization
- Use lifecycle policies for storage
- Right-size database instances
- Monitor and optimize API usage
- Set budget alerts

## 🐛 Troubleshooting

### Common Issues

1. **Terraform State Lock**
   ```bash
   terraform force-unlock LOCK_ID
   ```

2. **API Not Enabled**
   - Wait a few minutes after enabling
   - Check project billing is enabled

3. **Secret Manager Access**
   - Ensure service account has `secretmanager.secretAccessor` role
   - Check GOOGLE_APPLICATION_CREDENTIALS is set

4. **Monitoring Not Working**
   - Verify GCP_PROJECT_ID is set
   - Check service account permissions
   - Ensure monitoring API is enabled

### Support
For infrastructure issues:
1. Check Terraform logs
2. Review GCP audit logs
3. Check monitoring dashboards
4. Contact DevOps team

## Next Steps

1. **Application Deployment**: Deploy the Lucky Gas application to Cloud Run
2. **DNS Configuration**: Set up custom domains
3. **SSL Certificates**: Configure managed SSL certificates
4. **CI/CD Pipeline**: Set up automated deployments
5. **Backup Strategy**: Implement and test backup procedures
6. **Disaster Recovery**: Document and test DR procedures