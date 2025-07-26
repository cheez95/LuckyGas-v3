# Data Maintenance API Endpoints - Lucky Gas Legacy System

## 🎯 API Overview

The Data Maintenance module provides RESTful APIs for managing master data including products, employees, system parameters, and configurations. All endpoints follow consistent patterns with comprehensive validation and error handling.

### Base URL
```
https://api.luckygas.com.tw/api/v1/maintenance
```

### Common Headers
```http
Authorization: Bearer {jwt_token}
Content-Type: application/json
Accept-Language: zh-TW
X-Request-ID: {uuid}
```

### Standard Response Format
```json
{
  "success": true,
  "data": {},
  "message": "操作成功",
  "timestamp": "2024-01-25T10:30:00+08:00",
  "request_id": "550e8400-e29b-41d4-a716-446655440000"
}
```

### Error Response Format
```json
{
  "success": false,
  "error": {
    "code": "PROD-001",
    "message": "產品代碼已存在",
    "field": "product_code",
    "details": {}
  },
  "timestamp": "2024-01-25T10:30:00+08:00",
  "request_id": "550e8400-e29b-41d4-a716-446655440000"
}
```

---

## 📦 Product Management Endpoints

### Product CRUD Operations

#### **GET /products**
Retrieve products with filtering and pagination
```http
GET /api/v1/maintenance/products?category=01&active=true&page=1&limit=20
```

**Query Parameters:**
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| category | string | No | Product category (01-04) |
| active | boolean | No | Active status filter |
| search | string | No | Search in code/name |
| page | integer | No | Page number (default: 1) |
| limit | integer | No | Records per page (default: 20) |
| sort | string | No | Sort field (default: product_code) |
| order | string | No | Sort order (asc/desc) |

**Response:**
```json
{
  "success": true,
  "data": {
    "products": [
      {
        "product_id": "P001",
        "product_code": "GAS-20KG-STD",
        "product_name": "20公斤瓦斯桶",
        "category": "01",
        "standard_price": 850.00,
        "active_flag": true
      }
    ],
    "pagination": {
      "current_page": 1,
      "total_pages": 5,
      "total_records": 98,
      "records_per_page": 20
    }
  }
}
```

#### **GET /products/{product_id}**
Get detailed product information
```http
GET /api/v1/maintenance/products/P001
```

**Response:**
```json
{
  "success": true,
  "data": {
    "product": {
      "product_id": "P001",
      "product_code": "GAS-20KG-STD",
      "product_name": "20公斤瓦斯桶",
      "product_name_en": "20kg Gas Cylinder",
      "category": "01",
      "size": "20KG",
      "standard_price": 850.00,
      "min_price": 765.00,
      "requires_deposit": true,
      "deposit_amount": 1500.00,
      "inventory_settings": {
        "track_inventory": true,
        "safety_stock": 50,
        "reorder_point": 100
      },
      "active_flag": true,
      "created_date": "2020-01-15T08:00:00+08:00"
    }
  }
}
```

#### **POST /products**
Create new product
```http
POST /api/v1/maintenance/products
```

**Request Body:**
```json
{
  "product_code": "GAS-50KG-IND",
  "product_name": "50公斤工業用瓦斯桶",
  "category": "01",
  "size": "50KG",
  "standard_price": 1680.00,
  "cost_price": 1400.00,
  "requires_deposit": true,
  "deposit_amount": 2000.00,
  "track_inventory": true,
  "safety_stock_level": 30,
  "reorder_point": 60
}
```

#### **PUT /products/{product_id}**
Update existing product
```http
PUT /api/v1/maintenance/products/P001
```

**Request Body:**
```json
{
  "product_name": "20公斤家用瓦斯桶",
  "standard_price": 880.00,
  "safety_stock_level": 60
}
```

#### **DELETE /products/{product_id}**
Discontinue product (soft delete)
```http
DELETE /api/v1/maintenance/products/P001
```

**Request Body:**
```json
{
  "discontinue_date": "2024-02-28",
  "reason": "產品升級",
  "notify_customers": true
}
```

### Product Pricing Endpoints

#### **GET /products/{product_id}/pricing**
Get all pricing tiers for a product
```http
GET /api/v1/maintenance/products/P001/pricing
```

#### **POST /products/{product_id}/pricing**
Create new pricing tier
```http
POST /api/v1/maintenance/products/P001/pricing
```

**Request Body:**
```json
{
  "price_type": "03",
  "customer_category": "03",
  "min_quantity": 10,
  "unit_price": 800.00,
  "effective_from": "2024-02-01",
  "effective_to": "2024-03-31",
  "requires_approval": true
}
```

