# LuckyGas Kubernetes Deployment Guide

## Overview

This guide provides comprehensive instructions for deploying the LuckyGas application to Kubernetes using Google Kubernetes Engine (GKE).

## Prerequisites

1. **Tools Installation**:
   ```bash
   # Install gcloud CLI
   curl https://sdk.cloud.google.com | bash
   
   # Install kubectl
   gcloud components install kubectl
   
   # Install kustomize
   curl -s "https://raw.githubusercontent.com/kubernetes-sigs/kustomize/master/hack/install_kustomize.sh" | bash
   
   # Install Terraform
   brew install terraform  # macOS
   ```

2. **GCP Project Setup**:
   - Create GCP project
   - Enable billing
   - Configure gcloud: `gcloud auth login && gcloud config set project <PROJECT_ID>`

3. **Required Permissions**:
   - Kubernetes Engine Admin
   - Service Account Admin
   - Cloud SQL Admin
   - Storage Admin

## Infrastructure Setup

### 1. Create Infrastructure with Terraform

```bash
cd terraform/

# Initialize Terraform
terraform init

# Create workspace for environment
terraform workspace new production

# Review plan
terraform plan \
  -var="project_id=luckygas-production" \
  -var="environment=production" \
  -var="alert_email=ops@luckygas.com.tw"

# Apply infrastructure
terraform apply \
  -var="project_id=luckygas-production" \
  -var="environment=production" \
  -var="alert_email=ops@luckygas.com.tw"
```

### 2. Configure kubectl

```bash
# Get cluster credentials
gcloud container clusters get-credentials luckygas-cluster \
  --zone asia-east1-a \
  --project luckygas-production

# Verify connection
kubectl cluster-info
kubectl get nodes
```

## Application Deployment

### 1. Prepare Secrets

```bash
# Create namespace
kubectl create namespace luckygas

# Create secrets file
cat > k8s/overlays/production/secrets-production.env << EOF
DATABASE_URL=postgresql://user:pass@host:5432/luckygas
SECRET_KEY=your-secret-key
REDIS_PASSWORD=your-redis-password
GOOGLE_APPLICATION_CREDENTIALS_JSON={"type": "service_account", ...}
JWT_SECRET_KEY=your-jwt-secret
EINVOICE_API_KEY=production-einvoice-key
SMS_API_KEY=production-sms-key
EOF

# Create secret in Kubernetes
kubectl create secret generic luckygas-backend-secrets \
  --from-env-file=k8s/overlays/production/secrets-production.env \
  -n luckygas
```

### 2. Build and Push Docker Images

```bash
# Configure Docker for GCR
gcloud auth configure-docker

# Build and push backend
cd backend/
docker build -t gcr.io/luckygas-production/luckygas-backend:v1.0.0 .
docker push gcr.io/luckygas-production/luckygas-backend:v1.0.0

# Build and push frontend
cd ../frontend/
docker build -t gcr.io/luckygas-production/luckygas-frontend:v1.0.0 .
docker push gcr.io/luckygas-production/luckygas-frontend:v1.0.0
```

### 3. Deploy with Kustomize

```bash
# Deploy to production
cd k8s/overlays/production/

# Update image tags
kustomize edit set image \
  gcr.io/luckygas-production/luckygas-backend:v1.0.0 \
  gcr.io/luckygas-production/luckygas-frontend:v1.0.0

# Apply manifests
kustomize build . | kubectl apply -f -

# Wait for rollout
kubectl rollout status deployment --all -n luckygas
```

### 4. Configure Ingress

```bash
# Install cert-manager for SSL
kubectl apply -f https://github.com/cert-manager/cert-manager/releases/download/v1.13.0/cert-manager.yaml

# Create ClusterIssuer for Let's Encrypt
cat <<EOF | kubectl apply -f -
apiVersion: cert-manager.io/v1
kind: ClusterIssuer
metadata:
  name: letsencrypt-prod
spec:
  acme:
    server: https://acme-v02.api.letsencrypt.org/directory
    email: ops@luckygas.com.tw
    privateKeySecretRef:
      name: letsencrypt-prod
    solvers:
    - http01:
        ingress:
          class: nginx
EOF

# Apply ingress
kubectl apply -f k8s/base/ingress.yaml
```

### 5. Configure DNS

```bash
# Get ingress IP
INGRESS_IP=$(kubectl get ingress luckygas-ingress -n luckygas -o jsonpath='{.status.loadBalancer.ingress[0].ip}')
echo "Ingress IP: $INGRESS_IP"

# Update DNS records
# Add A records for:
# - luckygas.com.tw -> $INGRESS_IP
# - www.luckygas.com.tw -> $INGRESS_IP
# - api.luckygas.com.tw -> $INGRESS_IP
```

## Staging Validation (Before Production)

### Run Complete Validation Suite

Before deploying to production, thoroughly validate the staging environment:

```bash
# Navigate to scripts directory
cd k8s/scripts/

# Run all validations
./run-all-validations.sh

# Or run individual validations:
./staging-validation.sh    # Infrastructure and deployment validation
./integration-test.sh      # External service integration tests
./security-scan.sh         # Security vulnerability scanning
./load-test.sh all         # Performance and load testing

# Review results and update staging validation report
# Update /STAGING_VALIDATION_REPORT.md with results
```

### Validation Criteria

