# LuckyGas Launch Day Runbook

## 🚀 Production Go-Live Timeline

**Target Launch Date**: [DATE]  
**Launch Window**: 02:00 - 06:00 TST (Taiwan Standard Time)  
**War Room**: Slack #luckygas-launch  
**Video Bridge**: https://meet.google.com/luckygas-launch

---

## T-24 Hours: Final Staging Validation

### 14:00 - System Validation
- [ ] Run complete Playwright E2E test suite
  ```bash
  cd e2e && npm test -- --reporter=html
  ```
- [ ] Verify all 100+ tests pass
- [ ] Review test report for any warnings
- [ ] Document any known issues

### 16:00 - Performance Testing
- [ ] Run load tests on staging
  ```bash
  k6 run scripts/load-test.js --vus 100 --duration 30m
  ```
- [ ] Verify response times < 2s under load
- [ ] Check resource utilization
- [ ] Test Google Maps API integration under load

### 18:00 - Security Scan
- [ ] Run final security scan
  ```bash
  ./scripts/security-scan.sh staging
  ```
- [ ] Review and address any HIGH/CRITICAL findings
- [ ] Verify SSL certificates active
- [ ] Test WAF rules

### 20:00 - Data Validation
- [ ] Verify staging database matches production schema
- [ ] Test data migration scripts on staging copy
- [ ] Validate 預定配送日期 field functionality
- [ ] Confirm backup/restore procedures

**Decision Point**: GO/NO-GO for T-12 preparations

---

## T-12 Hours: Production Environment Setup

### 02:00 - Infrastructure Preparation
- [ ] Scale production cluster
  ```bash
  gcloud container clusters resize lucky-gas-prod --num-nodes=10
  ```
- [ ] Verify all nodes healthy
- [ ] Check resource quotas
- [ ] Enable production monitoring alerts

### 04:00 - Database Preparation
- [ ] Create production database backup
  ```bash
  ./deploy/backup-database.sh
  ```
- [ ] Verify backup uploaded to GCS
- [ ] Test backup restoration process
- [ ] Enable point-in-time recovery

### 06:00 - Configuration Validation
- [ ] Verify all production secrets set
  ```bash
  kubectl get secrets -n default
  ```
- [ ] Confirm environment variables
- [ ] Test external service connections
- [ ] Validate DNS propagation

### 08:00 - Team Notification
- [ ] Send launch preparation email
- [ ] Confirm on-call assignments
- [ ] Share emergency contact list
- [ ] Test communication channels

**Decision Point**: GO/NO-GO for T-6 activities

---

## T-6 Hours: Database Migration Dry Run

### 20:00 - Migration Testing
- [ ] Clone production database to test instance
  ```bash
  gcloud sql instances clone luckygas-prod luckygas-prod-test
  ```
- [ ] Run migration scripts on test instance
  ```bash
  ./scripts/migrate-production-dry-run.sh
  ```
- [ ] Verify all migrations successful
- [ ] Test rollback procedures

### 21:00 - Data Validation
- [ ] Verify customer data integrity
- [ ] Check 預定配送日期 field data
- [ ] Validate analytics aggregations
- [ ] Test critical queries performance

### 22:00 - Final Staging Deploy
- [ ] Deploy final build to staging
  ```bash
  ./deploy/deploy-staging.sh v1.0.0
  ```
- [ ] Run smoke tests
- [ ] Verify all integrations working
- [ ] Check monitoring dashboards

**Decision Point**: GO/NO-GO for T-2 briefing

---

## T-2 Hours: Team Briefing & Role Assignments

### 00:00 - Team Assembly
- [ ] All team members join war room
- [ ] Verify everyone has necessary access
- [ ] Test screen sharing and communication
- [ ] Review emergency procedures

### 00:15 - Role Assignments

| Role | Primary | Backup | Responsibilities |
|------|---------|--------|------------------|
| Launch Commander | [Name] | [Name] | Overall coordination, decisions |
| Backend Lead | [Name] | [Name] | API deployment, database |
| Frontend Lead | [Name] | [Name] | UI deployment, CDN |
| Database Admin | [Name] | [Name] | Migrations, backups |
| DevOps Lead | [Name] | [Name] | Infrastructure, monitoring |
| QA Lead | [Name] | [Name] | Validation, testing |
| Comms Lead | [Name] | [Name] | Status updates, customer comm |
| Security Lead | [Name] | [Name] | Security monitoring, incidents |

### 00:30 - Checklist Review
- [ ] Review go-live checklist together
- [ ] Confirm rollback procedures understood
- [ ] Verify emergency contacts updated
- [ ] Test incident response tools

### 00:45 - Final System Checks
- [ ] All monitoring dashboards loading
- [ ] Alerting systems operational
- [ ] Backup systems verified
- [ ] Communication channels active

**Decision Point**: FINAL GO/NO-GO Decision

---

## T-1 Hour: Final Go/No-Go Decision

### 01:00 - Leadership Review
- [ ] Review all system statuses
- [ ] Assess team readiness
- [ ] Check weather/external factors
- [ ] Make final GO/NO-GO decision

### 01:15 - Go Decision Communications
- [ ] Update status page: "Scheduled Maintenance"
- [ ] Send customer notifications
- [ ] Alert support team
- [ ] Post internal announcement

### 01:30 - Final Preparations
- [ ] Start recording session
- [ ] Open monitoring dashboards
- [ ] Prepare rollback scripts
- [ ] Clear deployment pipeline

### 01:45 - Pre-Launch Prayer Circle 🙏
- [ ] Team motivation speech
- [ ] Final questions addressed
- [ ] Confirm everyone ready
- [ ] Start deployment countdown

---

## T-0: Execute Deployment

