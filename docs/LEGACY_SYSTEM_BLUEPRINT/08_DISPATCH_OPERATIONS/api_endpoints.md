# Dispatch Operations API Endpoints - Lucky Gas Legacy System

## 🎯 API Overview

The Dispatch Operations API provides comprehensive endpoints for managing delivery operations, route optimization, driver assignments, and real-time tracking. These RESTful APIs support both internal system integration and external partner connectivity for Lucky Gas's logistics operations.

## 🔐 Authentication & Authorization

### Authentication Method
```http
Authorization: Bearer {jwt_token}
X-API-Key: {api_key}
X-Client-ID: {client_id}
```

### Role-Based Permissions
```yaml
dispatch_manager:
  - Full access to all dispatch operations
  - Route planning and optimization
  - Driver assignment management
  - Emergency dispatch authorization

route_planner:
  - Route creation and modification
  - Driver assignment suggestions
  - Performance analysis access
  - Read-only financial data

driver_supervisor:
  - Driver schedule management
  - Performance monitoring
  - Training assignment
  - Incident reporting

driver:
  - Own route access
  - Delivery confirmation
  - Status updates
  - Issue reporting

tracking_viewer:
  - Real-time location viewing
  - Delivery status monitoring
  - ETA information
  - Historical tracking data
```

## 📍 Base URLs

```yaml
Production: https://api.luckygas.com.tw/v1/dispatch
Staging: https://staging-api.luckygas.com.tw/v1/dispatch
Development: http://localhost:8080/api/v1/dispatch
```

## 🛣️ Route Planning Endpoints

### Create Route Plan
```http
POST /routes/plan
Content-Type: application/json

{
  "planDate": "2024-01-20",
  "zoneId": "ZONE_001",
  "vehicleType": "3.5T_TRUCK",
  "constraints": {
    "maxStops": 30,
    "maxDistance": 150,
    "maxDuration": 480,
    "startTime": "08:00",
    "endTime": "17:00"
  },
  "optimization": {
    "objective": "MINIMIZE_DISTANCE",
    "trafficModel": "HISTORICAL",
    "breakDuration": 60
  }
}

Response 200:
{
  "routeId": "ROUTE_20240120_001",
  "status": "PLANNED",
  "totalStops": 28,
  "totalDistance": 142.5,
  "estimatedDuration": 465,
  "efficiency": 0.89,
  "route": [
    {
      "sequence": 1,
      "customerId": "CUST_001",
      "arrivalTime": "08:30",
      "serviceTime": 10
    }
  ]
}
```

### Optimize Existing Routes
```http
POST /routes/optimize
Content-Type: application/json

{
  "routeIds": ["ROUTE_001", "ROUTE_002"],
  "optimizationType": "CROSS_ROUTE",
  "constraints": {
    "maintainDriverAssignment": false,
    "respectTimeWindows": true,
    "maxRouteChanges": 10
  }
}

Response 200:
{
  "optimizationId": "OPT_20240120_001",
  "originalCost": 5420.50,
  "optimizedCost": 4680.25,
  "savingsPercent": 13.7,
  "changes": [
    {
      "type": "MOVE_STOP",
      "stopId": "STOP_123",
      "fromRoute": "ROUTE_001",
      "toRoute": "ROUTE_002"
    }
  ]
}
```

### Get Route Details
```http
GET /routes/{routeId}

Response 200:
{
  "routeId": "ROUTE_20240120_001",
  "status": "IN_PROGRESS",
  "driver": {
    "id": "DRV_001",
    "name": "王大明",
    "mobile": "0912-345-678"
  },
  "vehicle": {
    "id": "VEH_001",
    "type": "3.5T_TRUCK",
    "plateNumber": "ABC-1234"
  },
  "progress": {
    "completedStops": 15,
    "totalStops": 28,
    "currentLocation": {
      "lat": 25.0330,
      "lng": 121.5654
    },
    "eta": "16:30"
  }
}
```

## 👨‍✈️ Driver Management Endpoints

### Assign Driver to Route
```http
POST /drivers/assign
Content-Type: application/json

{
  "routeId": "ROUTE_20240120_001",
  "driverId": "DRV_001",
  "vehicleId": "VEH_001",
  "effectiveTime": "2024-01-20T08:00:00+08:00",
  "notes": "Experienced with zone"
}

Response 200:
{
  "assignmentId": "ASSIGN_001",
  "status": "CONFIRMED",
  "matchScore": 0.92,
  "workHours": {
    "daily": 8.5,
    "weekly": 42.5,
    "overtime": 0
  },
  "notifications": [
    {
      "type": "SMS",
      "sentAt": "2024-01-19T20:00:00+08:00",
      "status": "DELIVERED"
    }
  ]
}
```

