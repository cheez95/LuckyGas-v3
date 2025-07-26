# Order Sales API Endpoints (訂單銷售 API)

**Module**: Order Sales  
**Base URL**: `https://api.luckygas.com.tw/api/v1`  
**Authentication**: Bearer JWT Token  
**Content-Type**: application/json  
**API Version**: 1.0

## 🔐 Authentication Headers

```http
Authorization: Bearer {jwt_token}
X-API-Version: 1.0
X-Client-ID: {client_id}
X-Request-ID: {uuid}
Accept-Language: zh-TW
```

## 📋 API Endpoints Overview

### Order Management
- **CREATE**: `POST /orders` - Create new order
- **READ**: `GET /orders/{id}` - Get order details
- **UPDATE**: `PUT /orders/{id}` - Update order
- **DELETE**: `DELETE /orders/{id}` - Cancel order
- **LIST**: `GET /orders` - List orders with filters

### Order Operations
- **STATUS**: `PUT /orders/{id}/status` - Update order status
- **VALIDATE**: `POST /orders/validate` - Pre-validate order
- **DUPLICATE**: `POST /orders/{id}/duplicate` - Copy order
- **SPLIT**: `POST /orders/{id}/split` - Split into multiple orders

### Search & Reporting
- **SEARCH**: `POST /orders/search` - Advanced search
- **REPORT**: `GET /orders/reports/{type}` - Generate reports
- **EXPORT**: `GET /orders/export` - Export data
- **STATS**: `GET /orders/statistics` - Order statistics

## 🚀 Order CRUD Operations

### Create Order
```http
POST /api/v1/orders
```

**Request Body:**
```json
{
  "customer_id": "C000123",
  "delivery_date": "2024-01-26",
  "delivery_time_slot": "02",  // 01:Morning, 02:Afternoon, 03:Evening
  "delivery_address_id": 456,
  "delivery_notes": "請按門鈴，狗不咬人",
  "payment_method": "01",  // 01:Cash, 02:Monthly, 03:Transfer
  "order_source": "01",    // 01:Phone, 02:Fax, 03:Web, 04:App
  "priority_flag": "N",
  "items": [
    {
      "product_id": "P001",
      "quantity": 2,
      "unit_price": 850.00,
      "discount_percent": 0,
      "special_price_reason": null,
      "notes": "客戶要求新桶"
    }
  ],
  "promotion_code": "NEWYEAR2024"
}
```

**Success Response (201 Created):**
```json
{
  "success": true,
  "data": {
    "order_id": "O-20240125-000123",
    "customer_id": "C000123",
    "order_date": "2024-01-25T14:30:00Z",
    "delivery_date": "2024-01-26",
    "delivery_time_slot": "02",
    "order_status": "02",  // Confirmed
    "items": [
      {
        "detail_id": 1234,
        "product_id": "P001",
        "product_name": "20kg 瓦斯桶",
        "quantity": 2,
        "unit_price": 850.00,
        "line_total": 1700.00
      }
    ],
    "subtotal": 1700.00,
    "tax_amount": 85.00,
    "delivery_fee": 50.00,
    "discount_amount": 0.00,
    "final_amount": 1835.00,
    "credit_used": 1835.00,
    "payment_status": "01",  // Unpaid
    "created_at": "2024-01-25T14:30:00Z",
    "created_by": "USER001"
  },
  "message": "訂單建立成功",
  "links": {
    "self": "/api/v1/orders/O-20240125-000123",
    "customer": "/api/v1/customers/C000123",
    "cancel": "/api/v1/orders/O-20240125-000123/cancel",
    "modify": "/api/v1/orders/O-20240125-000123"
  }
}
```

**Error Response (400 Bad Request):**
```json
{
  "success": false,
  "error": {
    "code": "INSUFFICIENT_CREDIT",
    "message": "信用額度不足",
    "details": {
      "credit_limit": 5000.00,
      "credit_used": 4500.00,
      "order_amount": 1835.00,
      "available_credit": 500.00
    },
    "suggestions": [
      "減少訂單數量",
      "要求預付款",
      "聯絡主管核准"
    ]
  }
}
```

### Get Order Details
```http
GET /api/v1/orders/{order_id}
```

**Path Parameters:**
- `order_id` (required): Order identifier

