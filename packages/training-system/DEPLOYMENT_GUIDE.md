# Lucky Gas Training System - Production Deployment Guide

## 📋 Prerequisites

### Infrastructure Requirements
- **Kubernetes Cluster**: v1.25+ with minimum 3 nodes
- **PostgreSQL**: v15+ with PostGIS extension
- **Redis**: v7+ for caching and sessions
- **AWS Account**: For S3, CloudFront, MediaConvert, and Lambda
- **Domain**: training.luckygas.com.tw with SSL certificates
- **Container Registry**: GitHub Container Registry or similar

### Tools Required
- `kubectl` v1.25+
- `helm` v3.10+
- `aws-cli` v2+
- `docker` v20+
- `terraform` v1.3+ (optional for infrastructure)

## 🏗️ Infrastructure Setup

### 1. AWS Services Setup

#### S3 Buckets
```bash
# Create buckets for video storage
aws s3 mb s3://luckygas-training-videos --region ap-northeast-1
aws s3 mb s3://luckygas-training-materials --region ap-northeast-1

# Enable versioning
aws s3api put-bucket-versioning \
  --bucket luckygas-training-videos \
  --versioning-configuration Status=Enabled

# Configure CORS for video streaming
cat > cors.json << EOF
{
  "CORSRules": [
    {
      "AllowedOrigins": ["https://training.luckygas.com.tw"],
      "AllowedMethods": ["GET", "HEAD"],
      "AllowedHeaders": ["*"],
      "MaxAgeSeconds": 3600
    }
  ]
}
EOF

aws s3api put-bucket-cors \
  --bucket luckygas-training-videos \
  --cors-configuration file://cors.json
```

#### CloudFront Distribution
```bash
# Create CloudFront distribution for video CDN
aws cloudfront create-distribution \
  --distribution-config file://cloudfront-config.json
```

#### MediaConvert Setup
1. Create MediaConvert role in IAM console
2. Note the endpoint URL for your region
3. Update Lambda environment variables

#### Lambda Function Deployment
```bash
cd packages/video-processor
zip -r lambda-package.zip lambda/* requirements.txt

aws lambda create-function \
  --function-name luckygas-training-video-processor \
  --runtime python3.11 \
  --role arn:aws:iam::YOUR_ACCOUNT:role/lambda-mediaconvert-role \
  --handler index.lambda_handler \
  --zip-file fileb://lambda-package.zip \
  --timeout 300 \
  --memory-size 512 \
  --environment Variables="{
    MEDIACONVERT_ENDPOINT=https://YOUR_ENDPOINT.mediaconvert.ap-northeast-1.amazonaws.com,
    MEDIACONVERT_ROLE_ARN=arn:aws:iam::YOUR_ACCOUNT:role/MediaConvertRole,
    OUTPUT_BUCKET=luckygas-training-videos
  }"

# Add S3 trigger
aws lambda add-permission \
  --function-name luckygas-training-video-processor \
  --statement-id s3-trigger \
  --action lambda:InvokeFunction \
  --principal s3.amazonaws.com \
  --source-arn arn:aws:s3:::luckygas-training-videos/*
```

### 2. Database Setup

#### PostgreSQL with PostGIS
```sql
-- Create database and user
CREATE DATABASE luckygas_training;
CREATE USER training_user WITH ENCRYPTED PASSWORD 'secure_password';
GRANT ALL PRIVILEGES ON DATABASE luckygas_training TO training_user;

-- Enable extensions
\c luckygas_training
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "postgis";

-- Create initial schema (run migrations)
cd packages/training-api
alembic upgrade head
```

#### Redis Configuration
```bash
# Redis configuration for production
cat > redis.conf << EOF
maxmemory 2gb
maxmemory-policy allkeys-lru
save 900 1
save 300 10
save 60 10000
appendonly yes
appendfsync everysec
EOF
```

### 3. Kubernetes Setup