### 02:00 - Initiate Launch Sequence
```bash
./launch-sequence.sh
```

### 02:05 - Phase 1: Pre-Deployment
- [ ] Automated pre-flight checks running
- [ ] Monitor check results
- [ ] Address any warnings
- [ ] Confirm proceed to Phase 2

### 02:15 - Phase 2: Database Migration
- [ ] Migration scripts executing
- [ ] Monitor migration progress
- [ ] Verify no errors
- [ ] Confirm data integrity

### 02:30 - Phase 3: Blue-Green Deployment
- [ ] New version deploying to green
- [ ] Health checks passing
- [ ] Smoke tests successful
- [ ] Ready for traffic switch

### 02:45 - Phase 4: Traffic Migration
- [ ] 5% traffic → monitor 30 min
- [ ] 25% traffic → monitor 1 hour
- [ ] 50% traffic → monitor 2 hours
- [ ] 100% traffic → full production

### Continuous Monitoring
- [ ] Watch error rates (< 1%)
- [ ] Monitor response times (< 2s)
- [ ] Check system resources
- [ ] Verify order processing

---

## T+1 Hour: First Health Check

### 03:00 - System Validation
- [ ] Run post-deployment validation
  ```bash
  ./deploy/post-deploy-validation.sh
  ```
- [ ] Create test orders with 預定配送日期
- [ ] Verify analytics dashboards
- [ ] Test all critical paths

### 03:15 - Performance Review
- [ ] Check response time metrics
- [ ] Review error logs
- [ ] Analyze resource usage
- [ ] Compare to baseline

### 03:30 - Initial Success Criteria
- [ ] Zero customer-facing errors ✓
- [ ] All orders processing correctly ✓
- [ ] Analytics dashboards accurate ✓
- [ ] Mobile app functional ✓

### 03:45 - Status Update
- [ ] Update status page: "Operational"
- [ ] Send success notification to stakeholders
- [ ] Post metrics to #luckygas-launch
- [ ] Schedule T+4h review

---

## T+4 Hours: Performance Review

### 06:00 - Comprehensive Review
- [ ] Analyze 4 hours of production data
- [ ] Review all monitoring dashboards
- [ ] Check customer feedback/support tickets
- [ ] Assess system stability

### 06:30 - Team Debrief
- [ ] What went well?
- [ ] What could improve?
- [ ] Any concerns for next 24h?
- [ ] Action items identified

### 07:00 - Stakeholder Update
- [ ] Prepare executive summary
- [ ] Share key metrics
- [ ] Highlight successes
- [ ] Note any issues

---

## T+24 Hours: First Day Retrospective

### Day+1 14:00 - Full Team Retrospective

#### Metrics Review
- [ ] Total orders processed
- [ ] Average response time
- [ ] Error rate percentage
- [ ] Customer complaints
- [ ] System availability

#### Technical Review
- [ ] Any production issues?
- [ ] Performance bottlenecks?
- [ ] Unexpected behaviors?
- [ ] Security incidents?

#### Process Review
- [ ] Launch process effectiveness
- [ ] Communication clarity
- [ ] Tool reliability
- [ ] Team coordination

#### Lessons Learned
1. What worked well:
   - 
   - 
   
2. What needs improvement:
   - 
   - 

3. Action items:
   - 
   - 

#### Success Celebration 🎉
- [ ] Team lunch/dinner
- [ ] Success announcement
- [ ] Thank you messages
- [ ] Plan optimization phase

---

## Emergency Procedures

### 🚨 Rollback Triggers
Any of these trigger immediate rollback:
- Error rate > 5%
- Response time > 5 seconds
- Database corruption detected
- Security breach identified
- Complete service outage

### 🔄 Rollback Procedure
```bash
# Immediate rollback
./deploy/rollback.sh

# Time target: < 2 minutes
```

### 📞 Escalation Chain
1. On-call Engineer
2. Team Lead: [Phone]
3. Engineering Manager: [Phone]
4. CTO: [Phone]
5. CEO: [Phone] (P1 only)

### 🏥 War Room Protocols
- Location: Slack #luckygas-launch
- Video: https://meet.google.com/luckygas-launch
- Docs: https://docs.luckygas.com/launch
- Status: https://status.luckygas.com.tw

### 📋 Communication Templates

**Customer Notification (Planned)**:
```
Subject: LuckyGas 系統升級通知

親愛的客戶您好，

我們將於 [DATE] 02:00-06:00 進行系統升級，期間服務可能短暫中斷。

升級完成後，您將享受到更快速、更穩定的服務體驗。

造成不便，敬請見諒。

LuckyGas 團隊
```

**Incident Communication**:
```
Subject: LuckyGas 服務狀態更新

目前狀態：調查中
影響範圍：[描述]
預計修復：[時間]

我們正在積極處理，最新狀態請參考 status.luckygas.com.tw
```

---

## Post-Launch Checklist

### Immediate (T+0 to T+4)
- [ ] Monitor all dashboards
- [ ] Respond to any alerts
- [ ] Check customer feedback
- [ ] Document any issues

### Day 1 (T+24)
- [ ] Full metrics analysis
- [ ] Team retrospective
- [ ] Stakeholder report
- [ ] Plan optimizations

### Week 1
- [ ] Performance tuning
- [ ] Address any bugs
- [ ] Gather user feedback
- [ ] Update documentation

### Month 1
- [ ] Full system audit
- [ ] Capacity planning
- [ ] Feature roadmap update
- [ ] Team celebration event

---

**Document Version**: 1.0  
**Last Updated**: 2025-01-29  
**Next Review**: Post-launch

**Remember**: Stay calm, follow the runbook, trust the process. You've got this! 🚀