# Data Maintenance Business Rules - Lucky Gas Legacy System

## 🎯 Overview

This document defines all business rules, validations, and constraints for the Data Maintenance module. These rules ensure data integrity, compliance with Taiwan regulations, and consistent business operations across the Lucky Gas system.

## 📋 Rule Categories

### 1. Product Management Rules
### 2. Employee Management Rules
### 3. System Parameter Rules
### 4. Zone Configuration Rules
### 5. Payment Terms Rules
### 6. Holiday Calendar Rules
### 7. Tax Configuration Rules
### 8. Data Import/Export Rules
### 9. Cross-Module Integration Rules
### 10. Security and Audit Rules

---

## 1. Product Management Rules

### 1.1 Product Code Rules
```yaml
Rule: PROD-001
Name: Product Code Format
Description: Product codes must follow specific format
Validation:
  - Pattern: "P[0-9]{3}"
  - Example: "P001", "P023", "P099"
  - Uniqueness: System-wide unique
  - Immutable: Cannot change after creation
Error: "產品代碼格式錯誤，必須為P開頭加3位數字"
```

### 1.2 Product Pricing Rules
```yaml
Rule: PROD-002
Name: Minimum Price Protection
Description: Prices cannot fall below cost threshold
Validation:
  - standard_price >= cost_price * 1.10
  - minimum_price >= cost_price
  - All prices > 0
Approval: Manager required if margin < 10%
Error: "價格低於成本加成門檻"

Rule: PROD-003
Name: Price Hierarchy
Description: Pricing follows strict hierarchy
Priority:
  1. Contract Price (if applicable)
  2. Special Customer Price
  3. Promotional Price (if active)
  4. Volume Discount Price
  5. Standard Price
Note: "Lower priority prices ignored when higher exists"

Rule: PROD-004
Name: Promotional Price Rules
Description: Time-bound promotional pricing
Constraints:
  - Must have end date
  - Cannot exceed 60 days
  - Maximum discount: 25%
  - Cannot overlap with same product
  - Requires approval if > 15% discount
```

### 1.3 Product Lifecycle Rules
```yaml
Rule: PROD-005
Name: Product Discontinuation
Description: Requirements before discontinuing product
Prerequisites:
  - Zero physical inventory
  - No open orders
  - No active promotions
  - All deposits returned
  - 30-day advance notice
Process: "Set discontinue date → Block new orders → Archive"

Rule: PROD-006
Name: Inventory Tracking Rules
Description: Products requiring inventory management
Required For:
  - All gas cylinders (category 01)
  - High-value accessories > NT$1000
  - Items with serial numbers
Not Required:
  - Services (category 03)
  - Low-value consumables
```

### 1.4 Taiwan-Specific Product Rules
```yaml
Rule: PROD-007
Name: Lucky Number Pricing
Description: Cultural pricing preferences
Guidelines:
  - Prefer prices ending in 8 (發)
  - Avoid prices ending in 4 (死)
  - Round to nearest 10 for >NT$1000
  - Special pricing for festivals
Example: "NT$888, NT$1,680, NT$2,888"

Rule: PROD-008
Name: Deposit Requirements
Description: Cylinder deposit rules
Requirements:
  - All gas cylinders require deposit
  - Standard deposit: NT$1,500
  - Cannot waive without GM approval
  - Track deposit per cylinder
  - Refund on cylinder return
```

---

## 2. Employee Management Rules

### 2.1 Employee Identification Rules
```yaml
Rule: EMP-001
Name: National ID Validation
Description: Taiwan National ID format and checksum
Validation:
  - Pattern: "[A-Z][12][0-9]{8}"
  - Checksum algorithm required
  - Uniqueness check
  - Cannot be modified after creation
Error: "身分證字號格式錯誤或檢查碼不符"

Rule: EMP-002
Name: Employee Code Format
Description: Unique employee identifier
Format:
  - Pattern: "E[0-9]{6}"
  - Sequential generation
  - Never reused
  - Display format: "E000123"
```

