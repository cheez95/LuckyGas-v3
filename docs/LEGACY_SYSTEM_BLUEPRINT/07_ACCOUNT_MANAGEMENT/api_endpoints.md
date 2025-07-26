# Account Management API Endpoints - Lucky Gas Legacy System

## 🌐 API Overview

The Account Management module exposes RESTful APIs for managing customer accounts, payments, credit limits, collections, and financial reporting. All endpoints follow consistent patterns for authentication, request/response formats, and error handling.

## 🔑 Authentication & Security

### Authentication Method
```yaml
Type: Bearer Token (JWT)
Header: Authorization: Bearer {token}
Expiry: 8 hours
Refresh: /api/auth/refresh endpoint

Permissions:
  - account.view: Read access to accounts
  - account.manage: Create/update accounts
  - payment.process: Process payments
  - credit.approve: Approve credit changes
  - collection.manage: Collection activities
```

### Rate Limiting
```yaml
Default Limits:
  - 100 requests per minute per user
  - 1000 requests per hour per user
  - Burst: 20 requests per second
  
Headers:
  X-RateLimit-Limit: 100
  X-RateLimit-Remaining: 95
  X-RateLimit-Reset: 1640995200
```

## 💳 Customer Account APIs

### Get Customer Account
```http
GET /api/v1/accounts/{customerId}
```

**Parameters:**
- `customerId` (path): Customer ID

**Response:**
```json
{
  "customerId": "C001234",
  "companyName": "台灣優質企業股份有限公司",
  "taxId": "12345678",
  "creditLimit": 500000,
  "currentBalance": 125000,
  "availableCredit": 375000,
  "creditStatus": "ACTIVE",
  "paymentTerms": "NET30",
  "riskCategory": "B",
  "lastPaymentDate": "2024-01-15",
  "accountStatus": "ACTIVE",
  "aging": {
    "current": 50000,
    "days1_30": 45000,
    "days31_60": 20000,
    "days61_90": 10000,
    "over90": 0
  }
}
```

### List Customer Accounts
```http
GET /api/v1/accounts
```

**Query Parameters:**
- `page` (int): Page number (default: 1)
- `size` (int): Page size (default: 20, max: 100)
- `status`: ACTIVE | INACTIVE | HOLD | CLOSED
- `creditStatus`: GOOD | WARNING | HOLD | SUSPENDED
- `search`: Search by name or tax ID
- `sortBy`: balance | creditLimit | name
- `sortOrder`: asc | desc

**Response:**
```json
{
  "data": [...],
  "pagination": {
    "page": 1,
    "size": 20,
    "total": 150,
    "totalPages": 8
  }
}
```

### Update Credit Limit
```http
PUT /api/v1/accounts/{customerId}/credit-limit
```

**Request Body:**
```json
{
  "newLimit": 800000,
  "effectiveDate": "2024-02-01",
  "reason": "Business expansion",
  "approvedBy": "MGR001",
  "reviewDate": "2024-07-01"
}
```

**Response:**
```json
{
  "success": true,
  "previousLimit": 500000,
  "newLimit": 800000,
  "approvalId": "APR-2024-0123"
}
```

### Get Account Statement
```http
GET /api/v1/accounts/{customerId}/statement
```

**Query Parameters:**
- `fromDate`: Start date (YYYY-MM-DD)
- `toDate`: End date (YYYY-MM-DD)
- `format`: pdf | excel | json
- `includeDetails`: true | false

**Response:**
```json
{
  "customerId": "C001234",
  "statementPeriod": {
    "from": "2024-01-01",
    "to": "2024-01-31"
  },
  "openingBalance": 150000,
  "transactions": [
    {
      "date": "2024-01-05",
      "type": "INVOICE",
      "reference": "INV-2024-0001",
      "debit": 25000,
      "credit": 0,
      "balance": 175000
    },
    {
      "date": "2024-01-15",
      "type": "PAYMENT",
      "reference": "PAY-2024-0050",
      "debit": 0,
      "credit": 50000,
      "balance": 125000
    }
  ],
  "closingBalance": 125000
}
```

## 💰 Payment Processing APIs

### Record Payment
```http
POST /api/v1/payments
```

**Request Body:**
```json
{
  "customerId": "C001234",
  "amount": 50000,
  "paymentDate": "2024-01-20",
  "paymentMethod": "BANK_TRANSFER",
  "reference": "TRF-123456789",
  "bankAccount": "004-1234567890",
  "allocationType": "AUTO",
  "notes": "January payment"
}
```

**Response:**
```json
{
  "paymentId": "PAY-2024-0123",
  "status": "RECORDED",
  "allocations": [
    {
      "invoiceId": "INV-2023-1234",
      "amount": 30000,
      "discount": 600
    },
    {
      "invoiceId": "INV-2023-1235",
      "amount": 19400,
      "discount": 0
    }
  ],
  "unallocated": 0,
  "receiptUrl": "/receipts/RCP-2024-0123.pdf"
}
```

### Payment Allocation
```http
POST /api/v1/payments/{paymentId}/allocate
```

