# LuckyGas Production Runbook

## Overview

This runbook provides operational procedures for maintaining the LuckyGas production environment. It covers daily operations, monitoring, troubleshooting, and maintenance tasks.

**System**: LuckyGas Delivery Management System
**Environment**: Production (Asia-East1)
**Critical SLAs**: 
- Uptime: 99.9%
- API Response: < 2 seconds
- Order Processing: < 30 seconds

## System Architecture

### Components
1. **Frontend**: React SPA on Cloud CDN
2. **Backend**: FastAPI on GKE
3. **Database**: Cloud SQL PostgreSQL
4. **Cache**: Redis on Memory Store
5. **Queue**: Cloud Tasks
6. **Storage**: Cloud Storage
7. **ML**: Vertex AI

### Critical URLs
- Production App: https://app.luckygas.com.tw
- API: https://api.luckygas.com.tw
- Monitoring: https://grafana.luckygas.com.tw
- Logs: https://console.cloud.google.com/logs

## Daily Operations

### Morning Checklist (08:00 TST)

1. **System Health Check**
   ```bash
   # Run automated health check
   ./deploy/health-check.sh
   
   # Check Grafana dashboard
   open https://grafana.luckygas.com.tw/d/luckygas-overview
   ```

2. **Review Overnight Alerts**
   - Check Slack #alerts channel
   - Review PagerDuty incidents
   - Check error logs for patterns

3. **Database Health**
   ```sql
   -- Check connection count
   SELECT count(*) FROM pg_stat_activity;
   
   -- Check long-running queries
   SELECT pid, age(clock_timestamp(), pg_stat_activity.query_start), usename, query 
   FROM pg_stat_activity 
   WHERE state != 'idle' AND query NOT ILIKE '%pg_stat_activity%' 
   ORDER BY query_start desc;
   
   -- Check table sizes
   SELECT schemaname,tablename,pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) AS size
   FROM pg_tables ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC LIMIT 10;
   ```

4. **Order Processing Status**
   ```bash
   # Check today's order stats
   kubectl exec -it $(kubectl get pod -l app=luckygas-backend -o jsonpath="{.items[0].metadata.name}") -- \
     python -c "from app.services import stats; print(stats.get_daily_stats())"
   ```

### Hourly Checks

1. **Performance Metrics**
   - API response time < 2s
   - Error rate < 0.1%
   - Active users count normal
   - Database connections < 80%

2. **Google Cloud Integration**
   - Maps API quota usage
   - Vertex AI predictions running
   - Cloud Storage accessibility

### End of Day (18:00 TST)

1. **Daily Report Generation**
   ```bash
   # Generate daily operations report
   kubectl exec -it $(kubectl get pod -l app=luckygas-backend -o jsonpath="{.items[0].metadata.name}") -- \
     python scripts/generate_daily_report.py
   ```

2. **Backup Verification**
   ```bash
   # Check today's backup
   gsutil ls gs://lucky-gas-backups/database/$(date +%Y%m%d)*
   ```

## Monitoring and Alerts

### Key Metrics to Monitor

#### Business Metrics
- **Orders per hour**: Normal range 50-200
- **Active drivers**: Normal range 20-50
- **Delivery success rate**: Target > 98%
- **Customer registrations**: Normal range 10-50/day

#### Technical Metrics
- **API Response Time**: p95 < 2 seconds
- **Error Rate**: < 0.1%
- **CPU Usage**: < 70%
- **Memory Usage**: < 80%
- **Database Connections**: < 100

### Alert Response Procedures

#### High API Response Time
1. Check current traffic
   ```bash
   kubectl top pods -l app=luckygas-backend
   ```

2. Scale if needed
   ```bash
   kubectl scale deployment luckygas-backend --replicas=5
   ```

3. Check database queries
   ```sql
   SELECT query, calls, mean_time 
   FROM pg_stat_statements 
   ORDER BY mean_time DESC 
   LIMIT 10;
   ```

#### Database Connection Exhaustion
1. Identify connection sources
   ```sql
   SELECT application_name, count(*) 
   FROM pg_stat_activity 
   GROUP BY application_name;
   ```

2. Kill idle connections
   ```sql
   SELECT pg_terminate_backend(pid) 
   FROM pg_stat_activity 
   WHERE state = 'idle' 
   AND state_change < current_timestamp - interval '10 minutes';
   ```

3. Restart connection pool if needed
   ```bash
   kubectl rollout restart deployment luckygas-backend
   ```

#### Analytics Endpoint Down
1. Check endpoint health
   ```bash
   curl -s https://api.luckygas.com.tw/api/v1/analytics/executive \
     -H "Authorization: Bearer $TOKEN" | jq .
   ```

