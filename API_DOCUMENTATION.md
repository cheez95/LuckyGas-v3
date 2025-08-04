# 🚀 Lucky Gas API Documentation

**Base URL**: `https://api.luckygas.com` (Production) | `https://fuzzy-onions-bathe.loca.lt` (UAT)  
**Version**: v1  
**Authentication**: JWT Bearer Token

## 📋 Table of Contents

1. [Authentication](#authentication)
2. [Customers](#customers)
3. [Orders](#orders)
4. [Routes](#routes)
5. [Delivery](#delivery)
6. [Analytics](#analytics)
7. [Predictions](#predictions)
8. [Payments](#payments)
9. [Admin](#admin)
10. [WebSocket](#websocket)

---

## 🔐 Authentication

### Login
```http
POST /api/v1/auth/login
Content-Type: application/x-www-form-urlencoded

username=admin@luckygas.com&password=Test123!
```

**Response**:
```json
{
  "access_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
  "token_type": "bearer",
  "expires_in": 86400
}
```

### Get Current User
```http
GET /api/v1/auth/me
Authorization: Bearer {token}
```

**Response**:
```json
{
  "id": 1,
  "email": "admin@luckygas.com",
  "username": "admin@luckygas.com",
  "full_name": "System Admin",
  "role": "SUPER_ADMIN",
  "is_active": true,
  "created_at": "2025-01-20T10:00:00Z"
}
```

### Register New User
```http
POST /api/v1/auth/register
Content-Type: application/json
Authorization: Bearer {admin_token}

{
  "email": "newuser@luckygas.com",
  "username": "newuser",
  "password": "SecurePass123!",
  "full_name": "New User",
  "role": "OFFICE_STAFF"
}
```

---

## 👥 Customers

### List Customers
```http
GET /api/v1/customers?skip=0&limit=20&search=王
Authorization: Bearer {token}
```

**Query Parameters**:
- `skip`: Offset for pagination (default: 0)
- `limit`: Number of results (default: 20, max: 100)
- `search`: Search by name, phone, or address
- `is_active`: Filter by active status (true/false)

**Response**:
```json
{
  "total": 150,
  "items": [
    {
      "id": 1,
      "customer_code": "C0001",
      "name": "王小明",
      "phone": "0912-345-678",
      "address": "台北市信義區信義路五段7號",
      "district": "信義區",
      "delivery_schedule": "WEEKLY",
      "last_delivery_date": "2025-01-15",
      "next_predicted_date": "2025-01-22",
      "regular_quantity": 2,
      "is_active": true
    }
  ]
}
```

### Create Customer
```http
POST /api/v1/customers
Content-Type: application/json
Authorization: Bearer {token}

{
  "name": "張美麗",
  "phone": "0923-456-789",
  "address": "台北市大安區復興南路一段1號",
  "district": "大安區",
  "delivery_schedule": "BIWEEKLY",
  "regular_quantity": 1,
  "payment_method": "CASH",
  "notes": "週末在家"
}
```

### Update Customer
```http
PUT /api/v1/customers/{customer_id}
Content-Type: application/json
Authorization: Bearer {token}

{
  "phone": "0923-456-000",
  "delivery_schedule": "MONTHLY"
}
```

---

## 📦 Orders

### Create Order
```http
POST /api/v1/orders
Content-Type: application/json
Authorization: Bearer {token}

{
  "customer_id": 1,
  "delivery_date": "2025-01-22",
  "quantity": 2,
  "unit_price": 650,
  "delivery_time_preference": "MORNING",
  "notes": "請按門鈴"
}
```

### List Orders
```http
GET /api/v1/orders?date=2025-01-22&status=PENDING
Authorization: Bearer {token}
```

**Query Parameters**:
- `date`: Filter by delivery date (YYYY-MM-DD)
- `status`: PENDING, ASSIGNED, IN_PROGRESS, DELIVERED, CANCELLED
- `customer_id`: Filter by customer
- `driver_id`: Filter by driver

### Update Order Status
```http
PATCH /api/v1/orders/{order_id}/status
Content-Type: application/json
Authorization: Bearer {token}

{
  "status": "DELIVERED",
  "delivered_at": "2025-01-22T10:30:00Z",
  "delivered_quantity": 2,
  "payment_received": 1300
}
```

---

## 🚚 Routes

### Optimize Routes
```http
POST /api/v1/routes/optimize
Content-Type: application/json
Authorization: Bearer {token}

{
  "date": "2025-01-22",
  "settings": {
    "algorithm": "DISTANCE_PRIORITY",
    "max_orders_per_route": 30,
    "start_time": "08:00",
    "end_time": "18:00",
    "break_duration": 60,
    "service_time_per_delivery": 10
  }
}
```

**Response**:
```json
{
  "optimization_id": "opt_20250122_001",
  "total_routes": 5,
  "total_distance_km": 125.5,
  "total_duration_minutes": 480,
  "routes": [
    {
      "route_id": "R001",
      "driver_id": null,
      "total_orders": 25,
      "total_distance_km": 28.3,
      "estimated_duration_minutes": 95,
      "orders": [...]
    }
  ]
}
```

### Assign Driver to Route
```http
POST /api/v1/routes/{route_id}/assign
Content-Type: application/json
Authorization: Bearer {token}

{
  "driver_id": 3,
  "vehicle_id": 2
}
```

### Get Route Details
```http
GET /api/v1/routes/{route_id}
Authorization: Bearer {token}
```

---

## 🚛 Delivery

### Update Delivery Status
```http
POST /api/v1/deliveries/{order_id}/status
Content-Type: application/json
Authorization: Bearer {token}

{
  "status": "ARRIVED",
  "location": {
    "latitude": 25.0330,
    "longitude": 121.5654
  },
  "timestamp": "2025-01-22T10:15:00Z"
}
```

### Upload Delivery Proof
```http
POST /api/v1/deliveries/{order_id}/proof
Content-Type: multipart/form-data
Authorization: Bearer {token}

photo: [binary]
signature: [binary]
notes: "已交付給管理員"
```

### Get Delivery History
```http
GET /api/v1/deliveries/history?customer_id=1&limit=10
Authorization: Bearer {token}
```

---

## 📊 Analytics

### Daily Summary
```http
GET /api/v1/analytics/daily-summary?date=2025-01-22
Authorization: Bearer {token}
```

**Response**:
```json
{
  "date": "2025-01-22",
  "total_orders": 125,
  "delivered_orders": 120,
  "pending_orders": 5,
  "total_revenue": 81250,
  "total_cylinders": 245,
  "delivery_rate": 96.0,
  "average_delivery_time_minutes": 12.5
}
```

### Driver Performance
```http
GET /api/v1/analytics/driver-performance?start_date=2025-01-01&end_date=2025-01-31
Authorization: Bearer {token}
```

### Customer Analytics
```http
GET /api/v1/analytics/customers/insights
Authorization: Bearer {token}
```

---

## 🔮 Predictions

### Daily Demand Prediction
```http
POST /api/v1/predictions/demand/daily
Content-Type: application/json
Authorization: Bearer {token}

{
  "date": "2025-01-23",
  "include_weather": true,
  "include_holidays": true
}
```

**Response**:
```json
{
  "date": "2025-01-23",
  "predicted_orders": 132,
  "confidence_level": 0.85,
  "factors": {
    "historical_average": 125,
    "weather_impact": 1.05,
    "day_of_week_factor": 1.02,
    "trend": "increasing"
  }
}
```

### Customer Churn Prediction
```http
POST /api/v1/predictions/churn
Content-Type: application/json
Authorization: Bearer {token}

{
  "customer_ids": [1, 2, 3],
  "threshold": 0.7
}
```

---

## 💰 Payments

### Record Payment
```http
POST /api/v1/payments
Content-Type: application/json
Authorization: Bearer {token}

{
  "order_id": 123,
  "amount": 1300,
  "payment_method": "CASH",
  "reference_number": "CASH-20250122-001"
}
```

### Payment Reconciliation
```http
POST /api/v1/payments/reconcile
Content-Type: application/json
Authorization: Bearer {token}

{
  "date": "2025-01-22",
  "driver_id": 3
}
```

### Generate Payment Report
```http
GET /api/v1/payments/reports/daily-summary?date=2025-01-22
Authorization: Bearer {token}
```

---

## 👤 Admin

### System Health Check
```http
GET /api/v1/health/detailed
Authorization: Bearer {token}
```

### Feature Flags
```http
GET /api/v1/feature-flags
Authorization: Bearer {admin_token}
```

### Migration Status
```http
GET /api/v1/admin/migration/metrics
Authorization: Bearer {admin_token}
```

---

## 🔌 WebSocket

### Connect to WebSocket
```javascript
const ws = new WebSocket('wss://api.luckygas.com/api/v1/ws');

ws.onopen = () => {
  ws.send(JSON.stringify({
    type: 'auth',
    token: 'your_jwt_token'
  }));
};

ws.onmessage = (event) => {
  const data = JSON.parse(event.data);
  console.log('Received:', data);
};
```

### Event Types
- `delivery_update`: Real-time delivery status updates
- `route_assigned`: Driver assigned to route
- `order_created`: New order created
- `payment_received`: Payment confirmation

---

## 🚨 Error Responses

### Standard Error Format
```json
{
  "detail": "錯誤訊息",
  "type": "error_type",
  "errors": [
    {
      "field": "email",
      "message": "無效的電子郵件格式"
    }
  ]
}
```

### Common HTTP Status Codes
- `200`: Success
- `201`: Created
- `400`: Bad Request (validation error)
- `401`: Unauthorized (invalid/missing token)
- `403`: Forbidden (insufficient permissions)
- `404`: Not Found
- `409`: Conflict (duplicate resource)
- `422`: Unprocessable Entity
- `500`: Internal Server Error

---

## 🔒 Rate Limiting

- **Default**: 100 requests per minute per IP
- **Authenticated**: 1000 requests per minute per user
- **Headers**:
  - `X-RateLimit-Limit`: Maximum requests
  - `X-RateLimit-Remaining`: Remaining requests
  - `X-RateLimit-Reset`: Reset timestamp

---

## 📝 Notes

1. All timestamps are in UTC format (ISO 8601)
2. Monetary amounts are in TWD (Taiwan Dollar)
3. Phone numbers should include country code (+886) or local format
4. Addresses should be in Traditional Chinese
5. Pagination uses `skip` and `limit` parameters
6. Search is case-insensitive and supports partial matching

---

## 🧪 Testing

Use the UAT environment for testing:
- Base URL: `https://fuzzy-onions-bathe.loca.lt`
- Test Accounts:
  - Admin: `admin@luckygas.com` / `Test123!`
  - User: `test@luckygas.com` / `Test123!`

---

## 📞 Support

For API support or questions:
- Email: api-support@luckygas.com
- Documentation: https://docs.luckygas.com/api
- Status Page: https://status.luckygas.com