# Lucky Gas V3 Security Best Practices Guide

## Overview

This guide provides security best practices for developers, operations teams, and users of the Lucky Gas system. Following these practices helps maintain a secure environment and protect sensitive data.

## 👩‍💻 Developer Security Best Practices

### Secure Coding Standards

#### Input Validation

**✅ DO:**
```python
# Validate all user inputs
from pydantic import BaseModel, validator, constr
import re

class CustomerCreate(BaseModel):
    name: constr(min_length=1, max_length=100)
    email: str
    phone: str
    taiwan_id: str
    
    @validator('email')
    def validate_email(cls, v):
        if not re.match(r'^[\w\.-]+@[\w\.-]+\.\w+$', v):
            raise ValueError('Invalid email format')
        return v.lower()
    
    @validator('phone')
    def validate_phone(cls, v):
        # Taiwan phone number format
        if not re.match(r'^09\d{2}-?\d{3}-?\d{3}$|^0[2-8]-?\d{7,8}$', v):
            raise ValueError('Invalid Taiwan phone number')
        return v.replace('-', '')
    
    @validator('taiwan_id')
    def validate_taiwan_id(cls, v):
        # Basic Taiwan ID format check
        if not re.match(r'^[A-Z][12]\d{8}$', v):
            raise ValueError('Invalid Taiwan ID format')
        # Add checksum validation here
        return v
```

**❌ DON'T:**
```python
# Never trust user input directly
def create_customer(request):
    # DANGEROUS: Direct use of user input
    query = f"INSERT INTO customers VALUES ('{request.name}', '{request.email}')"
    db.execute(query)  # SQL Injection vulnerability!
```

#### SQL Injection Prevention

**✅ DO:**
```python
# Use parameterized queries
from sqlalchemy import text

# Safe parameterized query
def get_customer_by_email(email: str):
    query = text("SELECT * FROM customers WHERE email = :email")
    result = db.execute(query, {"email": email})
    return result.fetchone()

# Using ORM (recommended)
def get_customer_orm(email: str):
    return db.query(Customer).filter(Customer.email == email).first()
```

**❌ DON'T:**
```python
# String concatenation with user input
def get_customer_unsafe(email: str):
    query = f"SELECT * FROM customers WHERE email = '{email}'"  # Vulnerable!
    return db.execute(query)
```

#### Authentication & Password Handling

**✅ DO:**
```python
from passlib.context import CryptContext
import secrets

# Configure secure password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto", bcrypt__rounds=12)

class AuthService:
    @staticmethod
    def hash_password(password: str) -> str:
        """Hash password using bcrypt with 12 rounds"""
        return pwd_context.hash(password)
    
    @staticmethod
    def verify_password(plain_password: str, hashed_password: str) -> bool:
        """Verify password against hash"""
        return pwd_context.verify(plain_password, hashed_password)
    
    @staticmethod
    def generate_secure_token(length: int = 32) -> str:
        """Generate cryptographically secure token"""
        return secrets.token_urlsafe(length)
    
    @staticmethod
    def validate_password_strength(password: str) -> tuple[bool, str]:
        """Validate password meets security requirements"""
        if len(password) < 12:
            return False, "Password must be at least 12 characters"
        
        checks = [
            (r'[A-Z]', "uppercase letter"),
            (r'[a-z]', "lowercase letter"),
            (r'\d', "number"),
            (r'[!@#$%^&*(),.?":{}|<>]', "special character")
        ]
        
        for pattern, requirement in checks:
            if not re.search(pattern, password):
                return False, f"Password must contain at least one {requirement}"
        
        return True, "Password is strong"
```

#### Secure Session Management

**✅ DO:**
```python
from datetime import datetime, timedelta
import jwt
from typing import Optional

class SessionManager:
    SECRET_KEY = settings.SECRET_KEY
    ALGORITHM = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES = 15
    REFRESH_TOKEN_EXPIRE_DAYS = 7
    
    @classmethod
    def create_access_token(cls, user_id: int, role: str) -> str:
        expire = datetime.utcnow() + timedelta(minutes=cls.ACCESS_TOKEN_EXPIRE_MINUTES)
        payload = {
            "sub": str(user_id),
            "role": role,
            "exp": expire,
            "iat": datetime.utcnow(),
            "type": "access"
        }
        return jwt.encode(payload, cls.SECRET_KEY, algorithm=cls.ALGORITHM)
    
    @classmethod
    def verify_token(cls, token: str) -> Optional[dict]:
        try:
            payload = jwt.decode(token, cls.SECRET_KEY, algorithms=[cls.ALGORITHM])
            # Additional validations
            if payload.get("type") != "access":
                return None
            return payload
        except jwt.ExpiredSignatureError:
            # Log expired token attempt
            return None
        except jwt.InvalidTokenError:
            # Log invalid token attempt
            return None
```