**Request Body:**
```json
{
  "allocations": [
    {
      "invoiceId": "INV-2023-1234",
      "amount": 25000
    },
    {
      "invoiceId": "INV-2023-1235",
      "amount": 25000
    }
  ]
}
```

### Reverse Payment
```http
POST /api/v1/payments/{paymentId}/reverse
```

**Request Body:**
```json
{
  "reason": "NSF_CHECK",
  "reversalDate": "2024-01-21",
  "approvedBy": "SUP001",
  "notes": "Check bounced"
}
```

### Search Payments
```http
GET /api/v1/payments
```

**Query Parameters:**
- `customerId`: Filter by customer
- `fromDate`: Payment date from
- `toDate`: Payment date to
- `method`: CASH | CHECK | BANK_TRANSFER | CREDIT_CARD
- `status`: RECORDED | ALLOCATED | REVERSED | UNIDENTIFIED
- `minAmount`: Minimum amount
- `maxAmount`: Maximum amount

## 📋 Invoice Management APIs

### Create Invoice
```http
POST /api/v1/invoices
```

**Request Body:**
```json
{
  "customerId": "C001234",
  "invoiceDate": "2024-01-20",
  "dueDate": "2024-02-19",
  "items": [
    {
      "productCode": "GAS-20KG",
      "description": "20KG Gas Cylinder",
      "quantity": 10,
      "unitPrice": 800,
      "taxRate": 0.05
    }
  ],
  "deliveryId": "DEL-2024-0456",
  "notes": "Regular monthly delivery"
}
```

### Get Invoice
```http
GET /api/v1/invoices/{invoiceId}
```

**Response:**
```json
{
  "invoiceId": "INV-2024-0234",
  "invoiceNumber": "GA2024010234",
  "customerId": "C001234",
  "invoiceDate": "2024-01-20",
  "dueDate": "2024-02-19",
  "subtotal": 8000,
  "taxAmount": 400,
  "totalAmount": 8400,
  "paidAmount": 0,
  "balance": 8400,
  "status": "OPEN",
  "items": [...],
  "payments": []
}
```

### Create Credit Note
```http
POST /api/v1/credit-notes
```

**Request Body:**
```json
{
  "customerId": "C001234",
  "relatedInvoiceId": "INV-2024-0234",
  "creditDate": "2024-01-25",
  "reason": "PRODUCT_RETURN",
  "items": [
    {
      "productCode": "GAS-20KG",
      "quantity": 2,
      "unitPrice": 800,
      "taxRate": 0.05
    }
  ],
  "approvedBy": "MGR001"
}
```

## 🏦 Credit Management APIs

### Credit Application
```http
POST /api/v1/credit-applications
```

**Request Body:**
```json
{
  "customerId": "C001234",
  "requestedLimit": 1000000,
  "justification": "Business expansion",
  "financialData": {
    "annualRevenue": 50000000,
    "currentRatio": 1.8,
    "debtRatio": 0.4
  },
  "tradeReferences": [
    {
      "company": "供應商A",
      "contact": "張經理",
      "phone": "02-12345678"
    }
  ]
}
```

### Credit Decision
```http
PUT /api/v1/credit-applications/{applicationId}/decision
```

**Request Body:**
```json
{
  "decision": "APPROVED",
  "approvedLimit": 800000,
  "conditions": [
    "Personal guarantee required",
    "Quarterly financial updates"
  ],
  "effectiveDate": "2024-02-01",
  "reviewDate": "2024-08-01",
  "approvedBy": "DIR001"
}
```

### Credit Review
```http
GET /api/v1/credit-reviews/due
```

**Query Parameters:**
- `dueDate`: Reviews due by date
- `category`: A | B | C | D
- `reviewer`: Assigned reviewer ID

## 📞 Collection Management APIs

### Get Collection Queue
```http
GET /api/v1/collections/queue
```

**Query Parameters:**
- `collector`: Assigned collector ID
- `ageGroup`: 1_7 | 8_15 | 16_30 | 31_45 | 46_60 | OVER_60
- `priority`: HIGH | MEDIUM | LOW
- `status`: PENDING | IN_PROGRESS | PROMISED | ESCALATED

### Record Collection Activity
```http
POST /api/v1/collections/activities
```

**Request Body:**
```json
{
  "customerId": "C001234",
  "activityType": "PHONE_CALL",
  "contactPerson": "王經理",
  "outcome": "PROMISE_TO_PAY",
  "promiseDate": "2024-01-25",
  "promiseAmount": 50000,
  "notes": "Will pay after receiving payment from customer",
  "nextAction": "FOLLOW_UP",
  "nextActionDate": "2024-01-26"
}
```

### Create Payment Plan
```http
POST /api/v1/payment-plans
```

**Request Body:**
```json
{
  "customerId": "C001234",
  "totalAmount": 150000,
  "downPayment": 30000,
  "installments": 3,
  "startDate": "2024-02-01",
  "schedule": [
    {
      "dueDate": "2024-02-01",
      "amount": 30000
    },
    {
      "dueDate": "2024-03-01",
      "amount": 40000
    },
    {
      "dueDate": "2024-04-01",
      "amount": 50000
    }
  ]
}
```

