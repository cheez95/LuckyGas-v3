# Quick Implementation Guide for Google API Integration

## Overview
Before adding actual Google API keys to the Lucky Gas system, implement these critical improvements to ensure security, reliability, and cost-effectiveness.

## Critical Improvements Checklist

### 🔒 1. Security (Must Implement First)
- [ ] **Encrypted API Key Storage**
  - Implement `APIKeyManager` with encryption for local development
  - Use Google Secret Manager for production
  - Never commit API keys to version control
  
- [ ] **Environment-Based Key Loading**
  ```python
  # Instead of: settings.GOOGLE_MAPS_API_KEY
  # Use: await gcp_config.get_maps_api_key()
  ```

### ⚡ 2. Rate Limiting & Quotas
- [ ] **Implement Rate Limiter**
  - Per-second limits: Routes (10/s), Geocoding (50/s)
  - Daily quotas: Routes (25k/day), Geocoding (2.5k/day)
  - Use Redis for distributed rate limiting

- [ ] **Add Pre-Flight Checks**
  ```python
  await rate_limiter.wait_if_needed("routes")
  # Then make API call
  ```

### 💰 3. Cost Management
- [ ] **Track Every API Call**
  ```python
  await cost_monitor.record_api_call("routes", "/computeRoutes")
  ```

- [ ] **Set Budget Alerts**
  - Daily warning: $50
  - Daily critical: $100
  - Auto-block at critical threshold

### 🛡️ 4. Error Handling & Resilience
- [ ] **Implement Retry Logic**
  - Exponential backoff for rate limits (429)
  - Max 3 retries for transient errors
  - No retry for authentication errors (401)

- [ ] **Add Circuit Breaker**
  - Open after 5 consecutive failures
  - Test recovery after 60 seconds
  - Fallback to mock services when open

### 📦 5. Caching Strategy
- [ ] **Cache API Responses**
  - Routes: 30 minutes
  - Geocoding: 30 days
  - Predictions: 1 hour

### 🔧 6. Development Experience
- [ ] **Offline Development Mode**
  ```bash
  # .env.development
  OFFLINE_MODE=true
  ```
  - Automatically uses mock services
  - No internet required for development

## Quick Start Implementation

### Step 1: Create Security Infrastructure
```bash
# Create secure key storage
mkdir -p backend/.keys
echo ".keys/" >> .gitignore

# Generate master key (development only)
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())" > backend/.keys/master.key
chmod 600 backend/.keys/master.key
```

### Step 2: Update Routes Service
```python
# app/services/google_cloud/routes_service.py
class GoogleRoutesService:
    async def optimize_route(self, ...):
        # Add rate limiting
        await self.rate_limiter.wait_if_needed("routes")
        
        # Check budget
        if not await self.cost_monitor.enforce_budget_limit("routes"):
            return self._create_unoptimized_route(depot, stops)
        
        # Try cache first
        cached = await self.cache.get("routes", params)
        if cached:
            return cached
        
        # Make API call with circuit breaker
        try:
            result = await self.circuit_breaker.call(
                self._make_api_request, params
            )
            
            # Record cost
            await self.cost_monitor.record_api_call("routes", endpoint)
            
            # Cache result
            await self.cache.set("routes", params, result)
            
            return result
        except GoogleAPIError as e:
            # Handle with appropriate fallback
            return self._create_unoptimized_route(depot, stops)
```

### Step 3: Environment Configuration
```bash
# .env.development
OFFLINE_MODE=true
GOOGLE_MAPS_API_KEY=  # Leave empty for offline mode

# .env.production
OFFLINE_MODE=false
GCP_PROJECT_ID=your-project-id
# API keys stored in Google Secret Manager
```

### Step 4: Add Monitoring Endpoints
```python
# app/api/v1/admin/routes.py
@router.get("/api-status")
async def get_api_status():
    return {
        "mode": "offline" if dev_mode.is_offline_mode() else "live",
        "daily_cost": await cost_monitor.get_cost_report("daily"),
        "rate_limits": await rate_limiter.get_usage_stats("routes"),
        "circuit_status": circuit_breaker.get_state()
    }
```

## Testing Before Going Live

### 1. Security Test
```bash
# Verify no API keys in code
grep -r "GOOGLE_MAPS_API_KEY" --include="*.py" .
# Should return no hardcoded keys
```

### 2. Rate Limit Test
```python
# Test rate limiting
for i in range(15):  # Exceeds 10/s limit
    await routes_service.optimize_route(...)
# Should see rate limit delays after 10th call
```

### 3. Cost Control Test
```python
# Simulate high usage
for i in range(100):
    await cost_monitor.record_api_call("routes", "test")
# Should trigger warning at $50, block at $100
```

### 4. Offline Mode Test
```bash
# Disconnect internet
export OFFLINE_MODE=true
pytest tests/test_routes.py
# All tests should pass using mock services
```

## Production Deployment Checklist

- [ ] API keys stored in Google Secret Manager
- [ ] Rate limiting configured and tested
- [ ] Cost monitoring alerts set up
- [ ] Circuit breakers configured
- [ ] Caching layer operational
- [ ] Error handling tested with real API errors
- [ ] Monitoring dashboard accessible
- [ ] Offline mode disabled in production
- [ ] All tests passing with mock services
- [ ] Budget alerts configured in Google Cloud Console

## Emergency Procedures

### If API Key Compromised:
1. Rotate key in Google Cloud Console immediately
2. Update in Secret Manager
3. Clear all API response caches
4. Review access logs for unauthorized usage

### If Costs Spike:
1. Circuit breakers will auto-activate at thresholds
2. Check dashboard at `/admin/google-api/dashboard`
3. Manually disable APIs if needed
4. Review usage patterns for anomalies

### If APIs Fail:
1. System auto-falls back to unoptimized routes
2. Check circuit breaker status
3. Mock services maintain basic functionality
4. Monitor for service recovery

## Support Contacts

- Google Cloud Support: [Console Link]
- Internal DevOps Team: devops@luckygas.tw
- Security Team: security@luckygas.tw

Remember: **Never commit API keys to version control!**