All of the following must pass before production deployment:
- ✅ All pods running and healthy
- ✅ All integrations functional (Cloud SQL, Redis, GCS, Vertex AI, etc.)
- ✅ Security scan shows no critical vulnerabilities
- ✅ Load tests meet performance targets (<200ms p95 response time)
- ✅ E2E tests passing
- ✅ SSL certificates valid
- ✅ Monitoring and alerting active

## Post-Deployment Tasks

### 1. Run Database Migrations

```bash
# Get backend pod
BACKEND_POD=$(kubectl get pod -n luckygas -l app.kubernetes.io/name=luckygas-backend -o jsonpath='{.items[0].metadata.name}')

# Run migrations
kubectl exec -it $BACKEND_POD -n luckygas -- python manage.py migrate

# Create admin user
kubectl exec -it $BACKEND_POD -n luckygas -- python manage.py createsuperuser

# Seed initial data
kubectl exec -it $BACKEND_POD -n luckygas -- python manage.py seed_data
```

### 2. Configure Monitoring

```bash
# Apply monitoring configurations
kubectl apply -f k8s/monitoring/

# Access Grafana (port-forward for initial setup)
kubectl port-forward -n monitoring svc/grafana 3000:80
# Access at http://localhost:3000
```

### 3. Configure Backup CronJob

```bash
# Apply backup job
kubectl apply -f k8s/overlays/production/backup-cronjob.yaml

# Test backup manually
kubectl create job --from=cronjob/database-backup manual-backup-$(date +%Y%m%d) -n luckygas
```

### 4. Verify Deployment

```bash
# Run smoke tests
./k8s/scripts/smoke-tests.sh production

# Check pod status
kubectl get pods -n luckygas

# Check logs
kubectl logs -f deployment/luckygas-backend -n luckygas

# Check metrics
kubectl top nodes
kubectl top pods -n luckygas
```

## Deployment Checklist

### Pre-Deployment
- [ ] Infrastructure provisioned with Terraform
- [ ] Docker images built and pushed
- [ ] Secrets configured
- [ ] DNS records prepared
- [ ] Backup of current production (if applicable)

### Staging Validation
- [ ] Staging environment deployed successfully
- [ ] Infrastructure validation passed (staging-validation.sh)
- [ ] Integration tests passed (integration-test.sh)
- [ ] Security scan completed with no critical issues (security-scan.sh)
- [ ] Load tests meet performance targets (load-test.sh)
- [ ] All E2E tests passing
- [ ] Staging validation report reviewed and approved
- [ ] Stakeholder sign-offs obtained

### Deployment
- [ ] Kubernetes manifests applied
- [ ] Pods running and healthy
- [ ] Ingress configured with SSL
- [ ] Database migrations completed
- [ ] Initial data seeded

### Post-Deployment
- [ ] Smoke tests passing
- [ ] Monitoring configured
- [ ] Alerts configured
- [ ] Backup job scheduled
- [ ] Documentation updated
- [ ] Team notified

## Rollback Procedure

If deployment fails:

```bash
# Quick rollback
./k8s/scripts/rollback.sh production

# Or manual rollback
kubectl rollout undo deployment/luckygas-backend -n luckygas
kubectl rollout undo deployment/luckygas-frontend -n luckygas
```

## Troubleshooting

### Common Issues

1. **Pods not starting**:
   ```bash
   kubectl describe pod <pod-name> -n luckygas
   kubectl logs <pod-name> -n luckygas --previous
   ```

2. **Database connection issues**:
   ```bash
   # Check Cloud SQL proxy
   kubectl logs deployment/cloud-sql-proxy -n luckygas
   
   # Test connection
   kubectl exec -it deployment/luckygas-backend -n luckygas -- nc -zv cloud-sql-proxy 5432
   ```

3. **Ingress not working**:
   ```bash
   # Check ingress status
   kubectl describe ingress luckygas-ingress -n luckygas
   
   # Check certificate
   kubectl describe certificate luckygas-tls -n luckygas
   ```

4. **High resource usage**:
   ```bash
   # Check HPA status
   kubectl get hpa -n luckygas
   
   # Manually scale if needed
   kubectl scale deployment/luckygas-backend --replicas=5 -n luckygas
   ```

## Security Considerations

1. **Network Policies**: Applied by default to restrict pod-to-pod communication
2. **RBAC**: Service accounts have minimal required permissions
3. **Secrets Management**: All sensitive data in Kubernetes secrets or GCP Secret Manager
4. **SSL/TLS**: Enforced for all external communications
5. **Pod Security**: Non-root containers with read-only filesystems

## Cost Optimization

1. **Node Pools**: Use preemptible nodes for non-critical workloads
2. **Autoscaling**: HPA configured to scale based on actual load
3. **Resource Limits**: Set appropriate requests and limits
4. **Storage**: Use appropriate storage classes (Standard vs Nearline)
5. **Monitoring**: Use GCP's free tier for monitoring where possible

## Maintenance

### Regular Tasks

- **Daily**: Check monitoring dashboard, review alerts
- **Weekly**: Review resource usage, check backup success
- **Monthly**: Update dependencies, security patches
- **Quarterly**: DR drill, review and update documentation

### Upgrade Procedure

```bash
# 1. Test in staging first
./k8s/scripts/deploy.sh staging v1.1.0

# 2. If successful, deploy to production
./k8s/scripts/deploy.sh production v1.1.0

# 3. Monitor closely for 24 hours
```

## Support

For issues or questions:
- Check logs and monitoring first
- Consult disaster recovery plan for major incidents
- Contact DevOps team at devops@luckygas.com.tw