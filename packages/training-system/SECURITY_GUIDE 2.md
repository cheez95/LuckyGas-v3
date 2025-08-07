# Lucky Gas Training System - Security Implementation Guide

## 🔐 Security Architecture Overview

The Lucky Gas Training System implements defense-in-depth security with multiple layers of protection:

1. **Application Security**: Authentication, authorization, input validation
2. **Network Security**: HTTPS, firewalls, rate limiting
3. **Data Security**: Encryption at rest and in transit
4. **Infrastructure Security**: Container security, secrets management
5. **Operational Security**: Monitoring, incident response, audit trails

## 🛡️ Security Features Implemented

### 1. Authentication & Authorization

#### JWT Implementation
- **Access Tokens**: Short-lived (15 minutes) for API access
- **Refresh Tokens**: Long-lived (7 days) stored securely
- **Token Rotation**: Automatic refresh with sliding expiration
- **Revocation**: Blacklist mechanism for compromised tokens

```python
# Token configuration
ACCESS_TOKEN_EXPIRE_MINUTES = 15
REFRESH_TOKEN_EXPIRE_DAYS = 7
JWT_ALGORITHM = "HS256"  # Use RS256 in production
```

#### Role-Based Access Control (RBAC)
```python
ROLES = {
    "super_admin": ["*"],  # All permissions
    "admin": ["manage_users", "manage_content", "view_analytics"],
    "training_manager": ["manage_content", "view_analytics"],
    "manager": ["view_team", "view_analytics"],
    "office_staff": ["view_content", "submit_progress"],
    "driver": ["view_content", "submit_progress"],
    "guest": ["view_public_content"]
}
```

### 2. Rate Limiting

#### Multi-Strategy Rate Limiting
- **IP-based**: Default for unauthenticated requests
- **User-based**: For authenticated users
- **API Key-based**: For third-party integrations
- **Endpoint-specific**: Different limits per endpoint

```python
# Rate limit configurations
RATE_LIMITS = {
    "default": {"requests": 100, "window": 60},  # 100 req/min
    "auth": {"requests": 5, "window": 300},      # 5 req/5min
    "upload": {"requests": 10, "window": 3600},  # 10 req/hour
    "api": {"requests": 1000, "window": 3600}    # 1000 req/hour
}
```

#### Dynamic Rate Limiting
- **Behavior Scoring**: Adjusts limits based on user behavior
- **System Load**: Reduces limits during high load
- **Geographic**: Different limits by country/region
- **Token Bucket**: Allows burst traffic with recovery

### 3. CSRF Protection

#### Double-Submit Cookie Pattern
- CSRF tokens in cookies and headers
- Automatic validation for state-changing requests
- SameSite cookie attributes
- Origin verification

```python
# CSRF configuration
CSRF_TOKEN_LENGTH = 32
CSRF_MAX_AGE = 3600  # 1 hour
CSRF_COOKIE_HTTPONLY = True
CSRF_COOKIE_SECURE = True  # HTTPS only
CSRF_COOKIE_SAMESITE = "Strict"
```

### 4. Content Security Policy (CSP)

#### Strict CSP Implementation
```javascript
Content-Security-Policy: 
  default-src 'self';
  script-src 'self' 'nonce-{random}' 'strict-dynamic';
  style-src 'self' 'nonce-{random}';
  img-src 'self' data: https:;
  font-src 'self' https://fonts.gstatic.com;
  connect-src 'self' wss: https://api.luckygas.com.tw;
  media-src 'self' https://cdn.luckygas.com.tw;
  object-src 'none';
  base-uri 'self';
  form-action 'self';
  frame-ancestors 'none';
  upgrade-insecure-requests;
```

#### Security Headers
- `X-Content-Type-Options: nosniff`
- `X-Frame-Options: DENY`
- `X-XSS-Protection: 1; mode=block`
- `Referrer-Policy: strict-origin-when-cross-origin`
- `Permissions-Policy: geolocation=(), microphone=(), camera=()`

### 5. Input Validation & Sanitization

#### Comprehensive Validation
- **Type Validation**: Pydantic models with strict typing
- **Length Limits**: Maximum field lengths enforced
- **Pattern Matching**: Regex validation for formats
- **Sanitization**: HTML escaping, SQL parameterization

```python
class CourseCreate(BaseModel):
    title_zh: str = Field(..., min_length=1, max_length=200)
    title_en: str = Field(..., min_length=1, max_length=200)
    description_zh: str = Field(..., max_length=2000)
    description_en: str = Field(..., max_length=2000)
    department: Department
    difficulty: Difficulty
    
    @validator('title_zh', 'title_en')
    def validate_title(cls, v):
        # Prevent script injection
        if re.search(r'<script|javascript:|onerror=', v, re.I):
            raise ValueError('Invalid content detected')
        return v
```

### 6. Data Encryption

#### Encryption at Rest
- **Database**: Transparent Data Encryption (TDE)
- **File Storage**: S3 server-side encryption (SSE-S3)
- **Backups**: Encrypted with customer-managed keys

#### Encryption in Transit
- **HTTPS**: TLS 1.3 minimum
- **WebSocket**: WSS with TLS
- **Internal**: mTLS between services

### 7. Secrets Management

#### Secure Secret Storage
```yaml
# Kubernetes secrets
apiVersion: v1
kind: Secret
metadata:
  name: training-secrets
type: Opaque
data:
  database-url: <base64-encoded>
  jwt-secret: <base64-encoded>
  aws-access-key: <base64-encoded>
```

