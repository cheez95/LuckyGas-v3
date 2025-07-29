# LuckyGas Production Deployment Guide

## Overview

This guide provides step-by-step instructions for deploying the LuckyGas delivery management system to production using our automated blue-green deployment pipeline.

**Deployment Strategy**: Blue-Green with zero downtime
**Target Environment**: Google Kubernetes Engine (GKE)
**Automation**: GitHub Actions CI/CD
**Monitoring**: Prometheus + Grafana + PagerDuty

## Prerequisites

### Required Tools
- `gcloud` CLI configured with production credentials
- `kubectl` with GKE plugin
- Docker (for local builds)
- GitHub repository access with release permissions
- Access to production secrets in GitHub

### Access Requirements
- Google Cloud Project: `lucky-gas-prod`
- GKE Cluster: `luckygas-prod-cluster` in `asia-east1-a`
- Container Registry: `gcr.io/lucky-gas-prod`
- Production URLs:
  - App: https://app.luckygas.com.tw
  - API: https://api.luckygas.com.tw
  - Grafana: https://grafana.luckygas.com.tw

## Deployment Process

### 1. Pre-Deployment Checklist

Before initiating deployment, verify:

- [ ] All E2E tests passing (100+ scenarios)
- [ ] No critical security vulnerabilities in code scan
- [ ] Database backup completed within last 24 hours
- [ ] Monitoring dashboards accessible
- [ ] PagerDuty integration active
- [ ] Rollback procedure reviewed

### 2. Creating a Release

Deployments are triggered by creating a version tag:

```bash
# Ensure you're on main branch with latest changes
git checkout main
git pull origin main

# Create and push a version tag
git tag -a v1.2.3 -m "Release v1.2.3: Brief description"
git push origin v1.2.3
```

This automatically triggers the deployment pipeline in GitHub Actions.

### 3. Deployment Pipeline Stages

The automated pipeline executes these stages:

#### Stage 1: E2E Testing
- Runs complete Playwright test suite
- Validates all critical user flows
- Tests 預定配送日期 field functionality
- Verifies Google Cloud integrations

#### Stage 2: Build & Push
- Builds Docker images for frontend and backend
- Scans for security vulnerabilities
- Pushes to Google Container Registry
- Tags with version and `latest`

#### Stage 3: Database Operations
- Creates automated backup with encryption
- Runs pending migrations
- Validates critical fields (預定配送日期)
- Stores backup in GCS with 30-day retention

#### Stage 4: Blue-Green Deployment
- Deploys to "green" environment
- Runs health checks on green
- Executes smoke tests
- Switches traffic from blue to green
- Preserves blue for rollback

#### Stage 5: Validation
- Comprehensive post-deployment tests
- Analytics endpoints verification
- Performance validation (<2s response)
- Security checks

### 4. Manual Deployment (Emergency)

If automated deployment fails, use manual process:

```bash
# Set deployment ID
export DEPLOYMENT_ID=$(date +%Y%m%d_%H%M%S)

# Run deployment orchestrator
cd deploy/
./deploy-production.sh
```

### 5. Monitoring Deployment Progress

#### GitHub Actions
Monitor at: https://github.com/your-org/LuckyGas-v3/actions

#### Slack Notifications
Join channels:
- `#deployments` - Deployment status
- `#alerts` - System alerts
- `#analytics-alerts` - Analytics-specific

#### Grafana Dashboards
- Overview: https://grafana.luckygas.com.tw/d/luckygas-overview
- Analytics: https://grafana.luckygas.com.tw/d/luckygas-analytics
- Delivery Ops: https://grafana.luckygas.com.tw/d/luckygas-delivery

## Rollback Procedures

### Automatic Rollback
If deployment fails, automatic rollback initiates:
- Traffic switches back to blue environment
- Database migrations reversed if needed
- Alerts sent to Slack and PagerDuty

### Manual Rollback
For manual rollback within 2 minutes:

```bash
# Execute rollback script
./deploy/rollback.sh $DEPLOYMENT_ID
```

