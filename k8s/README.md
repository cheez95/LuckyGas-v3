# LuckyGas Kubernetes Infrastructure

Production-grade Kubernetes infrastructure for the LuckyGas Delivery Management System.

## Overview

This directory contains all Kubernetes manifests and configurations for deploying LuckyGas to production. The infrastructure is designed with high availability, security, and observability in mind.

## Directory Structure

```
k8s/
├── base/                       # Base Kubernetes manifests
│   ├── namespace.yaml         # Namespace and resource quotas
│   ├── configmap.yaml         # Application configuration
│   ├── secrets.yaml           # Secret templates (placeholder values)
│   ├── serviceaccount.yaml    # Service accounts and RBAC
│   ├── backend-deployment.yaml # Backend deployment
│   ├── frontend-deployment.yaml # Frontend deployment
│   ├── services.yaml          # Kubernetes services
│   ├── networkpolicy.yaml     # Network security policies
│   └── kustomization.yaml     # Kustomize base configuration
├── overlays/                   # Environment-specific overlays
│   ├── development/           # Development environment
│   ├── staging/               # Staging environment
│   └── production/            # Production environment
│       ├── kustomization.yaml # Production kustomization
│       ├── ingress.yaml       # Ingress with SSL
│       ├── hpa.yaml          # Horizontal Pod Autoscalers
│       ├── pdb.yaml          # Pod Disruption Budgets
│       ├── monitoring.yaml    # ServiceMonitors and alerts
│       ├── backup-cronjob.yaml # Database backup job
│       └── *-patch.yaml      # Production patches
└── scripts/                    # Deployment and maintenance scripts
    ├── deploy.sh              # Automated deployment
    ├── rollback.sh           # Emergency rollback
    ├── health-check.sh       # Health verification
    └── setup-monitoring.sh   # Monitoring setup
```

## Prerequisites

1. **Kubernetes Cluster**: GKE cluster running Kubernetes 1.25+
2. **kubectl**: Configured to access the cluster
3. **kustomize**: For building manifests
4. **Docker**: For building container images
5. **gcloud**: For pushing images to GCR
6. **Helm**: For installing monitoring stack

## Quick Start

### 1. Initial Setup

```bash
# Create namespace
kubectl create namespace luckygas

# Create secrets (replace placeholder values first)
kubectl create secret generic luckygas-backend-secrets \
  --from-env-file=secrets-production.env \
  -n luckygas

# Create TLS certificate secret
kubectl create secret tls luckygas-tls-certificate \
  --cert=path/to/tls.crt \
  --key=path/to/tls.key \
  -n luckygas
```

### 2. Deploy to Production

```bash
# Deploy with specific version
./k8s/scripts/deploy.sh production v1.0.0

# Deploy with latest version
./k8s/scripts/deploy.sh production latest
```

### 3. Verify Deployment

```bash
# Run health checks
./k8s/scripts/health-check.sh production

# Check pod status
kubectl get pods -n luckygas

# Check ingress
kubectl get ingress -n luckygas
```

## Configuration

### Environment Variables

All environment variables are managed through ConfigMaps and Secrets:

- **ConfigMaps**: Non-sensitive configuration (see `base/configmap.yaml`)
- **Secrets**: Sensitive data like passwords and API keys (see `base/secrets.yaml`)

### Secret Management

Create a `secrets-production.env` file with actual values:

```env
DATABASE_USER=luckygas_user
DATABASE_PASSWORD=strong_password_here
REDIS_PASSWORD=redis_password_here
SECRET_KEY=jwt_secret_key_here
GOOGLE_MAPS_API_KEY=your_api_key_here
SMS_GATEWAY_API_KEY=sms_api_key_here
EINVOICE_APP_ID=einvoice_app_id_here
BANKING_API_KEY=banking_api_key_here
```

## Features

### High Availability

- **Multi-replica deployments**: 5 backend pods, 3 frontend pods in production
- **Pod Anti-affinity**: Pods distributed across nodes and zones
- **Pod Disruption Budgets**: Ensures minimum availability during updates
- **Health checks**: Liveness, readiness, and startup probes

### Auto-scaling

- **Horizontal Pod Autoscaler**: Scales based on CPU, memory, and custom metrics
- **Configurable thresholds**: Different scaling policies for backend and frontend
- **Graceful scale-down**: Prevents aggressive downscaling

### Security

- **Network Policies**: Strict ingress/egress rules
- **RBAC**: Minimal permissions for service accounts
- **Security Context**: Non-root users, read-only filesystems
- **TLS/SSL**: End-to-end encryption with cert-manager
- **Secret rotation**: Support for external secret management