### 2.2 Driver-Specific Rules
```yaml
Rule: EMP-003
Name: Driver License Requirements
Description: Minimum license requirements for drivers
Requirements:
  - Professional license (職業駕照) required
  - Valid for truck class (大貨車)
  - Minimum 1 year experience
  - No major violations in 2 years
  - Valid for at least 6 months
Validation: "Check with MVD database if available"

Rule: EMP-004
Name: Driver Medical Requirements
Description: Health requirements for gas delivery
Requirements:
  - Annual physical exam
  - Vision test (corrected 0.8+)
  - No mobility restrictions
  - Drug/alcohol screening
  - Valid for 1 year
Action: "Suspend driving privileges on expiry"

Rule: EMP-005
Name: Driver Zone Assignment
Description: Delivery zone restrictions
Rules:
  - Maximum 3 zones per driver
  - Must complete training for zone
  - Cannot assign mountain zones to new drivers
  - Experience requirements by zone type
Capacity: "Max 20 cylinders per trip standard"
```

### 2.3 Employment Rules
```yaml
Rule: EMP-006
Name: Age Requirements
Description: Minimum age by role
Requirements:
  - General staff: 18 years
  - Drivers: 20 years (insurance requirement)
  - No maximum age if fit for duty
  - Retirement age: 65 (optional)

Rule: EMP-007
Name: Probation Period
Description: New employee probation
Terms:
  - Standard: 3 months
  - Drivers: 6 months
  - Can extend once by 3 months
  - Performance review required
  - Simplified termination during probation
```

### 2.4 Access Control Rules
```yaml
Rule: EMP-008
Name: System Access Levels
Description: Role-based access hierarchy
Levels:
  SUPER_ADMIN: "System-wide access"
  MANAGER: "Department access + approvals"
  SUPERVISOR: "Team access + reports"
  OPERATOR: "Transaction access"
  DRIVER: "Mobile app only"
Principle: "Least privilege required"

Rule: EMP-009
Name: Password Policy
Description: System password requirements
Requirements:
  - Minimum 8 characters
  - Mix of letters and numbers
  - Change every 90 days
  - Cannot reuse last 5
  - Lock after 5 failed attempts
```

---

## 3. System Parameter Rules

### 3.1 Parameter Change Rules
```yaml
Rule: SYS-001
Name: Parameter Change Approval
Description: Approval requirements by parameter type
Matrix:
  Business Rules: "Manager approval"
  System Settings: "IT Manager approval"
  Financial Settings: "Finance Manager approval"
  Integration URLs: "IT + Manager approval"
Emergency: "Can override with 2 managers"

Rule: SYS-002
Name: Parameter Effective Time
Description: When parameter changes take effect
Timing:
  Immediate: "UI settings, messages"
  Next Transaction: "Validation rules"
  Next Day: "Business rules, pricing"
  Scheduled: "System behavior changes"
  Restart Required: "Core system settings"
```

### 3.2 Business Rule Parameters
```yaml
Rule: SYS-003
Name: Order Validation Parameters
Description: Order processing constraints
Parameters:
  MIN_ORDER_AMOUNT: "NT$800 minimum"
  MAX_ORDER_CYLINDERS: "10 per order"
  ADVANCE_ORDER_DAYS: "7 days maximum"
  CUTOFF_TIME: "14:00 for same day"
  CREDIT_CHECK_THRESHOLD: "NT$5,000"

Rule: SYS-004
Name: Delivery Parameters
Description: Delivery operation settings
Parameters:
  MAX_STOPS_PER_ROUTE: "25 stops"
  MAX_WEIGHT_PER_TRUCK: "1000 kg"
  DELIVERY_TIME_WINDOW: "30 minutes"
  DRIVER_WORK_HOURS: "10 hours max"
  BREAK_TIME_REQUIRED: "30 min per 5 hours"
```

---

## 4. Zone Configuration Rules

### 4.1 Zone Definition Rules
```yaml
Rule: ZONE-001
Name: Zone Boundary Rules
Description: Delivery zone demarcation
Requirements:
  - No overlapping postal codes
  - Complete coverage of service area
  - Contiguous zones preferred
  - Maximum 30 postal codes per zone
  - Clear zone boundaries
Validation: "System checks for gaps and overlaps"

Rule: ZONE-002
Name: Zone Service Levels
Description: Service requirements by zone type
Levels:
  Urban: "6 days/week, 8am-8pm"
  Suburban: "5 days/week, 8am-6pm"
  Remote: "3 days/week, 9am-5pm"
  Island: "Weekly service"
  Mountain: "Bi-weekly, weather permitting"
```