**Query Parameters:**
- `include` (optional): Comma-separated related data
  - `customer`: Include customer details
  - `driver`: Include assigned driver info
  - `history`: Include status history
  - `signature`: Include delivery signature

**Success Response (200 OK):**
```json
{
  "success": true,
  "data": {
    "order_id": "O-20240125-000123",
    "customer": {
      "customer_id": "C000123",
      "customer_name": "王大明",
      "phone": "0912-345-678",
      "credit_status": "GOOD"
    },
    "delivery": {
      "address": "台北市信義區信義路五段7號",
      "date": "2024-01-26",
      "time_slot": "02",
      "time_slot_desc": "下午 13:00-17:00",
      "driver": {
        "driver_id": "D001",
        "driver_name": "李師傅",
        "phone": "0923-456-789",
        "vehicle": "3456-AB"
      }
    },
    "items": [...],
    "payment": {
      "method": "01",
      "method_desc": "現金",
      "status": "01",
      "status_desc": "未付款",
      "amount": 1835.00
    },
    "status_history": [
      {
        "status": "01",
        "status_desc": "草稿",
        "timestamp": "2024-01-25T14:25:00Z",
        "user": "USER001"
      },
      {
        "status": "02",
        "status_desc": "已確認",
        "timestamp": "2024-01-25T14:30:00Z",
        "user": "USER001"
      }
    ]
  }
}
```

### Update Order
```http
PUT /api/v1/orders/{order_id}
```

**Request Body (Partial Update):**
```json
{
  "delivery_date": "2024-01-27",
  "delivery_time_slot": "01",
  "delivery_notes": "改到早上送，客戶下午不在",
  "modification_reason": "客戶要求更改配送時間"
}
```

**Success Response (200 OK):**
```json
{
  "success": true,
  "data": {
    "order_id": "O-20240125-000123",
    "changes_applied": {
      "delivery_date": {
        "old": "2024-01-26",
        "new": "2024-01-27"
      },
      "delivery_time_slot": {
        "old": "02",
        "new": "01"
      }
    },
    "updated_at": "2024-01-25T15:00:00Z",
    "updated_by": "USER001"
  },
  "message": "訂單更新成功"
}
```

### Cancel Order
```http
DELETE /api/v1/orders/{order_id}
```

**Request Body:**
```json
{
  "cancellation_reason": "01",  // Reason code
  "cancellation_notes": "客戶臨時出國",
  "waive_charges": false
}
```

**Success Response (200 OK):**
```json
{
  "success": true,
  "data": {
    "order_id": "O-20240125-000123",
    "cancellation": {
      "reason": "01",
      "reason_desc": "客戶改變心意",
      "notes": "客戶臨時出國",
      "charges": 0.00,
      "refund_amount": 0.00,
      "credit_released": 1835.00
    },
    "cancelled_at": "2024-01-25T16:00:00Z",
    "cancelled_by": "USER001"
  },
  "message": "訂單已取消"
}
```

## 🔍 Search & Query Operations

### List Orders
```http
GET /api/v1/orders
```

**Query Parameters:**
- `page` (default: 1): Page number
- `per_page` (default: 20, max: 100): Items per page
- `customer_id`: Filter by customer
- `status`: Filter by status (comma-separated)
- `date_from`: Start date (YYYY-MM-DD)
- `date_to`: End date (YYYY-MM-DD)
- `delivery_date`: Specific delivery date
- `driver_id`: Filter by assigned driver
- `sort_by` (default: order_date): Sort field
- `sort_order` (default: desc): asc or desc

**Example Request:**
```
GET /api/v1/orders?status=02,03&delivery_date=2024-01-26&sort_by=order_id
```

**Success Response (200 OK):**
```json
{
  "success": true,
  "data": {
    "orders": [
      {
        "order_id": "O-20240125-000123",
        "customer_id": "C000123",
        "customer_name": "王大明",
        "order_date": "2024-01-25T14:30:00Z",
        "delivery_date": "2024-01-26",
        "status": "02",
        "status_desc": "已確認",
        "total_amount": 1835.00,
        "payment_status": "01"
      }
    ],
    "pagination": {
      "page": 1,
      "per_page": 20,
      "total_pages": 5,
      "total_items": 98,
      "has_next": true,
      "has_prev": false
    }
  },
  "links": {
    "self": "/api/v1/orders?page=1",
    "next": "/api/v1/orders?page=2",
    "last": "/api/v1/orders?page=5"
  }
}
```

