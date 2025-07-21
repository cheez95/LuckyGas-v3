# 🚨 CRITICAL ACTIONS CHECKLIST
## Must Complete Before Adding Google API Keys

### Immediate Actions (Do Now!)

#### 1. Remove Hardcoded Credentials
```bash
# Check and remove from these files:
backend/app/core/config.py  # Line 180-181: admin credentials
backend/.env               # Database passwords
```

#### 2. Create Secure Environment Files
```bash
# backend/.env.example (template only - no real values)
SECRET_KEY=<generate-using-python-secrets>
DATABASE_URL=postgresql+asyncpg://user:password@localhost:5433/dbname
REDIS_URL=redis://localhost:6379/0
GOOGLE_API_KEY=<your-api-key-here>
FIRST_SUPERUSER_PASSWORD=<change-on-first-login>
```

#### 3. Generate Strong SECRET_KEY
```python
# Run this to generate a secure key:
import secrets
print(secrets.token_urlsafe(32))
```

#### 4. Fix CORS Configuration
```python
# backend/app/main.py - Replace lines 78-85
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "https://your-domain.com"],  # Add your domains
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["Authorization", "Content-Type"],
    allow_credentials=True
)
```

#### 5. Add HTTPS Enforcement
```python
# backend/app/main.py - Add after line 98
from fastapi.middleware.httpsredirect import HTTPSRedirectMiddleware

if settings.ENVIRONMENT == "production":
    app.add_middleware(HTTPSRedirectMiddleware)
```

#### 6. Validate Environment on Startup
```python
# Already implemented! Just ensure it runs:
# backend/app/main.py line 35
validate_environment()  # This will stop the app if critical vars are missing
```

#### 7. Use API Key Manager
```python
# Instead of accessing settings.GOOGLE_API_KEY directly:
from app.core.security.api_key_manager import get_api_key_manager

api_key_manager = await get_api_key_manager()
api_key = await api_key_manager.get_key("GOOGLE_API_KEY")
```

### Verification Commands

```bash
# 1. Search for hardcoded secrets
grep -r "password\|secret\|key" backend/app/core/config.py

# 2. Check environment validation
cd backend
uv run python -c "from app.core.env_validation import validate_environment; validate_environment()"

# 3. Test API key encryption
uv run python -c "from app.core.security.api_key_manager import LocalEncryptedKeyManager; print('API Key Manager OK')"

# 4. Verify no plain text keys in logs
grep -i "api.*key" backend/*.log
```

### Pre-Deployment Checklist

- [ ] All passwords removed from code
- [ ] SECRET_KEY in environment variable
- [ ] CORS restricted to specific domains
- [ ] HTTPS redirect enabled for production
- [ ] Environment validation passing
- [ ] API Key Manager tested
- [ ] All existing keys rotated
- [ ] .env file NOT in git repository
- [ ] Logs checked for sensitive data

### Quick Test After Changes

```bash
# Start the backend
cd backend
uv run uvicorn app.main:app --reload

# Check health endpoint
curl http://localhost:8000/health

# Verify CORS (should fail from unauthorized origin)
curl -H "Origin: http://evil.com" http://localhost:8000/api/v1/customers
```

## ⚠️ DO NOT ADD API KEYS UNTIL ALL ITEMS ARE CHECKED!