#### **PUT /products/{product_id}/pricing/{pricing_id}**
Update pricing tier
```http
PUT /api/v1/maintenance/products/P001/pricing/123
```

#### **POST /products/{product_id}/pricing/{pricing_id}/approve**
Approve pending price change
```http
POST /api/v1/maintenance/products/P001/pricing/123/approve
```

**Request Body:**
```json
{
  "approval_notes": "核准春節促銷價格"
}
```

### Product Inventory Endpoints

#### **GET /products/{product_id}/inventory**
Get current inventory status
```http
GET /api/v1/maintenance/products/P001/inventory
```

#### **PUT /products/{product_id}/inventory**
Update inventory parameters
```http
PUT /api/v1/maintenance/products/P001/inventory
```

**Request Body:**
```json
{
  "safety_stock_level": 75,
  "reorder_point": 150,
  "reorder_quantity": 300
}
```

---

## 👥 Employee Management Endpoints

### Employee CRUD Operations

#### **GET /employees**
List employees with filters
```http
GET /api/v1/maintenance/employees?type=01&department=01&active=true&page=1&limit=50
```

**Query Parameters:**
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| type | string | No | Employee type (01-06) |
| department | string | No | Department code |
| active | boolean | No | Employment status |
| search | string | No | Search name/code |
| page | integer | No | Page number |
| limit | integer | No | Records per page |

#### **GET /employees/{employee_id}**
Get employee details
```http
GET /api/v1/maintenance/employees/E000123
```

**Response:**
```json
{
  "success": true,
  "data": {
    "employee": {
      "employee_id": "E000123",
      "employee_code": "DRV001",
      "employee_name": "李大明",
      "employee_type": "01",
      "department": "01",
      "position": "資深司機",
      "hire_date": "2018-03-15",
      "employment_status": "01",
      "contact": {
        "phone_mobile": "0912-345-678",
        "email": "lee.dm@luckygas.com.tw",
        "address": "台北市大安區..."
      },
      "driver_details": {
        "license_number": "ABC123456",
        "license_expiry": "2025-06-30",
        "vehicle_id": "V001",
        "delivery_zones": ["NORTH", "CENTRAL"]
      }
    }
  }
}
```

#### **POST /employees**
Create new employee
```http
POST /api/v1/maintenance/employees
```

**Request Body:**
```json
{
  "national_id": "A123456789",
  "employee_name": "王小華",
  "employee_type": "02",
  "department": "02",
  "position": "業務專員",
  "hire_date": "2024-02-01",
  "phone_mobile": "0923-456-789",
  "address": "台北市信義區...",
  "emergency_contact": "王大華",
  "emergency_phone": "0934-567-890",
  "bank_code": "012",
  "bank_account": "123456789012",
  "base_salary": 35000
}
```

#### **PUT /employees/{employee_id}**
Update employee information
```http
PUT /api/v1/maintenance/employees/E000123
```

#### **POST /employees/{employee_id}/terminate**
Process employee termination
```http
POST /api/v1/maintenance/employees/E000123/terminate
```

**Request Body:**
```json
{
  "termination_date": "2024-02-28",
  "termination_type": "02",
  "reason": "個人因素",
  "exit_interview_completed": true,
  "assets_returned": true
}
```

### Driver-Specific Endpoints

#### **GET /employees/drivers**
List all active drivers
```http
GET /api/v1/maintenance/employees/drivers
```

#### **PUT /employees/{employee_id}/driver-details**
Update driver information
```http
PUT /api/v1/maintenance/employees/E000123/driver-details
```

**Request Body:**
```json
{
  "license_number": "XYZ789012",
  "license_expiry": "2026-12-31",
  "medical_check_date": "2024-01-20",
  "medical_check_result": "01",
  "delivery_zones": ["NORTH", "EAST"],
  "max_cylinders": 25
}
```

#### **POST /employees/{employee_id}/driver-details/validate-license**
Validate driver license
```http
POST /api/v1/maintenance/employees/E000123/driver-details/validate-license
```

### Employee Role Management

#### **GET /employees/{employee_id}/roles**
Get employee roles
```http
GET /api/v1/maintenance/employees/E000123/roles
```

#### **POST /employees/{employee_id}/roles**
Assign new role
```http
POST /api/v1/maintenance/employees/E000123/roles
```

**Request Body:**
```json
{
  "role_code": "SUPERVISOR",
  "module_code": "W100",
  "permissions": ["CREATE", "READ", "UPDATE"],
  "valid_from": "2024-02-01",
  "valid_to": "2024-12-31"
}
```