### 4.2 Zone Pricing Rules
```yaml
Rule: ZONE-003
Name: Delivery Fee Structure
Description: Zone-based delivery charges
Structure:
  Base Fee: "By zone type"
  Distance Surcharge: "Remote/Island"
  Rush Delivery: "2x base fee"
  Free Threshold: "Orders > NT$3000"
  Holiday Surcharge: "+30-50%"
Constraints: "Cannot exceed 10% of order value"

Rule: ZONE-004
Name: Zone Capacity Rules
Description: Delivery capacity by zone
Limits:
  Time Slot Capacity: "20 orders max"
  Daily Zone Limit: "100 orders"
  Driver Assignment: "Max 3 drivers/zone"
  Overflow Handling: "Route to next slot"
  Peak Season: "Can increase 50%"
```

---

## 5. Payment Terms Rules

### 5.1 Credit Terms Rules
```yaml
Rule: PAY-001
Name: Payment Term Assignment
Description: Customer credit term eligibility
Criteria:
  Cash Only: "New customers < 3 months"
  NET30: "Established customers"
  NET60: "VIP customers only"
  Special Terms: "Contract customers"
Approval: "Manager for > NET30"

Rule: PAY-002
Name: Credit Limit Rules
Description: Customer credit limit assignment
Calculation:
  New Customer: "NT$10,000 default"
  Regular: "3x average monthly"
  VIP: "6x average monthly"
  Maximum: "NT$500,000"
  Review: "Quarterly adjustment"
Override: "Finance Manager approval"
```

### 5.2 Late Payment Rules
```yaml
Rule: PAY-003
Name: Late Payment Penalties
Description: Overdue payment handling
Penalties:
  Grace Period: "5 days standard"
  Late Charge: "1.5% per month"
  Service Hold: "After 30 days"
  Collection: "After 60 days"
  Write-off: "After 180 days"
Exceptions: "Long-term customers case-by-case"

Rule: PAY-004
Name: Payment Discount Rules
Description: Early payment incentives
Discounts:
  Within 10 days: "2% discount"
  Within 20 days: "1% discount"
  Prepayment: "3% discount"
  Annual Contract: "5% discount"
Restrictions: "Not combinable"
```

---

## 6. Holiday Calendar Rules

### 6.1 Holiday Service Rules
```yaml
Rule: HOL-001
Name: Holiday Operations
Description: Service levels during holidays
Categories:
  National Holiday: "No regular service"
  Company Holiday: "Emergency only"
  Make-up Day: "Saturday schedule"
  Festival: "Half-day service"
  Special Event: "Modified hours"
Surcharge: "30-50% depending on type"

Rule: HOL-002
Name: Holiday Scheduling
Description: Order scheduling around holidays
Rules:
  - No delivery on government holidays
  - Pre-holiday rush management
  - Post-holiday catch-up priority
  - Customer notification required
  - Alternative delivery dates offered
Timeline: "Notify 7 days in advance"
```

### 6.2 Taiwan Holiday Specifics
```yaml
Rule: HOL-003
Name: Lunar Calendar Events
Description: Traditional holiday handling
Special Dates:
  Spring Festival: "5-day closure"
  Mid-Autumn: "1-day closure"
  Dragon Boat: "1-day closure"
  Tomb Sweeping: "1-day closure"
  Ghost Month: "No new contracts"
Business Impact: "Plan inventory accordingly"

Rule: HOL-004
Name: Typhoon Day Rules
Description: Natural disaster response
Protocol:
  - Government announcement based
  - Immediate service suspension
  - Emergency deliveries only
  - Double surcharge if operating
  - Driver safety paramount
Recovery: "Priority to hospitals/elderly"
```

---

## 7. Tax Configuration Rules

### 7.1 Tax Calculation Rules
```yaml
Rule: TAX-001
Name: VAT Application
Description: Business tax calculation
Standard Rate: "5%"
Tax-Exempt:
  - Export sales
  - Government entities
  - Medical facilities
Special Cases:
  - Zero-rated items
  - Small business (<NT$200k)
Invoice Requirement: "All B2B transactions"

Rule: TAX-002
Name: Invoice Requirements
Description: Government invoice compliance
Types:
  Duplicate: "B2C standard"
  Triplicate: "B2B required"
  Electronic: "Preferred, optional"
Timing: "Issue with delivery"
Storage: "7 years retention"
```

---

## 8. Data Import/Export Rules