#### Create Namespace and Secrets
```bash
# Create namespace
kubectl create namespace training-production

# Create secrets
kubectl create secret generic training-secrets \
  --namespace=training-production \
  --from-literal=DATABASE_URL="postgresql://training_user:password@postgres:5432/luckygas_training" \
  --from-literal=REDIS_URL="redis://:password@redis:6379/0" \
  --from-literal=JWT_SECRET="your-secure-jwt-secret" \
  --from-literal=AWS_ACCESS_KEY_ID="your-aws-key" \
  --from-literal=AWS_SECRET_ACCESS_KEY="your-aws-secret" \
  --from-literal=S3_BUCKET_NAME="luckygas-training-videos" \
  --from-literal=SMTP_PASSWORD="your-smtp-password" \
  --from-literal=SENTRY_DSN="your-sentry-dsn"

# Create ConfigMap
kubectl create configmap training-config \
  --namespace=training-production \
  --from-literal=ENVIRONMENT="production" \
  --from-literal=LOG_LEVEL="INFO" \
  --from-literal=CORS_ORIGINS="https://training.luckygas.com.tw" \
  --from-literal=GOOGLE_MAPS_API_KEY="your-google-maps-key" \
  --from-literal=AWS_REGION="ap-northeast-1"
```

## 🚀 Deployment Process

### 1. Build and Push Docker Images

```bash
# Build images
docker build -t ghcr.io/luckygas/training-portal:v1.0.0 packages/training-portal
docker build -t ghcr.io/luckygas/training-api:v1.0.0 packages/training-api

# Push to registry
docker push ghcr.io/luckygas/training-portal:v1.0.0
docker push ghcr.io/luckygas/training-api:v1.0.0

# Tag as latest
docker tag ghcr.io/luckygas/training-portal:v1.0.0 ghcr.io/luckygas/training-portal:latest
docker tag ghcr.io/luckygas/training-api:v1.0.0 ghcr.io/luckygas/training-api:latest
docker push ghcr.io/luckygas/training-portal:latest
docker push ghcr.io/luckygas/training-api:latest
```

### 2. Deploy to Kubernetes

```bash
# Apply Kubernetes manifests
kubectl apply -f k8s/training-system/deployment.yaml

# Verify deployment
kubectl get pods -n training-production
kubectl get services -n training-production
kubectl get ingress -n training-production

# Check pod logs
kubectl logs -f deployment/training-api -n training-production
kubectl logs -f deployment/training-portal -n training-production
```

### 3. SSL Certificate Setup

```bash
# Install cert-manager if not already installed
kubectl apply -f https://github.com/cert-manager/cert-manager/releases/download/v1.11.0/cert-manager.yaml

# Create ClusterIssuer for Let's Encrypt
cat > cluster-issuer.yaml << EOF
apiVersion: cert-manager.io/v1
kind: ClusterIssuer
metadata:
  name: letsencrypt-prod
spec:
  acme:
    server: https://acme-v02.api.letsencrypt.org/directory
    email: admin@luckygas.com.tw
    privateKeySecretRef:
      name: letsencrypt-prod
    solvers:
    - http01:
        ingress:
          class: nginx
EOF

kubectl apply -f cluster-issuer.yaml
```

### 4. Database Migrations

```bash
# Run migrations in production
kubectl exec -it deployment/training-api -n training-production -- \
  alembic upgrade head

# Seed initial data (if needed)
kubectl exec -it deployment/training-api -n training-production -- \
  python scripts/seed_data.py
```

## 📊 Monitoring Setup

### 1. Prometheus Configuration

```yaml
# prometheus-config.yaml
global:
  scrape_interval: 15s
  evaluation_interval: 15s

scrape_configs:
  - job_name: 'training-api'
    kubernetes_sd_configs:
      - role: pod
        namespaces:
          names:
            - training-production
    relabel_configs:
      - source_labels: [__meta_kubernetes_pod_label_app]
        action: keep
        regex: training-api
      - source_labels: [__meta_kubernetes_pod_ip]
        target_label: __address__
        replacement: $1:8000
```

### 2. Grafana Dashboard

```bash
# Import dashboard
kubectl create configmap grafana-dashboards \
  --from-file=packages/training-api/monitoring/grafana-dashboard.json \
  -n monitoring
```

