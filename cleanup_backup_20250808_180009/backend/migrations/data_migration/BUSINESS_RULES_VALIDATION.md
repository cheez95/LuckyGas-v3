# Lucky Gas Business Rules & Data Validation Requirements
**Prepared by**: Mary (Business Analyst)  
**Date**: 2025-01-29  
**Purpose**: Document comprehensive business rules and validation requirements for data migration

## 📋 Executive Summary

Based on the data migration analysis and existing business rules documentation, this document consolidates all business rules discovered in the raw data and provides validation requirements for ensuring data quality during migration.

## 🏢 Core Business Entities & Rules

### 1. Customer Management Rules

#### 1.1 Customer Identification & Classification
```yaml
customer_types:
  commercial:
    code_prefixes: ["C", "B"]  # Found in raw data
    requirements:
      - tax_id: "Required (8 digits)"
      - invoice_title: "Required for e-invoice"
      - credit_limit: "Default 30,000-100,000 NTD based on sub-type"
    sub_types:
      - "公司行號 (Company)"
      - "餐廳 (Restaurant)" 
      - "工廠 (Factory)"
      - "機關團體 (Institution)"
      
  residential:
    code_prefixes: ["R", "H"]  # Found in raw data
    requirements:
      - tax_id: "Optional"
      - credit_limit: "Default 10,000 NTD"
      - cylinder_count: "Usually 1-2 cylinders"
```

#### 1.2 Taiwan-Specific Validations
```python
# Tax ID (統一編號) Validation
def validate_taiwan_tax_id(tax_id):
    """
    Taiwan business tax ID validation algorithm
    Returns: (is_valid, error_message)
    """
    if not tax_id or len(tax_id) != 8:
        return False, "統一編號必須為8位數字"
    
    if not tax_id.isdigit():
        return False, "統一編號只能包含數字"
    
    weights = [1, 2, 1, 2, 1, 2, 4, 1]
    sum_value = 0
    
    for i in range(8):
        product = int(tax_id[i]) * weights[i]
        sum_value += product // 10 + product % 10
    
    if sum_value % 10 != 0:
        return False, "統一編號檢查碼錯誤"
    
    return True, None

# Phone Number Validation
def validate_taiwan_phone(phone):
    """
    Validate Taiwan phone numbers (mobile and landline)
    Returns: (is_valid, phone_type, formatted_number)
    """
    import re
    
    # Remove all non-digits
    digits = re.sub(r'\D', '', phone)
    
    # Mobile pattern: 09XX-XXX-XXX
    if digits.startswith('09') and len(digits) == 10:
        formatted = f"{digits[:4]}-{digits[4:7]}-{digits[7:]}"
        return True, 'mobile', formatted
    
    # Landline pattern: 0X-XXXX-XXXX (2-4 area code)
    if digits.startswith('0') and len(digits) in [9, 10]:
        if len(digits) == 9:  # 2-digit area code
            formatted = f"{digits[:2]}-{digits[2:6]}-{digits[6:]}"
        else:  # 3-digit area code
            formatted = f"{digits[:3]}-{digits[3:7]}-{digits[7:]}"
        return True, 'landline', formatted
    
    return False, None, None

# Address Validation
def validate_taiwan_address(address):
    """
    Validate and parse Taiwan address format
    Returns: (is_valid, parsed_components, postal_code)
    """
    import re
    
    # Extract postal code (3-5 digits)
    postal_match = re.search(r'^(\d{3,5})', address)
    postal_code = postal_match.group(1) if postal_match else None
    
    # Common address patterns
    patterns = {
        'city': r'(臺北|台北|新北|桃園|臺中|台中|臺南|台南|高雄|基隆|新竹|嘉義|苗栗|彰化|南投|雲林|屏東|宜蘭|花蓮|臺東|台東|澎湖|金門|連江)(?:市|縣)',
        'district': r'([\u4e00-\u9fa5]+)(?:區|鄉|鎮|市)',
        'road': r'([\u4e00-\u9fa5]+)(?:路|街|大道|巷|弄)',
        'number': r'(\d+)(?:號|之\d+)?'
    }
    
    components = {}
    for key, pattern in patterns.items():
        match = re.search(pattern, address)
        if match:
            components[key] = match.group(0)
    
    # Basic validation - must have at least city and district
    is_valid = 'city' in components and 'district' in components
    
    return is_valid, components, postal_code
```

### 2. Cylinder & Inventory Management Rules

