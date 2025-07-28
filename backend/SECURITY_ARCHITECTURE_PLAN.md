# LuckyGas v3 Security Architecture & Implementation Plan

**Document Version**: 1.0
**Last Updated**: 2025-01-28
**Classification**: CONFIDENTIAL

## Executive Summary

This document outlines the comprehensive security architecture for protecting API keys, credentials, and sensitive data in the LuckyGas v3 system. It addresses the critical security vulnerability discovered in commit 5427d04 where Google Maps API keys were exposed in source code.

### Critical Actions Required

🔑 **IMMEDIATE USER ACTION REQUIRED**:
1. **Revoke exposed Google Maps API key**: `AIzaSyDPHBiMtFoSAmd12SbbQU5gZYMQdF6DOcY`
2. **Audit Google Cloud Console** for any suspicious usage
3. **Generate new restricted API keys** for each environment

## Architecture Overview

```mermaid
graph TB
    subgraph "Client Layer"
        Web[Web App]
        Mobile[Mobile App]
    end
    
    subgraph "API Gateway"
        Proxy[API Proxy]
        RateLimit[Rate Limiter]
        Auth[Authentication]
    end
    
    subgraph "Backend Services"
        API[FastAPI Backend]
        Cache[Redis Cache]
        Queue[Task Queue]
    end
    
    subgraph "Secret Management"
        GSM[Google Secret Manager]
        Vault[HashiCorp Vault]
        EnvConfig[Environment Config]
    end
    
    subgraph "External Services"
        GMaps[Google Maps]
        SMS[SMS Gateways]
        Bank[Banking SFTP]
        Invoice[E-Invoice API]
    end
    
    Web --> Proxy
    Mobile --> Proxy
    Proxy --> API
    API --> GSM
    API --> Cache
    API --> Queue
    
    API -.-> GMaps
    API -.-> SMS
    API -.-> Bank
    API -.-> Invoice
    
    GSM --> API
    
    style GSM fill:#f9f,stroke:#333,stroke-width:4px
    style Proxy fill:#9ff,stroke:#333,stroke-width:4px
```

## Security Layers

### 1. Secret Management Layer

#### Google Secret Manager Integration
```python
# app/core/enhanced_secrets_manager.py
class EnhancedSecretsManager:
    def __init__(self):
        self.client = secretmanager.SecretManagerServiceClient()
        self.project_id = settings.GCP_PROJECT_ID
        self.cache = {}
        self.cache_ttl = 300  # 5 minutes
        
    async def get_secret(self, secret_id: str, version: str = "latest") -> str:
        """Retrieve secret with caching and audit logging"""
        cache_key = f"{secret_id}:{version}"
        
        # Check cache first
        if cache_key in self.cache:
            if self.cache[cache_key]['expires'] > time.time():
                return self.cache[cache_key]['value']
        
        # Fetch from Secret Manager
        secret = await self._fetch_secret(secret_id, version)
        
        # Cache the result
        self.cache[cache_key] = {
            'value': secret,
            'expires': time.time() + self.cache_ttl
        }
        
        # Audit log
        await self._audit_secret_access(secret_id)
        
        return secret
```

#### Environment-Specific Configuration
```yaml
# config/environments/production.yaml
environment: production
secrets:
  google_maps:
    secret_id: "google-maps-api-key-prod"
    restrictions:
      - type: "http_referrer"
        values: ["https://app.luckygas.tw/*"]
      - type: "api_restriction"
        apis: ["maps", "places", "geocoding", "directions"]
  
  banking:
    esun:
      secret_id: "banking-esun-sftp-prod"
      rotation_days: 90
    cathay:
      secret_id: "banking-cathay-sftp-prod"
      rotation_days: 90
```

### 2. API Proxy Layer

#### Backend Proxy Implementation
```python
# app/api/v1/maps_proxy.py
class SecureMapsProxy:
    def __init__(self):
        self.secrets_manager = EnhancedSecretsManager()
        self.rate_limiter = RateLimiter()
        self.circuit_breaker = CircuitBreaker()
        
    @router.post("/api/v1/maps/geocode")
    @rate_limit(calls=100, period=60)
    @circuit_breaker
    async def geocode(
        self,
        request: GeocodeRequest,
        current_user: User = Depends(get_current_user)
    ):
        # Validate user permissions
        if not current_user.has_permission("maps.geocode"):
            raise HTTPException(403, "Insufficient permissions")
        
        # Get API key from Secret Manager (never exposed to client)
        api_key = await self.secrets_manager.get_secret("google-maps-api-key")
        
        # Make proxied request
        async with httpx.AsyncClient() as client:
            response = await client.get(
                "https://maps.googleapis.com/maps/api/geocode/json",
                params={
                    "address": request.address,
                    "key": api_key,
                    "language": "zh-TW",
                    "region": "TW"
                }
            )
        
        # Audit log
        await self._audit_api_usage(current_user, "geocode", request)
        
        return response.json()
```

### 3. Key Rotation Automation

#### Automated Rotation Service
```python
# app/services/key_rotation_service.py
class KeyRotationService:
    def __init__(self):
        self.secrets_manager = EnhancedSecretsManager()
        self.notification_service = NotificationService()
        
    async def rotate_api_keys(self):
        """Automated key rotation with zero downtime"""
        rotation_schedule = [
            {"service": "google_maps", "days": 90},
            {"service": "twilio", "days": 90},
            {"service": "jwt_secret", "days": 30},
        ]
        
        for config in rotation_schedule:
            if await self._should_rotate(config):
                # Generate new key
                new_key = await self._generate_new_key(config["service"])
                
                # Store as new version
                await self.secrets_manager.create_secret_version(
                    f"{config['service']}-api-key",
                    new_key
                )
                
                # Update service configuration
                await self._update_service_config(config["service"], new_key)
                
                # Notify administrators
                await self.notification_service.send_rotation_notice(
                    config["service"]
                )
```

