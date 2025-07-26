# Driver API Endpoints Documentation

## Overview

The Driver API provides endpoints for mobile app functionality, allowing drivers to manage their daily routes, update delivery statuses, and communicate with the office. All endpoints require authentication with a driver role.

## Authentication

All driver endpoints require JWT authentication:

```http
Authorization: Bearer <jwt_token>
```

## Base URL

```
https://api.luckygas.com.tw/api/v1/driver
```

## Endpoints

### 1. Get Today's Routes

Retrieve all routes assigned to the driver for the current day.

**Endpoint:** `GET /routes/today`

**Response:**
```json
[
  {
    "id": "123",
    "name": "早班路線 - 大安信義區",
    "deliveryCount": 15,
    "completedCount": 5,
    "estimatedTime": "3小時30分",
    "distance": 52.5,
    "status": "IN_PROGRESS"
  }
]
```

**Status Codes:**
- `200 OK` - Routes retrieved successfully
- `401 Unauthorized` - Invalid or missing token
- `403 Forbidden` - User is not a driver

---

### 2. Get Today's Delivery Statistics

Get summary statistics for today's deliveries.

**Endpoint:** `GET /stats/today`

**Response:**
```json
{
  "total": 25,
  "completed": 10,
  "pending": 14,
  "failed": 1
}
```

**Status Codes:**
- `200 OK` - Statistics retrieved successfully
- `401 Unauthorized` - Invalid or missing token

---

### 3. Get Route Details

Get detailed information about a specific route including all deliveries.

**Endpoint:** `GET /routes/{route_id}`

**Parameters:**
- `route_id` (path) - The ID of the route

**Response:**
```json
{
  "id": "123",
  "name": "早班路線 - 大安信義區",
  "totalDeliveries": 15,
  "completedDeliveries": 5,
  "estimatedDuration": "3小時30分",
  "totalDistance": 52.5,
  "deliveries": [
    {
      "id": "456",
      "customerName": "王小明",
      "address": "台北市大安區信義路四段123號",
      "phone": "0912-345-678",
      "products": [
        {
          "name": "20公斤家用桶裝瓦斯",
          "quantity": 2
        }
      ],
      "notes": "請按門鈴，勿敲門",
      "status": "pending",
      "sequence": 1
    }
  ]
}
```

**Status Codes:**
- `200 OK` - Route details retrieved successfully
- `404 Not Found` - Route not found or not assigned to driver

---

### 4. Update Driver Location

Update the driver's current GPS location for real-time tracking.

**Endpoint:** `POST /location`

**Request Body:**
```json
{
  "latitude": 25.0330,
  "longitude": 121.5654,
  "accuracy": 10.5,
  "speed": 25.5,
  "heading": 180.0,
  "timestamp": "2024-01-20T10:30:00Z"
}
```

**Response:**
```json
{
  "status": "success",
  "message": "位置更新成功"
}
```

**Notes:**
- Location updates are broadcast to office staff via WebSocket
- Updates are stored for route tracking and optimization

---

### 5. Update Delivery Status

Update the status of a delivery (arrived, delivered, failed, etc.).

**Endpoint:** `POST /deliveries/status/{delivery_id}`

**Parameters:**
- `delivery_id` (path) - The ID of the delivery

**Request Body:**
```json
{
  "status": "delivered",
  "notes": "已交付給警衛室",
  "issue_type": null
}
```

**Valid Status Values:**
- `pending` - 待配送
- `arrived` - 已到達
- `delivered` - 已送達
- `failed` - 配送失敗

**Issue Types (for failed deliveries):**
- `absent` - 客戶不在
- `rejected` - 客戶拒收
- `wrong_address` - 地址錯誤
- `access_denied` - 無法進入
- `other` - 其他原因

**Response:**
```json
{
  "status": "success",
  "message": "狀態更新成功"
}
```

---

### 6. Confirm Delivery Completion

Complete a delivery with signature and/or photo proof.

**Endpoint:** `POST /deliveries/confirm/{delivery_id}`

**Parameters:**
- `delivery_id` (path) - The ID of the delivery

**Request Body (multipart/form-data):**
- `recipient_name` (string, optional) - Name of person who received delivery
- `notes` (string, optional) - Delivery notes
- `signature` (string, optional) - Base64 encoded signature image
- `photo` (file, optional) - Photo proof of delivery

**Response:**
```json
{
  "success": true,
  "message": "配送確認成功",
  "delivery_id": "456",
  "order_id": "789"
}
```

