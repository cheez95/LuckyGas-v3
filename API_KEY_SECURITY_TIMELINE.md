# API Key Security Timeline & Implementation Guide

**Document Version**: 1.0  
**Last Updated**: January 27, 2025  
**Security Classification**: CONFIDENTIAL  
**System Readiness**: 88% (API Keys NOT included)

---

## 🚨 CRITICAL: Current Security Status

### Immediate Actions Required
1. **REVOKE** the exposed Google Maps API key immediately
2. **ENABLE** webhook signature validation (currently disabled)
3. **NEVER** commit actual API keys to git

### Current Implementation Status
- ✅ Secure proxy architecture implemented
- ✅ Secret Manager integration ready
- ✅ Key rotation automation built
- ⚠️ Webhook validation disabled
- ❌ Historical key exposure in git

---

## 📅 Phased API Key Implementation Timeline

### Phase 1: Development (NOW - Days 1-2)
**Goal**: Secure development environment with restricted keys

#### Actions:
1. **Create Development-Only Keys**
   ```bash
   # Google Maps API
   - Name: luckygas-dev-maps
   - Restrictions: localhost:*, 127.0.0.1:*
   - APIs: Maps JavaScript API, Geocoding API
   - Quota: 100 requests/day
   
   # Twilio Test Account
   - Use Twilio test credentials
   - Geographic permissions: Taiwan only
   - Test numbers only
   
   # SMS Gateway
   - Use sandbox environment
   - Rate limit: 10 SMS/hour
   ```

2. **Configure Local Development**
   ```bash
   # .env.development
   GOOGLE_MAPS_API_KEY=dev_restricted_key_here
   TWILIO_ACCOUNT_SID=AC_test_account_here
   SMS_GATEWAY_MODE=sandbox
   USE_SECRET_MANAGER=false
   ```

3. **Implement Placeholders**
   ```python
   # All production keys as placeholders
   BANKING_SFTP_USER=PLACEHOLDER_PROD_KEY
   EINVOICE_PROD_API_KEY=PLACEHOLDER_PROD_KEY
   ```

#### Validation Checklist:
- [ ] All dev keys have heavy restrictions
- [ ] No production keys in dev environment
- [ ] Proxy endpoints tested with dev keys
- [ ] Rate limiting verified

---

### Phase 2: Staging (Week 2 - Days 8-14)
**Goal**: Test production-like environment with staging keys

#### Actions:
1. **Create Staging-Specific Keys**
   ```bash
   # Google Cloud Project
   - Project: luckygas-staging
   - Service Account: staging-api-access@luckygas-staging
   
   # Google Maps API
   - Name: luckygas-staging-maps
   - Restrictions: staging.luckygas.tw, *.staging.luckygas.tw
   - APIs: All required APIs
   - Quota: 1,000 requests/day
   
   # SMS Gateway
   - Staging account with Taiwan numbers
   - Rate limit: 100 SMS/hour
   - Webhook URL: https://staging.luckygas.tw/webhooks/sms
   ```

2. **Enable Secret Manager**
   ```bash
   # Upload staging secrets
   gcloud secrets create google-maps-api-key-staging \
     --data-file=- \
     --replication-policy=automatic
   
   # Grant access
   gcloud secrets add-iam-policy-binding google-maps-api-key-staging \
     --member=serviceAccount:staging-api@luckygas.iam \
     --role=roles/secretmanager.secretAccessor
   ```

3. **Test Key Rotation**
   ```bash
   # Dry run rotation
   python scripts/rotate_secrets.py --env=staging --dry-run
   
   # Schedule test rotation
   python scripts/rotate_secrets.py --env=staging --secret=test-key
   ```

#### Validation Checklist:
- [ ] All staging keys properly restricted
- [ ] Secret Manager integration working
- [ ] Key rotation procedures tested
- [ ] Monitoring alerts configured
- [ ] Webhook validation enabled

---

### Phase 3: Pilot (Week 3 - Days 15-21)
**Goal**: Limited production deployment with conservative limits

#### Actions:
1. **Generate Production Keys (Low Limits)**
   ```bash
   # Google Maps API
   - Name: luckygas-prod-maps-pilot
   - Restrictions: app.luckygas.tw, www.luckygas.tw
   - APIs: Maps, Places, Geocoding, Directions
   - Quota: 5,000 requests/day (pilot limit)
   
   # Twilio Production
   - Subaccount for pilot
   - Geographic: Taiwan only
   - Toll fraud protection enabled
   - Daily spend limit: $50
   
   # Banking Integration
   - Read-only access initially
   - IP whitelist: Production servers only
   - Mutual TLS required
   ```

2. **Implement Gradual Rollout**
   ```python
   # Feature flags for API usage
   PILOT_USERS = ["user1", "user2", "user3", "user4", "user5"]
   
   # Gradual increase
   Day 1: 5 customers
   Day 2: 10 customers  
   Day 3: 25 customers
   Day 4: 50 customers
   ```

3. **Monitor Usage Patterns**
   ```python
   # Real-time monitoring
   - API quota usage dashboard
   - Anomaly detection alerts
   - Cost tracking per API
   - Geographic usage patterns
   ```

#### Validation Checklist:
- [ ] Production keys have strict limits
- [ ] Emergency revocation tested
- [ ] Usage monitoring active
- [ ] Cost alerts configured
- [ ] Rollback plan ready

---

### Phase 4: Full Production (Week 4 - Days 22-28)
**Goal**: Scale to full production with appropriate limits

#### Actions:
1. **Scale Production Keys**
   ```bash
   # Google Maps API
   - Quota: 50,000 requests/day
   - Enable billing alerts at 80%
   
   # SMS Gateway
   - Production capacity
   - Multiple provider failover
   - International SMS blocked
   
   # Banking Integration
   - Full read/write access
   - Transaction signing enabled
   - Hardware token integration
   ```