#### **DELETE /employees/{employee_id}/roles/{role_id}**
Revoke role
```http
DELETE /api/v1/maintenance/employees/E000123/roles/456
```

---

## ⚙️ System Parameter Endpoints

### Parameter Management

#### **GET /parameters**
List system parameters
```http
GET /api/v1/maintenance/parameters?category=01&module=W100
```

#### **GET /parameters/{parameter_code}**
Get parameter details
```http
GET /api/v1/maintenance/parameters/ORDER.VALIDATION.MIN_AMOUNT
```

#### **PUT /parameters/{parameter_code}**
Update parameter value
```http
PUT /api/v1/maintenance/parameters/ORDER.VALIDATION.MIN_AMOUNT
```

**Request Body:**
```json
{
  "parameter_value": "1000",
  "effective_date": "2024-02-01T00:00:00+08:00",
  "change_reason": "調整最低訂單金額",
  "requires_restart": false
}
```

#### **POST /parameters/{parameter_code}/approve**
Approve parameter change
```http
POST /api/v1/maintenance/parameters/ORDER.VALIDATION.MIN_AMOUNT/approve
```

---

## 🌏 Zone Configuration Endpoints

### Zone Management

#### **GET /zones**
List delivery zones
```http
GET /api/v1/maintenance/zones?city=台北市&type=01&active=true
```

#### **GET /zones/{zone_id}**
Get zone details
```http
GET /api/v1/maintenance/zones/ZONE_N01
```

#### **POST /zones**
Create new zone
```http
POST /api/v1/maintenance/zones
```

**Request Body:**
```json
{
  "zone_code": "TAIPEI_SOUTH",
  "zone_name": "台北市南區",
  "zone_type": "01",
  "city": "台北市",
  "districts": ["大安區", "文山區", "信義區"],
  "postal_codes": ["106", "116", "110"],
  "base_delivery_fee": 50.00,
  "rush_delivery_fee": 100.00,
  "min_order_amount": 800.00,
  "service_days": "1,2,3,4,5,6",
  "service_start_time": "08:00",
  "service_end_time": "20:00"
}
```

#### **PUT /zones/{zone_id}**
Update zone configuration
```http
PUT /api/v1/maintenance/zones/ZONE_N01
```

#### **POST /zones/validate-coverage**
Validate zone coverage
```http
POST /api/v1/maintenance/zones/validate-coverage
```

**Request Body:**
```json
{
  "postal_codes": ["100", "103", "104", "105"]
}
```

---

## 💳 Payment Terms Endpoints

### Payment Terms Management

#### **GET /payment-terms**
List payment terms
```http
GET /api/v1/maintenance/payment-terms
```

#### **GET /payment-terms/{term_id}**
Get payment term details
```http
GET /api/v1/maintenance/payment-terms/TERM_30
```

#### **POST /payment-terms**
Create payment terms
```http
POST /api/v1/maintenance/payment-terms
```

**Request Body:**
```json
{
  "term_code": "NET45",
  "term_name": "月結45天",
  "payment_days": 45,
  "discount_days": 10,
  "discount_percent": 1.5,
  "late_charge_percent": 1.5,
  "grace_days": 7,
  "credit_limit_default": 50000.00,
  "customer_types": ["02", "03"]
}
```

---

## 📅 Holiday Calendar Endpoints

### Holiday Management

#### **GET /holidays**
List holidays
```http
GET /api/v1/maintenance/holidays?year=2024&type=01
```

#### **POST /holidays**
Add holiday
```http
POST /api/v1/maintenance/holidays
```

**Request Body:**
```json
{
  "holiday_date": "2024-02-10",
  "holiday_name": "春節初一",
  "holiday_type": "01",
  "is_working_day": false,
  "surcharge_percent": 50.0
}
```

#### **POST /holidays/import**
Import government calendar
```http
POST /api/v1/maintenance/holidays/import
```

**Request Body:**
```json
{
  "year": 2024,
  "source": "government",
  "merge_strategy": "add_missing"
}
```

---

## 🧾 Tax Configuration Endpoints

### Tax Management

#### **GET /tax-configurations**
List tax configurations
```http
GET /api/v1/maintenance/tax-configurations
```

#### **PUT /tax-configurations/{tax_code}**
Update tax rate
```http
PUT /api/v1/maintenance/tax-configurations/VAT_5
```

**Request Body:**
```json
{
  "tax_rate": 5.0,
  "effective_from": "2024-03-01",
  "approval_required": true
}
```

