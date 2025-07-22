# Lucky Gas Infrastructure as Code

This directory contains Terraform configurations for provisioning Lucky Gas infrastructure on Google Cloud Platform.

## Prerequisites

1. Install Terraform (>= 1.0)
2. Install Google Cloud SDK (`gcloud`)
3. Authenticate with Google Cloud:
   ```bash
   gcloud auth application-default login
   ```
4. Create GCS bucket for Terraform state (production only):
   ```bash
   gsutil mb -p YOUR_PROJECT_ID gs://YOUR_PROJECT_ID-terraform-state
   ```

## Directory Structure

```
terraform/
├── main.tf                 # Main configuration and providers
├── variables.tf            # Variable definitions
├── outputs.tf              # Output values
├── database.tf             # Cloud SQL and Redis configurations
├── storage.tf              # Cloud Storage buckets
├── monitoring.tf           # Monitoring and alerting
├── environments/
│   ├── staging.tfvars      # Staging environment values
│   └── production.tfvars   # Production environment values
└── README.md               # This file
```

## Usage

### Initialize Terraform

For staging:
```bash
terraform init \
  -backend-config="bucket=luckygas-staging-terraform-state" \
  -backend-config="prefix=terraform/state"
```

For production:
```bash
terraform init \
  -backend-config="bucket=luckygas-production-terraform-state" \
  -backend-config="prefix=terraform/state"
```

### Plan Changes

For staging:
```bash
terraform plan -var-file=environments/staging.tfvars
```

For production:
```bash
terraform plan -var-file=environments/production.tfvars
```

### Apply Changes

For staging:
```bash
terraform apply -var-file=environments/staging.tfvars
```

For production:
```bash
terraform apply -var-file=environments/production.tfvars
```

## Resources Created

### Networking
- VPC network with custom subnets
- Cloud NAT for outbound internet access
- Firewall rules for internal communication and health checks
- Private service connection for Cloud SQL and Redis

### Database
- Cloud SQL PostgreSQL instance
- Redis instance for caching
- Automated backups (configurable per environment)
- High availability for production

### Storage
- Media storage bucket for delivery photos
- Backup bucket for database backups
- Terraform state bucket (production only)

### Security
- Service account for application
- IAM roles and permissions
- Secrets stored in Secret Manager

### Monitoring
- Alert policies for error rates, latency, CPU, and memory
- Uptime checks
- Custom dashboard
- Budget alerts

## Environment-Specific Configurations

### Staging
- Smaller instance sizes (cost-optimized)
- Basic tier Redis
- 7-day backup retention
- $500 monthly budget alert

### Production
- Larger instance sizes (performance-optimized)
- High availability Redis
- 30-day backup retention
- Point-in-time recovery enabled
- $2000 monthly budget alert

## Important Notes

1. **Deletion Protection**: Production resources have deletion protection enabled. To destroy resources, you must first disable this in the console or update the Terraform configuration.

2. **State Management**: Terraform state contains sensitive information. Ensure the state bucket has proper access controls.

3. **Secrets**: Database passwords are automatically generated and stored in Secret Manager. The application should retrieve them from there.

4. **Costs**: Monitor your GCP billing dashboard. The configurations include budget alerts, but actual costs may vary based on usage.

## Troubleshooting

### API Not Enabled
If you see errors about APIs not being enabled, wait a few minutes after running `terraform apply` as API enablement can take time to propagate.

### Insufficient Permissions
Ensure your service account or user account has the following roles:
- Project Editor
- Security Admin
- Service Networking Admin
- Compute Network Admin

### State Lock
If Terraform state is locked, you can force unlock:
```bash
terraform force-unlock LOCK_ID
```

## Next Steps

After infrastructure is provisioned:

1. Update application configuration with the outputs:
   - Database connection details
   - Redis connection details
   - Storage bucket names
   - Service account email

2. Deploy the application to Cloud Run or GKE

3. Configure DNS records to point to the load balancer

4. Set up continuous deployment pipeline