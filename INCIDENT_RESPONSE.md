# LuckyGas Incident Response Plan

## Overview

This document defines the incident response procedures for the LuckyGas production system. It provides a structured approach to detecting, responding to, and recovering from incidents while minimizing customer impact.

**Incident Definition**: Any unplanned interruption or degradation of service quality
**Response Time SLA**: 
- Critical (P1): 15 minutes
- High (P2): 30 minutes  
- Medium (P3): 2 hours
- Low (P4): 24 hours

## Incident Severity Levels

### P1 - Critical
**Definition**: Complete service outage or data loss risk
**Examples**:
- Site completely down
- Database corruption
- Security breach
- Payment system failure
- All analytics endpoints down

**Response**: Immediate all-hands response, executive notification

### P2 - High  
**Definition**: Major functionality impaired
**Examples**:
- Login system failing
- Orders not processing
- Performance degradation >50%
- One analytics endpoint down
- Google Maps integration failing

**Response**: On-call engineer + backup, team lead notification

### P3 - Medium
**Definition**: Minor functionality impaired
**Examples**:
- Slow response times (2-5 seconds)
- Non-critical features failing
- Partial data sync issues
- Minor UI bugs

**Response**: On-call engineer, next business day resolution acceptable

### P4 - Low
**Definition**: Minimal impact
**Examples**:
- Cosmetic issues
- Non-blocking bugs
- Documentation errors

**Response**: Regular development cycle

## Incident Response Phases

### 1. Detection & Alert

**Automated Detection**:
- Prometheus alerts via PagerDuty
- Uptime monitoring via Pingdom
- Error rate monitoring
- Customer reports via support

**Initial Assessment** (0-5 minutes):
```bash
# Quick system check
./deploy/health-check.sh

# Check Grafana
open https://grafana.luckygas.com.tw/d/luckygas-overview

# Recent errors
gcloud logging read "severity>=ERROR" --limit=50 --format=json | jq '.[] | {timestamp: .timestamp, message: .jsonPayload.message}'
```

### 2. Triage & Escalation

**Triage Checklist**:
- [ ] Determine severity level
- [ ] Identify affected components
- [ ] Estimate customer impact
- [ ] Check for related alerts

**Escalation Decision Tree**:
```
Is the site completely down? → P1
Are users unable to login? → P1/P2
Are orders failing? → P2
Is performance degraded? → P2/P3
Is it customer-facing? → P3
Otherwise → P4
```

### 3. Response & Mitigation

#### Incident Commander Responsibilities
1. **Coordinate Response**
   - Assign roles
   - Direct troubleshooting
   - Make decisions
   - External communication

2. **Roles Assignment**
   - **IC**: Incident Commander
   - **TL**: Technical Lead (fixes issue)
   - **COM**: Communications (updates stakeholders)
   - **SCR**: Scribe (documents timeline)

#### Response Procedures by Type

**Complete Outage**:
```bash
# 1. Check all services
kubectl get all

# 2. Check ingress
kubectl describe ingress luckygas-ingress

# 3. Emergency failover
./scripts/emergency-failover.sh

# 4. Scale up everything
kubectl scale deployment luckygas-backend --replicas=10
kubectl scale deployment luckygas-frontend --replicas=5
```

**Database Issues**:
```sql
-- Check connections
SELECT count(*) FROM pg_stat_activity;

-- Kill long queries
SELECT pg_terminate_backend(pid) 
FROM pg_stat_activity 
WHERE state != 'idle' 
AND query_start < now() - interval '5 minutes';

-- Emergency read-only mode
ALTER DATABASE luckygas_prod SET default_transaction_read_only = true;
```

**Performance Degradation**:
```bash
# 1. Identify bottleneck
kubectl top pods --sort-by=cpu
kubectl top nodes

# 2. Scale affected service
kubectl scale deployment <service> --replicas=<n>

# 3. Clear cache if needed
kubectl exec -it redis-pod -- redis-cli FLUSHALL

# 4. Enable emergency caching
kubectl set env deployment/luckygas-backend CACHE_TTL=300
```

