# Customer Management API Endpoints

## 📡 Current System Pattern (ASP.NET WebForms)

The legacy system uses PostBack patterns with ViewState. Here's how to translate these into modern REST APIs:

### Legacy PostBack Pattern
```javascript
// Current system
__doPostBack('btnSave', '');
// Sends entire ViewState + form data to server
// Response: Full page HTML
```

### Modern API Translation
```javascript
// New system
POST /api/v1/customers
Content-Type: application/json
// Sends only necessary data
// Response: JSON with created resource
```

## 🔄 API Endpoint Specifications

### 1. Customer Search & Retrieval

#### Quick Search by Phone
```http
GET /api/v1/customers/search/quick?phone={phone_number}
```

**Request Parameters:**
```yaml
phone:
  type: string
  required: true
  format: "09XX-XXX-XXX or 0X-XXXX-XXXX"
  example: "0912-345-678"
```

**Response:**
```json
{
  "success": true,
  "data": {
    "customerId": "C000123",
    "customerName": "王小明瓦斯行",
    "phone": "0912-345-678",
    "address": "台北市中正區重慶南路一段122號",
    "creditLimit": 50000,
    "outstandingBalance": 12500,
    "status": "01"
  },
  "message": "查詢成功"
}
```

#### Advanced Search
```http
POST /api/v1/customers/search/advanced
```

**Request Body:**
```json
{
  "customerName": "王",
  "taxId": "",
  "city": "台北市",
  "district": "中正區",
  "customerType": ["01", "03"],
  "status": ["01"],
  "creditLimitMin": 10000,
  "creditLimitMax": 100000,
  "page": 1,
  "pageSize": 20
}
```

**Response:**
```json
{
  "success": true,
  "data": {
    "items": [
      {
        "customerId": "C000123",
        "customerName": "王小明瓦斯行",
        "customerType": "01",
        "phone": "0912-345-678",
        "city": "台北市",
        "district": "中正區",
        "creditLimit": 50000,
        "outstandingBalance": 12500
      }
    ],
    "totalCount": 45,
    "page": 1,
    "pageSize": 20,
    "totalPages": 3
  },
  "message": "找到 45 筆資料"
}
```

#### Get Customer by ID
```http
GET /api/v1/customers/{customerId}
```

**Response:**
```json
{
  "success": true,
  "data": {
    "basic": {
      "customerId": "C000123",
      "taxId": "12345678",
      "customerName": "王小明瓦斯行",
      "shortName": "王小明",
      "englishName": "Wang's Gas Store",
      "customerType": "01",
      "businessType": "4721"
    },
    "contact": {
      "contactPerson": "王小明",
      "contactTitle": "負責人",
      "phonePrimary": "02-2345-6789",
      "phoneSecondary": "",
      "mobile": "0912-345-678",
      "fax": "02-2345-6788",
      "email": "wang@example.com",
      "lineId": "wanggas"
    },
    "address": {
      "registration": {
        "postalCode": "10041",
        "city": "台北市",
        "district": "中正區",
        "address": "重慶南路一段122號"
      },
      "delivery": {
        "sameAsRegistration": false,
        "postalCode": "10042",
        "address": "台北市中正區愛國東路100號",
        "zone": "A01",
        "sequence": 15,
        "timePreference": "02",
        "instructions": "請按3樓電鈴"
      }
    },
    "financial": {
      "paymentTerms": "MON30",
      "creditLimit": 50000,
      "depositAmount": 3000,
      "priceLevel": "02",
      "taxType": "01",
      "invoiceType": "03",
      "invoiceDelivery": "03"
    },
    "status": {
      "status": "01",
      "firstTransDate": "2020-01-15",
      "lastTransDate": "2024-01-20",
      "totalAmount": 850000,
      "cylinderCount": 2,
      "outstandingBalance": 12500
    },
    "audit": {
      "createUser": "ADMIN",
      "createDate": "2020-01-15T10:30:00",
      "updateUser": "STAFF01",
      "updateDate": "2024-01-20T14:22:00"
    }
  },
  "message": "查詢成功"
}
```

### 2. Customer Creation

#### Create New Customer
```http
POST /api/v1/customers
```

