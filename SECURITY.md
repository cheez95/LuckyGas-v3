# 🔒 Security Policy

## Security Best Practices

### API Key Management

**NEVER commit API keys, passwords, or secrets to version control!**

#### Google Maps API Key Setup

1. **Obtain API Key**:
   - Go to [Google Cloud Console](https://console.cloud.google.com/)
   - Create or select your project
   - Enable Maps JavaScript API
   - Create credentials (API Key)

2. **Restrict Your Key** (CRITICAL):
   - **HTTP Referrers**: Add your production domains
     ```
     https://yourdomain.com/*
     https://www.yourdomain.com/*
     http://localhost:5173/* (for development)
     ```
   - **API Restrictions**: Select only the APIs you need:
     - Maps JavaScript API
     - Geocoding API
     - Places API

3. **Configure Environment**:
   ```bash
   # Backend (.env or .env.local)
   GOOGLE_MAPS_API_KEY=your-restricted-api-key-here
   ```

4. **Rotate Compromised Keys**:
   If a key is exposed:
   - Immediately revoke it in Google Cloud Console
   - Create a new key with proper restrictions
   - Update all environments with the new key
   - Review access logs for unauthorized usage

### Environment Variables

#### Required Variables
```bash
# Security Critical - Must be unique per environment
SECRET_KEY=minimum-32-character-random-string
DATABASE_URL=postgresql://user:password@host/database
GOOGLE_MAPS_API_KEY=your-restricted-api-key

# Authentication
FIRST_SUPERUSER=admin@yourdomain.com
FIRST_SUPERUSER_PASSWORD=strong-unique-password
```

#### Security Checklist
- [ ] All API keys are stored in environment variables
- [ ] `.env` files are in `.gitignore`
- [ ] Production uses different keys than development
- [ ] All keys have appropriate restrictions
- [ ] Regular key rotation schedule in place
- [ ] Access logs are monitored

### Pre-commit Hooks

Install secret scanning to prevent accidental commits:

```bash
# Install pre-commit
pip install pre-commit

# Install hooks
pre-commit install

# Run manually
pre-commit run --all-files
```

### Secret Scanning

The following patterns are automatically blocked from commits:
- API keys (Google, AWS, Azure, etc.)
- Private keys
- Passwords in configuration files
- OAuth tokens
- Database connection strings with passwords

### Reporting Security Issues

If you discover a security vulnerability:

1. **DO NOT** create a public GitHub issue
2. **DO NOT** commit fixes that reveal the vulnerability
3. Email security concerns to: security@luckygas.com
4. Include:
   - Description of the vulnerability
   - Steps to reproduce
   - Potential impact
   - Suggested fix (if any)

### Security Headers

Ensure these headers are set in production:

```nginx
# Nginx configuration
add_header X-Frame-Options "SAMEORIGIN" always;
add_header X-Content-Type-Options "nosniff" always;
add_header X-XSS-Protection "1; mode=block" always;
add_header Referrer-Policy "strict-origin-when-cross-origin" always;
add_header Content-Security-Policy "default-src 'self' https://*.googleapis.com https://*.gstatic.com; script-src 'self' 'unsafe-inline' https://*.googleapis.com; style-src 'self' 'unsafe-inline' https://*.googleapis.com;" always;
```

### HTTPS Configuration

**Production MUST use HTTPS:**

1. Obtain SSL certificate (Let's Encrypt recommended)
2. Configure forced HTTPS redirect
3. Enable HSTS header
4. Use secure cookies only

### Regular Security Audits

Run these checks regularly:

```bash
# Check for exposed secrets
git secrets --scan

# Check dependencies for vulnerabilities
npm audit (frontend)
pip-audit (backend)

# Check for common security issues
bandit -r backend/app

# OWASP dependency check
dependency-check --scan .
```

### Incident Response

In case of security breach:

1. **Immediate Actions**:
   - Revoke compromised credentials
   - Rotate all secrets
   - Enable additional logging
   - Notify affected users

2. **Investigation**:
   - Review access logs
   - Identify breach vector
   - Assess data exposure

3. **Remediation**:
   - Patch vulnerabilities
   - Update security measures
   - Document lessons learned

## Compliance

This system follows security best practices aligned with:
- OWASP Top 10
- PCI DSS (for payment processing)
- GDPR (for user data protection)
- Taiwan Personal Information Protection Act

## Security Contact

Security Team: security@luckygas.com  
Emergency: +886-xxx-xxx-xxx

---

**Last Updated**: 2025-08-17  
**Next Review**: 2025-09-17