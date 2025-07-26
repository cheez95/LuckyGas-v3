# Customer Management Business Rules

## 🏢 Core Business Rules

### 1. Customer Identification Rules

#### 1.1 Unique Identifiers
```yaml
tax_id_rules:
  format: "8 digits"
  validation_algorithm: |
    // Taiwan Tax ID (統一編號) validation
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
  
  uniqueness: "Must be unique across all active customers"
  required_for: ["Business customers", "Government entities"]
  optional_for: ["Individual households"]

customer_code_rules:
  format: "C + 6 digits (e.g., C000001)"
  generation: "Sequential, auto-generated"
  uniqueness: "System-enforced unique"
  modification: "Not allowed after creation"
```

#### 1.2 Phone Number Rules
```yaml
primary_phone:
  required: true
  formats:
    landline: 
      pattern: "0[2-9]-[0-9]{4}-[0-9]{4}"
      examples: ["02-2345-6789", "07-123-4567"]
    mobile:
      pattern: "09[0-9]{2}-[0-9]{3}-[0-9]{3}"
      examples: ["0912-345-678", "0988-123-456"]
  
  validation: "Must be reachable for delivery coordination"
  duplicate_check: "Warning issued but not blocked"
```

### 2. Customer Classification Rules

#### 2.1 Customer Types
```yaml
customer_types:
  "01":
    name: "公司行號"
    english: "Company"
    requirements:
      - "Tax ID mandatory"
      - "Company name required"
      - "Higher default credit limit"
    default_credit_limit: 30000
    
  "02":
    name: "個人住家"
    english: "Household"
    requirements:
      - "Tax ID optional"
      - "Individual name"
    default_credit_limit: 10000
    
  "03":
    name: "餐廳"
    english: "Restaurant"
    requirements:
      - "Business license preferred"
      - "Peak usage patterns"
    default_credit_limit: 50000
    special_handling: "Priority delivery during meal prep times"
    
  "04":
    name: "工廠"
    english: "Factory"
    requirements:
      - "Safety compliance required"
      - "Large volume handling"
    default_credit_limit: 100000
    special_handling: "Bulk delivery capabilities required"
    
  "05":
    name: "機關團體"
    english: "Institution"
    requirements:
      - "Official documentation"
      - "Purchase order process"
    default_credit_limit: 50000
    payment_terms: "Monthly billing only"
```

### 3. Credit Management Rules

#### 3.1 Credit Limit Assignment
```yaml
credit_limit_rules:
  initial_assignment:
    base_rules:
      - "Default by customer type (see above)"
      - "Can be overridden during creation"
      - "Manager approval thresholds apply"
    
  approval_matrix:
    "0-50000": 
      approver: "Any staff"
      documentation: "None required"
    "50001-100000":
      approver: "Manager"
      documentation: "Manager approval code"
    "100001-500000":
      approver: "Senior Manager"
      documentation: "Written approval + risk assessment"
    ">500000":
      approver: "General Manager"
      documentation: "Board approval may be required"
      
  increase_rules:
    conditions:
      - "Payment history > 6 months"
      - "No late payments in last 3 months"
      - "Average monthly volume supports increase"
    automatic_review: "Quarterly"
    
  decrease_triggers:
    - "Payment overdue > 60 days"
    - "Bounced checks"
    - "Bankruptcy filing"
    automatic_action: "Reduce to 50% of current limit"
```

#### 3.2 Credit Hold Rules
```yaml
credit_hold_triggers:
  automatic_hold:
    - condition: "Outstanding balance > credit limit"
      action: "Block new orders"
      notification: "Customer service + Sales manager"
      
    - condition: "Payment overdue > 30 days"
      action: "Warning flag"
      notification: "Accounting department"
      
    - condition: "Payment overdue > 60 days"
      action: "Full hold - no transactions"
      notification: "All departments"
      
    - condition: "3 bounced checks in 12 months"
      action: "Cash only status"
      notification: "Management team"
      
  release_process:
    payment_received:
      - "Automatic release if full payment"
      - "Partial payment requires manager approval"
    documentation:
      - "Payment receipt required"
      - "Release authorization logged"
```

### 4. Address Management Rules

#### 4.1 Address Validation
```yaml
address_rules:
  registration_address:
    required: true
    validation:
      postal_code:
        format: "[0-9]{3,5}"
        lookup: "Must match city/district database"
      components:
        - "City/County required"
        - "District/Township required"
        - "Street address required"
        - "Building/Floor optional"
    
  delivery_addresses:
    multiple_allowed: true
    maximum_count: 10
    validation:
      - "Must be within service area"
      - "GPS coordinates recommended"
      - "Delivery instructions encouraged"
    
  service_area_check:
    zones:
      "A01": "台北市中正區"
      "A02": "台北市大同區"
      "A03": "台北市中山區"
      # ... more zones
    out_of_area:
      action: "Flag for special handling"
      approval: "Logistics manager"
      surcharge: "May apply"
```

#### 4.2 Delivery Preferences
```yaml
delivery_rules:
  time_slots:
    "01": 
      name: "上午 (Morning)"
      hours: "08:00-12:00"
      capacity: "Limited by route"
    "02":
      name: "下午 (Afternoon)"  
      hours: "13:00-17:00"
      capacity: "Limited by route"
    "03":
      name: "不限 (Anytime)"
      hours: "08:00-17:00"
      priority: "Lower"
      
  special_instructions:
    max_length: 500
    common_instructions:
      - "Ring doorbell 3 times"
      - "Leave with security guard"
      - "Call before delivery"
      - "Avoid lunch hours (12-13)"
    
  access_requirements:
    - "Elevator access for high floors"
    - "Truck size limitations"
    - "Special permits for restricted areas"
```