### Get Driver Availability
```http
GET /drivers/availability?date=2024-01-20&shift=MORNING

Response 200:
{
  "date": "2024-01-20",
  "shift": "MORNING",
  "available": [
    {
      "driverId": "DRV_001",
      "name": "王大明",
      "licenseType": "PROFESSIONAL",
      "workHoursRemaining": 10,
      "skills": ["HAZMAT", "MOUNTAIN"],
      "homeLocation": {
        "lat": 25.0478,
        "lng": 121.5318
      }
    }
  ],
  "onLeave": ["DRV_005", "DRV_012"],
  "restricted": [
    {
      "driverId": "DRV_008",
      "reason": "MEDICAL_CHECK_PENDING"
    }
  ]
}
```

### Update Driver Status
```http
PATCH /drivers/{driverId}/status
Content-Type: application/json

{
  "status": "ON_BREAK",
  "location": {
    "lat": 25.0330,
    "lng": 121.5654
  },
  "duration": 30,
  "reason": "LUNCH"
}

Response 200:
{
  "driverId": "DRV_001",
  "previousStatus": "DELIVERING",
  "currentStatus": "ON_BREAK",
  "resumeTime": "2024-01-20T12:30:00+08:00",
  "routeAdjustment": {
    "required": true,
    "newETA": "17:00"
  }
}
```

## 📍 Delivery Tracking Endpoints

### Update Vehicle Location
```http
POST /tracking/location
Content-Type: application/json

{
  "vehicleId": "VEH_001",
  "timestamp": "2024-01-20T10:30:45+08:00",
  "location": {
    "lat": 25.0330,
    "lng": 121.5654,
    "accuracy": 10,
    "speed": 45,
    "heading": 270
  },
  "status": {
    "engineOn": true,
    "moving": true,
    "fuel": 75
  }
}

Response 200:
{
  "accepted": true,
  "processed": "2024-01-20T10:30:46+08:00",
  "alerts": [
    {
      "type": "SPEED_WARNING",
      "message": "Speed limit exceeded"
    }
  ]
}
```

### Get Real-time Tracking
```http
GET /tracking/live/{routeId}

Response 200:
{
  "routeId": "ROUTE_20240120_001",
  "lastUpdate": "2024-01-20T10:31:00+08:00",
  "vehicle": {
    "location": {
      "lat": 25.0330,
      "lng": 121.5654
    },
    "speed": 42,
    "status": "EN_ROUTE"
  },
  "progress": {
    "currentStop": 15,
    "nextStop": {
      "customerId": "CUST_016",
      "address": "台北市大安區信義路四段",
      "eta": "10:45",
      "distance": 2.3
    }
  }
}
```

### Subscribe to Tracking Updates (WebSocket)
```javascript
ws://api.luckygas.com.tw/v1/dispatch/tracking/subscribe

// Subscribe message
{
  "action": "subscribe",
  "routeIds": ["ROUTE_001", "ROUTE_002"],
  "events": ["location", "status", "delivery"]
}

// Update message
{
  "event": "location_update",
  "routeId": "ROUTE_001",
  "timestamp": "2024-01-20T10:31:15+08:00",
  "data": {
    "lat": 25.0331,
    "lng": 121.5655,
    "speed": 38
  }
}
```

## 🚚 Delivery Operations Endpoints

### Confirm Delivery
```http
POST /deliveries/confirm
Content-Type: application/json

{
  "deliveryId": "DEL_20240120_001_015",
  "timestamp": "2024-01-20T10:45:30+08:00",
  "location": {
    "lat": 25.0330,
    "lng": 121.5654
  },
  "proof": {
    "type": "SIGNATURE",
    "data": "base64_signature_image",
    "recipientName": "陳小姐"
  },
  "products": [
    {
      "productId": "GAS_20KG",
      "quantity": 2,
      "serialNumbers": ["SN123456", "SN123457"]
    }
  ],
  "payment": {
    "method": "CASH",
    "amount": 1800,
    "collected": true
  }
}

Response 200:
{
  "deliveryId": "DEL_20240120_001_015",
  "status": "COMPLETED",
  "confirmation": {
    "number": "CONF_20240120_0234",
    "timestamp": "2024-01-20T10:45:32+08:00"
  },
  "nextStop": {
    "sequence": 16,
    "customerId": "CUST_017",
    "distance": 1.8,
    "eta": "11:00"
  }
}
```

