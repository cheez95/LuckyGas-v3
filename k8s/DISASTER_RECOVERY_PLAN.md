# LuckyGas Disaster Recovery Plan

## Overview

This document outlines the disaster recovery (DR) procedures for the LuckyGas production system. It covers various failure scenarios and provides step-by-step recovery procedures.

## Recovery Objectives

- **Recovery Time Objective (RTO)**: 2 hours
- **Recovery Point Objective (RPO)**: 1 hour
- **Maximum Tolerable Downtime (MTD)**: 4 hours

## Failure Scenarios and Recovery Procedures

### 1. Application Pod Failures

#### Symptoms
- Pods in CrashLoopBackOff state
- High error rates
- Service unavailable errors

#### Recovery Steps

1. **Identify failing pods**:
   ```bash
   kubectl get pods -n luckygas | grep -v Running
   ```

2. **Check pod logs**:
   ```bash
   kubectl logs <pod-name> -n luckygas --previous
   ```

3. **Describe pod for events**:
   ```bash
   kubectl describe pod <pod-name> -n luckygas
   ```

4. **Quick recovery - restart pods**:
   ```bash
   kubectl rollout restart deployment/<deployment-name> -n luckygas
   ```

5. **If persistent, rollback to previous version**:
   ```bash
   kubectl rollout undo deployment/<deployment-name> -n luckygas
   ```

### 2. Database Failure

#### Symptoms
- Database connection errors
- Application unable to persist data
- Health check failures

#### Recovery Steps

1. **Check Cloud SQL instance status**:
   ```bash
   gcloud sql instances describe luckygas-db-production-<suffix>
   ```

2. **For minor issues, restart instance**:
   ```bash
   gcloud sql instances restart luckygas-db-production-<suffix>
   ```

3. **For major failures, failover to replica** (if available):
   ```bash
   gcloud sql instances failover luckygas-db-production-<suffix>
   ```

4. **Restore from backup if needed**:
   ```bash
   # List available backups
   gcloud sql backups list --instance=luckygas-db-production-<suffix>
   
   # Restore from backup
   gcloud sql backups restore <backup-id> \
     --restore-instance=luckygas-db-production-<suffix>
   ```

5. **Update connection strings if IP changed**:
   ```bash
   # Update secret in Kubernetes
   kubectl create secret generic luckygas-backend-secrets \
     --from-literal=DATABASE_URL=<new-connection-string> \
     -n luckygas --dry-run=client -o yaml | kubectl apply -f -
   ```

### 3. Complete Cluster Failure

#### Symptoms
- Unable to connect to Kubernetes API
- All services down
- GKE cluster unreachable

#### Recovery Steps

1. **Check cluster status**:
   ```bash
   gcloud container clusters describe luckygas-cluster \
     --zone asia-east1-a
   ```

2. **If cluster is recoverable, repair it**:
   ```bash
   gcloud container clusters repair luckygas-cluster \
     --zone asia-east1-a
   ```

3. **If cluster is unrecoverable, create new cluster from Terraform**:
   ```bash
   cd terraform/
   terraform plan -var="environment=production"
   terraform apply -var="environment=production"
   ```

4. **Restore applications**:
   ```bash
   cd k8s/
   ./scripts/deploy.sh production
   ```

5. **Restore persistent data from backups**

### 4. Data Corruption

#### Symptoms
- Inconsistent data
- Application errors related to data integrity
- Customer complaints about incorrect information

#### Recovery Steps

1. **Identify scope of corruption**:
   ```sql
   -- Connect to database
   -- Run integrity checks
   SELECT COUNT(*) FROM orders WHERE created_at > NOW() - INTERVAL '1 day';
   ```

2. **Restore specific tables from backup**:
   ```bash
   # Export specific tables from backup
   pg_dump -h <backup-host> -U postgres -t <table_name> luckygas > table_backup.sql
   
   # Import to production
   psql -h <prod-host> -U postgres luckygas < table_backup.sql
   ```

3. **Run data validation scripts**:
   ```bash
   kubectl exec -it <backend-pod> -n luckygas -- python manage.py validate_data
   ```

### 5. Security Breach

#### Symptoms
- Unauthorized access detected
- Suspicious activity in logs
- Data exfiltration alerts

#### Recovery Steps

1. **Immediate isolation**:
   ```bash
   # Apply network policy to isolate affected components
   kubectl apply -f k8s/emergency/isolation-policy.yaml
   ```

2. **Rotate all credentials**:
   ```bash
   # Rotate database passwords
   gcloud sql users set-password luckygas_app \
     --instance=luckygas-db-production-<suffix> \
     --password=<new-password>
   
   # Update Kubernetes secrets
   ./scripts/rotate-secrets.sh production
   ```