**Security Incident**:
```bash
# 1. Isolate affected components
kubectl cordon <node>

# 2. Revoke compromised credentials
kubectl delete secret <secret-name>
kubectl create secret generic <secret-name> --from-literal=key=<new-value>

# 3. Enable audit logging
kubectl edit cm audit-config

# 4. Block suspicious IPs
gcloud compute firewall-rules create block-suspicious --deny=tcp --source-ranges=<IP>
```

### 4. Communication

#### Internal Communication

**Slack Channels**:
- `#incidents` - Primary coordination
- `#incidents-active` - Active incident only
- `#incidents-updates` - Status updates

**Update Template**:
```
🚨 INCIDENT UPDATE [P<severity>]
Status: <Investigating|Identified|Monitoring|Resolved>
Impact: <customer impact description>
Current Action: <what we're doing>
Next Update: <time>
```

#### External Communication

**Status Page Updates** (status.luckygas.com.tw):
- Within 15 minutes of P1/P2 detection
- Every 30 minutes until resolved

**Customer Notification** (P1 only):
```
Subject: LuckyGas 服務異常通知

親愛的客戶您好，

我們目前遇到技術問題，可能影響您的服務使用。我們的團隊正在積極處理中。

影響範圍：[具體說明]
預計修復時間：[時間]

造成您的不便，我們深感抱歉。最新狀態請參考：status.luckygas.com.tw

LuckyGas 技術團隊
```

### 5. Resolution & Recovery

**Resolution Checklist**:
- [ ] Root cause identified
- [ ] Fix implemented and tested
- [ ] Affected services restored
- [ ] Monitoring confirms stability
- [ ] Data integrity verified

**Recovery Validation**:
```bash
# Run full system validation
./deploy/post-deploy-validation.sh

# Check critical user flows
curl -X POST https://api.luckygas.com.tw/api/v1/auth/login -d '{"email":"test@example.com","password":"test"}'
curl https://api.luckygas.com.tw/api/v1/analytics/executive -H "Authorization: Bearer $TOKEN"

# Verify order processing
./scripts/test-order-creation.sh
```

### 6. Post-Incident

**Immediate Actions** (within 2 hours):
1. Update incident ticket with resolution
2. Send final status update
3. Create post-mortem document
4. Schedule post-mortem meeting