#### 2.1 Cylinder Types & Sizes
```yaml
cylinder_types:
  standard_sizes:
    50kg:
      deposit: 3000
      common_use: "Industrial, Large restaurants"
      refill_price_range: "1800-2200 NTD"
      
    20kg:
      deposit: 1500
      common_use: "Restaurants, Small businesses"
      refill_price_range: "800-1000 NTD"
      
    16kg:
      deposit: 1200
      common_use: "Residential, Small restaurants"
      refill_price_range: "650-800 NTD"
      
    10kg:
      deposit: 1000
      common_use: "Residential"
      refill_price_range: "450-550 NTD"
      
    4kg:
      deposit: 800
      common_use: "Camping, Small use"
      refill_price_range: "200-300 NTD"

  special_brands:
    "營": 
      name: "營業用 (Commercial)"
      restrictions: "Commercial customers only"
      
    "好運":
      name: "Good Luck Brand"
      premium: true
      
    "幸福丸":
      name: "Happiness Brand"
      premium: true
```

#### 2.2 Cylinder Tracking Rules
```yaml
cylinder_tracking:
  customer_inventory:
    track_by_size: true
    track_serial_numbers: false  # Not in current data
    
  balance_calculation:
    formula: "owned + rented - empty_returns"
    validation: "total_at_customer >= 0"
    
  return_rules:
    empty_return_credit: "Applied to next order"
    damaged_cylinder: "Customer liability unless proven defect"
    lost_cylinder: "Full deposit charged"
```

### 3. Delivery & Scheduling Rules

#### 3.1 Delivery Time Management
```yaml
delivery_time_slots:
  morning_slots:
    "08-09": 
      code: "T01"
      capacity: "Limited by route"
      
    "09-10": 
      code: "T02"
      peak_demand: true
      
    "10-11": 
      code: "T03"
      
    "11-12": 
      code: "T04"
      
  afternoon_slots:
    "13-14": 
      code: "T05"
      
    "14-15": 
      code: "T06"
      
    "15-16": 
      code: "T07"
      peak_demand: true
      
    "16-17": 
      code: "T08"
      
  evening_slots:
    "17-18": 
      code: "T09"
      surcharge: 20%
      
    "18-19": 
      code: "T10"
      surcharge: 30%
      
    "19-20": 
      code: "T11"
      surcharge: 50%
      limited_areas: true

  special_codes:
    "早1": 
      meaning: "Morning preference"
      slots: ["T01", "T02", "T03", "T04"]
      
    "午2": 
      meaning: "Afternoon preference"
      slots: ["T05", "T06", "T07", "T08"]
      
    "晚3": 
      meaning: "Evening preference"
      slots: ["T09", "T10", "T11"]
      
    "全天0": 
      meaning: "Any time"
      priority: "Lower"
```

#### 3.2 Same-Day Delivery Rules
```yaml
same_day_delivery:
  cutoff_times:
    morning_delivery: "Previous day 17:00"
    afternoon_delivery: "Same day 10:00"
    evening_delivery: "Same day 14:00"
    
  eligible_customers:
    - "Restaurants (during operating hours)"
    - "VIP customers"
    - "Emergency requests (surcharge applies)"
    
  surcharge:
    regular: 100
    urgent: 300
    emergency: 500
```

### 4. Pricing & Payment Rules

#### 4.1 Pricing Structure
```yaml
pricing_methods:
  "定價":
    type: "Fixed price"
    description: "Standard list price"
    
  "特價":
    type: "Special price"
    description: "Customer-specific negotiated price"
    
  "合約價":
    type: "Contract price"
    description: "Long-term contract pricing"
    
  "量價":
    type: "Volume price"
    description: "Quantity-based discounts"
    tiers:
      - quantity: 50+
        discount: 5%
      - quantity: 100+
        discount: 8%
      - quantity: 200+
        discount: 10%
```

#### 4.2 Payment Terms
```yaml
payment_methods:
  "現金":
    code: "CASH"
    credit_days: 0
    
  "月結":
    code: "MONTHLY"
    credit_days: 30
    requirements: "Credit approval required"
    
  "票期30":
    code: "CHECK30"
    credit_days: 30
    requirements: "Post-dated check"
    
  "票期60":
    code: "CHECK60"
    credit_days: 60
    requirements: "Post-dated check, higher credit limit"
    
  "預付":
    code: "PREPAID"
    credit_days: -1
    discount: 2%
```

### 5. Equipment & Accessories Rules

