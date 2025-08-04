# 🚨 Lucky Gas Disaster Recovery Playbook

## 📋 Overview

This playbook provides step-by-step procedures for recovering Lucky Gas systems from various disaster scenarios.

## 🎯 Recovery Objectives

- **RTO (Recovery Time Objective)**: 4 hours
- **RPO (Recovery Point Objective)**: 1 hour
- **Priority**: 1) Authentication → 2) Orders → 3) Routes → 4) Analytics

## 🚨 Incident Response Team

| Role | Primary | Backup | Contact |
|------|---------|---------|---------|
| Incident Commander | CTO | VP Engineering | +886-xxx-xxxx |
| Technical Lead | Lead DevOps | Senior Backend | +886-xxx-xxxx |
| Database Admin | DBA | Senior Backend | +886-xxx-xxxx |
| Communications | Customer Success | Operations | +886-xxx-xxxx |

## 📊 System Health Dashboard

Before declaring a disaster, check:
- https://console.cloud.google.com/monitoring (Lucky Gas Dashboard)
- https://status.cloud.google.com/ (GCP Status)
- Internal monitoring at https://grafana.luckygas.com.tw

## 🔥 Disaster Scenarios

### 1. Complete Backend Failure

**Symptoms**: 
- API returns 5xx errors or timeouts
- Health check failing
- Cloud Run instances crashing

**Recovery Steps**:

```bash
# 1. Check Cloud Run status
gcloud run services describe luckygas-backend --region asia-east1

# 2. Check recent deployments
gcloud run revisions list --service luckygas-backend --region asia-east1

# 3. Rollback to last known good version
gcloud run services update-traffic luckygas-backend \
  --to-revisions=luckygas-backend-00042-abc=100 \
  --region asia-east1

# 4. If rollback fails, redeploy from stable image
gcloud run deploy luckygas-backend \
  --image gcr.io/luckygas-production/backend:stable \
  --region asia-east1

# 5. Verify health
curl https://api.luckygas.com.tw/api/v1/health
```

### 2. Database Failure

**Symptoms**:
- Connection timeouts
- "Database unavailable" errors
- Slow queries

**Recovery Steps**:

```bash
# 1. Check database status
gcloud sql instances describe luckygas-db-production

# 2. Check recent backups
gcloud sql backups list --instance=luckygas-db-production

# 3. If database is corrupted, restore from backup
BACKUP_ID=$(gcloud sql backups list --instance=luckygas-db-production \
  --limit=1 --format="value(id)")

gcloud sql backups restore $BACKUP_ID \
  --restore-instance=luckygas-db-production

# 4. If instance is unrecoverable, create new instance
gcloud sql instances create luckygas-db-recovery \
  --database-version=POSTGRES_15 \
  --tier=db-n1-standard-4 \
  --region=asia-east1

# 5. Restore from Cloud Storage backup
gsutil cp gs://luckygas-backups/latest-backup.sql .
gcloud sql import sql luckygas-db-recovery latest-backup.sql \
  --database=luckygas

# 6. Update connection string in Secret Manager
echo -n "postgresql://user:pass@new-instance/luckygas" | \
  gcloud secrets versions add database-url --data-file=-

# 7. Restart backend to pick up new connection
gcloud run services update luckygas-backend --region asia-east1
```

### 3. Frontend CDN Failure

**Symptoms**:
- Website not loading
- 404 errors
- Stale content

**Recovery Steps**:

```bash
# 1. Check bucket status
gsutil ls -L gs://luckygas-frontend/

# 2. Re-upload frontend files
cd frontend
npm run build
gsutil -m rsync -r -d dist/ gs://luckygas-frontend/

# 3. Invalidate CDN cache
gcloud compute url-maps invalidate-cdn-cache luckygas-lb \
  --path "/*"

# 4. If bucket is corrupted, restore from backup
gsutil -m rsync -r gs://luckygas-frontend-backup/ gs://luckygas-frontend/
```

### 4. Regional Outage

**Symptoms**:
- All services in asia-east1 unavailable
- GCP status page shows regional issues

**Recovery Steps**:

```bash
# 1. Activate DR region (asia-southeast1)
cd infrastructure/terraform
terraform workspace select disaster-recovery
terraform apply -var="region=asia-southeast1" -auto-approve

# 2. Update DNS to point to DR region
gcloud dns record-sets transaction start --zone=luckygas-zone
gcloud dns record-sets transaction add \
  --name=api.luckygas.com.tw \
  --ttl=60 \
  --type=A \
  --zone=luckygas-zone \
  --rrdatas="DR_IP_ADDRESS"
gcloud dns record-sets transaction execute --zone=luckygas-zone

# 3. Restore latest database backup to DR region
gsutil cp gs://luckygas-backups/latest-backup.sql .
gcloud sql import sql luckygas-db-dr latest-backup.sql \
  --database=luckygas
```

### 5. Data Corruption

**Symptoms**:
- Inconsistent data
- Application errors
- Customer complaints about wrong information

**Recovery Steps**:

```sql
-- 1. Connect to database
gcloud sql connect luckygas-db-production --user=postgres

-- 2. Identify corrupted data
SELECT COUNT(*), DATE(created_at) 
FROM orders 
WHERE status = 'corrupted'
GROUP BY DATE(created_at);

-- 3. Begin transaction for safety
BEGIN;

-- 4. Restore from audit log
INSERT INTO orders_recovery
SELECT * FROM orders_audit 
WHERE created_at > '2025-01-20 00:00:00'
AND id NOT IN (SELECT id FROM orders WHERE status != 'corrupted');

-- 5. Verify data
SELECT COUNT(*) FROM orders_recovery;

-- 6. If correct, replace corrupted data
DELETE FROM orders WHERE status = 'corrupted';
INSERT INTO orders SELECT * FROM orders_recovery;

-- 7. Commit or rollback
COMMIT; -- or ROLLBACK;
```

### 6. Security Breach

**Symptoms**:
- Unusual API activity
- Unauthorized access attempts
- Data exfiltration alerts

**Recovery Steps**:

```bash
# 1. IMMEDIATE: Block suspicious IPs
gcloud compute security-policies rules create 9999 \
  --security-policy=luckygas-security-policy \
  --expression="origin.ip in ['SUSPICIOUS_IP']" \
  --action=deny-403

# 2. Rotate all secrets
gcloud secrets versions add secret-key --data-file=<(openssl rand -base64 32)
gcloud secrets versions add database-password --data-file=<(openssl rand -base64 32)

# 3. Force all users to re-authenticate
# Run this SQL to invalidate all sessions
gcloud sql connect luckygas-db-production --user=postgres
UPDATE users SET last_token_refresh = NOW() - INTERVAL '1 year';

# 4. Enable additional logging
gcloud logging write security-incident \
  "Security incident detected at $(date)" \
  --severity=CRITICAL

# 5. Review audit logs
gcloud logging read "resource.type=cloud_run_revision AND severity>=WARNING" \
  --limit=100 --format=json > security-audit.json
```

### 7. Complete System Recovery

**When all else fails**, recover entire system from scratch:

```bash
# 1. Run Terraform to recreate infrastructure
cd infrastructure/terraform
terraform init
terraform apply -auto-approve

# 2. Restore latest database backup
LATEST_BACKUP=$(gsutil ls gs://luckygas-backups/ | tail -1)
gsutil cp $LATEST_BACKUP latest-backup.sql
gcloud sql import sql luckygas-db-production latest-backup.sql

# 3. Deploy backend
cd ../../backend
docker build -t gcr.io/luckygas-production/backend:recovery .
docker push gcr.io/luckygas-production/backend:recovery
gcloud run deploy luckygas-backend \
  --image gcr.io/luckygas-production/backend:recovery

# 4. Deploy frontend
cd ../frontend
npm run build
gsutil -m rsync -r -d dist/ gs://luckygas-frontend/

# 5. Verify system health
./infrastructure/scripts/health-check-all.sh
```

## 📞 Vendor Support Contacts

| Service | Support Level | Contact | Account # |
|---------|--------------|---------|-----------|
| Google Cloud | Premium | +886-2-2326-1099 | C-XXXXXX |
| Cloudflare | Enterprise | support@cloudflare.com | XXXXXX |
| SendGrid | Pro | support@sendgrid.com | XXXXXX |

## 📝 Post-Incident Procedures

After recovery:

1. **Document Timeline**
   ```
   - Incident detected: YYYY-MM-DD HH:MM
   - Recovery started: YYYY-MM-DD HH:MM
   - Service restored: YYYY-MM-DD HH:MM
   - Full recovery: YYYY-MM-DD HH:MM
   ```

2. **Calculate Impact**
   - Downtime duration
   - Affected users count
   - Lost revenue estimate
   - SLA compliance

3. **Root Cause Analysis**
   - What failed?
   - Why did it fail?
   - How to prevent recurrence?

4. **Update Runbooks**
   - Document new procedures
   - Update contact information
   - Revise recovery steps

5. **Customer Communication**
   - Send incident report
   - Offer compensation if needed
   - Publish post-mortem

## 🧪 Recovery Testing Schedule

| Scenario | Frequency | Last Tested | Next Test |
|----------|-----------|-------------|-----------|
| Backend rollback | Monthly | 2025-01-15 | 2025-02-15 |
| Database restore | Quarterly | 2024-12-20 | 2025-03-20 |
| Regional failover | Bi-annual | 2024-10-01 | 2025-04-01 |
| Full recovery | Annual | 2024-07-15 | 2025-07-15 |

## 🔐 Access Requirements

Ensure these accesses are available to on-call personnel:

- [ ] GCP Console access with Owner role
- [ ] Database admin credentials in 1Password
- [ ] Domain registrar access
- [ ] Monitoring dashboard access
- [ ] Communication channels (Slack, email)
- [ ] This playbook (offline copy)

## 📱 Mobile Apps (Future)

For mobile app incidents:
- App Store Connect access for iOS
- Google Play Console access for Android
- Push notification service credentials
- App signing keys in secure storage

---

**Remember**: Stay calm, follow the playbook, and communicate regularly with stakeholders.