**Post-Mortem Template**: See [Post-Mortem Template](#post-mortem-template)

## Runbooks by Incident Type

### API Response Time > 2 seconds

**Symptoms**: 
- Alert: "HighAPIResponseTime"
- User complaints about slowness
- Grafana shows p95 > 2s

**Response**:
1. Check current load
   ```bash
   kubectl top pods -l app=luckygas-backend
   ```

2. Check database queries
   ```sql
   SELECT query, mean_time FROM pg_stat_statements 
   WHERE mean_time > 1000 ORDER BY mean_time DESC LIMIT 5;
   ```

3. Scale if needed
   ```bash
   kubectl scale deployment luckygas-backend --replicas=10
   ```

4. Enable query caching
   ```bash
   kubectl set env deployment/luckygas-backend QUERY_CACHE_TTL=300
   ```

### Analytics Endpoint Down

**Symptoms**:
- Alert: "AnalyticsEndpointDown"
- 404/500 errors on /api/v1/analytics/*

**Response**:
1. Check specific endpoint
   ```bash
   for endpoint in executive operations financial performance; do
     echo "Checking $endpoint..."
     curl -s -o /dev/null -w "%{http_code}" https://api.luckygas.com.tw/api/v1/analytics/$endpoint
   done
   ```

2. Check aggregation jobs
   ```bash
   kubectl get cronjobs
   kubectl logs -l job-name=analytics-aggregation --tail=100
   ```

3. Manual aggregation
   ```bash
   kubectl exec -it backend-pod -- python scripts/run_analytics_aggregation.py
   ```

### Order Processing Failure

**Symptoms**:
- Orders stuck in "pending"
- Alert: "NoOrdersProcessed"

**Response**:
1. Check order queue
   ```bash
   gcloud tasks queues describe orders-queue
   ```

2. Check worker logs
   ```bash
   kubectl logs -l app=order-worker --tail=200
   ```

3. Process manually
   ```bash
   kubectl exec -it backend-pod -- python scripts/process_pending_orders.py
   ```

### Database Connection Pool Exhausted

**Symptoms**:
- Alert: "DatabaseConnectionPoolExhausted"
- "too many connections" errors

**Response**:
1. Kill idle connections
   ```sql
   SELECT pg_terminate_backend(pid) FROM pg_stat_activity 
   WHERE state = 'idle' AND state_change < current_timestamp - interval '5 minutes';
   ```

2. Increase pool size temporarily
   ```bash
   kubectl set env deployment/luckygas-backend DB_POOL_SIZE=150
   ```

3. Restart services
   ```bash
   kubectl rollout restart deployment/luckygas-backend
   ```

## Tools and Resources

### Monitoring & Alerting
- **Grafana**: https://grafana.luckygas.com.tw
- **Prometheus**: https://prometheus.luckygas.com.tw
- **PagerDuty**: https://luckygas.pagerduty.com
- **Status Page**: https://status.luckygas.com.tw

### Logs & Debugging
- **GCP Logs**: https://console.cloud.google.com/logs
- **Kubernetes Dashboard**: https://k8s.luckygas.com.tw
- **APM**: https://apm.luckygas.com.tw

### Communication
- **Slack**: https://luckygas.slack.com
- **Incident Tracker**: https://incidents.luckygas.com.tw
- **War Room**: https://meet.google.com/luckygas-incident

### Scripts & Automation
All scripts in `/scripts/incident-response/`:
- `quick-diagnostics.sh` - System health snapshot
- `emergency-scale.sh` - Scale all services
- `cache-clear.sh` - Clear all caches
- `db-connections-reset.sh` - Reset DB connections

## Post-Mortem Template

```markdown
# Incident Post-Mortem: [Incident Title]

**Incident Number**: INC-YYYY-MM-DD-001
**Date**: YYYY-MM-DD
**Duration**: XX minutes
**Severity**: P1/P2/P3/P4
**Author**: [Name]

## Summary
Brief description of what happened.

## Timeline
- HH:MM - Alert triggered
- HH:MM - Engineer acknowledged
- HH:MM - Root cause identified
- HH:MM - Fix deployed
- HH:MM - Incident resolved

## Impact
- **Customer Impact**: X customers affected
- **Data Loss**: None/Description
- **Financial Impact**: $X
- **SLA Impact**: X% uptime

## Root Cause
Detailed explanation of why this happened.

## Resolution
How the incident was resolved.

## Lessons Learned
### What Went Well
- Item 1
- Item 2

### What Went Poorly
- Item 1
- Item 2

## Action Items
| Action | Owner | Due Date | Status |
|--------|-------|----------|--------|
| Add monitoring for X | @person | YYYY-MM-DD | Open |
| Update runbook for Y | @person | YYYY-MM-DD | Open |

## Supporting Information
- [Link to logs]
- [Link to graphs]
- [Link to code changes]
```

## Training & Drills

### Monthly Incident Drills
- First Monday: Database failure scenario
- Second Monday: API degradation scenario
- Third Monday: Security incident scenario
- Fourth Monday: Complete outage scenario

### New Team Member Training
1. Shadow on-call for 1 week
2. Review past post-mortems
3. Practice with drill scenarios
4. Paired on-call for first rotation

## Metrics & Reporting

### Key Metrics
- **MTTA** (Mean Time To Acknowledge): Target < 5 minutes
- **MTTR** (Mean Time To Resolve): Target < 30 minutes
- **Incident Rate**: Target < 2 per month
- **Customer Impact**: Target < 100 affected per incident

### Monthly Review
- Review all incidents
- Update runbooks
- Identify patterns
- Plan improvements

---

**Last Updated**: 2025-01-29
**Version**: 1.0.0
**Next Drill**: First Monday of next month