### Report Delivery Issue
```http
POST /deliveries/issues
Content-Type: application/json

{
  "deliveryId": "DEL_20240120_001_015",
  "issueType": "CUSTOMER_NOT_HOME",
  "description": "客戶不在家，已留字條",
  "location": {
    "lat": 25.0330,
    "lng": 121.5654
  },
  "photos": ["photo_url_1"],
  "resolution": {
    "action": "RESCHEDULE",
    "proposedTime": "2024-01-20T15:00:00+08:00"
  }
}

Response 200:
{
  "issueId": "ISSUE_20240120_001",
  "status": "PENDING_RESOLUTION",
  "customerNotified": true,
  "rescheduled": {
    "newDeliveryId": "DEL_20240120_002_008",
    "assignedRoute": "ROUTE_20240120_002",
    "eta": "15:30"
  }
}
```

## 📦 Loading & Dispatch Endpoints

### Create Loading Plan
```http
POST /loading/plan
Content-Type: application/json

{
  "date": "2024-01-20",
  "vehicleId": "VEH_001",
  "routeId": "ROUTE_20240120_001",
  "products": [
    {
      "productId": "GAS_20KG",
      "quantity": 50,
      "loadingSequence": "LIFO"
    },
    {
      "productId": "GAS_16KG",
      "quantity": 30,
      "loadingSequence": "FIFO"
    }
  ]
}

Response 200:
{
  "loadingPlanId": "LOAD_20240120_001",
  "vehicleCapacityUsed": 0.85,
  "weightDistribution": {
    "front": 0.45,
    "rear": 0.55
  },
  "loadingInstructions": [
    {
      "step": 1,
      "product": "GAS_20KG",
      "quantity": 25,
      "position": "REAR_LEFT"
    }
  ]
}
```

### Complete Loading
```http
POST /loading/complete
Content-Type: application/json

{
  "loadingPlanId": "LOAD_20240120_001",
  "actualProducts": [
    {
      "productId": "GAS_20KG",
      "quantity": 48,
      "serialNumbers": ["SN_LIST..."]
    }
  ],
  "checklist": {
    "vehicleInspection": true,
    "loadSecured": true,
    "documentsComplete": true,
    "safetyEquipment": true
  },
  "loadedBy": "STAFF_001",
  "verifiedBy": "SUPERVISOR_001"
}

Response 200:
{
  "status": "LOADING_COMPLETE",
  "departureAuthorized": true,
  "discrepancies": [
    {
      "productId": "GAS_20KG",
      "planned": 50,
      "actual": 48,
      "reason": "STOCK_SHORTAGE"
    }
  ]
}
```

## 🚨 Emergency Dispatch Endpoints

### Create Emergency Request
```http
POST /emergency/request
Content-Type: application/json

{
  "priority": "CRITICAL",
  "type": "GAS_LEAK",
  "customer": {
    "id": "CUST_999",
    "name": "台大醫院",
    "contact": "02-2312-3456"
  },
  "location": {
    "address": "台北市中正區中山南路7號",
    "lat": 25.0408,
    "lng": 121.5197
  },
  "description": "醫院氧氣供應緊急",
  "requiredProducts": [
    {
      "productId": "OXYGEN_MEDICAL",
      "quantity": 10,
      "urgency": "IMMEDIATE"
    }
  ]
}

Response 200:
{
  "emergencyId": "EMRG_20240120_001",
  "status": "DISPATCHING",
  "priority": "CRITICAL",
  "assignedResources": {
    "driver": "DRV_EMERGENCY_001",
    "vehicle": "VEH_EMERGENCY_001",
    "eta": "2024-01-20T11:15:00+08:00"
  },
  "notifications": [
    "Customer notified",
    "Driver alerted",
    "Management informed"
  ]
}
```