### 4. Monitoring & Alerting

#### Security Monitoring
```python
# app/services/security_monitoring.py
class SecurityMonitor:
    def __init__(self):
        self.alert_service = AlertService()
        self.metrics = SecurityMetrics()
        
    async def monitor_api_usage(self):
        """Monitor for suspicious API usage patterns"""
        thresholds = {
            "rate_spike": 3.0,  # 3x normal rate
            "geographic_anomaly": True,
            "failed_auth_threshold": 10,
            "key_exposure_patterns": [
                r"AIza[0-9A-Za-z-_]{35}",
                r"sk_live_[0-9a-zA-Z]{24}",
                r"[a-f0-9]{40}"  # Generic API key
            ]
        }
        
        # Check for anomalies
        if await self._detect_rate_anomaly() > thresholds["rate_spike"]:
            await self.alert_service.send_critical_alert(
                "API usage spike detected",
                {"current_rate": current_rate, "threshold": threshold}
            )
```

## Implementation Phases

### Phase 1: Emergency Response (Day 1)
✅ **Completed**:
- Identified exposed Google Maps API key
- Created comprehensive key inventory
- Documented all external service dependencies

🔑 **User Actions Required**:
1. **REVOKE** exposed API key in Google Cloud Console
2. **AUDIT** API usage logs for suspicious activity
3. **GENERATE** new restricted API keys

### Phase 2: Secret Manager Implementation (Days 2-5)

#### Tasks:
1. **Set up Google Secret Manager**
   ```bash
   # Enable Secret Manager API
   gcloud services enable secretmanager.googleapis.com
   
   # Create service account
   gcloud iam service-accounts create luckygas-secrets \
     --display-name="LuckyGas Secret Manager"
   ```

2. **Implement Secret Manager client**
   - Create enhanced secrets manager class
   - Add caching layer
   - Implement audit logging

3. **Migrate existing secrets**
   - 🔑 **KEY REQUIRED**: All services - Please provide production credentials

### Phase 3: API Proxy Implementation (Days 6-10)

#### Google Maps Proxy Endpoints:
- `/api/v1/maps/geocode` - Address geocoding
- `/api/v1/maps/directions` - Route calculation
- `/api/v1/maps/places` - Place search
- `/api/v1/maps/distance-matrix` - Distance calculations

#### Security Features:
- Rate limiting per user/IP
- Request validation
- Response caching
- Audit logging

### Phase 4: Monitoring & Automation (Days 11-15)

#### Monitoring Dashboard:
- API usage by service
- Failed authentication attempts
- Rate limit violations
- Geographic anomalies
- Key rotation status

#### Automated Alerts:
- Exposed key patterns in logs
- Unusual API usage spikes
- Failed rotation attempts
- Service degradation

## Security Best Practices

### 1. Development Environment
- Use `.env.local` (gitignored) for local secrets
- Never commit real credentials
- Use mock services when possible
- Implement pre-commit hooks for secret detection

### 2. CI/CD Pipeline
```yaml
# .github/workflows/security-scan.yml
name: Security Scan
on: [push, pull_request]

jobs:
  secret-scan:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: TruffleHog Secret Scan
        uses: trufflesecurity/trufflehog@main
        with:
          path: ./
          base: main
          head: HEAD
```

### 3. Production Deployment
- All secrets from Secret Manager only
- No environment variables for secrets
- Workload identity for service authentication
- Network security policies

## Compliance & Audit

### Audit Requirements:
1. **Access Logs**: All secret access logged with timestamp, user, and purpose
2. **Rotation History**: Complete history of key rotations
3. **Usage Analytics**: API usage patterns and anomaly detection
4. **Compliance Reports**: Monthly security compliance reports

### Regulatory Compliance:
- **PCI DSS**: For future payment processing
- **Taiwan Personal Information Protection Act**: For customer data
- **Banking Security Standards**: For SFTP connections

## Risk Mitigation

### Current Risks:
1. **Exposed API Key**: Google Maps key in git history
   - **Mitigation**: Immediate revocation and rotation
   
2. **Hardcoded Test Credentials**: In .env file
   - **Mitigation**: Use separate test credentials, never production
   
3. **Multiple External Dependencies**: 20+ API integrations
   - **Mitigation**: Centralized secret management and monitoring

### Future Risks:
1. **Key Rotation Failures**: Manual rotation is error-prone
   - **Mitigation**: Automated rotation with monitoring
   
2. **Service Account Compromise**: Broad permissions
   - **Mitigation**: Principle of least privilege
   
3. **Supply Chain Attacks**: Third-party dependencies
   - **Mitigation**: Dependency scanning and vendoring

## Success Metrics

### Security KPIs:
- **Zero** hardcoded secrets in codebase
- **100%** of external APIs proxied through backend
- **<5 minutes** secret rotation time
- **<1 hour** incident response time
- **Monthly** security audits passed

### Implementation Timeline:
- **Week 1**: Emergency response and Secret Manager setup
- **Week 2**: API proxy implementation
- **Week 3**: Monitoring and automation
- **Week 4**: Testing and production deployment

---

## Appendix: Security Checklist

- [ ] Revoke exposed Google Maps API key
- [ ] Audit all API usage logs
- [ ] Generate new restricted API keys
- [ ] Implement Secret Manager
- [ ] Create API proxy endpoints
- [ ] Set up monitoring dashboards
- [ ] Configure automated alerts
- [ ] Implement key rotation
- [ ] Conduct security audit
- [ ] Train team on security practices