2. **Enable Advanced Security**
   ```python
   # Automated threat detection
   - Unusual geographic patterns
   - Spike detection
   - Repeated failure monitoring
   - Automatic temporary blocks
   ```

3. **Configure High Availability**
   ```yaml
   # Multiple API keys for failover
   primary_key: "prod-key-1"
   secondary_key: "prod-key-2"
   emergency_key: "prod-key-emergency"
   ```

---

## 🔒 Security Configuration by Service

### Google Maps API
```javascript
// Development
{
  restrictions: {
    http_referrers: ["http://localhost:*", "http://127.0.0.1:*"],
    apis: ["maps", "geocoding"],
    quota_limit: 100
  }
}

// Production
{
  restrictions: {
    http_referrers: ["https://*.luckygas.tw"],
    apis: ["maps", "places", "geocoding", "directions"],
    quota_limit: 50000,
    ip_restriction: ["Production_Server_IPs"]
  }
}
```

### SMS Gateway (Twilio)
```python
# Development
{
    "account_type": "test",
    "geographic_permissions": ["TW"],
    "messaging_service": "test_service",
    "rate_limit": "10/hour"
}

# Production
{
    "account_type": "production",
    "geographic_permissions": ["TW"],
    "messaging_service": "prod_service",
    "rate_limit": "1000/hour",
    "webhook_validation": "enabled",
    "toll_fraud_protection": "enabled"
}
```

### Banking SFTP
```yaml
# Never store actual credentials
# Use hardware security module (HSM) in production
development:
  access: "none"
  
staging:
  access: "read_only"
  test_accounts: true
  
production:
  access: "read_write"
  mfa_required: true
  ip_whitelist: required
  audit_logging: enabled
```

---

## 🚨 Emergency Procedures

### Key Compromise Response
```bash
# 1. Immediate Revocation
python scripts/emergency_security_response.py revoke-key --key-name=compromised_key

# 2. System Lockdown
python scripts/emergency_security_response.py lockdown --level=critical

# 3. Generate New Keys
python scripts/emergency_security_response.py rotate-all --emergency

# 4. Update All Services
python scripts/emergency_security_response.py update-services --validate

# 5. Incident Report
python scripts/emergency_security_response.py generate-report --incident-id=INC001
```

### Rate Limit Exceeded
```python
# Automatic fallback
if rate_limit_exceeded:
    switch_to_secondary_key()
    alert_operations_team()
    implement_temporary_throttling()
```

---

## ✅ Pre-Launch Security Checklist

### Critical (Must Complete)
- [ ] Revoke exposed Google Maps API key
- [ ] Enable webhook signature validation
- [ ] Configure domain restrictions on all keys
- [ ] Test emergency revocation procedures
- [ ] Implement rate limiting on all APIs
- [ ] Set up cost alerts for all services

### Important (Should Complete)
- [ ] Configure Secret Manager for all environments
- [ ] Test key rotation procedures
- [ ] Set up monitoring dashboards
- [ ] Document all API dependencies
- [ ] Train team on emergency procedures
- [ ] Create runbook for key management

### Nice to Have
- [ ] Implement automated security scanning
- [ ] Set up key usage analytics
- [ ] Create cost optimization reports
- [ ] Implement predictive scaling
- [ ] Set up compliance reporting

---

## 📊 Monitoring & Alerts

### Key Usage Metrics
```yaml
alerts:
  - name: api_quota_warning
    condition: usage > 80%
    action: notify_team
    
  - name: api_quota_critical
    condition: usage > 95%
    action: 
      - notify_team
      - auto_scale
      - prepare_fallback
      
  - name: unusual_usage_pattern
    condition: spike > 500%
    action:
      - investigate
      - temporary_throttle
      
  - name: geographic_anomaly
    condition: requests_from_unexpected_country
    action:
      - block_requests
      - alert_security
```

---

## 🎯 Key Implementation Rules

### Golden Rules
1. **NEVER** commit real API keys to git
2. **ALWAYS** use Secret Manager in production
3. **ROTATE** keys every 90 days minimum
4. **MONITOR** usage continuously
5. **RESTRICT** keys to minimum required permissions
6. **TEST** emergency procedures regularly
7. **DOCUMENT** all API dependencies

### Environment Separation
```
Development: Heavy restrictions, low quotas
Staging: Production-like with limits
Pilot: Conservative production limits
Production: Full capacity with monitoring
```

---

## 📝 Documentation Requirements

### For Each API Key
1. **Purpose**: What is this key used for?
2. **Restrictions**: What limitations are applied?
3. **Owner**: Who is responsible?
4. **Rotation**: When was it last rotated?
5. **Dependencies**: What services use this key?
6. **Fallback**: What happens if it fails?

---

## 🔄 Key Rotation Schedule

| Service | Rotation Frequency | Last Rotated | Next Rotation |
|---------|-------------------|--------------|---------------|
| Google Maps | 90 days | N/A | After pilot |
| SMS Gateway | 60 days | N/A | After pilot |
| Banking SFTP | 30 days | N/A | After pilot |
| JWT Secret | 180 days | N/A | After launch |
| Database | 90 days | N/A | After launch |

---

## 🏁 Final Notes

The system is currently at 88% readiness WITHOUT production API keys. This is intentional and correct. Production keys should be the LAST thing added before launch to minimize the exposure window.

Remember: A system with perfect features but compromised API keys is worse than a system with fewer features but secure key management.

**Next Review Date**: Before staging deployment  
**Document Owner**: Security Team  
**Classification**: CONFIDENTIAL - Do not share outside the team