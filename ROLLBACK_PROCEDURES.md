# LuckyGas Rollback Procedures

## Overview

This document outlines the procedures for rolling back deployments in the LuckyGas production environment. Our rollback strategy prioritizes system stability and data integrity while minimizing downtime.

**Rollback SLA**: < 2 minutes for traffic switchover
**Data Safety**: All rollbacks preserve customer data
**Automation Level**: Fully automated with manual override options

## Rollback Triggers

### Automatic Rollback Triggers
1. **Deployment Failure**
   - Health checks fail after deployment
   - Post-deployment validation fails
   - Critical services not responding

2. **Performance Degradation**
   - API response time > 2 seconds for 5 minutes
   - Error rate > 5% for 5 minutes
   - Database connection pool exhausted

3. **Critical Alerts**
   - Analytics endpoints down > 2 minutes
   - Google Cloud integrations failing
   - Authentication service unavailable

### Manual Rollback Triggers
- Business logic errors discovered
- Data integrity issues
- Customer-reported critical bugs
- Security vulnerabilities detected

## Rollback Types

### 1. Immediate Rollback (< 2 minutes)
Used immediately after deployment failure.

```bash
# Automated via deployment pipeline
./deploy/rollback.sh $DEPLOYMENT_ID

# What it does:
# 1. Switches traffic to blue environment
# 2. Scales down green environment
# 3. Reverts database migrations if needed
# 4. Restores monitoring configuration
```

### 2. Standard Rollback (2-30 minutes)
Used when issues discovered shortly after deployment.

```bash
# Step 1: Assess current state
kubectl get deployments -l app=luckygas
kubectl get services

# Step 2: Identify stable version
kubectl get deployment luckygas-backend-blue -o jsonpath='{.spec.template.spec.containers[0].image}'

# Step 3: Execute rollback
./deploy/rollback.sh $DEPLOYMENT_ID
```

### 3. Extended Rollback (> 30 minutes)
Used when rolling back to a much earlier version.

```bash
# Step 1: Create backup of current state
./deploy/backup-database.sh ROLLBACK_$(date +%Y%m%d_%H%M%S)

# Step 2: Deploy previous version
git checkout v1.2.2  # Previous stable version
git tag -a v1.2.2-rollback -m "Rollback to v1.2.2"
git push origin v1.2.2-rollback

# This triggers new deployment with old version
```

## Step-by-Step Procedures

### Emergency Rollback Procedure

**Time Estimate**: 2 minutes

1. **Initiate Rollback**
   ```bash
   cd /path/to/deploy
   ./rollback.sh $DEPLOYMENT_ID
   ```

2. **Monitor Progress**
   - Watch Slack #alerts channel
   - Check Grafana dashboards
   - Monitor kubectl events

3. **Verify Rollback**
   ```bash
   # Check service selectors
   kubectl get service luckygas-frontend -o jsonpath='{.spec.selector.deployment}'
   kubectl get service luckygas-backend -o jsonpath='{.spec.selector.deployment}'
   
   # Should show "blue" for both
   ```

4. **Validate System Health**
   ```bash
   curl https://api.luckygas.com.tw/health
   curl https://app.luckygas.com.tw
   ```

### Database Rollback Procedure

**WARNING**: Only perform if migrations were applied

1. **Check Migration Status**
   ```bash
   cat migrations_${DEPLOYMENT_ID}.log
   grep "Previous version:" migrations_${DEPLOYMENT_ID}.log
   ```

2. **Execute Migration Rollback**
   ```bash
   cd backend/
   alembic downgrade <previous_version>
   ```

3. **Verify Database State**
   ```sql
   -- Connect to database
   psql -h $DB_HOST -U $DB_USER -d luckygas_prod
   
   -- Verify critical tables
   SELECT column_name FROM information_schema.columns 
   WHERE table_name='orders' AND column_name='預定配送日期';
   ```

### Application State Rollback

1. **Identify Affected Data**
   ```bash
   # Check for new data created after deployment
   echo "SELECT COUNT(*) FROM orders WHERE created_at > '$DEPLOYMENT_TIME';" | psql
   ```

2. **Preserve Business Data**
   - New orders remain valid
   - Customer data unchanged
   - Only application code reverted

3. **Clear Caches**
   ```bash
   # Clear Redis cache if used
   redis-cli FLUSHDB
   
   # Clear CDN cache
   gcloud compute url-maps invalidate-cdn-cache luckygas-cdn --path "/*"
   ```

## Rollback Validation

### Health Checks
Run these checks after rollback:

```bash
# 1. API Health
./deploy/health-check.sh

# 2. Critical Endpoints
curl -s https://api.luckygas.com.tw/api/v1/analytics/executive -H "Authorization: Bearer $TOKEN"
curl -s https://api.luckygas.com.tw/api/v1/analytics/operations -H "Authorization: Bearer $TOKEN"
curl -s https://api.luckygas.com.tw/api/v1/analytics/financial -H "Authorization: Bearer $TOKEN"
curl -s https://api.luckygas.com.tw/api/v1/analytics/performance -H "Authorization: Bearer $TOKEN"

# 3. Order Creation Test
./deploy/post-deploy-validation.sh
```

### Performance Validation
Check in Grafana:
- API response times returned to normal
- Error rates decreased
- No memory leaks
- Database connections stable

## Communication Protocol

### During Rollback
1. **Immediate** (0-1 min)
   - Automated Slack notification sent
   - PagerDuty incident created
   - On-call engineer alerted

2. **Progress Updates** (1-5 min)
   - Post in #incidents channel
   - Update status page if customer-facing
   - Notify team leads

3. **Completion** (5+ min)
   - Confirm rollback success
   - Document incident details
   - Schedule post-mortem

### Notification Templates

**Rollback Initiated**
```
🔄 ROLLBACK IN PROGRESS
Deployment: v1.2.3 → v1.2.2
Reason: [Brief reason]
ETA: 2 minutes
Impact: Minimal - Blue/Green switch
```

**Rollback Complete**
```
✅ ROLLBACK COMPLETE
Previous Version: v1.2.3
Current Version: v1.2.2
Duration: X minutes
Status: System Stable
Next Steps: Post-mortem scheduled
```

## Special Scenarios

### Partial Rollback
When only specific services need rollback:

```bash
# Rollback only backend
kubectl set image deployment/luckygas-backend-green \
  backend=gcr.io/lucky-gas-prod/backend:v1.2.2

# Keep frontend on new version
```

### Data Migration Conflicts
If new version created data incompatible with old version:

1. **Assess Impact**
   ```sql
   -- Find affected records
   SELECT COUNT(*) FROM orders 
   WHERE created_at > '$DEPLOYMENT_TIME'
   AND new_field IS NOT NULL;
   ```

2. **Create Compatibility Layer**
   - Add database views for compatibility
   - Implement data transformation
   - Document data handling

### Multi-Region Rollback
If deployment was to multiple regions:

```bash
# Rollback each region
for REGION in asia-east1 asia-southeast1; do
  gcloud container clusters get-credentials luckygas-$REGION --region $REGION
  ./rollback.sh $DEPLOYMENT_ID
done
```

## Prevention and Learning

### Post-Rollback Checklist
- [ ] Incident report created
- [ ] Root cause identified
- [ ] Tests added to prevent recurrence
- [ ] Deployment process updated
- [ ] Team briefed on learnings

### Common Rollback Causes
1. **Missing Tests** (40%)
   - Edge cases not covered
   - Integration tests insufficient
   - Performance tests missing

2. **Configuration Issues** (30%)
   - Environment variables incorrect
   - API keys not updated
   - Resource limits too low

3. **Database Problems** (20%)
   - Migration errors
   - Performance degradation
   - Constraint violations

4. **External Dependencies** (10%)
   - Google Cloud API changes
   - Third-party service issues
   - Network connectivity

## Rollback Metrics

Track these metrics for continuous improvement:

- **MTTR** (Mean Time To Rollback): Target < 2 minutes
- **Rollback Frequency**: Target < 5% of deployments
- **Data Loss Incidents**: Target = 0
- **Customer Impact Duration**: Target < 5 minutes

## Emergency Contacts

### Escalation Path
1. **On-Call Engineer** (0-5 min)
   - Check PagerDuty
   - Primary: +886-9XX-XXX-XXX

2. **Team Lead** (5-15 min)
   - Platform Lead: platform-lead@luckygas.com.tw
   - Secondary: +886-9XX-XXX-XXX

3. **CTO** (15+ min)
   - For customer-impacting incidents
   - cto@luckygas.com.tw

### External Support
- **Google Cloud Support**: [Case URL]
- **Database Vendor**: +886-2-XXXX-XXXX
- **CDN Support**: support@cdn-provider.com

## Automation Scripts

All rollback scripts are located in `/deploy/`:
- `rollback.sh` - Main rollback orchestrator
- `health-check.sh` - System health validation
- `backup-database.sh` - Emergency backup creation
- `restore-database.sh` - Database restoration

## Related Documentation
- [DEPLOYMENT_GUIDE.md](./DEPLOYMENT_GUIDE.md)
- [INCIDENT_RESPONSE.md](./INCIDENT_RESPONSE.md)
- [PRODUCTION_RUNBOOK.md](./PRODUCTION_RUNBOOK.md)

---

**Last Updated**: 2025-01-29
**Version**: 1.0.0
**Approved By**: Platform Team Lead