# Consolidated Legacy System Documentation - Lucky Gas

**Generated**: 2025-07-25  
**Purpose**: Complete reference documentation for the Lucky Gas legacy system migration

## 📚 Table of Contents

1. [System Overview](#system-overview)
2. [Architecture](#architecture)
3. [Module Documentation](#module-documentation)
4. [Data Structures](#data-structures)
5. [Business Rules & Workflows](#business-rules--workflows)
6. [Technical Implementation Details](#technical-implementation-details)
7. [Migration Strategy](#migration-strategy)

---

## System Overview

### Current System Information
- **URL**: https://www.renhongtech2.com.tw/luckygas_97420648/index.aspx
- **Technology**: ASP.NET WebForms (.NET Framework 4.x)
- **Database**: SQL Server
- **Authentication**: Forms-based with Tax ID, Customer ID, and Password
- **UI**: Frame-based layout (legacy)
- **Language**: Traditional Chinese (繁體中文)

### System Modules (11 Major + 102 Leaf Nodes)

1. **會員作業 (C000)** - Customer Management - 11 features
2. **資料維護 (W000)** - Data Maintenance - 12 features  
3. **訂單銷售 (W100)** - Order Sales - 13 features
4. **報表作業 (W300)** - Reports - 15 features
5. **熱氣球作業 (W500)** - Hot Air Balloon - 4 features
6. **幸福氣APP (W600)** - Lucky Gas APP - 4 features
7. **發票作業 (W700)** - Invoice Operations - 10 features
8. **帳務管理 (W800)** - Account Management - 10 features
9. **CSV匯出 (Z100)** - CSV Export - 6 features
10. **派遣作業 (Z200)** - Dispatch Operations - 9 features
11. **通報作業 (Z300)** - Notification Operations - 8 features

---

## Architecture

### Technical Stack
```
┌─────────────────────────────────────────────────────────┐
│                    Browser Client                        │
├─────────────────────────────────────────────────────────┤
│  ┌─────────────┬──────────────────┬─────────────────┐  │
│  │   Banner    │    Main Frame    │                  │  │
│  │   Frame     │   (main.aspx)    │                  │  │
│  ├─────────────┤                  │                  │  │
│  │ Navigation  │   Content Area   │                  │  │
│  │   Frame     │                  │                  │  │
│  │ (Left.aspx) │                  │                  │  │
│  └─────────────┴──────────────────┴─────────────────┘  │
└─────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────┐
│                    Web Server (IIS)                      │
├─────────────────────────────────────────────────────────┤
│                 ASP.NET WebForms Engine                  │
└─────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────┐
│              SQL Server Database                         │
└─────────────────────────────────────────────────────────┘
```

### Authentication Flow
1. User accesses `/index.aspx`
2. Enters credentials: Tax ID (統一編號), Customer ID (客戶編號), Password
3. System validates against database
4. Creates ASP.NET Forms Authentication ticket
5. Redirects to main frameset

### Key Security Issues (Must Fix in New System)
- Plain text passwords stored in database
- No password complexity requirements
- No account lockout mechanism
- Session fixation vulnerability
- No multi-factor authentication

---

## Module Documentation

### 1. Customer Management (會員作業)

**Key Features**:
- Customer registration and profile management
- Multiple delivery addresses per customer
- Credit limit management
- Payment method settings
- Customer type classification (residential/commercial)

**Data Fields** (76 total):
```yaml
customer:
  customer_id: "C000001"      # Auto-generated
  tax_id: "53212539"         # 8-digit validated
  customer_name: "幸福瓦斯行"
  phone_primary: "0912-345-678"
  delivery_address: "台北市中正區重慶南路一段122號"
  credit_limit: 50000
  payment_method: "月結"     # Monthly/Cash
  customer_type: "商業"      # Commercial/Residential
```

### 2. Order Sales (訂單銷售)

**Key Features**:
- Order creation with customer selection
- Gas cylinder type and quantity
- Delivery scheduling
- Price calculation
- Credit limit checking
- Order modification and cancellation

**Order Workflow**:
1. Select customer → Check credit limit
2. Add gas cylinders (20kg, 50kg, etc.)
3. Set delivery date/time
4. Calculate pricing
5. Confirm order
6. Generate order number

### 3. Dispatch Operations (派遣作業)

**Key Features**:
- Route planning and optimization
- Driver assignment
- Delivery tracking
- Emergency dispatch
- Route modification

**Dispatch Process**:
1. Load pending orders
2. Group by area/zone
3. Assign to drivers
4. Print route sheets
5. Track completion

### 4. Invoice Operations (發票作業)

**Key Features**:
- Taiwan e-invoice generation
- Government tax system integration
- Invoice void/cancellation
- Credit note management
- Monthly invoice batch

**Taiwan Compliance**:
- Format: Government XML standard
- Submission: Daily batch to tax authority
- Storage: 5-year retention requirement

---

## Data Structures

### Core Entities

#### Customer Entity
```sql
CREATE TABLE CUST_CUSTOMER (
    CUSTOMER_ID VARCHAR(10) PRIMARY KEY,    -- C000001
    TAX_ID VARCHAR(10) UNIQUE,              -- 統一編號
    CUSTOMER_NAME NVARCHAR(100) NOT NULL,   -- 客戶名稱
    PHONE_PRIMARY VARCHAR(20) NOT NULL,     -- 主要電話
    DELIVERY_ADDRESS NVARCHAR(200),         -- 送貨地址
    INVOICE_ADDRESS NVARCHAR(200),          -- 發票地址
    CREDIT_LIMIT DECIMAL(10,2) DEFAULT 0,   -- 信用額度
    PAYMENT_METHOD VARCHAR(20),             -- 付款方式
    CUSTOMER_TYPE VARCHAR(20),              -- 客戶類型
    CREATE_DATE DATETIME,
    UPDATE_DATE DATETIME,
    DELETE_FLAG CHAR(1) DEFAULT 'N'
);
```

#### Order Entity
```sql
CREATE TABLE ORD_ORDER (
    ORDER_ID VARCHAR(20) PRIMARY KEY,       -- ORD20250125001
    CUSTOMER_ID VARCHAR(10) NOT NULL,
    ORDER_DATE DATETIME NOT NULL,
    DELIVERY_DATE DATE NOT NULL,
    DELIVERY_TIME_SLOT VARCHAR(20),         -- AM/PM/特定時段
    TOTAL_AMOUNT DECIMAL(10,2),
    ORDER_STATUS VARCHAR(20),               -- 待處理/已派遣/已送達
    DRIVER_ID VARCHAR(10),
    CREATE_USER VARCHAR(20),
    CREATE_DATE DATETIME
);
```

#### Gas Cylinder Types
```yaml
cylinders:
  - type: "4kg"    # 家庭用小桶
  - type: "10kg"   # 家庭用
  - type: "16kg"   # 家庭用
  - type: "20kg"   # 商業用
  - type: "50kg"   # 工業用
```

---

## Business Rules & Workflows

### Credit Management Rules
```
IF customer.payment_method = '月結' THEN
  current_balance = GET_OUTSTANDING_BALANCE(customer_id)
  IF (current_balance + order.total) > customer.credit_limit THEN
    IF customer.credit_limit > 50000 THEN
      REQUIRE_MANAGER_APPROVAL()
    ELSE
      BLOCK_ORDER("超過信用額度")
    END IF
  END IF
END IF
```

### Delivery Rules
- Service hours: 08:00 - 18:00
- Time slots: Morning (08:00-12:00), Afternoon (13:00-18:00)
- Emergency delivery: +30% surcharge
- Same-day delivery: Before 10:00 AM order

### Taiwan-Specific Validations

#### Phone Number Validation
```javascript
// Mobile: 09XX-XXX-XXX
const mobileRegex = /^09\d{8}$/;

// Landline: 0X-XXXX-XXXX (area code 02-09)
const landlineRegex = /^0[2-9]-?\d{4}-?\d{4}$/;
```

#### Tax ID Validation (統一編號)
```javascript
function validateTaxId(taxId) {
  if (!/^\d{8}$/.test(taxId)) return false;
  
  const weights = [1, 2, 1, 2, 1, 2, 4, 1];
  let sum = 0;
  
  for (let i = 0; i < 8; i++) {
    const product = parseInt(taxId[i]) * weights[i];
    sum += Math.floor(product / 10) + (product % 10);
  }
  
  return sum % 10 === 0;
}
```

---

## Technical Implementation Details

### API Patterns (New System)

#### Standard Response Format
```json
{
  "success": true,
  "data": { },
  "message": "操作成功",
  "timestamp": "2025-01-25T10:30:00Z"
}
```

#### Common API Endpoints
```
POST   /api/v1/customers          # Create customer
GET    /api/v1/customers          # List customers (paginated)
GET    /api/v1/customers/{id}     # Get customer details
PUT    /api/v1/customers/{id}     # Update customer
DELETE /api/v1/customers/{id}     # Soft delete

POST   /api/v1/orders             # Create order
GET    /api/v1/orders/pending     # Get orders for dispatch
PUT    /api/v1/orders/{id}/status # Update delivery status
```

### Database Patterns

#### Audit Fields (All Tables)
```sql
CREATE_USER VARCHAR(20),      -- User who created record
CREATE_DATE DATETIME,         -- Creation timestamp
UPDATE_USER VARCHAR(20),      -- Last modified by
UPDATE_DATE DATETIME,         -- Last modification
DELETE_FLAG CHAR(1) DEFAULT 'N'  -- Soft delete
```

#### Common Status Codes
```yaml
order_status:
  PENDING: "待處理"
  DISPATCHED: "已派遣"
  DELIVERED: "已送達"
  CANCELLED: "已取消"

customer_status:
  ACTIVE: "正常"
  CREDIT_HOLD: "信用凍結"
  SUSPENDED: "暫停服務"
  TERMINATED: "終止"
```

---

## Migration Strategy

### Phase 1: Foundation (Current)
- ✅ Modern tech stack setup (React + FastAPI)
- ✅ Authentication system
- ✅ Basic customer management
- 🔄 Order management (in progress)

### Phase 2: Core Operations
- [ ] Complete order workflow
- [ ] Dispatch/route planning
- [ ] Driver mobile app
- [ ] Basic reporting

### Phase 3: Financial & Compliance
- [ ] Invoice generation
- [ ] E-invoice integration
- [ ] Account management
- [ ] Financial reports

### Phase 4: Advanced Features
- [ ] AI route optimization
- [ ] Predictive analytics
- [ ] Customer mobile app
- [ ] Real-time tracking

### Critical Migration Considerations

1. **Data Migration**
   - Convert from Big5 to UTF-8 encoding
   - Validate all Taiwan-specific formats
   - Preserve all historical data
   - Maintain referential integrity

2. **User Training**
   - Side-by-side comparison guides
   - Video tutorials in Traditional Chinese
   - Practice environment
   - Phased rollout by department

3. **Compatibility**
   - Support existing hardware (printers, scanners)
   - Import/export same file formats
   - Maintain integration with government systems
   - Keep familiar workflows

4. **Zero Downtime Migration**
   - Parallel running period
   - Real-time sync between systems
   - Gradual user migration
   - Rollback capability

---

## Appendices

### A. Navigation Quick Reference

| Legacy Menu | New System Location |
|-------------|-------------------|
| 會員作業 (C000) | Customers > Management |
| 訂單銷售 (W100) | Orders > New Order |
| 派遣作業 (Z200) | Dispatch > Route Planning |
| 報表作業 (W300) | Analytics > Reports |
| 發票作業 (W700) | Billing > Invoices |

### B. Common Error Messages

| Code | Legacy Message | New Message | Action |
|------|---------------|-------------|---------|
| E001 | 超過信用額度 | Credit limit exceeded | Request manager approval |
| E002 | 客戶資料重複 | Duplicate customer | Check existing records |
| E003 | 無效的統一編號 | Invalid tax ID | Verify checksum |

### C. Integration Points

1. **Government Tax System**
   - Protocol: HTTPS POST
   - Format: XML (specific schema)
   - Schedule: Daily 10 PM

2. **Banking System**
   - Method: SFTP
   - Format: Fixed-width text
   - Schedule: Daily 6 AM

3. **SMS Gateway**
   - API: RESTful HTTP
   - Provider: Local telecom
   - Usage: Delivery notifications

---

**Document Version**: 1.0  
**Last Updated**: 2025-07-25  
**Next Review**: After Phase 2 completion