### 5. Customer Lifecycle Rules

#### 5.1 Activation Rules
```yaml
new_customer_activation:
  requirements:
    - "All required fields completed"
    - "Credit check passed (if applicable)"
    - "Service area confirmed"
    - "Initial deposit collected (if required)"
  
  cylinder_deposit:
    "20kg": 1500
    "50kg": 3000
    waiver_conditions:
      - "Corporate customers with guarantee"
      - "Government institutions"
      - "Existing customers with good history"
```

#### 5.2 Deactivation Rules
```yaml
deactivation_types:
  voluntary_closure:
    prerequisites:
      - "No outstanding balance"
      - "All cylinders returned"
      - "Final reading completed"
    process:
      - "Customer request in writing"
      - "Account settlement"
      - "Deposit refund"
    
  involuntary_suspension:
    triggers:
      - "Non-payment > 90 days"
      - "Fraud detection"
      - "Safety violations"
    process:
      - "Management approval required"
      - "Legal notice sent"
      - "Collection process initiated"
    
  blacklist_criteria:
    severe_violations:
      - "Cylinder theft"
      - "Payment fraud"
      - "Safety endangerment"
      - "Repeated NSF checks"
    consequences:
      - "No future service"
      - "Shared with industry (if applicable)"
      - "Legal action possible"
```

### 6. Data Quality Rules

#### 6.1 Duplicate Prevention
```yaml
duplicate_check_rules:
  check_points:
    - "On new customer creation"
    - "On data import"
    - "Periodic batch checks"
    
  matching_criteria:
    exact_match:
      - "Tax ID (if provided)"
      - "Phone number + name"
    
    fuzzy_match:
      - "Similar name + same district"
      - "Same address different format"
      
  resolution:
    exact_match_found:
      action: "Block creation"
      message: "Customer already exists"
      next_step: "Redirect to existing record"
      
    fuzzy_match_found:
      action: "Warning with continue option"
      message: "Possible duplicate found"
      next_step: "Manager review required"
```

#### 6.2 Data Maintenance Rules
```yaml
maintenance_rules:
  regular_updates:
    frequency: "Annual verification"
    method: "Customer contact during delivery"
    fields_to_verify:
      - "Phone numbers"
      - "Delivery address"
      - "Contact person"
      
  data_retention:
    active_customers: "Indefinite"
    inactive_customers: "7 years from last transaction"
    deleted_customers: "Soft delete only"
    
  audit_trail:
    tracked_changes:
      - "Credit limit modifications"
      - "Status changes"
      - "Address updates"
      - "Payment term changes"
    retention: "2 years minimum"
```

### 7. Integration Rules

#### 7.1 Order Integration
```yaml
order_creation_rules:
  customer_requirements:
    - "Status must be active"
    - "No credit hold"
    - "Valid delivery address"
    
  validation_cascade:
    - "Check customer status"
    - "Verify credit available"
    - "Confirm delivery zone serviced"
    - "Check special instructions"
```

#### 7.2 Financial Integration
```yaml
invoice_generation_rules:
  customer_data_required:
    - "Tax ID for business customers"
    - "Current billing address"
    - "Invoice delivery preference"
    
  payment_posting_rules:
    - "Match by customer code"
    - "Update outstanding balance"
    - "Release credit holds if applicable"
    - "Generate receipt"
```

### 8. Reporting Rules

#### 8.1 Customer Analytics
```yaml
kpi_calculations:
  customer_lifetime_value:
    formula: "Total revenue / Months active * 12 * Retention rate"
    
  churn_risk_score:
    factors:
      - "Declining order frequency: 40%"
      - "Late payments: 30%"
      - "Service complaints: 20%"
      - "Competitive activity: 10%"
    thresholds:
      high_risk: "> 70"
      medium_risk: "40-70"
      low_risk: "< 40"
      
  segmentation_rules:
    vip_customers:
      - "Monthly volume > 50 cylinders"
      - "Payment history excellent"
      - "3+ years relationship"
    benefits:
      - "Priority delivery"
      - "Special pricing"
      - "Dedicated service line"
```

## 🚨 Exception Scenarios

### Critical Business Rule Violations

1. **Credit Limit Exceeded**
   - System blocks new orders automatically
   - Notification sent to sales and credit teams
   - Customer contacted within 24 hours

2. **Invalid Tax ID on Business Customer**
   - Cannot save record
   - Must correct or change customer type
   - Manager override not available

3. **Delivery Outside Service Area**
   - Warning displayed
   - Requires logistics approval
   - May incur additional charges

4. **Duplicate Customer Creation Attempt**
   - Hard block on exact Tax ID match
   - Soft warning on phone/name match
   - Audit log entry created

## 📋 Compliance Requirements

### Personal Data Protection
- Customer consent required for data usage
- Right to data deletion (with restrictions)
- Data portability upon request
- Breach notification within 72 hours

### Tax Compliance
- Valid Tax ID for all business customers
- E-invoice capability mandatory
- Monthly reporting to tax authority
- Audit trail maintenance

### Industry Regulations
- Safety compliance documentation
- Cylinder tracking requirements
- Delivery personnel licensing
- Insurance verification

---

These business rules represent the core logic governing customer management in the Lucky Gas system. They must be implemented in the new system to maintain business continuity and compliance.