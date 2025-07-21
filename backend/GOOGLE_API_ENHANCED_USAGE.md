# Google API Enhanced Services Usage Guide

This guide explains how to use the enhanced Google API services with comprehensive monitoring, security, and resilience features.

## 🚀 Quick Start

### Development Mode

By default, the system runs in development mode with mock services:

```bash
# No API keys needed - uses mock services
DEVELOPMENT_MODE=development
```

### Production Mode

To use real Google APIs:

```bash
# Set API keys securely
uv run python -c "
from app.core.security.api_key_manager import get_api_key_manager
import asyncio

async def set_keys():
    manager = await get_api_key_manager()
    await manager.set_key('routes', 'your-routes-api-key')
    await manager.set_key('vertex_ai', 'your-vertex-ai-key')
    print('API keys set securely')

asyncio.run(set_keys())
"

# Enable production mode
export DEVELOPMENT_MODE=production
```

## 📊 API Dashboard

Monitor all Google API usage through the dashboard:

### View Dashboard Overview
```bash
curl http://localhost:8000/api/v1/google-api/dashboard/overview
```

Response:
```json
{
  "timestamp": "2024-01-20T10:30:00Z",
  "services": {
    "routes": {
      "status": "healthy",
      "requests": {
        "total": 1000,
        "successful": 980,
        "failed": 20,
        "success_rate": 98.0
      },
      "cost": {
        "daily": 45.50,
        "budget_remaining": 54.50,
        "budget_percentage": 45.5
      },
      "rate_limit": {
        "available": true,
        "current_usage": {
          "per_second": 5,
          "per_minute": 150,
          "per_day": 10000
        }
      },
      "circuit_breaker": {
        "state": "CLOSED",
        "failure_count": 0
      }
    }
  }
}
```

### Cost Report
```bash
curl http://localhost:8000/api/v1/google-api/dashboard/costs
```

### Rate Limit Status
```bash
curl http://localhost:8000/api/v1/google-api/dashboard/rate-limits
```

## 🔧 Enhanced Features

### 1. Automatic Fallback to Mock Services

When rate limits or budgets are exceeded:

```python
# In your route optimization code
result = await enhanced_routes_service.calculate_route(
    origin="25.033,121.565",
    destination="25.047,121.517"
)
# Automatically falls back to mock if limits exceeded
```

### 2. Caching for Performance

Results are automatically cached:

```python
# First call - hits API
route1 = await enhanced_routes_service.calculate_route(origin, dest)

# Second call within TTL - returns from cache
route2 = await enhanced_routes_service.calculate_route(origin, dest)
```

### 3. Circuit Breaker Protection

Services automatically stop calling APIs when failures accumulate:

```python
# Circuit breaker opens after 5 consecutive failures
# Automatically recovers after timeout period
health = await enhanced_routes_service.health_check()
print(health["components"]["circuit_breaker"]["status"])
```

### 4. Cost Monitoring

Track and control API costs:

```python
# Check current costs
cost_status = await enhanced_routes_service.cost_monitor.get_api_usage("routes")
print(f"Daily cost: ${cost_status['daily_cost']}")
print(f"Budget remaining: ${100 - cost_status['daily_cost']}")
```

## 📝 Example: Daily Route Optimization

```python
from datetime import date
from app.services.route_optimization import route_optimization_service
from app.core.database import get_async_session

async def optimize_daily_routes():
    async with get_async_session() as session:
        # This automatically uses enhanced services
        routes = await route_optimization_service.optimize_daily_routes(
            target_date=date.today(),
            session=session
        )
        
        print(f"Optimized {len(routes)} routes")
        for route in routes:
            print(f"Route {route.route_number}: {route.total_stops} stops, "
                  f"{route.total_distance_km}km")
```

## 🔍 Example: Demand Prediction

```python
async def generate_predictions():
    # Generate batch predictions with monitoring
    result = await enhanced_vertex_ai_service.predict_demand_batch()
    
    print(f"Generated {result['predictions_count']} predictions")
    print(f"Model version: {result['model_version']}")
    
    # Check service health
    health = await enhanced_vertex_ai_service.health_check()
    print(f"Service status: {health['status']}")
```

## ⚙️ Configuration

### Environment Variables

```bash
# Development mode (auto/development/production/offline)
DEVELOPMENT_MODE=auto

# Redis for rate limiting and caching
REDIS_URL=redis://localhost:6379/0

# Cost thresholds (optional)
DAILY_COST_WARNING=50.00
DAILY_COST_CRITICAL=100.00

# Rate limit overrides (optional)
ROUTES_RATE_LIMIT_PER_SECOND=10
ROUTES_RATE_LIMIT_PER_DAY=25000
```