#### Secure API Design

**✅ DO:**
```python
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPBearer
from typing import List

router = APIRouter()
security = HTTPBearer()

# Role-based access control
def require_role(allowed_roles: List[str]):
    def role_checker(token: str = Depends(security)):
        payload = SessionManager.verify_token(token.credentials)
        if not payload or payload.get("role") not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions"
            )
        return payload
    return role_checker

# Secure endpoint with authentication and authorization
@router.get("/api/v1/admin/users")
async def get_all_users(
    current_user: dict = Depends(require_role(["admin", "manager"])),
    limit: int = 100,  # Prevent resource exhaustion
    offset: int = 0
):
    # Additional security checks
    if limit > 1000:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Limit cannot exceed 1000"
        )
    
    # Audit log
    audit_log.info(f"User {current_user['sub']} accessed user list")
    
    # Return data with sensitive fields masked
    users = db.query(User).limit(limit).offset(offset).all()
    return [mask_sensitive_data(user) for user in users]
```

### Secure File Handling

**✅ DO:**
```python
import os
import magic
from pathlib import Path
import hashlib

class SecureFileHandler:
    ALLOWED_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.pdf', '.doc', '.docx'}
    MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB
    UPLOAD_DIR = Path("/secure/uploads")
    
    @classmethod
    def validate_file(cls, file_content: bytes, filename: str) -> tuple[bool, str]:
        # Check file size
        if len(file_content) > cls.MAX_FILE_SIZE:
            return False, "File too large"
        
        # Check extension
        ext = Path(filename).suffix.lower()
        if ext not in cls.ALLOWED_EXTENSIONS:
            return False, f"File type {ext} not allowed"
        
        # Verify file content matches extension
        mime = magic.from_buffer(file_content, mime=True)
        expected_mimes = {
            '.jpg': ['image/jpeg'],
            '.jpeg': ['image/jpeg'],
            '.png': ['image/png'],
            '.pdf': ['application/pdf']
        }
        
        if mime not in expected_mimes.get(ext, []):
            return False, "File content does not match extension"
        
        # Check for malicious content
        if cls._contains_malicious_content(file_content):
            return False, "File contains potentially malicious content"
        
        return True, "File is valid"
    
    @classmethod
    def save_file_securely(cls, file_content: bytes, original_filename: str) -> str:
        # Generate secure filename
        file_hash = hashlib.sha256(file_content).hexdigest()
        ext = Path(original_filename).suffix.lower()
        secure_filename = f"{file_hash}{ext}"
        
        # Create secure path (prevent directory traversal)
        file_path = cls.UPLOAD_DIR / secure_filename
        file_path = file_path.resolve()
        
        # Ensure path is within upload directory
        if not str(file_path).startswith(str(cls.UPLOAD_DIR)):
            raise ValueError("Invalid file path")
        
        # Save with restricted permissions
        file_path.write_bytes(file_content)
        os.chmod(file_path, 0o640)
        
        return str(file_path)
```

### Secure Logging