**Request Body:**
```json
{
  "basic": {
    "taxId": "12345678",
    "customerName": "新客戶瓦斯行",
    "shortName": "新客戶",
    "customerType": "01",
    "businessType": "4721"
  },
  "contact": {
    "contactPerson": "陳大明",
    "contactTitle": "負責人",
    "phonePrimary": "02-8888-9999",
    "mobile": "0933-222-111",
    "email": "new@example.com"
  },
  "address": {
    "registration": {
      "postalCode": "10643",
      "city": "台北市",
      "district": "大安區",
      "address": "信義路四段1號"
    },
    "delivery": {
      "sameAsRegistration": true
    }
  },
  "financial": {
    "paymentTerms": "CASH",
    "creditLimit": 10000,
    "priceLevel": "01",
    "taxType": "01",
    "invoiceType": "03",
    "invoiceDelivery": "01"
  },
  "product": {
    "primaryProduct": "20KG",
    "avgMonthlyQty": 10,
    "safetyStock": 2
  }
}
```

**Response:**
```json
{
  "success": true,
  "data": {
    "customerId": "C000456",
    "customerName": "新客戶瓦斯行",
    "message": "客戶資料已建立"
  },
  "message": "新增成功"
}
```

**Validation Errors Response:**
```json
{
  "success": false,
  "errors": [
    {
      "field": "taxId",
      "message": "統一編號已存在"
    },
    {
      "field": "creditLimit",
      "message": "信用額度超過新客戶上限，需要主管核准"
    }
  ],
  "message": "資料驗證失敗"
}
```

### 3. Customer Updates

#### Update Customer Information
```http
PUT /api/v1/customers/{customerId}
```

**Request Body:** (Partial update supported)
```json
{
  "contact": {
    "mobile": "0933-444-555",
    "email": "updated@example.com"
  },
  "financial": {
    "creditLimit": 80000,
    "creditLimitApproval": {
      "approver": "MGR001",
      "approvalCode": "AP2024012001",
      "reason": "良好付款記錄"
    }
  }
}
```

**Response:**
```json
{
  "success": true,
  "data": {
    "customerId": "C000123",
    "updatedFields": ["mobile", "email", "creditLimit"],
    "version": 5
  },
  "message": "更新成功"
}
```

#### Update Customer Status
```http
PATCH /api/v1/customers/{customerId}/status
```

**Request Body:**
```json
{
  "status": "02",
  "reason": "長期未交易",
  "effectiveDate": "2024-02-01"
}
```

### 4. Customer Deletion

#### Soft Delete Customer
```http
DELETE /api/v1/customers/{customerId}
```

**Request Body:**
```json
{
  "reason": "客戶要求停止服務",
  "checksPassed": {
    "noActiveOrders": true,
    "noOutstandingBalance": true,
    "noCylindersOnLoan": true
  }
}
```

**Response:**
```json
{
  "success": true,
  "data": {
    "customerId": "C000123",
    "status": "02",
    "deleteFlag": "Y"
  },
  "message": "客戶已停用"
}
```

### 5. Customer Validation

#### Validate Tax ID
```http
POST /api/v1/customers/validate/tax-id
```

**Request Body:**
```json
{
  "taxId": "12345678"
}
```

**Response:**
```json
{
  "success": true,
  "data": {
    "valid": true,
    "exists": false,
    "format": "valid"
  }
}
```

#### Check Credit Availability
```http
GET /api/v1/customers/{customerId}/credit/available
```

**Response:**
```json
{
  "success": true,
  "data": {
    "creditLimit": 50000,
    "outstandingBalance": 12500,
    "pendingOrders": 5000,
    "availableCredit": 32500,
    "creditHold": false
  }
}
```

### 6. Bulk Operations

#### Import Customers
```http
POST /api/v1/customers/import
```

**Request:** (Multipart form data)
```yaml
file: customers.xlsx
options:
  validateOnly: false
  updateExisting: true
  skipDuplicates: false
```

**Response:**
```json
{
  "success": true,
  "data": {
    "processed": 100,
    "created": 85,
    "updated": 10,
    "skipped": 5,
    "errors": [
      {
        "row": 23,
        "customerId": "",
        "error": "統一編號格式錯誤"
      }
    ]
  },
  "message": "匯入完成"
}
```

#### Export Customers
```http
POST /api/v1/customers/export
```

**Request Body:**
```json
{
  "format": "xlsx",
  "filters": {
    "status": ["01"],
    "customerType": ["01", "03"]
  },
  "fields": [
    "customerId",
    "customerName",
    "taxId",
    "phone",
    "address",
    "creditLimit",
    "outstandingBalance"
  ]
}
```