### Monitoring Thresholds

Edit `app/services/google_cloud/monitoring/cost_monitor.py`:

```python
THRESHOLDS = {
    "routes": {
        "daily_warning": Decimal("50.00"),
        "daily_critical": Decimal("100.00"),
    },
    "vertex_ai": {
        "daily_warning": Decimal("100.00"),
        "daily_critical": Decimal("200.00"),
    }
}
```

## 🚨 Error Handling

All services include comprehensive error handling:

```python
try:
    result = await enhanced_routes_service.calculate_route(origin, dest)
except Exception as e:
    # Service automatically retries and falls back to mock
    # You still get a result
    print(f"Got result despite error: {result}")
```

## 📈 Metrics and Monitoring

### Get Service Metrics

```python
# Routes service metrics
metrics = await enhanced_routes_service.get_route_metrics()
print(f"Success rate: {metrics['monitoring_stats']['success_rate']}%")
print(f"Cache hit rate: {metrics['monitoring_stats']['cache_hit_rate']}%")

# Vertex AI metrics
metrics = await enhanced_vertex_ai_service.get_prediction_metrics()
print(f"Prediction success rate: {metrics['monitoring_stats']['success_rate']}%")
```

### Health Checks

```python
# Check all components
routes_health = await enhanced_routes_service.health_check()
vertex_health = await enhanced_vertex_ai_service.health_check()

for service, health in [("Routes", routes_health), ("Vertex AI", vertex_health)]:
    print(f"\n{service} Service:")
    print(f"  Status: {health['status']}")
    for component, details in health['components'].items():
        print(f"  {component}: {details['status']}")
```

## 🔐 Security Features

### Encrypted API Keys

API keys are automatically encrypted at rest:

```python
# Keys are encrypted using Fernet encryption
# Never stored in plain text
manager = await get_api_key_manager()
await manager.set_key("routes", "your-api-key")  # Automatically encrypted
```

### Key Rotation

```python
# Rotate API keys without downtime
await manager.set_key("routes", "new-api-key")  # Old key replaced
```

## 🧪 Testing in Development

The mock services provide realistic responses:

```python
# Mock routes include Taiwan-specific traffic patterns
mock_route = await enhanced_routes_service.calculate_route(
    origin="25.033,121.565",  # Taipei
    destination="25.047,121.517"
)
print(f"Distance: {mock_route['routes'][0]['distance']}m")
print(f"Duration: {mock_route['routes'][0]['duration']}s")

# Mock predictions include seasonal patterns
mock_prediction = await enhanced_vertex_ai_service.predict_demand_batch()
print(f"Predictions: {mock_prediction['predictions_count']}")
```

## 📋 Best Practices

1. **Always use enhanced services** - They provide automatic fallback and monitoring
2. **Monitor costs regularly** - Check the dashboard daily
3. **Set appropriate budgets** - Configure thresholds based on your usage
4. **Use caching** - Let the system cache repeated requests
5. **Handle errors gracefully** - Services provide fallbacks automatically
6. **Test in development first** - Use mock services before production

## 🆘 Troubleshooting

### Service Unhealthy

```python
health = await service.health_check()
if health['status'] == 'degraded':
    print(f"Unhealthy components: {health['unhealthy_components']}")
    # Check specific component
    if 'circuit_breaker' in health['unhealthy_components']:
        # Circuit is open - wait for recovery
        await asyncio.sleep(60)
```

### Rate Limit Exceeded

```python
# Check current usage
usage = await service.rate_limiter.get_current_usage("routes")
if not usage['available']:
    print(f"Rate limit exceeded. Resets in next time window.")
    # Service automatically uses mock - no action needed
```

### Budget Exceeded

```python
# Check cost status
cost = await service.cost_monitor.get_api_usage("routes")
if cost['over_budget']:
    print(f"Daily budget exceeded: ${cost['daily_cost']}")
    # Service automatically uses mock - no action needed
```

## 🎯 Summary

The enhanced Google API services provide:

- ✅ **Automatic fallback** to mock services
- ✅ **Cost monitoring** with budget enforcement
- ✅ **Rate limiting** to prevent quota issues  
- ✅ **Circuit breaker** for resilience
- ✅ **Response caching** for performance
- ✅ **Comprehensive monitoring** dashboard
- ✅ **Secure key management** with encryption
- ✅ **Development mode** for testing

All these features work automatically - just use the enhanced services and they handle the rest!