### Advanced Search
```http
POST /api/v1/orders/search
```

**Request Body:**
```json
{
  "filters": {
    "customer": {
      "name_contains": "王",
      "credit_status": ["GOOD", "FAIR"]
    },
    "order": {
      "total_amount": {
        "min": 1000,
        "max": 5000
      },
      "created_between": {
        "start": "2024-01-01T00:00:00Z",
        "end": "2024-01-31T23:59:59Z"
      }
    },
    "delivery": {
      "zones": ["NORTH", "CENTRAL"],
      "time_slots": ["01", "02"]
    },
    "product": {
      "product_ids": ["P001", "P002"],
      "min_quantity": 2
    }
  },
  "aggregations": {
    "by_status": true,
    "by_payment_method": true,
    "total_revenue": true
  },
  "sort": [
    {"field": "order_date", "order": "desc"},
    {"field": "total_amount", "order": "desc"}
  ],
  "pagination": {
    "page": 1,
    "per_page": 50
  }
}
```

## 📊 Reporting Endpoints

### Daily Report
```http
GET /api/v1/orders/reports/daily
```

**Query Parameters:**
- `date` (required): Report date (YYYY-MM-DD)
- `zone` (optional): Delivery zone filter
- `format` (default: json): json, csv, pdf

**Success Response:**
```json
{
  "success": true,
  "data": {
    "report_date": "2024-01-25",
    "summary": {
      "total_orders": 156,
      "total_revenue": 234500.00,
      "total_cylinders": 203,
      "delivery_success_rate": 0.94
    },
    "by_status": {
      "confirmed": 45,
      "dispatched": 78,
      "delivered": 142,
      "cancelled": 4
    },
    "by_time_slot": {
      "morning": 67,
      "afternoon": 72,
      "evening": 17
    },
    "by_payment": {
      "cash": 98,
      "monthly": 45,
      "transfer": 13
    },
    "top_customers": [
      {
        "customer_id": "C000456",
        "customer_name": "大同餐廳",
        "orders": 3,
        "revenue": 5400.00
      }
    ]
  }
}
```

### Monthly Report
```http
GET /api/v1/orders/reports/monthly
```

**Query Parameters:**
- `year` (required): Year (YYYY)
- `month` (required): Month (1-12)
- `include_comparison` (optional): Include YoY comparison

### Custom Report
```http
POST /api/v1/orders/reports/custom
```

**Request Body:**
```json
{
  "date_range": {
    "start": "2024-01-01",
    "end": "2024-01-31"
  },
  "metrics": [
    "order_count",
    "revenue",
    "average_order_value",
    "cylinder_count"
  ],
  "group_by": ["date", "zone", "customer_type"],
  "filters": {
    "zones": ["NORTH"],
    "min_amount": 1000
  }
}
```

## 🔄 Order Operations

### Update Order Status
```http
PUT /api/v1/orders/{order_id}/status
```

**Request Body:**
```json
{
  "new_status": "03",  // Dispatched
  "reason": "正常派送",
  "driver_id": "D001",
  "route_sequence": 5,
  "estimated_arrival": "2024-01-26T14:30:00Z"
}
```

### Validate Order
```http
POST /api/v1/orders/validate
```

**Request Body:** (Same as create order)

**Success Response:**
```json
{
  "success": true,
  "data": {
    "validation_result": "PASS",
    "checks": {
      "customer_active": true,
      "credit_available": true,
      "products_available": true,
      "delivery_zone_valid": true,
      "delivery_slot_available": true
    },
    "warnings": [
      "客戶有一筆逾期款項 NT$ 500"
    ],
    "estimated_total": 1835.00
  }
}
```

### Duplicate Order
```http
POST /api/v1/orders/{order_id}/duplicate
```

**Request Body:**
```json
{
  "delivery_date": "2024-02-01",
  "include_items": true,
  "auto_confirm": false
}
```

### Split Order
```http
POST /api/v1/orders/{order_id}/split
```

**Request Body:**
```json
{
  "split_strategy": "BY_AMOUNT",  // BY_AMOUNT, BY_ITEMS, CUSTOM
  "parts": [
    {
      "items": [
        {"detail_id": 1234, "quantity": 1}
      ],
      "delivery_date": "2024-01-26"
    },
    {
      "items": [
        {"detail_id": 1234, "quantity": 1}
      ],
      "delivery_date": "2024-01-27"
    }
  ]
}
```