### Observability

- **Prometheus metrics**: Custom application metrics
- **Grafana dashboards**: Pre-configured dashboards
- **Alert rules**: Critical alerts for SRE team
- **Centralized logging**: Loki for log aggregation
- **Distributed tracing**: OpenTelemetry ready

### Backup & Recovery

- **Automated backups**: Daily database backups to GCS
- **Retention policies**: 30 days daily, 12 weeks weekly, 12 months monthly
- **Point-in-time recovery**: Support for database restoration
- **Disaster recovery**: Cross-region backup replication

## Deployment Process

### Production Deployment

1. **Build Images**: Multi-stage Docker builds with security scanning
2. **Push to Registry**: Images pushed to Google Container Registry
3. **Update Manifests**: Kustomize updates image tags
4. **Apply Changes**: Rolling update with zero downtime
5. **Health Verification**: Automated health checks
6. **Monitoring**: Real-time metrics and alerts

### Rollback Process

```bash
# View deployment history
kubectl rollout history deployment/prod-luckygas-backend -n luckygas

# Rollback to previous version
./k8s/scripts/rollback.sh production 1

# Rollback to specific revision
./k8s/scripts/rollback.sh production 3
```

## Monitoring & Alerts

### Setup Monitoring Stack

```bash
./k8s/scripts/setup-monitoring.sh
```

### Access Dashboards

```bash
# Grafana (admin / luckygas-admin)
kubectl port-forward -n monitoring svc/prometheus-grafana 3000:80

# Prometheus
kubectl port-forward -n monitoring svc/prometheus-kube-prometheus-prometheus 9090:9090

# AlertManager
kubectl port-forward -n monitoring svc/alertmanager-main 9093:9093
```

### Key Metrics

- **Request rate**: Requests per second by service
- **Error rate**: 5xx errors percentage
- **Response time**: 95th percentile latency
- **Resource usage**: CPU and memory utilization
- **Database connections**: Connection pool usage

## Troubleshooting

### Common Issues

1. **Pods not starting**
   ```bash
   kubectl describe pod <pod-name> -n luckygas
   kubectl logs <pod-name> -n luckygas
   ```

2. **Database connection issues**
   ```bash
   kubectl exec -it <backend-pod> -n luckygas -- python -c "import psycopg2; print('DB OK')"
   ```

3. **Ingress not working**
   ```bash
   kubectl describe ingress luckygas-ingress -n luckygas
   kubectl logs -n ingress-nginx deployment/ingress-nginx-controller
   ```

### Debug Commands

```bash
# Get all resources
kubectl get all -n luckygas

# Check events
kubectl get events -n luckygas --sort-by='.lastTimestamp'

# Port forward for debugging
kubectl port-forward -n luckygas pod/<pod-name> 8000:8000

# Execute commands in pod
kubectl exec -it -n luckygas <pod-name> -- /bin/bash
```

## Maintenance

### Certificate Renewal

Certificates are automatically renewed by cert-manager. To manually renew:

```bash
kubectl delete certificate luckygas-tls-certificate -n luckygas
```

### Database Maintenance

```bash
# Manual backup
kubectl create job manual-backup --from=cronjob/luckygas-database-backup -n luckygas

# Check backup status
kubectl logs -n luckygas job/manual-backup
```

### Scaling

```bash
# Manual scaling
kubectl scale deployment prod-luckygas-backend --replicas=10 -n luckygas

# Update HPA limits
kubectl edit hpa luckygas-backend-hpa -n luckygas
```

## Security Considerations

1. **Secrets**: Never commit actual secret values to git
2. **Network Policies**: Review and update as needed
3. **Image Scanning**: Enable vulnerability scanning in GCR
4. **RBAC**: Follow principle of least privilege
5. **Audit Logging**: Enable Kubernetes audit logs

## Performance Tuning

1. **Resource Limits**: Adjust based on actual usage patterns
2. **HPA Metrics**: Fine-tune scaling thresholds
3. **Database Pooling**: Optimize connection pool sizes
4. **Caching**: Configure Redis for optimal performance
5. **CDN**: Use Cloud CDN for static assets

## Disaster Recovery

1. **Backup Verification**: Regularly test backup restoration
2. **Multi-region**: Consider multi-region deployment
3. **Incident Response**: Document runbooks for common scenarios
4. **RTO/RPO**: Define and test recovery objectives

## Support

For issues or questions:
1. Check the [troubleshooting guide](#troubleshooting)
2. Review application logs in Grafana/Loki
3. Check Prometheus alerts
4. Contact the SRE team

## License

Copyright © 2024 Lucky Gas. All rights reserved.