## 📊 Reporting APIs

### Aging Report
```http
GET /api/v1/reports/aging
```

**Query Parameters:**
- `asOfDate`: Report date (default: today)
- `groupBy`: customer | salesperson | region
- `includeDisputed`: true | false
- `format`: json | pdf | excel

**Response:**
```json
{
  "reportDate": "2024-01-20",
  "summary": {
    "totalAR": 5000000,
    "current": 2500000,
    "overdue": 2500000
  },
  "aging": [
    {
      "bucket": "CURRENT",
      "amount": 2500000,
      "percentage": 50,
      "count": 120
    },
    {
      "bucket": "1_30_DAYS",
      "amount": 1000000,
      "percentage": 20,
      "count": 45
    }
  ],
  "details": [...]
}
```

### Cash Flow Forecast
```http
GET /api/v1/reports/cash-flow
```

**Query Parameters:**
- `fromDate`: Start date
- `toDate`: End date
- `interval`: daily | weekly | monthly

### DSO Report
```http
GET /api/v1/reports/dso
```

**Query Parameters:**
- `period`: MONTH | QUARTER | YEAR
- `compareWith`: PREVIOUS_PERIOD | PREVIOUS_YEAR

## 📅 Period Operations APIs

### Period Status
```http
GET /api/v1/periods/current
```

**Response:**
```json
{
  "period": "2024-01",
  "status": "OPEN",
  "startDate": "2024-01-01",
  "endDate": "2024-01-31",
  "closeDeadline": "2024-02-05"
}
```

### Execute Period Close
```http
POST /api/v1/periods/{period}/close
```

**Request Body:**
```json
{
  "cutoffDateTime": "2024-01-31T23:59:59",
  "includeAccruals": true,
  "runProvision": true,
  "approvedBy": "CFO001"
}
```

### Period Reopening
```http
POST /api/v1/periods/{period}/reopen
```

**Request Body:**
```json
{
  "reason": "Correction required",
  "authorizedBy": "CFO001",
  "expectedCloseDate": "2024-02-01"
}
```

## 🔄 Reconciliation APIs

### Bank Reconciliation
```http
POST /api/v1/reconciliation/bank
```

**Request Body:**
```json
{
  "bankAccount": "004-1234567890",
  "statementDate": "2024-01-31",
  "statementBalance": 2500000,
  "transactions": [
    {
      "date": "2024-01-15",
      "reference": "DEP123456",
      "amount": 100000,
      "type": "DEPOSIT"
    }
  ]
}
```

### Customer Reconciliation
```http
POST /api/v1/reconciliation/customer/{customerId}
```

**Request Body:**
```json
{
  "reconciliationDate": "2024-01-31",
  "customerBalance": 125000,
  "disputes": [
    {
      "invoiceId": "INV-2024-0123",
      "disputeAmount": 5000,
      "reason": "Quantity difference"
    }
  ]
}
```

## 🚨 Error Responses

### Standard Error Format
```json
{
  "error": {
    "code": "CREDIT_LIMIT_EXCEEDED",
    "message": "Credit limit would be exceeded",
    "details": {
      "currentLimit": 500000,
      "currentBalance": 450000,
      "requestedAmount": 100000
    },
    "timestamp": "2024-01-20T10:30:45Z",
    "traceId": "abc-123-def"
  }
}
```

### Common Error Codes
| Code | HTTP Status | Description |
|------|-------------|-------------|
| CUSTOMER_NOT_FOUND | 404 | Customer ID does not exist |
| INSUFFICIENT_CREDIT | 400 | Credit limit exceeded |
| INVALID_PAYMENT_METHOD | 400 | Payment method not allowed |
| DUPLICATE_PAYMENT | 409 | Payment already exists |
| PERIOD_CLOSED | 400 | Cannot modify closed period |
| UNAUTHORIZED | 401 | Invalid or missing token |
| FORBIDDEN | 403 | Insufficient permissions |
| RATE_LIMITED | 429 | Too many requests |

## 🔔 Webhooks

### Payment Received
```json
{
  "event": "payment.received",
  "timestamp": "2024-01-20T10:30:45Z",
  "data": {
    "paymentId": "PAY-2024-0123",
    "customerId": "C001234",
    "amount": 50000
  }
}
```

### Credit Limit Changed
```json
{
  "event": "credit.limit.changed",
  "timestamp": "2024-01-20T10:30:45Z",
  "data": {
    "customerId": "C001234",
    "oldLimit": 500000,
    "newLimit": 800000
  }
}
```

### Collection Escalated
```json
{
  "event": "collection.escalated",
  "timestamp": "2024-01-20T10:30:45Z",
  "data": {
    "customerId": "C001234",
    "escalationLevel": "LEGAL",
    "overdueAmount": 150000
  }
}
```

## 📝 API Versioning

- Current Version: v1
- Version in URL: `/api/v1/...`
- Deprecation Notice: 6 months minimum
- Sunset Period: 3 months after deprecation
- Version Header: `API-Version: 1.0`