**✅ DO:**
```python
import logging
import json
from typing import Any, Dict

class SecureLogger:
    # PII patterns to mask
    PII_PATTERNS = {
        'email': (r'\b[\w\.-]+@[\w\.-]+\.\w+\b', 'user@*****.com'),
        'phone': (r'\b09\d{2}-?\d{3}-?\d{3}\b', '09XX-XXX-XXX'),
        'taiwan_id': (r'\b[A-Z][12]\d{8}\b', 'X1XXXXXX90'),
        'credit_card': (r'\b\d{4}[\s-]?\d{4}[\s-]?\d{4}[\s-]?\d{4}\b', 'XXXX-XXXX-XXXX-XXXX'),
        'password': (r'password["\']?\s*[:=]\s*["\']?[^"\'}\s]+', 'password: *****')
    }
    
    @classmethod
    def mask_pii(cls, message: str) -> str:
        """Mask PII in log messages"""
        for pattern_name, (pattern, replacement) in cls.PII_PATTERNS.items():
            message = re.sub(pattern, replacement, message, flags=re.IGNORECASE)
        return message
    
    @classmethod
    def log_security_event(cls, event_type: str, details: Dict[str, Any]):
        """Log security events with proper structure"""
        log_entry = {
            'timestamp': datetime.utcnow().isoformat(),
            'event_type': event_type,
            'severity': cls._get_severity(event_type),
            'details': cls._sanitize_details(details),
            'correlation_id': details.get('correlation_id', 'N/A')
        }
        
        # Log to security audit log
        security_logger = logging.getLogger('security')
        security_logger.info(json.dumps(log_entry))
    
    @classmethod
    def _sanitize_details(cls, details: Dict[str, Any]) -> Dict[str, Any]:
        """Remove sensitive data from log details"""
        sanitized = {}
        sensitive_keys = {'password', 'token', 'api_key', 'secret'}
        
        for key, value in details.items():
            if any(sensitive in key.lower() for sensitive in sensitive_keys):
                sanitized[key] = '*****'
            else:
                sanitized[key] = cls.mask_pii(str(value)) if isinstance(value, str) else value
        
        return sanitized
```

### Secure Error Handling

**✅ DO:**
```python
from enum import Enum

class ErrorCode(Enum):
    AUTHENTICATION_FAILED = "AUTH001"
    AUTHORIZATION_FAILED = "AUTH002"
    VALIDATION_FAILED = "VAL001"
    RESOURCE_NOT_FOUND = "RES001"
    INTERNAL_ERROR = "INT001"

class SecureErrorHandler:
    @staticmethod
    def handle_error(error: Exception, request_id: str) -> dict:
        """Handle errors securely without exposing sensitive info"""
        
        # Log full error details internally
        logger.error(f"Request {request_id}: {type(error).__name__}: {str(error)}", 
                    exc_info=True)
        
        # Return safe error to client
        if isinstance(error, ValidationError):
            return {
                "error_code": ErrorCode.VALIDATION_FAILED.value,
                "message": "Invalid input provided",
                "request_id": request_id,
                "details": error.errors()  # Safe validation errors only
            }
        elif isinstance(error, AuthenticationError):
            return {
                "error_code": ErrorCode.AUTHENTICATION_FAILED.value,
                "message": "Authentication failed",
                "request_id": request_id
            }
        else:
            # Generic error for unexpected exceptions
            return {
                "error_code": ErrorCode.INTERNAL_ERROR.value,
                "message": "An error occurred processing your request",
                "request_id": request_id
            }
```

## 🔧 Operations Security Best Practices

### Infrastructure Security

#### Secure Deployment Pipeline

```yaml
# .github/workflows/secure-deploy.yml
name: Secure Deployment

on:
  push:
    branches: [main]

jobs:
  security-checks:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      
      - name: Run Security Scan
        run: |
          # SAST scan
          bandit -r backend/ -f json -o bandit-report.json
          
          # Dependency check
          safety check --json > safety-report.json
          
          # Secret scanning
          trufflehog filesystem . --json > secrets-report.json
          
      - name: Container Scan
        run: |
          trivy image luckygas:latest --format json > trivy-report.json
          
      - name: Fail on Critical Issues
        run: |
          python scripts/check_security_reports.py
```

#### Secure Configuration Management

```python
# config/secure_settings.py
import os
from typing import Any, Dict

class SecureConfig:
    """Secure configuration management"""
    
    @staticmethod
    def get_secret(key: str, default: Any = None) -> Any:
        """Get secret from environment or secret manager"""
        # Try environment variable first
        value = os.environ.get(key)
        
        if value is None:
            # Try Google Secret Manager
            try:
                from google.cloud import secretmanager
                client = secretmanager.SecretManagerServiceClient()
                name = f"projects/{os.environ['GCP_PROJECT']}/secrets/{key}/versions/latest"
                response = client.access_secret_version(request={"name": name})
                value = response.payload.data.decode("UTF-8")
            except Exception as e:
                logger.warning(f"Failed to get secret {key}: {e}")
                value = default
        
        return value
    
    @staticmethod
    def validate_config() -> Dict[str, bool]:
        """Validate all required configuration"""
        required_configs = [
            'DATABASE_URL',
            'SECRET_KEY',
            'GOOGLE_MAPS_API_KEY',
            'JWT_SECRET',
            'REDIS_URL'
        ]
        
        results = {}
        for config in required_configs:
            results[config] = bool(SecureConfig.get_secret(config))
        
        return results
```