#### 5.1 Equipment Types
```yaml
equipment_tracking:
  flow_meters:
    sizes: ["50kg", "20kg", "16kg"]
    purpose: "Accurate gas consumption measurement"
    rental_fee: "200-500 NTD/month"
    
  switches:
    types: ["自動切換器 (Auto-switch)", "手動切換器 (Manual)"]
    purpose: "Cylinder switching for continuous supply"
    
  smart_scales:
    purpose: "Real-time gas level monitoring"
    connectivity: "IoT/4G"
    monthly_fee: "300 NTD"
    
  hoses_regulators:
    inspection: "Annual safety check required"
    replacement: "Every 5 years or when damaged"
```

## 🔍 Missing Business Logic Requiring Clarification

### 1. Customer Lifecycle
- **Question**: What triggers customer status changes (Active → Inactive)?
- **Question**: How long before inactive customers are archived?
- **Question**: Can deleted customers be reactivated?

### 2. Pricing Exceptions
- **Question**: How are promotional prices applied with contract prices?
- **Question**: What's the approval process for prices below cost?
- **Question**: How are price changes communicated to customers?

### 3. Delivery Constraints
- **Question**: Maximum cylinders per delivery vehicle?
- **Question**: How are route capacity limits determined?
- **Question**: Rules for combining multiple customer orders?

### 4. Inventory Management
- **Question**: Cylinder lifecycle tracking (manufacture date, inspection)?
- **Question**: Rules for cylinder allocation during shortages?
- **Question**: Safety stock levels by cylinder size?

### 5. Financial Rules
- **Question**: Bad debt write-off criteria?
- **Question**: Deposit refund process and timeline?
- **Question**: Interest charges on overdue accounts?

## ✅ Data Validation Rules

### 1. Pre-Migration Validation Checks
```python
class DataValidationRules:
    """Comprehensive validation rules for data migration"""
    
    @staticmethod
    def validate_customer_record(record):
        validations = []
        
        # Required field checks
        required_fields = {
            'commercial': ['customer_code', 'company_name', 'tax_id', 'address'],
            'residential': ['customer_code', 'name', 'phone', 'address']
        }
        
        # Taiwan-specific validations
        if record.get('tax_id'):
            is_valid, error = validate_taiwan_tax_id(record['tax_id'])
            if not is_valid:
                validations.append(f"Invalid tax ID: {error}")
        
        if record.get('phone'):
            is_valid, _, _ = validate_taiwan_phone(record['phone'])
            if not is_valid:
                validations.append("Invalid phone number format")
        
        # Business logic validations
        if record.get('credit_limit', 0) < 0:
            validations.append("Credit limit cannot be negative")
        
        # Cylinder inventory validations
        cylinder_fields = ['50kg', '20kg', '16kg', '10kg', '4kg']
        for field in cylinder_fields:
            if record.get(field, 0) < 0:
                validations.append(f"Negative cylinder count for {field}")
        
        return validations
    
    @staticmethod
    def validate_delivery_record(record):
        validations = []
        
        # Date validation
        if record.get('delivery_date'):
            # Convert Taiwan date format
            taiwan_date = str(record['delivery_date'])
            if len(taiwan_date) == 7:  # Format: 1140102
                year = int(taiwan_date[:3]) + 1911
                month = int(taiwan_date[3:5])
                day = int(taiwan_date[5:7])
                
                if not (1 <= month <= 12 and 1 <= day <= 31):
                    validations.append("Invalid date values")
        
        # Quantity validations
        if record.get('quantity', 0) <= 0:
            validations.append("Delivery quantity must be positive")
        
        # Price validations
        if record.get('unit_price', 0) < 0:
            validations.append("Unit price cannot be negative")
        
        return validations
```

### 2. Post-Migration Validation Queries
```sql
-- Customer data integrity checks
SELECT 'Duplicate Tax IDs' as check_name,
       COUNT(*) as issue_count
FROM customers
WHERE tax_id IS NOT NULL
GROUP BY tax_id
HAVING COUNT(*) > 1

UNION ALL

SELECT 'Missing addresses' as check_name,
       COUNT(*) as issue_count
FROM customers
WHERE address IS NULL OR address = ''

UNION ALL

SELECT 'Invalid phone numbers' as check_name,
       COUNT(*) as issue_count
FROM customers
WHERE phone NOT REGEXP '^0[2-9]-[0-9]{4}-[0-9]{4}$'
  AND phone NOT REGEXP '^09[0-9]{2}-[0-9]{3}-[0-9]{3}$'

UNION ALL

SELECT 'Negative cylinder counts' as check_name,
       COUNT(*) as issue_count
FROM customer_cylinders
WHERE quantity < 0

UNION ALL

SELECT 'Orphaned deliveries' as check_name,
       COUNT(*) as issue_count
FROM deliveries d
LEFT JOIN customers c ON d.customer_id = c.id
WHERE c.id IS NULL;
```