### Update Emergency Status
```http
PATCH /emergency/{emergencyId}/status
Content-Type: application/json

{
  "status": "EN_ROUTE",
  "currentLocation": {
    "lat": 25.0350,
    "lng": 121.5400
  },
  "eta": "2024-01-20T11:12:00+08:00",
  "notes": "Traffic cleared, arriving earlier"
}

Response 200:
{
  "emergencyId": "EMRG_20240120_001",
  "previousStatus": "DISPATCHING",
  "currentStatus": "EN_ROUTE",
  "customerNotified": true,
  "timeline": [
    {
      "timestamp": "11:00:00",
      "event": "Emergency reported"
    },
    {
      "timestamp": "11:02:00",
      "event": "Driver dispatched"
    },
    {
      "timestamp": "11:05:00",
      "event": "En route"
    }
  ]
}
```

## 📊 Analytics & Reporting Endpoints

### Get Route Performance Metrics
```http
GET /analytics/routes/performance?date=2024-01-20

Response 200:
{
  "date": "2024-01-20",
  "metrics": {
    "totalRoutes": 25,
    "completionRate": 0.96,
    "onTimeDelivery": 0.92,
    "averageStopsPerRoute": 28,
    "averageTimePerStop": 12.5,
    "fuelEfficiency": {
      "average": 8.2,
      "unit": "km/l"
    }
  },
  "topPerformers": [
    {
      "driverId": "DRV_001",
      "efficiency": 0.98,
      "customerRating": 4.8
    }
  ],
  "issues": {
    "delays": 8,
    "failed": 3,
    "rescheduled": 5
  }
}
```

### Get Driver Performance Report
```http
GET /analytics/drivers/{driverId}/performance?period=2024-01

Response 200:
{
  "driverId": "DRV_001",
  "period": "2024-01",
  "summary": {
    "totalDeliveries": 580,
    "onTimeRate": 0.94,
    "customerRating": 4.7,
    "safetyScore": 98,
    "fuelEfficiency": 8.5
  },
  "violations": [
    {
      "date": "2024-01-15",
      "type": "SPEED_WARNING",
      "severity": "MINOR"
    }
  ],
  "recognition": [
    {
      "type": "CUSTOMER_COMPLIMENT",
      "date": "2024-01-18",
      "details": "Excellent service"
    }
  ]
}
```

## 🔄 Integration Webhooks

### Delivery Status Webhook
```http
POST https://customer-system.com/webhook/delivery
Content-Type: application/json
X-Webhook-Signature: sha256=...

{
  "event": "delivery.completed",
  "timestamp": "2024-01-20T10:45:32+08:00",
  "data": {
    "deliveryId": "DEL_20240120_001_015",
    "customerId": "CUST_015",
    "status": "COMPLETED",
    "products": [
      {
        "productId": "GAS_20KG",
        "quantity": 2
      }
    ],
    "signature": "https://cdn.luckygas.com/signatures/sign_12345.png"
  }
}
```

### Route Optimization Webhook
```http
POST https://planning-system.com/webhook/optimization
Content-Type: application/json

{
  "event": "route.optimized",
  "timestamp": "2024-01-20T06:00:00+08:00",
  "data": {
    "optimizationId": "OPT_20240120_001",
    "affectedRoutes": ["ROUTE_001", "ROUTE_002"],
    "savings": {
      "distance": 45.2,
      "time": 120,
      "fuel": 5.5
    }
  }
}
```

## 🚦 Rate Limiting

```yaml
Endpoint Limits:
  tracking/location: 1000 requests/minute
  routes/*: 100 requests/minute
  analytics/*: 10 requests/minute
  emergency/*: No limit
  
Burst Allowance: 2x normal rate for 10 seconds
Exceeded Response: HTTP 429 with Retry-After header
```

## 🔍 Error Responses

### Standard Error Format
```json
{
  "error": {
    "code": "ROUTE_NOT_FOUND",
    "message": "指定的路線不存在",
    "details": {
      "routeId": "ROUTE_999",
      "timestamp": "2024-01-20T10:30:00+08:00"
    },
    "requestId": "req_abc123"
  }
}
```

### Common Error Codes
- `AUTH_FAILED` - Authentication failed
- `PERMISSION_DENIED` - Insufficient permissions
- `RESOURCE_NOT_FOUND` - Requested resource not found
- `VALIDATION_ERROR` - Input validation failed
- `CONFLICT` - Resource conflict (e.g., double booking)
- `CAPACITY_EXCEEDED` - Vehicle/route capacity exceeded
- `DRIVER_UNAVAILABLE` - Driver not available
- `SYSTEM_ERROR` - Internal server error

## 📝 API Versioning

- Current version: v1
- Version in URL path: `/v1/dispatch`
- Deprecation notice: 6 months
- Sunset period: 12 months
- Migration guide provided for breaking changes