---

## 📥📤 Import/Export Endpoints

### Data Import

#### **POST /import/validate**
Validate import file
```http
POST /api/v1/maintenance/import/validate
```

**Request Body (multipart/form-data):**
```
file: [binary]
entity_type: products
update_strategy: skip_duplicates
```

#### **POST /import/execute**
Execute import
```http
POST /api/v1/maintenance/import/execute
```

**Request Body:**
```json
{
  "validation_token": "abc123...",
  "confirm_import": true,
  "send_notifications": true
}
```

#### **GET /import/history**
Import history
```http
GET /api/v1/maintenance/import/history?entity_type=products&days=30
```

### Data Export

#### **POST /export/products**
Export products
```http
POST /api/v1/maintenance/export/products
```

**Request Body:**
```json
{
  "format": "excel",
  "filters": {
    "category": ["01", "02"],
    "active": true
  },
  "fields": ["product_code", "product_name", "standard_price"],
  "include_headers": true,
  "compress": true
}
```

#### **GET /export/download/{export_id}**
Download export file
```http
GET /api/v1/maintenance/export/download/xyz789
```

---

## 🔄 Batch Operations

### Bulk Updates

#### **POST /batch/products/update-prices**
Bulk price update
```http
POST /api/v1/maintenance/batch/products/update-prices
```

**Request Body:**
```json
{
  "update_type": "percentage",
  "percentage": 5.0,
  "category": "01",
  "effective_date": "2024-03-01",
  "round_to": 10,
  "approval_required": true
}
```

#### **POST /batch/employees/update-departments**
Bulk department transfer
```http
POST /api/v1/maintenance/batch/employees/update-departments
```

**Request Body:**
```json
{
  "employee_ids": ["E000123", "E000124", "E000125"],
  "new_department": "02",
  "effective_date": "2024-02-01",
  "update_roles": true
}
```

---

## 🔍 Search and Lookup Endpoints

#### **GET /search/products**
Global product search
```http
GET /api/v1/maintenance/search/products?q=20公斤&include_inactive=false
```

#### **GET /lookup/reference-data**
Get reference data
```http
GET /api/v1/maintenance/lookup/reference-data?category=CUSTOMER_TYPE
```

#### **GET /lookup/postal-codes**
Postal code lookup
```http
GET /api/v1/maintenance/lookup/postal-codes?city=台北市
```

---

## 📊 Reporting Endpoints

#### **GET /reports/data-quality**
Data quality report
```http
GET /api/v1/maintenance/reports/data-quality?entity=products&date=2024-01-25
```

#### **GET /reports/change-log**
Change log report
```http
GET /api/v1/maintenance/reports/change-log?entity=employees&from=2024-01-01&to=2024-01-31
```

---

## 🔐 Security Headers

All endpoints require authentication and include security headers:

```http
X-Content-Type-Options: nosniff
X-Frame-Options: DENY
X-XSS-Protection: 1; mode=block
Strict-Transport-Security: max-age=31536000; includeSubDomains
Content-Security-Policy: default-src 'self'
```

## 📝 Rate Limiting

API rate limits per endpoint category:

| Category | Rate Limit | Window |
|----------|------------|---------|
| Read Operations | 1000/hour | Sliding |
| Write Operations | 100/hour | Sliding |
| Bulk Operations | 10/hour | Fixed |
| Import/Export | 5/hour | Fixed |

## 🚨 Common Error Codes

| Code | Description | HTTP Status |
|------|-------------|-------------|
| PROD-001 | Product code already exists | 409 |
| PROD-002 | Invalid price below minimum | 400 |
| EMP-001 | Invalid national ID format | 400 |
| EMP-002 | Employee not found | 404 |
| SYS-001 | Parameter update requires approval | 403 |
| ZONE-001 | Zone overlap detected | 409 |
| IMP-001 | Import validation failed | 400 |
| AUTH-001 | Unauthorized access | 401 |
| RATE-001 | Rate limit exceeded | 429 |

## 🔄 Webhook Events

The system can send webhooks for critical events:

```json
{
  "event": "product.price.changed",
  "timestamp": "2024-01-25T10:30:00+08:00",
  "data": {
    "product_id": "P001",
    "old_price": 850.00,
    "new_price": 880.00,
    "effective_date": "2024-02-01"
  }
}
```

Available webhook events:
- `product.created`
- `product.price.changed`
- `product.discontinued`
- `employee.onboarded`
- `employee.terminated`
- `parameter.updated`
- `zone.modified`
- `import.completed`