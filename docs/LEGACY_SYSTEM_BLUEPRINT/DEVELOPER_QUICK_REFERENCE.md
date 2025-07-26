# Developer Quick Reference - Lucky Gas Blueprint

**Purpose**: Quick lookup for developers implementing the new Lucky Gas system based on the legacy blueprint documentation.

## 🚀 Getting Started

### Documentation Structure
```
LEGACY_SYSTEM_BLUEPRINT/
├── 00_SYSTEM_OVERVIEW/          # Start here for architecture
├── 01_CUSTOMER_MANAGEMENT/      # Complete reference implementation
├── 02_DATA_MAINTENANCE/         # (Coming soon)
├── 03_ORDER_SALES/             # (Coming soon)
└── ...
```

### Where to Find What

| What You Need | Where to Look | File |
|--------------|---------------|------|
| System Architecture | System Overview | `00_SYSTEM_OVERVIEW/system_architecture.md` |
| Database Schema | Data Models | `*/data_models/*.yaml` |
| API Endpoints | API Specs | `*/api_endpoints.md` |
| Business Logic | Business Rules | `*/business_rules.md` |
| User Workflows | Workflows | `*/workflows/*.md` |
| Field Validations | Validations | `*/taiwan_specific_validations.md` |

## 💾 Database Quick Reference

### Customer Tables
```sql
-- Main customer table
CREATE TABLE CUST_CUSTOMER (
    CUSTOMER_ID VARCHAR(10) PRIMARY KEY,  -- Format: C000001
    TAX_ID VARCHAR(10) UNIQUE,            -- 8 digits, validated
    CUSTOMER_NAME VARCHAR(100) NOT NULL,
    PHONE_PRIMARY VARCHAR(20) NOT NULL,
    -- ... 76 total fields
);

-- Additional addresses
CREATE TABLE CUST_ADDRESS (
    ADDRESS_ID INTEGER PRIMARY KEY AUTO_INCREMENT,
    CUSTOMER_ID VARCHAR(10) REFERENCES CUST_CUSTOMER,
    ADDRESS_TYPE VARCHAR(2),  -- 01:Delivery, 02:Invoice
    -- ... see data model for all fields
);
```

### Common Field Patterns
- IDs: `VARCHAR(10)` with specific formats
- Dates: `DATETIME` with Taiwan timezone
- Money: `DECIMAL(10,2)` for TWD amounts
- Status: `VARCHAR(2)` with lookup values
- Delete: Soft delete with `DELETE_FLAG = 'Y'`

## 🔌 API Quick Reference

### Base URL Pattern
```
https://api.luckygas.com.tw/api/v1
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
  "data": { },
  "message": "操作成功",
  "timestamp": "2024-01-25T10:30:00Z"
}
```

### Error Response Format
```json
{
  "success": false,
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "驗證失敗",
    "details": { }
  }
}
```

## ✅ Validation Quick Reference

### Taiwan Phone Numbers
```javascript
// Mobile: 09XX-XXX-XXX
const mobileRegex = /^09\d{8}$/;

// Landline: 0X-XXXX-XXXX
const landlineRegex = /^0[2-9]-?\d{4}-?\d{4}$/;
```

### Taiwan Tax ID (統一編號)
```javascript
function validateTaxId(taxId) {
  const weights = [1, 2, 1, 2, 1, 2, 4, 1];
  // See taiwan_specific_validations.md for full algorithm
}
```

### Common Validation Rules
| Field Type | Validation | Example |
|------------|------------|---------|
| Phone | Taiwan format | 0912-345-678 |
| Tax ID | 8 digits + checksum | 53212539 |
| Postal Code | 3 or 5 digits | 10041 |
| Credit Limit | > 0, manager approval > 50k | 30000 |
| Customer Code | Auto-generated C###### | C000123 |

## 🔄 Common Workflows

### Customer Creation Flow
```
1. Search existing → 2. Fill form → 3. Validate → 4. Credit check → 5. Save
```

### Order Creation Flow
```
1. Select customer → 2. Check credit → 3. Add items → 4. Set delivery → 5. Confirm
```

### Key Decision Points
- Credit > 50,000 → Manager approval required
- New address → Validate service area
- Overdue > 30 days → Auto credit hold

## 🌏 Taiwan-Specific Features

### Date Formatting
```javascript
// ROC Calendar (民國年)
const rocYear = westernYear - 1911;
// Display: 民國113年01月25日
```

### Currency Formatting
```javascript
// TWD (no decimal places)
const formatted = `NT$ ${amount.toLocaleString('zh-TW')}`;
// Display: NT$ 1,500
```

### Address Format
```
[郵遞區號] [縣市][區鄉鎮][路街][段][巷][弄][號][樓][室]
10041 台北市中正區重慶南路一段122號3樓之2
```

## 🚨 Critical Business Rules

### Credit Management
- Default limit by customer type
- Automatic hold triggers
- Manager approval matrix

### Delivery Rules
- Service area validation
- Time slot preferences
- Special instructions

### Data Quality
- No duplicate Tax IDs
- Phone number uniqueness warning
- Soft delete only

## 📋 Implementation Checklist

### For Each Module
- [ ] Create database tables from data models
- [ ] Implement API endpoints from specifications
- [ ] Add field validations (client & server)
- [ ] Implement business rule logic
- [ ] Create UI following workflows
- [ ] Add Taiwan-specific formatting
- [ ] Implement error handling
- [ ] Add audit logging
- [ ] Create unit tests
- [ ] Document API with Swagger

### Security Requirements
- [ ] JWT authentication
- [ ] Role-based permissions
- [ ] Field-level security for sensitive data
- [ ] Audit trail for all changes
- [ ] Input sanitization
- [ ] SQL injection prevention

## 🔗 Quick Links

### Internal Documentation
- [System Architecture](00_SYSTEM_OVERVIEW/system_architecture.md)
- [Customer Management](01_CUSTOMER_MANAGEMENT/module_overview.md)
- [API Patterns](01_CUSTOMER_MANAGEMENT/api_endpoints.md)
- [Validation Rules](01_CUSTOMER_MANAGEMENT/taiwan_specific_validations.md)

### External Resources
- [Taiwan Tax ID Validation](https://www.etax.nat.gov.tw/)
- [Taiwan Postal Codes](https://www.post.gov.tw/)
- [Traditional Chinese Encoding](https://en.wikipedia.org/wiki/Big5)

## 💡 Pro Tips

1. **Always validate Tax IDs** - Critical for e-invoice integration
2. **Use transactions** - Many operations update multiple tables
3. **Cache postal codes** - They rarely change
4. **Log everything** - Audit requirements are strict
5. **Test with real addresses** - Taiwan formats are specific
6. **Handle Big5 encoding** - Legacy data might need conversion
7. **Implement soft delete** - Never hard delete customer data
8. **Check credit before orders** - Prevent business risk

---

**Remember**: The blueprint documentation is the source of truth. When in doubt, refer to the detailed module documentation for complete specifications.