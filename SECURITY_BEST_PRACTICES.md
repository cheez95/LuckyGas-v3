# 🛡️ Security Best Practices Guide

## Table of Contents
1. [API Key Management](#api-key-management)
2. [Environment Variables](#environment-variables)
3. [Secret Rotation](#secret-rotation)
4. [Incident Response](#incident-response)
5. [Developer Guidelines](#developer-guidelines)
6. [CI/CD Security](#cicd-security)

---

## API Key Management

### Never Hardcode Secrets
```python
# ❌ NEVER DO THIS
api_key = "AIzaSyBNLrJhOMz6idD05pzfn5lhA-TAw-mAZCU"

# ✅ ALWAYS DO THIS
api_key = os.getenv('GOOGLE_MAPS_API_KEY')
if not api_key:
    raise ValueError("API key not configured")
```

### Key Restrictions
Always restrict API keys to:
1. **Specific domains/IPs**
   ```
   Production: https://yourdomain.com/*
   Development: http://localhost:5173/*
   ```

2. **Required APIs only**
   - Enable only what you need
   - Disable unused APIs
   - Monitor usage regularly

3. **Usage quotas**
   - Set daily/monthly limits
   - Configure billing alerts
   - Monitor for anomalies

---

## Environment Variables

### File Structure
```
project/
├── .env.example      # Template with placeholders (commit this)
├── .env             # Development values (never commit)
├── .env.local       # Local overrides (never commit)
└── .env.production  # Production values (never commit)
```

### Loading Priority
1. System environment variables (highest priority)
2. `.env.local` (local overrides)
3. `.env` (default values)
4. `.env.example` (fallback reference)

### Best Practices
```bash
# .env.example (commit this)
DATABASE_URL=postgresql://user:password@localhost/database
API_KEY=your-api-key-here
SECRET_KEY=minimum-32-character-secret

# .env (never commit)
DATABASE_URL=postgresql://luckygas:ActualPass123@localhost/luckygas
API_KEY=AIzaSyB-ActualKeyHere
SECRET_KEY=actual-secret-key-with-32-characters-minimum
```

---

## Secret Rotation

### Rotation Schedule
| Secret Type | Rotation Frequency | Priority |
|------------|-------------------|----------|
| API Keys | Every 90 days | HIGH |
| Database Passwords | Every 60 days | CRITICAL |
| JWT Secrets | Every 180 days | MEDIUM |
| Service Account Keys | Every 30 days | HIGH |
| SSL Certificates | Before expiry | CRITICAL |

### Rotation Process
1. **Generate new secret**
   ```bash
   openssl rand -base64 32  # For random secrets
   ```

2. **Update in parallel**
   - Deploy new secret alongside old
   - Test with new secret
   - Monitor for issues

3. **Deprecate old secret**
   - Remove from all systems
   - Revoke/delete if possible
   - Update documentation

4. **Verify rotation**
   ```bash
   ./scan-secrets.sh  # Run security scan
   ```

---

## Incident Response

### If a Secret is Exposed

#### Immediate Actions (< 1 hour)
1. **Revoke the exposed secret**
   ```bash
   # Google Cloud Console
   # AWS IAM Console
   # Database admin panel
   ```

2. **Generate new secret**
   ```bash
   # Create new with proper restrictions
   ```

3. **Update all services**
   ```bash
   # Update environment variables
   # Restart services
   ```

4. **Check for unauthorized usage**
   ```bash
   # Review access logs
   # Check billing/usage metrics
   ```

#### Follow-up Actions (< 24 hours)
1. **Audit git history**
   ```bash
   git log -p -S "exposed-secret"
   ```

2. **Clean git history** (if needed)
   ```bash
   # Use BFG Repo-Cleaner
   bfg --delete-files id_{dsa,rsa}
   bfg --replace-text passwords.txt
   ```

3. **Notify stakeholders**
   - Security team
   - Affected users (if applicable)
   - Management (for critical exposures)

4. **Document incident**
   - What was exposed
   - How long it was exposed
   - What actions were taken
   - Lessons learned

---

## Developer Guidelines

### Pre-commit Checks
```bash
# Install pre-commit hooks (MANDATORY)
pip install pre-commit
pre-commit install

# Run manually before committing
pre-commit run --all-files
```

### Code Review Checklist
- [ ] No hardcoded secrets
- [ ] Environment variables used
- [ ] `.env` files in `.gitignore`
- [ ] API keys have restrictions
- [ ] Sensitive data is encrypted
- [ ] Logging doesn't expose secrets
- [ ] Error messages are sanitized

### Testing with Secrets
```python
# Use mock values in tests
@patch.dict(os.environ, {'API_KEY': 'test-key-123'})
def test_api_call():
    # Test with mock key
    pass

# Never use real credentials in tests
```

---

## CI/CD Security

### GitHub Actions Secrets
```yaml
# .github/workflows/deploy.yml
env:
  API_KEY: ${{ secrets.API_KEY }}  # Use GitHub secrets
  DATABASE_URL: ${{ secrets.DATABASE_URL }}
```

### Setting Secrets
```bash
# Via GitHub CLI
gh secret set API_KEY

# Via GitHub UI
# Settings > Secrets > Actions > New repository secret
```

### Security Scanning in CI
```yaml
# Run on every PR
on:
  pull_request:
    branches: [main]

jobs:
  security:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Secret Scanning
        run: |
          ./scan-secrets.sh
          if [ $? -ne 0 ]; then
            echo "Secrets detected! Blocking merge."
            exit 1
          fi
```

---

## Security Tools

### Automated Scanning
1. **Gitleaks** - Git history scanning
2. **TruffleHog** - Entropy-based detection
3. **detect-secrets** - Pre-commit integration
4. **Bandit** - Python security linting
5. **npm audit** - Node dependency scanning

### Manual Verification
```bash
# Quick scan for common patterns
grep -r "password\|api[_-]key\|secret" . \
  --exclude-dir=node_modules \
  --exclude-dir=.git \
  --exclude="*.lock"

# Run comprehensive scan
./scan-secrets.sh
```

### Monitoring
- Enable GitHub secret scanning
- Set up dependabot alerts
- Configure security advisories
- Monitor access logs
- Review billing anomalies

---

## Security Contacts

**Report Security Issues**:
- Email: security@luckygas.com
- Do NOT create public issues for vulnerabilities
- Include full details and reproduction steps

**Emergency Response**:
- On-call: +886-xxx-xxx-xxx
- Escalation: security-team@luckygas.com

---

## Quick Reference

### Environment Setup
```bash
# 1. Copy example file
cp .env.example .env

# 2. Add your secrets
nano .env

# 3. Verify gitignore
grep "^.env$" .gitignore

# 4. Install pre-commit
pre-commit install

# 5. Run security scan
./scan-secrets.sh
```

### Daily Security Checklist
- [ ] Check for security alerts in GitHub
- [ ] Review access logs for anomalies
- [ ] Verify API usage is normal
- [ ] Ensure secrets are not in code
- [ ] Confirm pre-commit hooks work

### Emergency Commands
```bash
# Revoke all tokens
./scripts/revoke-all-tokens.sh

# Rotate all secrets
./scripts/rotate-secrets.sh

# Lock down production
./scripts/emergency-lockdown.sh

# Scan everything
./scan-secrets.sh --deep
```

---

**Last Updated**: 2025-08-17  
**Next Review**: 2025-09-17  
**Owner**: Security Team