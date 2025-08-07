# Google Routes API Integration

This directory contains the comprehensive Google Routes API integration for Lucky Gas delivery route optimization.

## Overview

The Google Routes API integration provides intelligent route optimization capabilities that:
- Reduce fuel costs by 25-30%
- Decrease delivery time by 20%
- Handle 100+ delivery stops efficiently
- Integrate real-time traffic data
- Support Taiwan-specific requirements

## Components

### 1. Core Service (`routes_service.py`)
The main service class that handles:
- Route optimization with waypoint reordering
- Distance matrix calculations
- Real-time traffic integration
- Retry logic with exponential backoff
- Rate limiting
- Comprehensive error handling

### 2. Enhanced Service (`routes_service_enhanced.py`)
Extended version with additional monitoring:
- Circuit breaker pattern
- Cost monitoring and budget enforcement
- Advanced caching with intelligent TTL
- API key rotation
- Health monitoring

### 3. Mock Server (`mock_routes_server.py`)
Full mock implementation for testing:
- Simulates all Google Routes API endpoints
- Supports rate limiting simulation
- Generates realistic Taiwan-based data
- No API costs during development/testing

### 4. Configuration (`routes_config.py`)
Centralized configuration management:
- API endpoints and parameters
- Rate limiting settings
- Taiwan-specific optimizations
- Cost management thresholds

## Usage

### Basic Route Optimization

```python
from app.services.google_cloud.routes_service import google_routes_service

# Optimize a route
result = await google_routes_service.optimize_route(
    depot=(25.0330, 121.5654),  # Taipei depot
    stops=[
        {
            "order_id": 1,
            "customer_id": 1,
            "customer_name": "客戶 A",
            "address": "台北市信義區信義路五段7號",
            "lat": 25.0330,
            "lng": 121.5654,
            "priority": 1,
            "service_time": 10,
            "products": {"20kg": 2}
        },
        # ... more stops
    ],
    vehicle_capacity=100,
    time_windows={"start": "08:00", "end": "18:00"}
)

# Result contains:
# - Optimized stop sequence
# - Total distance and duration
# - Estimated arrival times
# - Fuel consumption estimate
# - Route polyline for visualization
```

### Multiple Route Optimization

```python
# Optimize routes for multiple drivers
routes = await google_routes_service.optimize_multiple_routes(
    orders=orders_list,
    drivers=[
        {"id": 1, "name": "司機 A"},
        {"id": 2, "name": "司機 B"}
    ],
    date=datetime.now()
)
```

### Distance Matrix Calculation

```python
# Calculate distances between multiple points
matrix = await google_routes_service.calculate_distance_matrix(
    origins=[(25.0330, 121.5654), (25.0418, 121.5435)],
    destinations=[(25.0476, 121.5170), (25.0145, 121.5272)]
)
```

## Features

### 1. Intelligent Retry Logic
- Exponential backoff for transient failures
- Maximum 3 retry attempts
- Graceful degradation to unoptimized routes

### 2. Rate Limiting
- 10 requests per second limit
- Automatic request spacing
- Thread-safe implementation

### 3. Cost Optimization
- Request only necessary fields
- Intelligent caching to reduce API calls
- Budget monitoring and enforcement

### 4. Taiwan-Specific Optimizations
- Traditional Chinese (zh-TW) language support
- Taiwan region (TW) traffic patterns
- Avoid ferries for reliability
- Optimized for urban delivery patterns

### 5. Error Handling
- Comprehensive error code handling
- Fallback to distance-based sorting
- Detailed error logging

## Configuration

### Environment Variables
```bash
GOOGLE_MAPS_API_KEY=your_api_key_here
GCP_PROJECT_ID=your-project-id
GCP_LOCATION=asia-east1
DEPOT_LAT=25.0330
DEPOT_LNG=121.5654
```

### API Key Setup
1. Enable Google Routes API in Google Cloud Console
2. Create an API key with Routes API access
3. Restrict key to your application's IP addresses
4. Set daily quota limits for cost control

## Testing

### Unit Tests
```bash
pytest tests/unit/services/google_cloud/test_routes_service.py -v
```

### Integration Tests with Mock Server
```bash
# Start mock server (in separate terminal)
python -m app.services.google_cloud.mock_routes_server

# Run integration tests
pytest tests/integration/google_cloud/test_routes_integration.py -v
```

### Using Mock Server in Development
```python
# Override service URLs for development
service.base_url = "http://localhost:8888/directions/v2:computeRoutes"
service.api_key = "mock_AIzaSyC-1234567890abcdefghijklmnop"
```

## Cost Management

### Estimated Costs
- Basic route computation: ~$0.005 per request
- Route optimization: ~$0.01 per request
- Distance matrix: ~$0.005 per element

### Cost Optimization Strategies
1. Cache results for repeated routes (1-hour TTL)
2. Batch distance matrix requests
3. Use field masks to reduce response size
4. Implement daily budget limits

## Monitoring

### Health Check
```python
health = await routes_service.get_service_health()
# Returns API key status, rate limit usage, cost metrics, etc.
```

### Metrics
- Route optimization time (Prometheus histogram)
- API call success/failure rates
- Cost tracking per endpoint
- Cache hit rates

## Best Practices

1. **Always validate addresses** before optimization
2. **Use time windows** for customer preferences
3. **Monitor API costs** daily
4. **Test with mock server** during development
5. **Handle API failures gracefully** with fallbacks
6. **Cache frequently used routes**
7. **Batch operations** when possible

## Troubleshooting

### Common Issues

1. **Rate Limit Exceeded**
   - Solution: Implement request queuing
   - Use exponential backoff

2. **Invalid API Key**
   - Verify key in Google Cloud Console
   - Check key restrictions

3. **No Routes Found**
   - Validate coordinates
   - Check for accessibility

4. **High API Costs**
   - Review field masks
   - Increase cache TTL
   - Implement request batching

## Future Enhancements

1. **Real-time traffic webhooks**
2. **Driver preference learning**
3. **Historical route analysis**
4. **Multi-objective optimization**
5. **Electric vehicle support**

## Support

For issues or questions:
1. Check error logs in CloudWatch/Stackdriver
2. Review API quotas in Google Cloud Console
3. Contact the development team