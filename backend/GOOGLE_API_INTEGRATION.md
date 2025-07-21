# Google API Integration Guide

This comprehensive guide consolidates all Google API integration documentation for the Lucky Gas delivery management system.

## Table of Contents

1. [Overview](#overview)
2. [Architecture](#architecture)
3. [API Services](#api-services)
4. [Security & Monitoring](#security--monitoring)
5. [Development Mode](#development-mode)
6. [Configuration](#configuration)
7. [Usage Examples](#usage-examples)
8. [Troubleshooting](#troubleshooting)

## Overview

The Lucky Gas system integrates with multiple Google Cloud services to provide:
- **Route Optimization**: Google Routes API with OR-Tools for vehicle routing
- **AI Predictions**: Vertex AI for demand forecasting
- **Geocoding**: Address validation and coordinate conversion
- **Cloud Storage**: Document and data storage

## Architecture

### Service Layer Structure

```
app/services/google_cloud/
├── monitoring/
│   ├── api_cache.py          # Response caching
│   ├── circuit_breaker.py    # Resilience patterns
│   ├── cost_monitor.py       # Cost tracking
│   ├── error_handler.py      # Retry logic
│   └── rate_limiter.py       # Rate limiting
├── security/
│   └── api_key_manager.py    # Secure key management
├── routes_service_enhanced.py # Enhanced Routes API
├── vertex_ai_service_enhanced.py # Enhanced Vertex AI
├── mock_routes_service.py    # Mock for development
├── mock_vertex_ai_service.py # Mock for development
└── development_mode.py       # Mode management
```

## API Services

### 1. Google Routes API

**Purpose**: Optimize delivery routes using real-time traffic data and OR-Tools.

**Key Features**:
- Real-time traffic consideration
- Multiple waypoint optimization
- Vehicle capacity constraints
- Time window support
- Taiwan-specific routing

**Usage**:
```python
from app.services.google_cloud.routes_service_enhanced import EnhancedRoutesService

routes_service = EnhancedRoutesService()
optimized_route = await routes_service.optimize_route(
    origin={"lat": 25.0330, "lng": 121.5654},
    destination={"lat": 25.0478, "lng": 121.5319},
    waypoints=[...],
    departure_time=datetime.now()
)
```

### 2. Vertex AI

**Purpose**: Machine learning predictions for demand forecasting.

**Key Features**:
- Daily demand predictions
- Customer behavior analysis
- Seasonal pattern recognition
- Automatic model retraining

**Usage**:
```python
from app.services.google_cloud.vertex_ai_service_enhanced import EnhancedVertexAIService

ai_service = EnhancedVertexAIService()
predictions = await ai_service.predict_demand(
    customer_id="CUST001",
    historical_data=[...],
    horizon_days=7
)
```

## Security & Monitoring

### API Key Management

**Local Development**: Encrypted storage using Fernet
```bash
# Keys stored in .keys/encrypted_keys.json
# Master key in .keys/master.key (keep secure!)
```

**Production**: Google Secret Manager integration
```python
# Automatic environment detection
api_key_manager = await get_api_key_manager()
api_key = await api_key_manager.get_key("GOOGLE_API_KEY")
```

### Rate Limiting

**Configuration**:
- Routes API: 10 requests/second, 1000/minute, 10000/day
- Vertex AI: 5 requests/second, 300/minute, 5000/day

**Dynamic Adjustment**: Automatic throttling based on quota usage

### Cost Monitoring

**Budget Enforcement**:
- Warning threshold: $50/day
- Critical threshold: $100/day
- Automatic blocking when exceeded

**Cost Tracking**:
```python
# View current costs
GET /api/v1/google-api/costs/current
```

### Circuit Breaker

**States**:
- **CLOSED**: Normal operation
- **OPEN**: Service blocked after failures
- **HALF_OPEN**: Testing recovery

**Configuration**:
- Failure threshold: 5 failures
- Recovery timeout: 60 seconds
- Success threshold: 3 successes

## Development Mode

### Mode Selection

**Environment Variable**: `DEVELOPMENT_MODE`
- `auto`: Automatic detection (default)
- `production`: Force production APIs
- `development`: Force mock services
- `offline`: Always use mocks

### Mock Services

**Mock Routes Service**:
- Realistic Taiwan addresses
- Simulated traffic patterns
- Consistent response times

**Mock Vertex AI Service**:
- Predictable test data
- Seasonal patterns
- Error simulation

## Configuration

### Required Environment Variables

```bash
# Google API Keys
GOOGLE_API_KEY=your-routes-api-key
GOOGLE_APPLICATION_CREDENTIALS=/path/to/service-account.json
GCP_PROJECT_ID=your-project-id

# Optional Configuration
DEVELOPMENT_MODE=auto
DAILY_COST_WARNING=50.00
DAILY_COST_CRITICAL=100.00
ROUTES_RATE_LIMIT_PER_SECOND=10
```

### Service Account Setup

1. Create service account in GCP Console
2. Grant required permissions:
   - Vertex AI User
   - Secret Manager Secret Accessor
3. Download credentials JSON
4. Set GOOGLE_APPLICATION_CREDENTIALS

## Usage Examples

### Route Optimization with OR-Tools

```python
# Optimize delivery route for multiple customers
from app.services.google_cloud.routes_service_enhanced import EnhancedRoutesService

routes_service = EnhancedRoutesService()

# Define delivery locations
locations = [
    {"lat": 25.0330, "lng": 121.5654, "demand": 2},  # Customer 1
    {"lat": 25.0478, "lng": 121.5319, "demand": 1},  # Customer 2
    {"lat": 25.0621, "lng": 121.5198, "demand": 3},  # Customer 3
]

# Optimize with vehicle capacity
optimized = await routes_service.optimize_with_ortools(
    depot_location={"lat": 25.0375, "lng": 121.5637},
    customer_locations=locations,
    vehicle_capacity=10,
    time_windows=[(8, 12), (9, 17), (13, 18)]
)
```

### Demand Prediction

```python
# Predict next week's demand
from app.services.google_cloud.vertex_ai_service_enhanced import EnhancedVertexAIService

ai_service = EnhancedVertexAIService()

prediction = await ai_service.predict_customer_demand(
    customer_id="CUST001",
    features={
        "avg_monthly_orders": 4.5,
        "last_order_days_ago": 28,
        "total_gas_consumed": 120.5,
        "is_commercial": False
    }
)
```

### Dashboard Integration

```python
# Access monitoring dashboard
GET /api/v1/google-api/dashboard

# Check API health
GET /api/v1/google-api/health

# View current usage
GET /api/v1/google-api/usage/current
```

## Troubleshooting

### Common Issues

**1. API Key Not Found**
```
Error: Missing API key for GOOGLE_API_KEY
Solution: Set environment variable or add to .env file
```

**2. Rate Limit Exceeded**
```
Error: 429 Too Many Requests
Solution: Check rate limit status, wait for quota reset
```

**3. Circuit Breaker Open**
```
Error: Circuit breaker is OPEN
Solution: Check service health, wait for recovery
```

**4. Cost Limit Exceeded**
```
Error: Daily cost limit exceeded
Solution: Review usage, adjust limits, or wait for reset
```

### Debug Mode

Enable detailed logging:
```bash
export LOG_LEVEL=DEBUG
export GOOGLE_API_DEBUG=true
```

### Health Checks

```python
# Check all services
GET /api/v1/google-api/health

# Response
{
    "routes_api": {
        "status": "healthy",
        "mode": "production",
        "circuit_breaker": "CLOSED"
    },
    "vertex_ai": {
        "status": "healthy",
        "mode": "production",
        "last_prediction": "2024-01-20T10:30:00Z"
    }
}
```

## Best Practices

1. **Always use enhanced services** instead of base services
2. **Monitor costs daily** to avoid surprises
3. **Implement proper error handling** for API failures
4. **Use caching** for repeated requests
5. **Test with mocks** before production deployment
6. **Set up alerts** for cost and error thresholds
7. **Regularly rotate API keys** for security

## Migration Notes

When migrating from basic to enhanced services:

1. Update imports to use enhanced services
2. Add error handling for new failure modes
3. Configure monitoring thresholds
4. Test circuit breaker behavior
5. Verify cost tracking accuracy

## Support

For issues or questions:
1. Check the error logs in `backend/backend.log`
2. Review the monitoring dashboard
3. Verify environment configuration
4. Test with mock services first