**Notes:**
- At least one proof method (signature or photo) should be provided
- Customer notifications are sent automatically upon completion

---

### 7. Sync Offline Data

Synchronize offline data collected during network outages.

**Endpoint:** `POST /sync`

**Request Body:**
```json
{
  "locations": [
    {
      "id": "loc_123",
      "latitude": 25.0330,
      "longitude": 121.5654,
      "accuracy": 10.5,
      "timestamp": "2024-01-20T10:30:00Z"
    }
  ],
  "deliveries": [
    {
      "delivery_id": 456,
      "status": "delivered",
      "notes": "已交付",
      "delivered_at": "2024-01-20T10:45:00Z",
      "timestamp": "2024-01-20T10:45:00Z"
    }
  ]
}
```

**Response:**
```json
{
  "success": true,
  "synced_count": 5,
  "failed_count": 0,
  "synced_items": [
    {
      "type": "location",
      "id": "loc_123",
      "status": "synced"
    }
  ],
  "failed_items": [],
  "updated_routes": [...],
  "updated_stats": {...}
}
```

**Notes:**
- The sync endpoint handles batch updates from offline operations
- Returns updated routes and statistics after synchronization

---

### 8. Clock Out

Clock out at the end of the work day.

**Endpoint:** `POST /clock-out`

**Response:**
```json
{
  "success": true,
  "message": "打卡下班成功",
  "summary": {
    "working_hours": "8小時30分",
    "deliveries_completed": 25,
    "distance_traveled": 86.5,
    "overtime": "30分"
  }
}
```

---

## Error Responses

All endpoints may return the following error responses:

### 400 Bad Request
```json
{
  "detail": "Invalid request data"
}
```

### 401 Unauthorized
```json
{
  "detail": "Not authenticated"
}
```

### 403 Forbidden
```json
{
  "detail": "Not enough permissions"
}
```

### 404 Not Found
```json
{
  "detail": "Resource not found"
}
```

### 500 Internal Server Error
```json
{
  "detail": "Internal server error"
}
```

---

## WebSocket Events

Driver actions trigger real-time WebSocket events:

### Driver Location Update
```json
{
  "type": "driver.location",
  "driver_id": "123",
  "location": {
    "latitude": 25.0330,
    "longitude": 121.5654,
    "accuracy": 10.5,
    "timestamp": "2024-01-20T10:30:00Z",
    "speed": 25.5,
    "heading": 180.0
  }
}
```

### Delivery Status Update
```json
{
  "type": "delivery.status",
  "delivery_id": "456",
  "order_id": "789",
  "old_status": "pending",
  "new_status": "delivered",
  "driver": "張司機",
  "customer": "王小明",
  "timestamp": "2024-01-20T10:45:00Z"
}
```

### Delivery Completion
```json
{
  "type": "delivery.completed",
  "delivery_id": "456",
  "order_id": "789",
  "customer": "王小明",
  "driver": "張司機",
  "timestamp": "2024-01-20T10:45:00Z"
}
```

---

## Implementation Notes

### Mobile Optimization
- All endpoints are optimized for mobile network conditions
- Responses are kept minimal to reduce data usage
- Offline sync capability for areas with poor connectivity

### Security Considerations
- JWT tokens expire after 8 hours
- Driver can only access their own assigned routes
- Location data is encrypted in transit
- Signature/photo uploads are stored securely

### Performance Guidelines
- Location updates can be batched every 30 seconds
- Route details are cached for offline access
- Images are compressed before upload
- Sync operations use delta updates

---

## Example Usage

### cURL Example - Get Today's Routes
```bash
curl -X GET https://api.luckygas.com.tw/api/v1/driver/routes/today \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIs..."
```

### JavaScript Example - Update Location
```javascript
const updateLocation = async (lat, lng) => {
  const response = await fetch('/api/v1/driver/location', {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${token}`,
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({
      latitude: lat,
      longitude: lng,
      accuracy: 10.5,
      timestamp: new Date().toISOString()
    })
  });
  
  return response.json();
};
```

### React Native Example - Confirm Delivery
```javascript
const confirmDelivery = async (deliveryId, signature) => {
  const formData = new FormData();
  formData.append('recipient_name', '王小明');
  formData.append('notes', '已交付給本人');
  formData.append('signature', signature);
  
  const response = await fetch(`/api/v1/driver/deliveries/confirm/${deliveryId}`, {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${token}`
    },
    body: formData
  });
  
  return response.json();
};
```