### Monitoring and Alerting

#### Security Monitoring Setup

```python
# monitoring/security_monitor.py
from dataclasses import dataclass
from typing import List, Dict
import asyncio

@dataclass
class SecurityAlert:
    severity: str  # critical, high, medium, low
    category: str  # auth, access, data, system
    message: str
    details: Dict[str, Any]
    timestamp: datetime

class SecurityMonitor:
    def __init__(self):
        self.alert_thresholds = {
            'failed_logins': {'count': 5, 'window': 300},  # 5 failures in 5 min
            'api_errors': {'count': 50, 'window': 60},     # 50 errors in 1 min
            'new_ips': {'count': 10, 'window': 3600},      # 10 new IPs in 1 hour
            'data_access': {'count': 1000, 'window': 300}  # 1000 queries in 5 min
        }
    
    async def check_failed_logins(self):
        """Monitor for brute force attempts"""
        query = """
        SELECT username, ip_address, COUNT(*) as attempts
        FROM audit_logs
        WHERE event_type = 'login_failed'
        AND timestamp > NOW() - INTERVAL '5 minutes'
        GROUP BY username, ip_address
        HAVING COUNT(*) >= 5
        """
        
        results = await db.fetch_all(query)
        
        for row in results:
            alert = SecurityAlert(
                severity='high',
                category='auth',
                message=f"Possible brute force attack on {row['username']}",
                details={
                    'username': row['username'],
                    'ip_address': row['ip_address'],
                    'attempts': row['attempts']
                },
                timestamp=datetime.utcnow()
            )
            await self.send_alert(alert)
    
    async def check_data_exfiltration(self):
        """Monitor for potential data exfiltration"""
        query = """
        SELECT user_id, COUNT(*) as query_count, 
               SUM(result_count) as total_records
        FROM api_logs
        WHERE endpoint LIKE '%export%' OR endpoint LIKE '%download%'
        AND timestamp > NOW() - INTERVAL '1 hour'
        GROUP BY user_id
        HAVING SUM(result_count) > 10000
        """
        
        results = await db.fetch_all(query)
        
        for row in results:
            alert = SecurityAlert(
                severity='critical',
                category='data',
                message=f"Potential data exfiltration by user {row['user_id']}",
                details={
                    'user_id': row['user_id'],
                    'query_count': row['query_count'],
                    'total_records': row['total_records']
                },
                timestamp=datetime.utcnow()
            )
            await self.send_alert(alert)
```

### Backup and Recovery

#### Secure Backup Procedures

```bash
#!/bin/bash
# scripts/secure_backup.sh

set -euo pipefail

# Configuration
BACKUP_BUCKET="gs://luckygas-backups"
ENCRYPTION_KEY_NAME="backup-encryption-key"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

# Function to encrypt and upload backup
secure_backup() {
    local source=$1
    local destination=$2
    
    # Create encrypted backup
    echo "Creating encrypted backup of ${source}..."
    
    # Dump database
    pg_dump $DATABASE_URL | gzip > /tmp/backup.sql.gz
    
    # Encrypt using Google KMS
    gcloud kms encrypt \
        --key=$ENCRYPTION_KEY_NAME \
        --keyring=backup-keyring \
        --location=asia-east1 \
        --plaintext-file=/tmp/backup.sql.gz \
        --ciphertext-file=/tmp/backup.sql.gz.enc
    
    # Upload to secure bucket
    gsutil cp /tmp/backup.sql.gz.enc "${BACKUP_BUCKET}/${destination}"
    
    # Clean up temporary files
    shred -vfz -n 3 /tmp/backup.sql.gz
    rm -f /tmp/backup.sql.gz.enc
    
    echo "Backup completed: ${destination}"
}

# Backup database
secure_backup "database" "db/prod_${TIMESTAMP}.sql.gz.enc"

# Backup configuration
tar czf /tmp/config.tar.gz /app/config/
secure_backup "config" "config/prod_${TIMESTAMP}.tar.gz.enc"

# Verify backup
gsutil ls -l "${BACKUP_BUCKET}/db/prod_${TIMESTAMP}.sql.gz.enc"

# Test restore capability
echo "Testing restore capability..."
./scripts/test_restore.sh "${BACKUP_BUCKET}/db/prod_${TIMESTAMP}.sql.gz.enc"
```