### 8.1 Import Validation Rules
```yaml
Rule: IMP-001
Name: Import Data Quality
Description: Minimum data quality standards
Requirements:
  - Required fields: 100% complete
  - Format compliance: 100%
  - Business rule validation: Pass
  - Duplicate checking: Performed
  - Reference integrity: Verified
Rejection: "Any row failure = batch rejection"

Rule: IMP-002
Name: Import Size Limits
Description: Performance and safety limits
Limits:
  File Size: "50MB maximum"
  Row Count: "100,000 records"
  Processing Time: "30 minutes max"
  Batch Size: "1,000 per transaction"
  Memory Usage: "2GB maximum"
Handling: "Split large files before import"
```

### 8.2 Export Security Rules
```yaml
Rule: EXP-001
Name: Export Data Privacy
Description: Sensitive data protection
Masking Required:
  - National ID: "Show last 4 only"
  - Full Address: "District only"
  - Phone: "Show last 4 only"
  - Salary: "Authorized roles only"
  - Credit Card: "Never export"
Approval: "Manager for customer data"

Rule: EXP-002
Name: Export Audit Trail
Description: Export activity tracking
Logging:
  - User ID and timestamp
  - Export parameters
  - Record count
  - File location
  - Access history
Retention: "90 days minimum"
Review: "Monthly security audit"
```

---

## 9. Cross-Module Integration Rules

### 9.1 Data Consistency Rules
```yaml
Rule: INT-001
Name: Referential Integrity
Description: Cross-module data consistency
Enforcement:
  - Cannot delete referenced data
  - Cascade updates carefully
  - Validate before commit
  - Transaction boundaries
  - Rollback on failure
Examples: "Active product in orders"

Rule: INT-002
Name: Data Propagation
Description: Change notification rules
Real-time Updates:
  - Price changes → Orders
  - Zone changes → Delivery
  - Employee status → Access
  - Holiday changes → Schedule
  - Parameter changes → All modules
Method: "Event bus or direct call"
```

### 9.2 Module Dependencies
```yaml
Rule: INT-003
Name: Dependency Management
Description: Module startup order
Sequence:
  1. Data Maintenance (master data)
  2. Customer Management
  3. Order Sales
  4. Dispatch Operations
  5. Invoice Operations
  6. Reports
Validation: "Check dependencies on start"
```

---

## 10. Security and Audit Rules

### 10.1 Change Audit Rules
```yaml
Rule: AUD-001
Name: Comprehensive Audit Trail
Description: Track all data changes
Required Fields:
  - Table and record ID
  - Field changed
  - Old value
  - New value
  - User ID
  - Timestamp
  - IP address
  - Change reason
Retention: "7 years minimum"

Rule: AUD-002
Name: Sensitive Data Access
Description: Track access to sensitive data
Monitored Operations:
  - Salary views/exports
  - Personal data access
  - Financial reports
  - System parameters
  - Bulk exports
Alert: "Unusual patterns to security team"
```

### 10.2 Data Quality Rules
```yaml
Rule: DQ-001
Name: Data Completeness
Description: Required field enforcement
Standards:
  - Core fields: 100% required
  - Contact info: 95% complete
  - Optional fields: 50% target
  - Update frequency: Per type
Monitoring: "Daily quality reports"

Rule: DQ-002
Name: Data Accuracy
Description: Validation and verification
Checks:
  - Format validation: Real-time
  - Business rule: On save
  - Duplicate detection: On create
  - Reference validation: Continuous
  - Periodic review: Monthly
Correction: "Audit trail for fixes"
```

---

## 🚨 Rule Violation Handling

### Severity Levels
1. **Critical**: System prevents action, manager notification
2. **Warning**: User warning, proceed with caution
3. **Info**: Logged for audit, no blocking

### Override Authority
- **Supervisor**: Warning-level rules
- **Manager**: Most business rules
- **General Manager**: Financial and critical rules
- **System Admin**: Technical constraints only

### Violation Tracking
- All violations logged with details
- Monthly violation reports
- Pattern analysis for training
- System improvement recommendations

---

## 📊 Business Rule Metrics

### Monitoring Points
- Rule violation frequency
- Override usage patterns
- Processing time impact
- User satisfaction scores
- Compliance rates

### Review Schedule
- **Monthly**: Violation reports
- **Quarterly**: Rule effectiveness
- **Annually**: Complete rule review
- **As Needed**: Regulation changes

---

## 🔄 Rule Maintenance

### Change Process
1. Request with business justification
2. Impact analysis across modules
3. Approval based on change type
4. Testing in non-production
5. Scheduled deployment
6. User communication
7. Monitor post-change

### Documentation
- All rules versioned
- Change history maintained
- Business reason documented
- Test cases updated
- Training materials revised