## 🎯 Edge Case Handling Recommendations

### 1. Data Quality Issues
```yaml
duplicate_customers:
  detection: "Same tax_id or (name + phone)"
  resolution:
    - "Merge records, keeping most recent data"
    - "Combine cylinder counts"
    - "Preserve all delivery history"
    - "Log merge actions for audit"

missing_required_fields:
  tax_id:
    - "Flag for manual review"
    - "Create placeholder 'PENDING-XXXX'"
    - "Add to exception report"
    
  phone:
    - "Check alternate phone fields"
    - "Use 'NO-PHONE' placeholder"
    - "Flag for customer contact"

invalid_dates:
  - "Log original value"
  - "Apply business logic (e.g., if day > 31, likely typo)"
  - "Use last known good date if available"
  - "Flag for review"
```

### 2. Business Logic Conflicts
```yaml
credit_exceed_without_approval:
  - "Cap at customer type maximum"
  - "Create approval request record"
  - "Notify credit manager"

conflicting_pricing:
  - "Apply hierarchy: Contract > Special > Volume > Standard"
  - "Log pricing decision"
  - "Flag unusual discounts (>20%)"

invalid_delivery_slots:
  - "Map to closest valid slot"
  - "Preserve original preference as note"
  - "Notify dispatch for confirmation"
```

### 3. Data Transformation Rules
```yaml
address_standardization:
  - "Parse into components"
  - "Validate postal code against official database"
  - "Geocode for delivery optimization"
  - "Preserve original as 'raw_address'"

phone_normalization:
  - "Remove all non-numeric characters"
  - "Add appropriate dashes"
  - "Separate multiple numbers"
  - "Set primary/secondary flags"

name_formatting:
  - "Preserve Traditional Chinese characters"
  - "Separate company/personal names"
  - "Extract titles (董事長, 總經理, etc.)"
  - "Handle Unicode properly"
```

## 📊 Migration Success Metrics

### 1. Data Completeness
- **Target**: 100% of active customers migrated
- **Target**: 99.9% of delivery history preserved
- **Target**: 100% of financial balances reconciled

### 2. Data Quality
- **Target**: <0.1% validation errors post-migration
- **Target**: 100% of critical fields populated
- **Target**: Zero duplicate active customers

### 3. Business Continuity
- **Target**: All delivery routes operational Day 1
- **Target**: All pricing rules applied correctly
- **Target**: Zero disruption to billing cycle

## 🔄 Rollback Procedures

### 1. Validation Checkpoints
```sql
-- Pre-migration counts
CREATE TABLE migration_metrics AS
SELECT 
    'customers' as entity,
    COUNT(*) as original_count,
    COUNT(DISTINCT tax_id) as unique_tax_ids,
    SUM(credit_limit) as total_credit
FROM source_customers
WHERE status = 'ACTIVE';

-- Post-migration validation
SELECT 
    entity,
    original_count,
    (SELECT COUNT(*) FROM customers) as migrated_count,
    CASE 
        WHEN original_count = (SELECT COUNT(*) FROM customers)
        THEN 'PASS'
        ELSE 'FAIL'
    END as status
FROM migration_metrics;
```

### 2. Rollback Triggers
- Any validation checkpoint fails
- Financial totals don't reconcile
- Critical business rule violations detected
- Performance degradation >50%

### 3. Recovery Process
1. Stop all write operations
2. Restore from pre-migration backup
3. Apply transaction logs for interim changes
4. Investigate and fix root cause
5. Re-run migration with fixes

## 📝 Documentation Requirements

### 1. Migration Logs
- Timestamp all operations
- Record row counts at each stage
- Log all transformations applied
- Capture all validation errors
- Document manual interventions

### 2. Exception Reports
- Customers requiring manual review
- Data quality issues found
- Business rule violations
- Performance metrics
- Reconciliation results

### 3. Audit Trail
- Original vs. transformed data samples
- Approval records for overrides
- Rollback decision points
- Success/failure metrics
- Lessons learned

---

**Next Steps**:
1. Review and approve business rules with Lucky Gas management
2. Clarify missing business logic items
3. Implement validation functions in migration scripts
4. Create test cases for edge scenarios
5. Schedule migration dry run

**Risk Level**: HIGH - This migration affects core business operations and financial data

**Recommendation**: Proceed with staged migration approach, starting with read-only test environment