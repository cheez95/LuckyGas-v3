# Lucky Gas Deployment Guide

## Overview

This guide covers the deployment process for the Lucky Gas delivery management system to Google Cloud Platform.

## Prerequisites

### Required Tools
- Google Cloud SDK (`gcloud`)
- Docker
- Terraform >= 1.0
- Node.js 20.x
- Python 3.11
- uv (Python package manager)

### GCP Setup
1. Create a GCP project
2. Enable required APIs (see `infrastructure/terraform/main.tf`)
3. Create service accounts with appropriate permissions
4. Set up billing

### Environment Variables
```bash
export GCP_PROJECT_ID="your-project-id"
export GCP_REGION="asia-east1"
export ENVIRONMENT="production"  # or staging
```

## Infrastructure Deployment

### 1. Initialize Terraform
```bash
cd infrastructure/terraform
terraform init
```

### 2. Plan Infrastructure
```bash
# For staging
terraform plan -var-file="../environments/staging.tfvars"

# For production
terraform plan -var-file="../environments/production.tfvars"
```

### 3. Apply Infrastructure
```bash
# For staging
terraform apply -var-file="../environments/staging.tfvars"

# For production
terraform apply -var-file="../environments/production.tfvars"
```

### 4. Note Outputs
```bash
terraform output
```
Save the following:
- Load balancer IP
- Database connection string
- Redis host

## Application Deployment

### 1. Configure DNS
Point your domain to the load balancer IP:
- `app.luckygas.tw` ’ Load Balancer IP
- `www.luckygas.tw` ’ Load Balancer IP

### 2. Set up Secrets
```bash
# Database password
gcloud secrets create database-password --data-file=-
# Enter password and press Ctrl+D

# JWT secret
gcloud secrets create jwt-secret-key --data-file=-
# Enter secret and press Ctrl+D

# Other secrets
gcloud secrets create google-api-key --data-file=-
gcloud secrets create sentry-dsn --data-file=-
```

### 3. Deploy Application
```bash
# Using the deployment script
./scripts/deploy.sh

# Or manually
docker build -t backend ./backend
docker build -t frontend ./frontend
# Push to Artifact Registry and deploy to Cloud Run
```

### 4. Run Database Migrations
```bash
# Connect to Cloud SQL
gcloud sql connect luckygas-db-production --user=luckygas_app

# Run migrations
cd backend
uv run alembic upgrade head
```

### 5. Import Initial Data
```bash
# Import historical data
cd backend
uv run python -m scripts.import_historical_data
```

## Monitoring Setup

### 1. Install Monitoring Dashboard
```bash
gcloud monitoring dashboards create --config-from-file=infrastructure/monitoring/dashboard.yaml
```

### 2. Create Alert Policies
```bash
# Apply alert policies
gcloud alpha monitoring policies create --policy-from-file=infrastructure/monitoring/alerts.yaml
```

### 3. Configure Sentry
1. Create a Sentry project at https://sentry.io
2. Get the DSN
3. Update the secret:
```bash
gcloud secrets versions add sentry-dsn --data-file=-
# Enter DSN and press Ctrl+D
```

## CI/CD Setup

### 1. GitHub Secrets
Add the following secrets to your GitHub repository:
- `GCP_PROJECT_ID`: Your GCP project ID
- `GCP_SA_KEY`: Service account key JSON
- `SLACK_WEBHOOK_URL`: For notifications (optional)

### 2. Enable GitHub Actions
The workflows in `.github/workflows/` will automatically:
- Run tests on pull requests
- Deploy to staging on push to `develop`
- Deploy to production on push to `main`

## Rollout Strategy

### Staging Deployment
1. Deploy to staging environment first
2. Run smoke tests
3. Perform user acceptance testing
4. Monitor for 24 hours

### Production Deployment
1. Deploy during low-traffic hours (2-4 AM Taiwan time)
2. Use gradual rollout (10% ’ 50% ’ 100%)
3. Monitor metrics closely
4. Have rollback plan ready

### Rollback Procedure
```bash
# Automatic rollback to previous version
./scripts/rollback.sh

# Rollback to specific version
./scripts/rollback.sh abc123
```

## Post-Deployment

### 1. Verify Services
- Frontend: https://app.luckygas.tw
- API Health: https://app.luckygas.tw/api/v1/health
- WebSocket: wss://app.luckygas.tw/ws

### 2. Test Critical Flows
- User authentication
- Order creation
- Route optimization
- Real-time updates
- Payment processing

### 3. Monitor Performance
- Check dashboard for errors
- Verify response times < 200ms
- Ensure no memory leaks
- Monitor WebSocket connections

### 4. Enable Backups
```bash
# Verify automated backups are running
gcloud sql backups list --instance=luckygas-db-production
```

## Troubleshooting

### Common Issues

#### 1. Cloud Run Service Not Starting
- Check logs: `gcloud run services logs read luckygas-backend`
- Verify environment variables
- Check health endpoint

#### 2. Database Connection Failed
- Verify VPC connector
- Check Cloud SQL proxy
- Validate credentials

#### 3. WebSocket Not Connecting
- Check CORS settings
- Verify WebSocket upgrade headers
- Check Redis connection

#### 4. High Response Times
- Review Cloud Run scaling settings
- Check database query performance
- Analyze APM traces

### Debug Commands
```bash
# View service logs
gcloud logging read "resource.type=cloud_run_revision"

# Check service status
gcloud run services describe luckygas-backend --region=asia-east1

# Database connections
gcloud sql operations list --instance=luckygas-db-production

# Redis status
gcloud redis instances describe luckygas-redis-production --region=asia-east1
```

## Maintenance

### Regular Tasks
- **Daily**: Check monitoring dashboard
- **Weekly**: Review error logs, update dependencies
- **Monthly**: Security patches, performance review
- **Quarterly**: Disaster recovery drill

### Scaling Considerations
- Monitor active instance count
- Adjust min/max instances based on traffic
- Consider regional expansion for growth
- Plan for database read replicas if needed

## Security Checklist
- [ ] All secrets in Secret Manager
- [ ] HTTPS enforced
- [ ] WAF rules configured
- [ ] Database encryption enabled
- [ ] Backup encryption enabled
- [ ] Audit logging enabled
- [ ] Identity-Aware Proxy configured
- [ ] Least privilege IAM roles

## Support

For deployment issues:
1. Check logs and monitoring
2. Consult troubleshooting guide
3. Contact DevOps team
4. Escalate to GCP support if needed