## 👤 User Security Best Practices

### Account Security

#### Strong Password Guidelines

```markdown
## Password Requirements for Lucky Gas Users

Your password must meet ALL of the following requirements:

✅ **Length**: At least 12 characters (recommended: 16+ characters)
✅ **Complexity**: Must include ALL of the following:
   - At least one uppercase letter (A-Z)
   - At least one lowercase letter (a-z)
   - At least one number (0-9)
   - At least one special character (!@#$%^&*(),.?":{}|<>)

✅ **Uniqueness**: 
   - Not used on any other website
   - Not similar to previous passwords
   - Not contain personal information (name, birthdate, etc.)

❌ **Avoid**:
   - Common passwords (password123, admin, etc.)
   - Dictionary words
   - Keyboard patterns (qwerty, 123456)
   - Personal information
   - Company name or variations

💡 **Tips for Creating Strong Passwords**:
1. Use a passphrase: "MyDog&IWalk2Times@Day!"
2. Use a password manager
3. Consider using the first letters of a sentence
4. Mix languages if you're multilingual
```

#### Two-Factor Authentication Setup

```python
# Example 2FA implementation guide for users
class TwoFactorSetupGuide:
    @staticmethod
    def generate_setup_instructions() -> dict:
        return {
            "steps": [
                {
                    "step": 1,
                    "title": "安裝驗證器應用程式",
                    "description": "在您的手機上安裝 Google Authenticator 或 Microsoft Authenticator",
                    "apps": {
                        "ios": "https://apps.apple.com/app/google-authenticator/id388497605",
                        "android": "https://play.google.com/store/apps/details?id=com.google.android.apps.authenticator2"
                    }
                },
                {
                    "step": 2,
                    "title": "掃描 QR Code",
                    "description": "使用驗證器應用程式掃描下方的 QR Code",
                    "alternative": "或手動輸入此密鑰"
                },
                {
                    "step": 3,
                    "title": "輸入驗證碼",
                    "description": "輸入應用程式顯示的 6 位數驗證碼",
                    "note": "驗證碼每 30 秒更新一次"
                },
                {
                    "step": 4,
                    "title": "保存備用碼",
                    "description": "請安全保存這些備用碼，以備手機遺失時使用",
                    "warning": "每個備用碼只能使用一次"
                }
            ],
            "security_tips": [
                "不要截圖 QR Code",
                "不要與他人分享驗證碼",
                "定期檢查已授權的設備",
                "如果手機遺失，立即停用 2FA"
            ]
        }
```

### Safe Browsing Practices

```markdown
## 安全使用 Lucky Gas 系統指南

### 🔒 登入安全
1. **確認網址正確**
   - ✅ 正確: https://app.luckygas.com.tw
   - ❌ 錯誤: http://luckygas-app.fake.com
   
2. **檢查 SSL 證書**
   - 尋找瀏覽器地址欄的鎖頭圖標
   - 點擊查看證書詳情
   - 確認證書由受信任的機構簽發

3. **避免公共 WiFi**
   - 使用 4G/5G 行動網路
   - 或使用 VPN 連線
   - 避免在網咖或公共場所登入

### 🎯 防範釣魚攻擊
1. **識別可疑郵件**
   - Lucky Gas 不會要求您透過郵件提供密碼
   - 檢查寄件者地址是否為 @luckygas.com.tw
   - 注意拼寫錯誤或語法問題

2. **驗證連結**
   - 將滑鼠懸停在連結上查看實際網址
   - 不要點擊可疑連結
   - 直接在瀏覽器輸入網址

3. **報告可疑活動**
   - 發現可疑郵件請轉寄至 security@luckygas.com.tw
   - 撥打客服專線確認

### 💻 設備安全
1. **保持軟體更新**
   - 定期更新作業系統
   - 更新瀏覽器到最新版本
   - 安裝防毒軟體

2. **安全登出**
   - 使用完畢請點擊「登出」
   - 不要只是關閉瀏覽器
   - 清除瀏覽器快取

3. **避免共用帳號**
   - 每位員工使用獨立帳號
   - 不要分享登入資訊
   - 定期更換密碼
```

### API Key Security for Developers