#### Secret Rotation
- Automated rotation every 90 days
- Zero-downtime key rotation
- Audit trail for all rotations

### 8. SQL Injection Prevention

#### Parameterized Queries
```python
# Safe query with SQLAlchemy
query = select(Course).where(
    Course.department == department,
    Course.is_active == True
)

# Never use string formatting
# BAD: f"SELECT * FROM courses WHERE dept = '{department}'"
```

### 9. XSS Prevention

#### Context-Aware Output Encoding
```typescript
// React automatically escapes values
<div>{userInput}</div>

// For HTML content, use DOMPurify
import DOMPurify from 'dompurify';
<div dangerouslySetInnerHTML={{
  __html: DOMPurify.sanitize(htmlContent)
}} />
```

### 10. File Upload Security

#### Strict File Validation
```python
ALLOWED_EXTENSIONS = {
    'video': ['mp4', 'mov', 'avi', 'mkv', 'webm'],
    'document': ['pdf', 'doc', 'docx', 'ppt', 'pptx'],
    'image': ['jpg', 'jpeg', 'png', 'gif', 'webp']
}

MAX_FILE_SIZES = {
    'video': 2 * 1024 * 1024 * 1024,  # 2GB
    'document': 50 * 1024 * 1024,      # 50MB
    'image': 10 * 1024 * 1024          # 10MB
}

def validate_file(file, file_type):
    # Check extension
    ext = file.filename.split('.')[-1].lower()
    if ext not in ALLOWED_EXTENSIONS[file_type]:
        raise ValueError("Invalid file type")
    
    # Check MIME type
    mime = magic.from_buffer(file.read(1024), mime=True)
    file.seek(0)
    
    # Check file size
    if file.size > MAX_FILE_SIZES[file_type]:
        raise ValueError("File too large")
    
    # Scan for malware (using ClamAV)
    if not scan_file_for_malware(file):
        raise ValueError("Malware detected")
```

## 🔍 Security Monitoring

### Real-time Monitoring
- **Failed Login Attempts**: Alert after 5 failures
- **Rate Limit Violations**: Track and analyze patterns
- **CSP Violations**: Monitor and fix policy issues
- **SQL Injection Attempts**: Log and block
- **XSS Attempts**: Detect and prevent

### Security Metrics
```python
SECURITY_METRICS = {
    "auth_failures": Counter('auth_failures_total'),
    "rate_limit_hits": Counter('rate_limit_violations_total'),
    "csp_violations": Counter('csp_violations_total'),
    "sql_injection_attempts": Counter('sql_injection_attempts_total'),
    "xss_attempts": Counter('xss_attempts_total'),
    "malware_detected": Counter('malware_detected_total')
}
```

## 🚨 Incident Response

### Security Incident Workflow
1. **Detection**: Automated alerts via monitoring
2. **Triage**: Assess severity and impact
3. **Containment**: Isolate affected systems
4. **Investigation**: Root cause analysis
5. **Remediation**: Fix vulnerabilities
6. **Recovery**: Restore normal operations
7. **Post-mortem**: Document and improve

### Emergency Contacts
- **Security Team**: security@luckygas.com.tw
- **On-Call Engineer**: +886-2-XXXX-XXXX
- **CISO**: ciso@luckygas.com.tw

## 📝 Security Checklist

### Development
- [ ] Input validation on all user inputs
- [ ] Output encoding for all dynamic content
- [ ] Use parameterized queries
- [ ] Implement proper error handling
- [ ] No sensitive data in logs
- [ ] Security headers configured
- [ ] HTTPS enforced
- [ ] Authentication required
- [ ] Authorization checks
- [ ] Rate limiting enabled

### Deployment
- [ ] Secrets encrypted
- [ ] TLS certificates valid
- [ ] Firewall rules configured
- [ ] Security patches applied
- [ ] Monitoring enabled
- [ ] Backups encrypted
- [ ] Access logs enabled
- [ ] Intrusion detection active
- [ ] Vulnerability scanning
- [ ] Penetration testing

### Operations
- [ ] Regular security audits
- [ ] Dependency updates
- [ ] Access reviews
- [ ] Incident response drills
- [ ] Security training
- [ ] Compliance checks
- [ ] Backup testing
- [ ] Disaster recovery testing
- [ ] Third-party assessments
- [ ] Security metrics review

## 🔑 Best Practices

### Password Policy
- Minimum 12 characters
- Mix of uppercase, lowercase, numbers, symbols
- No common passwords
- Regular rotation (90 days)
- Multi-factor authentication

### API Security
- API keys with limited scope
- Request signing
- Rate limiting per key
- IP whitelisting
- Audit logging

### Database Security
- Principle of least privilege
- Connection encryption
- Query logging
- Regular backups
- Access monitoring

### Container Security
- Non-root containers
- Read-only filesystems
- Security scanning
- Network policies
- Resource limits

## 📚 Security Resources

- [OWASP Top 10](https://owasp.org/www-project-top-ten/)
- [CWE/SANS Top 25](https://cwe.mitre.org/top25/)
- [NIST Cybersecurity Framework](https://www.nist.gov/cyberframework)
- [Taiwan Personal Data Protection Act](https://law.moj.gov.tw/ENG/LawClass/LawAll.aspx?pcode=I0050021)