### 3. Application Logs

```bash
# Configure Fluentd for log aggregation
kubectl apply -f k8s/monitoring/fluentd-config.yaml

# View logs in CloudWatch or ELK stack
aws logs tail /aws/containerinsights/luckygas-cluster/application
```

## 🔍 Health Checks and Validation

### 1. Run Smoke Tests

```bash
# Run smoke tests against production
./scripts/smoke-tests.sh production

# Expected output:
# ✓ Homepage (200)
# ✓ API health (healthy)
# ✓ WebSocket connection
# ✓ Video streaming
# ✓ Security headers
```

### 2. Performance Testing

```bash
# Run load tests
npm install -g artillery
artillery run tests/load/training-system.yml

# Check response times
curl -w "@curl-format.txt" -o /dev/null -s https://training.luckygas.com.tw
```

### 3. Security Validation

```bash
# SSL/TLS check
nmap --script ssl-cert,ssl-enum-ciphers -p 443 training.luckygas.com.tw

# Security headers check
curl -I https://training.luckygas.com.tw | grep -E "X-Content-Type|X-Frame|X-XSS"

# OWASP ZAP scan (optional)
docker run -t owasp/zap2docker-stable zap-baseline.py \
  -t https://training.luckygas.com.tw
```

## 🔄 Rollback Procedure

### Quick Rollback

```bash
# Rollback to previous version
kubectl rollout undo deployment/training-api -n training-production
kubectl rollout undo deployment/training-portal -n training-production

# Check rollback status
kubectl rollout status deployment/training-api -n training-production
kubectl rollout status deployment/training-portal -n training-production
```

### Database Rollback

```bash
# Rollback database migrations
kubectl exec -it deployment/training-api -n training-production -- \
  alembic downgrade -1
```

## 📝 Post-Deployment Tasks

### 1. Configure Monitoring Alerts

```yaml
# alerting-rules.yaml
groups:
  - name: training-system
    rules:
      - alert: HighErrorRate
        expr: rate(training_api_requests_total{status=~"5.."}[5m]) > 0.05
        for: 5m
        annotations:
          summary: "High error rate detected"
          
      - alert: LowActiveUsers
        expr: training_active_users < 10
        for: 30m
        annotations:
          summary: "Low number of active users"
```

### 2. Setup Backup Schedule

```bash
# PostgreSQL backup
kubectl create cronjob postgres-backup \
  --schedule="0 2 * * *" \
  --namespace=training-production \
  --image=postgres:15 \
  -- pg_dump -h postgres -U training_user luckygas_training > /backup/training-$(date +%Y%m%d).sql

# S3 backup sync
aws s3 sync s3://luckygas-training-videos s3://luckygas-training-backup --delete
```

### 3. User Training

- Deploy training materials to `/docs` endpoint
- Schedule training sessions with departments
- Create admin accounts for managers
- Setup support channels

## 🚨 Troubleshooting

### Common Issues

1. **Pods not starting**
   ```bash
   kubectl describe pod <pod-name> -n training-production
   kubectl logs <pod-name> -n training-production --previous
   ```

2. **Database connection issues**
   ```bash
   # Test connection from pod
   kubectl exec -it deployment/training-api -n training-production -- \
     psql $DATABASE_URL -c "SELECT 1"
   ```

3. **Video upload failures**
   - Check Lambda logs in CloudWatch
   - Verify S3 bucket permissions
   - Check MediaConvert job status

4. **WebSocket connection issues**
   - Verify nginx ingress websocket annotations
   - Check CORS configuration
   - Test with wscat tool

### Support Contacts

- **DevOps Team**: devops@luckygas.com.tw
- **On-Call**: +886-2-2345-6789
- **Escalation**: CTO / Engineering Manager

## 📚 Additional Resources

- [API Documentation](https://training-api.luckygas.com.tw/docs)
- [Architecture Diagrams](./docs/architecture/)
- [Runbook](./docs/runbook.md)
- [Security Guidelines](./docs/security.md)