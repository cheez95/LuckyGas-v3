# Weekend UAT Support Plan

**Effective**: February 1-2, 2025 (Weekend before UAT)

## 📅 Support Schedule

### Saturday, February 1
- **On-Call Hours**: 9:00 AM - 9:00 PM
- **Primary**: David Chen (陳工程師)
- **Backup**: Lisa Wang (王工程師)
- **Manager**: Michael Zhang (張經理)

### Sunday, February 2
- **On-Call Hours**: 9:00 AM - 11:00 PM (Extended for URL deployment)
- **Primary**: Lisa Wang (王工程師)
- **Backup**: David Chen (陳工程師)
- **Manager**: Michael Zhang (張經理)

### Shift Handover
- Handover at 6:00 PM each day
- 15-minute overlap for status update
- Document all ongoing issues

## 📞 Emergency Contacts

### Primary Support Line
- **Number**: 0900-123-456
- **Available**: During on-call hours
- **Response Time**: Within 15 minutes

### Escalation Contacts
1. **Level 1** - On-Call Engineer
   - Direct phone call
   - Response within 15 minutes

2. **Level 2** - Backup Engineer
   - If primary doesn't respond in 15 minutes
   - Can assist with complex issues

3. **Level 3** - IT Manager
   - For critical decisions
   - Infrastructure failures
   - Michael Zhang: 0900-234-567

4. **Level 4** - CTO
   - For business-critical decisions
   - System-wide failures
   - Dr. Lin: 0900-345-678 (emergency only)

### Vendor Contacts
- **Cloud Provider**: GCP Support - [Support ticket system]
- **Database Admin**: James Liu - 0900-456-789
- **Network Team**: Network Ops - 0900-567-890

## 🚨 Priority Issue Categories

### P1 - Critical (Response: 30 minutes)
- Complete system outage
- Authentication service down
- Database unreachable
- Data loss or corruption
- Security breach

**Actions**:
1. Immediately call primary on-call
2. Start incident log
3. Notify IT Manager
4. Begin troubleshooting

### P2 - High (Response: 1 hour)
- Major feature unavailable
- Performance degradation >50%
- Integration failures
- Partial outages

**Actions**:
1. Contact on-call engineer
2. Document issue details
3. Attempt workaround
4. Schedule fix

### P3 - Medium (Response: 4 hours)
- Minor feature issues
- UI/UX problems
- Non-critical bugs
- Slow performance <50%

**Actions**:
1. Log in issue tracker
2. Email on-call engineer
3. Provide workaround to users
4. Plan Monday fix

### P4 - Low (Response: Next business day)
- Cosmetic issues
- Feature requests
- Documentation updates
- Training questions

**Actions**:
1. Document for Monday
2. Add to UAT feedback log

## 🛠️ Common Issues & Solutions

### 1. Deployment Issues
**Problem**: Staging deployment fails
**Solution**:
```bash
# Check deployment status
kubectl get pods -n staging

# Rollback if needed
kubectl rollout undo deployment/backend -n staging

# Check logs
kubectl logs -f deployment/backend -n staging
```

### 2. Database Connection
**Problem**: Database connection errors
**Solution**:
1. Check connection pool: `pgbouncer stats`
2. Verify credentials in secrets
3. Restart connection pool if needed
4. Check firewall rules

### 3. Authentication Failures
**Problem**: Users cannot login
**Solution**:
1. Verify JWT secret is set
2. Check Redis connectivity
3. Clear user session cache
4. Verify CORS settings

### 4. Performance Issues
**Problem**: Slow response times
**Solution**:
1. Check CPU/Memory usage
2. Review slow query logs
3. Scale pods if needed
4. Clear application cache

## 📋 Escalation Procedures

### When to Escalate
- Issue exceeds your technical capability
- Requires infrastructure changes
- Involves data loss risk
- Needs business decision
- Security implications

### How to Escalate
1. **Document Current State**
   - What's the issue?
   - What's been tried?
   - What's the impact?
   - What's needed?

2. **Contact Next Level**
   - Call, don't text for P1/P2
   - Provide issue summary
   - Share remote access if needed
   - Stay on to assist

3. **Update Stakeholders**
   - Send status email every hour for P1
   - Update WhatsApp group for P2
   - Log all actions taken

## 🔧 Emergency Procedures

### System Recovery
1. **Assess Impact**
   - Which services affected?
   - How many users impacted?
   - Data integrity status?

2. **Stabilize System**
   ```bash
   # Quick health check
   ./scripts/health-check.sh
   
   # Emergency restart
   docker-compose restart
   
   # Check critical services
   ./scripts/validate-deployment.sh
   ```

3. **Communicate Status**
   - Update status page
   - Notify UAT participants
   - Email stakeholders

### Data Recovery
1. **Stop Write Operations**
   - Enable read-only mode
   - Prevent further corruption

2. **Assess Damage**
   - Check backup status
   - Identify affected records
   - Estimate recovery time

3. **Execute Recovery**
   - Use latest clean backup
   - Apply transaction logs
   - Verify data integrity

## 📱 Communication Templates

### Status Update Template
```
[P1/P2/P3] Issue Status Update
Time: [HH:MM]
Issue: [Brief description]
Impact: [User impact]
Actions: [What's being done]
ETA: [Resolution estimate]
Next Update: [Time]
```

### Escalation Template
```
ESCALATION REQUIRED
Priority: [P1/P2]
Issue: [Description]
Attempted Solutions: [List]
Current Status: [State]
Assistance Needed: [Specific help]
Contact: [Your phone]
```

## 🔐 Access Information

### Critical Systems
- **Staging Environment**: [URLs in secure doc]
- **Monitoring**: [Grafana URL]
- **Logs**: [CloudWatch/Stackdriver]
- **Kubernetes**: `kubectl config use-context staging`

### Emergency Access
- **Break-glass Admin**: admin@luckygas.tw
- **Password**: [In secure vault]
- **2FA Bypass**: [Contact IT Manager]

## 📝 Post-Incident Procedures

1. **Document Everything**
   - Timeline of events
   - Actions taken
   - Resolution steps
   - Lessons learned

2. **Update Runbooks**
   - Add new solutions
   - Update contact info
   - Revise procedures

3. **Monday Handoff**
   - Brief Monday team
   - Transfer open issues
   - Share recommendations

## ✅ Weekend Checklist

### Saturday Morning
- [ ] Verify staging environment is up
- [ ] Check all test accounts work
- [ ] Confirm monitoring alerts are active
- [ ] Test support phone line
- [ ] Review priority issues from Friday

### Sunday Evening
- [ ] Deploy final staging URLs
- [ ] Send URL notification emails
- [ ] Verify all services are healthy
- [ ] Clear test data if needed
- [ ] Prepare Monday handoff notes

---

**Remember**: 
- Stay calm under pressure
- Document everything
- Don't hesitate to escalate
- User communication is key
- We're all in this together

**Good luck with weekend support!** 🍀