```python
# Example of secure API key usage
class APIKeyBestPractices:
    """
    Best practices for API key management
    """
    
    # ✅ DO: Store API keys securely
    @staticmethod
    def get_api_key():
        # From environment variable
        api_key = os.environ.get('LUCKYGAS_API_KEY')
        
        # From secure key management service
        if not api_key:
            api_key = SecretManager.get_secret('luckygas-api-key')
        
        return api_key
    
    # ❌ DON'T: Hardcode API keys
    # NEVER DO THIS:
    # API_KEY = "lgas_1234567890abcdef"  # WRONG!
    
    # ✅ DO: Use API keys with restrictions
    @staticmethod
    def create_restricted_api_key():
        restrictions = {
            "allowed_ips": ["203.0.113.0/24"],  # Your office IP range
            "allowed_domains": ["*.luckygas.com.tw"],
            "rate_limit": 1000,  # requests per hour
            "scopes": ["read:orders", "write:orders"],
            "expiry": datetime.utcnow() + timedelta(days=90)
        }
        return APIKeyManager.create_key(restrictions)
    
    # ✅ DO: Rotate API keys regularly
    @staticmethod
    def rotate_api_key(old_key: str):
        # Create new key
        new_key = APIKeyManager.create_key()
        
        # Update all services to use new key
        services = ['frontend', 'mobile', 'partner-api']
        for service in services:
            ConfigManager.update_api_key(service, new_key)
        
        # Schedule old key for deletion after grace period
        APIKeyManager.schedule_deletion(old_key, days=7)
        
        return new_key
```

## 🔐 Security Checklist for Different Roles

### Developer Checklist
- [ ] All inputs validated and sanitized
- [ ] SQL queries use parameters, not concatenation
- [ ] Passwords hashed with bcrypt (12+ rounds)
- [ ] Sensitive data encrypted at rest
- [ ] API endpoints require authentication
- [ ] Rate limiting implemented
- [ ] Security headers configured
- [ ] Error messages don't leak information
- [ ] Dependencies updated and scanned
- [ ] Code reviewed for security issues

### DevOps Checklist
- [ ] SSL/TLS certificates valid and strong
- [ ] Firewall rules follow least privilege
- [ ] Secrets stored in secret manager
- [ ] Backups encrypted and tested
- [ ] Monitoring alerts configured
- [ ] Security patches applied timely
- [ ] Access logs enabled and monitored
- [ ] Network segmentation implemented
- [ ] DDoS protection enabled
- [ ] Incident response plan tested

### Manager Checklist
- [ ] Security training completed by team
- [ ] Access reviews conducted quarterly
- [ ] Security metrics tracked
- [ ] Incident reports reviewed
- [ ] Compliance requirements met
- [ ] Third-party security assessed
- [ ] Security budget allocated
- [ ] Business continuity plan updated
- [ ] Insurance coverage adequate
- [ ] Executive briefings scheduled

### End User Checklist
- [ ] Strong unique password set
- [ ] Two-factor authentication enabled
- [ ] Recovery email/phone updated
- [ ] Suspicious emails reported
- [ ] Software kept updated
- [ ] Secure network used
- [ ] Account activity reviewed
- [ ] Personal data minimal
- [ ] Logout when finished
- [ ] Devices secured

## 📚 Security Resources

### Internal Resources
- Security Team Email: security@luckygas.com.tw
- Security Hotline: +886-2-XXXX-XXXX
- Security Wiki: https://wiki.luckygas.com.tw/security
- Training Portal: https://training.luckygas.com.tw

### External Resources
- [OWASP Top 10](https://owasp.org/www-project-top-ten/)
- [Taiwan CERT/CC](https://www.twcert.org.tw/)
- [Google Cloud Security Best Practices](https://cloud.google.com/security/best-practices)
- [SANS Security Resources](https://www.sans.org/security-resources/)

### Security Tools
- **Scanning**: OWASP ZAP, Burp Suite, nmap
- **Code Analysis**: Bandit, ESLint security plugin, SonarQube
- **Dependency Check**: Safety, npm audit, Dependabot
- **Secrets Detection**: TruffleHog, git-secrets
- **Container Security**: Trivy, Clair, Anchore

---

**Document Version**: 1.0  
**Last Updated**: 2024-01-30  
**Next Review**: 2024-03-30  
**Owner**: Security Team  
**Classification**: Internal Use