### Extended Rollback
For rollback after successful deployment:

1. Identify the previous stable version
2. Create a new deployment with that version tag
3. Or use kubectl to switch services:

```bash
# Switch services back to blue
kubectl patch service luckygas-frontend -p '{"spec":{"selector":{"deployment":"blue"}}}'
kubectl patch service luckygas-backend -p '{"spec":{"selector":{"deployment":"blue"}}}'
```

## Post-Deployment Tasks

### 1. Verification Checklist
- [ ] Homepage loads correctly
- [ ] Login functionality working
- [ ] Orders can be created with 預定配送日期
- [ ] Analytics dashboards accessible
- [ ] Google Maps integration functional
- [ ] Mobile app connectivity verified

### 2. Performance Validation
Check these metrics in Grafana:
- API response time p95 < 2 seconds
- Error rate < 0.1%
- All analytics endpoints responding
- Database connection pool < 80%

### 3. Communication
- Update status in #deployments channel
- Send release notes to stakeholders
- Update customer-facing changelog if needed

## Troubleshooting

### Common Issues

#### 1. Pod Not Starting
```bash
# Check pod status
kubectl get pods -l app=luckygas-backend
kubectl describe pod <pod-name>
kubectl logs <pod-name>
```

#### 2. Database Connection Failed
- Verify Cloud SQL proxy is running
- Check database credentials in secrets
- Ensure VPC peering is active

#### 3. Google Maps API Errors
- Verify API key is valid
- Check quota limits in GCP Console
- Ensure billing is active

#### 4. Analytics Endpoints Failing
- Check database indexes
- Verify data aggregation jobs running
- Monitor query performance

### Emergency Contacts

**On-Call Engineer**: Check PagerDuty schedule
**Platform Team**: platform@luckygas.com.tw
**Database Team**: database@luckygas.com.tw
**Google Cloud Support**: [Support Case Link]

## Scheduled Deployments

### Deployment Windows
- **Primary**: Tuesday/Thursday 10:00-12:00 TST
- **Emergency**: Any time with manager approval
- **Avoid**: Fridays, holidays, peak hours (17:00-20:00)

### Monthly Tasks
- Review and test rollback procedures
- Update deployment documentation
- Audit access permissions
- Clean up old Docker images

## Security Considerations

### Pre-Deployment
- Never commit secrets to repository
- Rotate API keys quarterly
- Review security scan results
- Update dependencies for vulnerabilities

### During Deployment
- Monitor for unusual traffic patterns
- Check authentication logs
- Verify SSL certificates valid

### Post-Deployment
- Audit deployment logs
- Review access patterns
- Update security documentation

## Appendix

### Environment Variables
Required secrets in GitHub:
- `GCP_SA_KEY` - Service account for GCP
- `SLACK_WEBHOOK` - Deployment notifications
- `PAGERDUTY_SERVICE_KEY` - Critical alerts
- `DB_PASSWORD` - Production database
- `TEST_USER_PASSWORD` - E2E test user

### Useful Commands

```bash
# View current deployments
kubectl get deployments -l app=luckygas

# Check service endpoints
kubectl get services

# View recent events
kubectl get events --sort-by='.lastTimestamp'

# Pod resource usage
kubectl top pods -l app=luckygas

# Database backup status
gsutil ls gs://lucky-gas-backups/database/

# Force pod restart
kubectl rollout restart deployment/luckygas-backend
```

### Related Documentation
- [ROLLBACK_PROCEDURES.md](./ROLLBACK_PROCEDURES.md)
- [PRODUCTION_RUNBOOK.md](./PRODUCTION_RUNBOOK.md)
- [INCIDENT_RESPONSE.md](./INCIDENT_RESPONSE.md)
- [DEPLOYMENT_CHECKLIST.md](./DEPLOYMENT_CHECKLIST.md)

---

**Last Updated**: 2025-01-29
**Version**: 1.0.0
**Maintained By**: Platform Team