2. Check aggregation jobs
   ```bash
   kubectl get cronjobs
   kubectl describe cronjob analytics-aggregation
   ```

3. Manually trigger if needed
   ```bash
   kubectl create job --from=cronjob/analytics-aggregation manual-analytics-$(date +%s)
   ```

## Common Operations

### Scaling Operations

#### Horizontal Scaling
```bash
# Scale backend
kubectl scale deployment luckygas-backend --replicas=5

# Scale frontend
kubectl scale deployment luckygas-frontend --replicas=3

# Autoscaling status
kubectl get hpa
```

#### Vertical Scaling
```yaml
# Edit deployment resources
kubectl edit deployment luckygas-backend

# Update resources section:
resources:
  requests:
    memory: "1Gi"
    cpu: "500m"
  limits:
    memory: "2Gi"
    cpu: "2000m"
```

### Cache Operations

#### Clear Cache
```bash
# Clear all cache
kubectl exec -it $(kubectl get pod -l app=redis -o jsonpath="{.items[0].metadata.name}") -- redis-cli FLUSHALL

# Clear specific pattern
kubectl exec -it $(kubectl get pod -l app=redis -o jsonpath="{.items[0].metadata.name}") -- redis-cli --scan --pattern "analytics:*" | xargs redis-cli DEL
```

#### Cache Statistics
```bash
kubectl exec -it $(kubectl get pod -l app=redis -o jsonpath="{.items[0].metadata.name}") -- redis-cli INFO stats
```

### Database Operations

#### Backup Operations
```bash
# Manual backup
./deploy/backup-database.sh MANUAL_$(date +%Y%m%d_%H%M%S)

# Verify backup
gsutil ls -l gs://lucky-gas-backups/database/ | tail -5
```

#### Performance Tuning
```sql
-- Update statistics
ANALYZE;

-- Reindex if needed
REINDEX TABLE orders;
REINDEX TABLE customers;

-- Vacuum
VACUUM ANALYZE;
```

### Log Analysis

#### Common Log Queries
```bash
# Error logs
gcloud logging read "resource.type=k8s_container AND severity>=ERROR AND timestamp>=\"$(date -u -d '1 hour ago' '+%Y-%m-%dT%H:%M:%S')Z\"" --limit 50

# Slow queries
gcloud logging read "jsonPayload.duration>2000 AND resource.labels.container_name=backend" --limit 20

# Failed orders
gcloud logging read "jsonPayload.event=order_failed" --limit 10
```

## Troubleshooting Guide

### Application Issues

#### Users Cannot Login
1. Check auth service
   ```bash
   curl -X POST https://api.luckygas.com.tw/api/v1/auth/health
   ```

2. Check JWT secret
   ```bash
   kubectl get secret jwt-secret -o jsonpath="{.data.secret}" | base64 -d
   ```

3. Test login
   ```bash
   curl -X POST https://api.luckygas.com.tw/api/v1/auth/login \
     -H "Content-Type: application/json" \
     -d '{"email":"test@example.com","password":"test"}'
   ```

#### Orders Not Processing
1. Check order queue
   ```bash
   kubectl logs -l app=luckygas-worker --tail=100
   ```

2. Check scheduled tasks
   ```bash
   gcloud tasks queues describe orders-queue
   ```

3. Manually process stuck orders
   ```bash
   kubectl exec -it $(kubectl get pod -l app=luckygas-backend -o jsonpath="{.items[0].metadata.name}") -- \
     python scripts/process_stuck_orders.py
   ```

#### Google Maps Integration Failing
1. Check API key
   ```bash
   kubectl get secret google-api-keys -o jsonpath="{.data.maps-api-key}" | base64 -d
   ```

2. Check quota
   ```bash
   open https://console.cloud.google.com/apis/api/maps-backend.googleapis.com/metrics
   ```

3. Test geocoding
   ```bash
   curl "https://api.luckygas.com.tw/api/v1/maps/geocode?address=台北市信義區市府路1號"
   ```

### Database Issues

#### Slow Queries
1. Identify slow queries
   ```sql
   SELECT query, calls, total_time, mean_time, max_time
   FROM pg_stat_statements
   WHERE mean_time > 1000
   ORDER BY mean_time DESC
   LIMIT 10;
   ```

2. Explain query plan
   ```sql
   EXPLAIN ANALYZE <slow_query>;
   ```

3. Add indexes if needed
   ```sql
   CREATE INDEX CONCURRENTLY idx_orders_date ON orders(預定配送日期);
   ```

#### Connection Issues
1. Check connection limits
   ```sql
   SHOW max_connections;
   SELECT count(*) FROM pg_stat_activity;
   ```

2. Check for locks
   ```sql
   SELECT pid, usename, pg_blocking_pids(pid) as blocked_by, query 
   FROM pg_stat_activity 
   WHERE cardinality(pg_blocking_pids(pid)) > 0;
   ```

