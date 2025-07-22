# API Enhancement Documentation

This document describes the API enhancements implemented for BE-1.3, including CORS configuration, rate limiting, API versioning, and WebSocket/Socket.IO setup.

## Table of Contents
1. [CORS Configuration](#cors-configuration)
2. [Rate Limiting](#rate-limiting)
3. [API Versioning](#api-versioning)
4. [WebSocket/Socket.IO Enhancement](#websocketsocketio-enhancement)
5. [Usage Examples](#usage-examples)

## CORS Configuration

### Overview
Cross-Origin Resource Sharing (CORS) has been configured to allow secure communication between the frontend and backend across different origins.

### Configuration Details
- **Allowed Origins**: Configured through environment settings with defaults for development
- **Allowed Methods**: GET, POST, PUT, DELETE, OPTIONS, PATCH
- **Allowed Headers**: Authorization, Content-Type, X-Request-ID, and more
- **Credentials**: Enabled for cookie-based authentication
- **Preflight Cache**: 1 hour (3600 seconds)

### Environment-Specific Settings
```python
# Development
- http://localhost:3000 (React default)
- http://localhost:5173 (Vite default)
- http://localhost:* (wildcard for development)

# Production
- https://app.luckygas.tw
- https://www.luckygas.tw
```

### Custom CORS Origins
Add custom origins via the `BACKEND_CORS_ORIGINS` environment variable:
```bash
BACKEND_CORS_ORIGINS=["https://custom-domain.com","https://another-domain.com"]
```

## Rate Limiting

### Overview
Rate limiting prevents API abuse and ensures fair usage across all clients. It uses a sliding window algorithm with Redis for distributed rate limiting.

### Features
- **Per-IP Rate Limiting**: Anonymous users are limited by IP address
- **Per-User Rate Limiting**: Authenticated users get 2x the rate limit
- **Endpoint-Specific Limits**: Different endpoints have different limits
- **Sliding Window Algorithm**: Smooth rate limiting without sudden resets
- **Distributed**: Works across multiple server instances using Redis

### Default Limits
```python
# General endpoints
- Production: 100 requests/minute
- Development: 1000 requests/minute

# Specific endpoints
- /api/v1/auth/login: 5 requests/minute
- /api/v1/auth/register: 3 requests/minute
- /api/v1/predictions/*: 10 requests/minute
- /api/v1/routes/optimize: 10 requests/minute
- /api/v1/orders/bulk: 5 requests/minute
```

### Rate Limit Headers
All responses include rate limit information:
- `X-RateLimit-Limit`: Total allowed requests
- `X-RateLimit-Remaining`: Remaining requests in current window
- `X-RateLimit-Reset`: Unix timestamp when the limit resets

### Rate Limit Response
When rate limit is exceeded:
```json
{
  "detail": "請求次數超過限制，請稍後再試",
  "error": "rate_limit_exceeded",
  "retry_after": 45
}
```

### Using Rate Limit Decorator
Apply custom rate limits to specific endpoints:
```python
from app.core.decorators import rate_limit

@router.get("/expensive-operation")
@rate_limit(requests_per_minute=5)
async def expensive_operation():
    return {"result": "success"}
```

## API Versioning

### Overview
API versioning allows for backward compatibility while introducing new features and improvements.

### Version Format
Versions follow semantic versioning: `vMAJOR.MINOR.PATCH`
- **MAJOR**: Breaking changes
- **MINOR**: New features (backward compatible)
- **PATCH**: Bug fixes

### Version Detection Priority
1. `Accept-Version` header
2. `API-Version` header
3. URL path (e.g., `/api/v1/...`)
4. Default to current version

### Version Headers
All responses include version information:
- `API-Version`: Current version being used
- `API-Version-Latest`: Latest available version
- `Deprecated`: True if using deprecated version
- `Sunset`: Date when deprecated version will be removed

### Using Version Decorators
```python
from app.core.versioning import version_deprecated, requires_version

# Mark endpoint as deprecated
@router.get("/old-endpoint")
@version_deprecated(
    deprecated_in="v1.1",
    removed_in="v2.0",
    alternative="/api/v1/new-endpoint"
)
async def old_endpoint():
    return {"data": "legacy"}

# Require minimum version
@router.post("/new-feature")
@requires_version("v1.2")
async def new_feature():
    return {"data": "new"}
```

### Version-Specific Features
```python
# Check features for current version
features = get_version_features(version)
if features.get("batch_operations"):
    # Enable batch operations
    pass
```

## WebSocket/Socket.IO Enhancement

### Overview
Real-time communication is implemented using Socket.IO, which provides:
- Automatic reconnection
- Room-based broadcasting
- Acknowledgments
- Better browser compatibility

### CORS Configuration
Socket.IO CORS is synchronized with the main application settings:
```python
sio = socketio.AsyncServer(
    cors_allowed_origins=settings.get_all_cors_origins(),
    # ... other settings
)
```

### Connection Authentication
Clients must provide a valid JWT token:
```javascript
// Frontend connection example
const socket = io('http://localhost:8000', {
  auth: {
    token: 'your-jwt-token'
  }
});
```

### Available Rooms
- `orders_room`: Order updates
- `routes_room`: Route assignments and updates
- `predictions_room`: Prediction results
- `drivers_room`: Driver-specific updates
- `notifications_room`: General notifications

### Auto-Join by Role
Users automatically join rooms based on their role:
- **super_admin/manager**: All rooms
- **office_staff**: orders, routes, predictions, notifications
- **driver**: routes, drivers, notifications
- **customer**: notifications only

### Socket.IO Events

#### Client to Server
```javascript
// Subscribe to topic
socket.emit('subscribe', { topic: 'orders' });

// Driver location update
socket.emit('driver_location', {
  latitude: 25.0330,
  longitude: 121.5654,
  accuracy: 10
});

// Delivery status update
socket.emit('delivery_status', {
  order_id: 123,
  status: 'delivered',
  notes: 'Customer received'
});
```

#### Server to Client
```javascript
// Order update
socket.on('order_update', (data) => {
  console.log('Order updated:', data);
});

// Route assignment
socket.on('route_assigned', (data) => {
  console.log('New route assigned:', data);
});

// System notification
socket.on('notification', (data) => {
  console.log('Notification:', data.title, data.message);
});
```

## Usage Examples

### 1. Making CORS Requests from Frontend
```javascript
// React/TypeScript example
const response = await fetch('http://localhost:8000/api/v1/customers', {
  method: 'GET',
  headers: {
    'Authorization': `Bearer ${token}`,
    'Content-Type': 'application/json',
  },
  credentials: 'include', // Important for CORS with credentials
});
```

### 2. Handling Rate Limits
```javascript
async function makeAPICall() {
  const response = await fetch('/api/v1/orders');
  
  if (response.status === 429) {
    const retryAfter = response.headers.get('Retry-After');
    console.log(`Rate limited. Retry after ${retryAfter} seconds`);
    // Implement exponential backoff
    await sleep(retryAfter * 1000);
    return makeAPICall(); // Retry
  }
  
  // Check remaining requests
  const remaining = response.headers.get('X-RateLimit-Remaining');
  if (remaining < 10) {
    console.warn('Approaching rate limit');
  }
  
  return response.json();
}
```

### 3. Version-Aware Requests
```javascript
// Request specific version
const response = await fetch('/api/v1/customers', {
  headers: {
    'Accept-Version': 'v1.2',
    'Authorization': `Bearer ${token}`
  }
});

// Check version in response
const currentVersion = response.headers.get('API-Version');
const latestVersion = response.headers.get('API-Version-Latest');

if (currentVersion < latestVersion) {
  console.warn('Using outdated API version');
}
```

### 4. Socket.IO Real-time Updates
```javascript
// Initialize Socket.IO connection
import { io } from 'socket.io-client';

const socket = io('http://localhost:8000', {
  auth: {
    token: localStorage.getItem('access_token')
  }
});

// Handle connection
socket.on('connected', (data) => {
  console.log('Connected:', data);
  
  // Subscribe to updates
  socket.emit('subscribe', { topic: 'orders' });
});

// Listen for order updates
socket.on('order_update', (data) => {
  // Update UI with new order status
  updateOrderStatus(data.order_id, data.status);
});

// Send driver location
if (navigator.geolocation) {
  navigator.geolocation.watchPosition((position) => {
    socket.emit('driver_location', {
      latitude: position.coords.latitude,
      longitude: position.coords.longitude,
      accuracy: position.coords.accuracy
    });
  });
}
```

### 5. Combining All Enhancements
```javascript
class APIClient {
  constructor(baseURL, token) {
    this.baseURL = baseURL;
    this.token = token;
    this.version = 'v1.2';
  }
  
  async request(endpoint, options = {}) {
    const response = await fetch(`${this.baseURL}${endpoint}`, {
      ...options,
      headers: {
        'Authorization': `Bearer ${this.token}`,
        'Accept-Version': this.version,
        'Content-Type': 'application/json',
        ...options.headers
      },
      credentials: 'include'
    });
    
    // Handle rate limiting
    if (response.status === 429) {
      const retryAfter = parseInt(response.headers.get('Retry-After'));
      throw new RateLimitError(retryAfter);
    }
    
    // Check deprecation
    if (response.headers.get('Deprecated') === 'true') {
      console.warn('Using deprecated endpoint:', endpoint);
    }
    
    return response;
  }
}
```

## Security Considerations

1. **CORS**: Only whitelist trusted domains in production
2. **Rate Limiting**: Adjust limits based on actual usage patterns
3. **WebSocket**: Always validate JWT tokens on connection
4. **Versioning**: Plan deprecation schedules and communicate clearly

## Monitoring and Metrics

All enhancements include built-in monitoring:
- Rate limit violations are logged
- WebSocket connections are tracked
- Version usage is monitored
- CORS violations are logged

Check Prometheus metrics at `/metrics` endpoint.

## Troubleshooting

### CORS Issues
1. Check browser console for CORS errors
2. Verify origin is in allowed list
3. Ensure credentials are included in requests

### Rate Limiting Issues
1. Check rate limit headers in response
2. Implement proper retry logic
3. Consider authentication for higher limits

### Version Issues
1. Check supported version range
2. Update client to use newer versions
3. Monitor deprecation warnings

### WebSocket Issues
1. Verify JWT token is valid
2. Check network connectivity
3. Monitor Socket.IO debug logs