## 🔒 Bulk Operations

### Bulk Create Orders
```http
POST /api/v1/orders/bulk
```

**Request Body:**
```json
{
  "orders": [
    {...},  // Order 1
    {...}   // Order 2
  ],
  "validation_mode": "STRICT",  // STRICT, LENIENT
  "transaction_mode": "ALL_OR_NONE"  // ALL_OR_NONE, BEST_EFFORT
}
```

### Bulk Update Status
```http
PUT /api/v1/orders/bulk/status
```

**Request Body:**
```json
{
  "order_ids": ["O-20240125-000123", "O-20240125-000124"],
  "new_status": "03",
  "driver_id": "D001",
  "update_reason": "批次派送"
}
```

## 📤 Export Operations

### Export Orders
```http
GET /api/v1/orders/export
```

**Query Parameters:**
- `format` (required): csv, excel, pdf
- `date_from` (required): Start date
- `date_to` (required): End date
- `fields` (optional): Comma-separated field list
- `timezone` (default: Asia/Taipei): Timezone for dates

**Success Response:**
```json
{
  "success": true,
  "data": {
    "export_id": "EXP-20240125-001",
    "status": "PROCESSING",
    "estimated_time": 30,
    "download_url": null
  },
  "message": "匯出處理中，完成後將發送通知"
}
```

### Check Export Status
```http
GET /api/v1/orders/export/{export_id}
```

**Success Response (When Ready):**
```json
{
  "success": true,
  "data": {
    "export_id": "EXP-20240125-001",
    "status": "COMPLETED",
    "download_url": "https://api.luckygas.com.tw/downloads/EXP-20240125-001.csv",
    "expires_at": "2024-01-26T14:30:00Z",
    "file_size": 125000,
    "row_count": 1523
  }
}
```

## 🔔 Webhooks

### Order Status Changed
```http
POST {webhook_url}
```

**Webhook Payload:**
```json
{
  "event": "order.status_changed",
  "timestamp": "2024-01-25T14:30:00Z",
  "data": {
    "order_id": "O-20240125-000123",
    "old_status": "02",
    "new_status": "03",
    "changed_by": "SYSTEM"
  },
  "signature": "sha256=..."
}
```

### Available Webhook Events
- `order.created`
- `order.confirmed`
- `order.dispatched`
- `order.delivered`
- `order.cancelled`
- `order.modified`
- `order.payment_received`

## 🚫 Error Handling

### Error Response Format
```json
{
  "success": false,
  "error": {
    "code": "ERROR_CODE",
    "message": "Human readable message in zh-TW",
    "details": {},
    "request_id": "req_12345",
    "documentation_url": "https://docs.luckygas.com.tw/errors/ERROR_CODE"
  }
}
```

### Common Error Codes
| Code | HTTP Status | Description |
|------|-------------|-------------|
| `INVALID_REQUEST` | 400 | Request validation failed |
| `INSUFFICIENT_CREDIT` | 400 | Credit limit exceeded |
| `PRODUCT_UNAVAILABLE` | 400 | Product out of stock |
| `ORDER_NOT_FOUND` | 404 | Order ID doesn't exist |
| `ORDER_NOT_MODIFIABLE` | 409 | Order status prevents changes |
| `DELIVERY_SLOT_FULL` | 409 | No capacity for time slot |
| `UNAUTHORIZED` | 401 | Invalid or missing auth |
| `FORBIDDEN` | 403 | Insufficient permissions |
| `RATE_LIMITED` | 429 | Too many requests |
| `SERVER_ERROR` | 500 | Internal server error |

## 🔐 Security Considerations

### Rate Limiting
- **Default**: 1000 requests per hour per API key
- **Bulk Operations**: 100 requests per hour
- **Reports**: 50 requests per hour

### Data Privacy
- Customer phone numbers partially masked in responses
- Payment details never included in full
- Audit logs for all data access
- GDPR/PDPA compliant data handling

### API Versioning
- Version specified in header: `X-API-Version: 1.0`
- Deprecated endpoints return warning headers
- Breaking changes require version increment
- 6-month deprecation notice period

---

**Note**: This API is designed for internal and partner integrations. Public API access requires additional authentication and has restricted endpoints.