3. **Review audit logs**:
   ```bash
   gcloud logging read "resource.type=k8s_cluster" \
     --project=luckygas-production \
     --limit=1000
   ```

4. **Apply security patches and restart**:
   ```bash
   ./scripts/emergency-patch.sh
   kubectl rollout restart deployment --all -n luckygas
   ```

## Backup Procedures

### Database Backups

**Automated backups** are configured in Cloud SQL:
- Daily backups at 3:00 AM Taiwan time
- 30-day retention for production
- Point-in-time recovery enabled

**Manual backup**:
```bash
gcloud sql backups create \
  --instance=luckygas-db-production-<suffix> \
  --description="Manual backup before maintenance"
```

### Application Data Backups

**Storage bucket backups**:
```bash
# Sync to backup bucket
gsutil -m rsync -r -d \
  gs://luckygas-app-data-production \
  gs://luckygas-backups-production/$(date +%Y%m%d)
```

### Kubernetes Configuration Backups

**Export all resources**:
```bash
kubectl get all,cm,secret,pvc,pv,ingress -n luckygas -o yaml > backup-$(date +%Y%m%d).yaml
```

## Testing Procedures

### Monthly DR Drills

1. **Backup restoration test**:
   - Restore database to staging environment
   - Verify data integrity
   - Test application functionality

2. **Failover test**:
   - Simulate pod failures
   - Test automatic recovery
   - Measure recovery time

3. **Communication test**:
   - Test alert notifications
   - Verify escalation procedures
   - Update contact information

## Communication Plan

### Incident Response Team

| Role | Name | Phone | Email |
|------|------|-------|-------|
| Incident Commander | TBD | +886-XXX-XXXX | ic@luckygas.com.tw |
| Technical Lead | TBD | +886-XXX-XXXX | tech@luckygas.com.tw |
| Database Admin | TBD | +886-XXX-XXXX | dba@luckygas.com.tw |
| Communications | TBD | +886-XXX-XXXX | comm@luckygas.com.tw |

### Escalation Matrix

1. **Level 1** (0-30 min): On-call engineer
2. **Level 2** (30-60 min): Technical lead
3. **Level 3** (60+ min): CTO and executive team

### Customer Communication

- **Minor incidents**: Status page update only
- **Major incidents**: Email to affected customers + status page
- **Critical incidents**: Phone calls to key accounts + email + status page

## Recovery Validation

### Post-Recovery Checklist

- [ ] All pods running and healthy
- [ ] Database connections established
- [ ] API endpoints responding
- [ ] Frontend accessible
- [ ] WebSocket connections working
- [ ] Background jobs processing
- [ ] Monitoring and alerts functional
- [ ] Recent orders can be viewed
- [ ] New orders can be created
- [ ] Driver app functional
- [ ] SMS notifications working
- [ ] Payment processing operational

### Performance Validation

```bash
# Run smoke tests
./k8s/scripts/smoke-tests.sh production

# Run load test
kubectl run -it --rm load-test --image=luckygas/load-test \
  --restart=Never -- /scripts/load-test.sh

# Check metrics
kubectl top nodes
kubectl top pods -n luckygas
```

## Important Commands Reference

### Cluster Management
```bash
# Get cluster credentials
gcloud container clusters get-credentials luckygas-cluster \
  --zone asia-east1-a --project luckygas-production

# Check cluster status
kubectl cluster-info
kubectl get nodes
```

### Application Management
```bash
# Check application status
kubectl get all -n luckygas

# View logs
kubectl logs -f deployment/luckygas-backend -n luckygas

# Execute commands in pod
kubectl exec -it deployment/luckygas-backend -n luckygas -- /bin/bash
```

### Database Management
```bash
# Connect to database
gcloud sql connect luckygas-db-production-<suffix> --user=postgres

# Export database
gcloud sql export sql luckygas-db-production-<suffix> \
  gs://luckygas-backups-production/manual-backup-$(date +%Y%m%d).sql \
  --database=luckygas
```

## Preventive Measures

1. **Regular backups**: Automated daily backups with tested restoration
2. **Monitoring**: Comprehensive monitoring with proactive alerts
3. **Redundancy**: Multi-zone deployment with automatic failover
4. **Security**: Regular security audits and patch management
5. **Documentation**: Keep DR procedures updated and accessible
6. **Training**: Regular DR drills for the operations team

## Document Maintenance

This document should be reviewed and updated:
- After any major infrastructure changes
- After each DR drill
- At least quarterly
- After any actual incident

Last Updated: 2025-01-27
Next Review: 2025-04-27