### Performance Issues

#### High CPU Usage
1. Identify CPU-intensive pods
   ```bash
   kubectl top pods --sort-by=cpu
   ```

2. Check for infinite loops
   ```bash
   kubectl logs <pod-name> --tail=100 | grep -i "error\|loop\|timeout"
   ```

3. Profile application
   ```bash
   kubectl exec -it <pod-name> -- py-spy top -p 1
   ```

#### Memory Leaks
1. Monitor memory growth
   ```bash
   kubectl top pods --sort-by=memory
   watch kubectl top pods
   ```

2. Get memory dump
   ```bash
   kubectl exec -it <pod-name> -- python -m pyheapdump dump /tmp/heap.dump
   kubectl cp <pod-name>:/tmp/heap.dump ./heap.dump
   ```

## Maintenance Procedures

### Weekly Maintenance

#### Monday - Database Maintenance
```sql
-- Vacuum and analyze
VACUUM ANALYZE;

-- Update table statistics
ANALYZE orders;
ANALYZE customers;
ANALYZE routes;

-- Check for bloat
SELECT schemaname, tablename, pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) as size,
       n_live_tup, n_dead_tup, round(n_dead_tup * 100.0 / (n_live_tup + n_dead_tup), 2) as dead_ratio
FROM pg_stat_user_tables
WHERE n_dead_tup > 1000
ORDER BY dead_ratio DESC;
```

#### Wednesday - Security Updates
```bash
# Check for security updates
gcloud container images scan <image>

# Update base images if needed
docker pull gcr.io/lucky-gas-prod/backend:latest
```

#### Friday - Backup Verification
```bash
# Test restore procedure
./deploy/restore-test.sh

# Clean old backups
gsutil ls gs://lucky-gas-backups/database/ | grep -E "$(date -d '31 days ago' +%Y%m)" | xargs gsutil rm
```

### Monthly Maintenance

1. **Certificate Renewal Check**
   ```bash
   echo | openssl s_client -servername api.luckygas.com.tw -connect api.luckygas.com.tw:443 2>/dev/null | openssl x509 -noout -dates
   ```

2. **Capacity Planning Review**
   - Review growth trends
   - Plan scaling needs
   - Budget adjustments

3. **Disaster Recovery Test**
   - Execute DR drill
   - Document results
   - Update procedures

## Integration Points

### External Services
1. **Google Maps API**
   - Endpoint: https://maps.googleapis.com
   - Monitoring: API Console
   - Quota: 25,000 requests/day

2. **Vertex AI**
   - Project: lucky-gas-prod
   - Models: demand-prediction, churn-prediction
   - Monitoring: AI Platform Console

3. **SMS Gateway**
   - Provider: Taiwan SMS Provider
   - Endpoint: https://api.sms-provider.com.tw
   - Rate Limit: 100 msg/minute

### Internal Services
1. **Authentication Service**
   - Port: 8000
   - Health: /api/v1/auth/health

2. **Analytics Service**
   - Endpoints: executive, operations, financial, performance
   - Cache: 5 minutes

3. **Notification Service**
   - Types: SMS, Email, Push
   - Queue: Cloud Tasks

## Emergency Procedures

### System Down
1. Check all services
   ```bash
   kubectl get all -n default
   ```

2. Check ingress
   ```bash
   kubectl describe ingress luckygas-ingress
   ```

3. Emergency scale up
   ```bash
   ./scripts/emergency-scale.sh
   ```

### Data Corruption
1. Stop writes
   ```bash
   kubectl scale deployment luckygas-backend --replicas=0
   ```

2. Assess damage
   ```sql
   -- Check data integrity
   SELECT COUNT(*) FROM orders WHERE 預定配送日期 IS NULL;
   ```

3. Restore from backup
   ```bash
   ./deploy/restore-database.sh <backup_id>
   ```

### Security Breach
1. Isolate affected components
2. Rotate all credentials
3. Enable enhanced logging
4. Contact security team

## Contact Information

### Internal Contacts
- **Platform Team**: platform@luckygas.com.tw
- **Database Team**: database@luckygas.com.tw
- **Security Team**: security@luckygas.com.tw

### External Support
- **Google Cloud**: +886-2-8729-6000
- **Database Support**: +886-2-2345-6789
- **CDN Support**: +886-2-3456-7890

### Escalation Matrix
1. L1 - On-call Engineer (0-15 min)
2. L2 - Team Lead (15-30 min)
3. L3 - Director of Engineering (30-60 min)
4. L4 - CTO (60+ min)

---

**Last Updated**: 2025-01-29
**Version**: 1.0.0
**Next Review**: 2025-02-28