**Response:**
```json
{
  "success": true,
  "data": {
    "downloadUrl": "/api/v1/downloads/customers_20240125_143022.xlsx",
    "expiresAt": "2024-01-25T15:30:22Z",
    "recordCount": 1523
  }
}
```

### 7. Related Data

#### Get Customer Addresses
```http
GET /api/v1/customers/{customerId}/addresses
```

**Response:**
```json
{
  "success": true,
  "data": [
    {
      "addressId": 1,
      "addressType": "01",
      "addressName": "總公司",
      "postalCode": "10041",
      "fullAddress": "台北市中正區重慶南路一段122號",
      "isDefault": true,
      "active": true
    },
    {
      "addressId": 2,
      "addressType": "01",
      "addressName": "分店",
      "postalCode": "10642",
      "fullAddress": "台北市大安區敦化南路二段100號",
      "isDefault": false,
      "active": true
    }
  ]
}
```

#### Get Customer Contacts
```http
GET /api/v1/customers/{customerId}/contacts
```

### 8. Reporting Endpoints

#### Customer List Report
```http
POST /api/v1/customers/reports/list
```

**Request Body:**
```json
{
  "filters": {
    "zone": ["A01", "A02"],
    "customerType": ["01"],
    "status": ["01"]
  },
  "sortBy": "customerName",
  "sortOrder": "asc",
  "format": "pdf"
}
```

#### Customer Transaction History
```http
GET /api/v1/customers/{customerId}/transactions?startDate={date}&endDate={date}
```

#### Customer Statistics
```http
POST /api/v1/customers/reports/statistics
```

**Request Body:**
```json
{
  "period": "2024-01",
  "groupBy": "customerType",
  "metrics": ["count", "totalRevenue", "avgOrderValue"]
}
```

## 🔐 Authentication & Authorization

### Headers Required
```http
Authorization: Bearer {jwt_token}
X-User-Role: STAFF
X-Request-ID: {uuid}
Accept-Language: zh-TW
```

### Permission Matrix

| Endpoint | Admin | Manager | Staff | Driver |
|----------|-------|---------|-------|---------|
| GET /customers/search | ✅ | ✅ | ✅ | Limited |
| GET /customers/{id} | ✅ | ✅ | ✅ | ❌ |
| POST /customers | ✅ | ✅ | ✅ | ❌ |
| PUT /customers/{id} | ✅ | ✅ | ✅ | ❌ |
| DELETE /customers/{id} | ✅ | ✅ | ❌ | ❌ |
| POST /customers/import | ✅ | ✅ | ❌ | ❌ |
| */reports/* | ✅ | ✅ | Limited | ❌ |

## 🚨 Error Responses

### Standard Error Format
```json
{
  "success": false,
  "error": {
    "code": "CUSTOMER_NOT_FOUND",
    "message": "客戶資料不存在",
    "field": null,
    "details": {}
  },
  "timestamp": "2024-01-25T14:30:00Z",
  "requestId": "550e8400-e29b-41d4-a716-446655440000"
}
```

### Common Error Codes

| Code | HTTP Status | Description |
|------|-------------|-------------|
| CUSTOMER_NOT_FOUND | 404 | Customer ID not found |
| DUPLICATE_TAX_ID | 409 | Tax ID already exists |
| INVALID_TAX_ID | 400 | Tax ID format invalid |
| CREDIT_LIMIT_EXCEEDED | 400 | Order exceeds available credit |
| APPROVAL_REQUIRED | 403 | Manager approval needed |
| CUSTOMER_ON_HOLD | 403 | Customer account suspended |
| INVALID_PHONE_FORMAT | 400 | Phone number format invalid |
| OUT_OF_SERVICE_AREA | 400 | Address not in service area |

## 📊 Performance Considerations

### Response Time Targets
- Search operations: < 200ms
- Single record retrieval: < 100ms
- Create/Update operations: < 500ms
- Report generation: < 5s
- Bulk import: < 100ms per record

### Pagination
- Default page size: 20
- Maximum page size: 100
- Always return total count for UI pagination

### Caching Strategy
- Customer basic data: 5 minutes
- Credit availability: No cache (real-time)
- Reports: 1 hour for identical parameters

---

This API specification provides a RESTful translation of the current ASP.NET WebForms functionality, ready for implementation in the new system.