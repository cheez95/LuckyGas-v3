# Order Sales Business Rules (訂單銷售業務規則)

**Module**: Order Sales  
**Document Version**: 1.0  
**Last Updated**: 2024-01-25  
**Business Critical**: ⭐⭐⭐⭐⭐

## 📋 Overview

This document defines all business rules, validations, and constraints for the Order Sales module. These rules ensure data integrity, business compliance, and operational efficiency while maintaining flexibility for Taiwan's business environment.

## 🎯 Core Business Rules

### BR-001: Order Creation Rules

#### BR-001.1: Customer Eligibility
```javascript
Rule: Customer Must Be Active
IF customer.status != 'ACTIVE' THEN
    REJECT order with message "客戶帳戶非有效狀態"
END IF

Exceptions:
- VIP customers can override with manager approval
- Government accounts exempt from status check
```

#### BR-001.2: Minimum Order Requirements
```javascript
Rule: Minimum Order Value
IF order.total_amount < system.minimum_order_value THEN
    IF customer.type == 'VIP' OR customer.type == 'CORPORATE' THEN
        ALLOW with warning
    ELSE
        REJECT with message "訂單金額低於最低要求 NT$ {minimum}"
    END IF
END IF

Current Values:
- Residential: NT$ 800
- Commercial: NT$ 2,000
- Industrial: NT$ 5,000
```

#### BR-001.3: Product Availability
```javascript
Rule: Stock Availability Check
FOR each order_line IN order.lines DO
    IF product.track_inventory == TRUE THEN
        IF product.available_quantity < order_line.quantity THEN
            IF customer.priority >= HIGH THEN
                RESERVE from future stock
            ELSE
                SUGGEST alternative or partial fulfillment
            END IF
        END IF
    END IF
END FOR
```

#### BR-001.4: Delivery Scheduling
```javascript
Rule: Delivery Time Constraints
// Same day delivery cutoff
IF order.delivery_date == TODAY THEN
    IF current_time > '14:00' THEN
        SET order.delivery_date = NEXT_BUSINESS_DAY
        NOTIFY customer of change
    END IF
END IF

// Advance booking limit
IF order.delivery_date > TODAY + 30 DAYS THEN
    REQUIRE deposit of 30%
END IF

// Holiday handling
IF order.delivery_date IN holiday_calendar THEN
    SUGGEST next available date
END IF
```

### BR-002: Credit Management Rules

#### BR-002.1: Credit Limit Validation
```javascript
Rule: Available Credit Check
available_credit = customer.credit_limit - customer.credit_used - customer.pending_orders

IF order.payment_method == 'MONTHLY' THEN
    IF order.final_amount > available_credit THEN
        OPTIONS:
        1. Request prepayment for excess
        2. Get manager override (up to 50% over limit)
        3. Split order into multiple parts
        4. Reduce order quantity
    END IF
END IF

Special Cases:
- First-time customers: Prepayment required
- Overdue > 60 days: Cash only
- Bounced check history: Restricted credit
```

#### BR-002.2: Payment Terms Assignment
```javascript
Rule: Payment Terms by Customer Type
CASE customer.type:
    'RESIDENTIAL':
        terms = 'COD' // Cash on delivery
        discount = 0%
    'COMMERCIAL':
        terms = 'NET30'
        discount = 2% if paid within 10 days
    'CORPORATE':
        terms = 'NET45'
        discount = 3% if paid within 15 days
    'GOVERNMENT':
        terms = 'NET90'
        discount = 0% // Government pricing
END CASE

Override Authority:
- Sales Manager: Can extend terms by 15 days
- Director: Can extend terms by 30 days
- CEO: Unlimited
```

### BR-003: Pricing & Discount Rules

#### BR-003.1: Base Pricing Structure
```javascript
Rule: Price Determination Hierarchy
price = COALESCE(
    customer.contract_price,      // 1. Contract price (highest priority)
    customer.special_price,        // 2. Customer-specific price
    product.promotional_price,     // 3. Active promotion
    volume_discount_price,         // 4. Volume-based price
    product.standard_price        // 5. Standard list price
)

// Volume discount tiers
IF order_line.quantity >= 50 THEN discount = 5%
ELSE IF order_line.quantity >= 20 THEN discount = 3%
ELSE IF order_line.quantity >= 10 THEN discount = 2%
```

#### BR-003.2: Promotional Pricing
```javascript
Rule: Promotion Application
IF promotion.is_active AND TODAY BETWEEN promotion.start_date AND promotion.end_date THEN
    IF customer IN promotion.eligible_customers OR promotion.eligible_customers == 'ALL' THEN
        IF order.total_amount >= promotion.minimum_order THEN
            APPLY promotion.discount_percent OR promotion.fixed_discount
        END IF
    END IF
END IF

Restrictions:
- Cannot combine multiple promotions
- Contract prices override promotions
- Promotions don't apply to delivery fees
```

#### BR-003.3: Delivery Charge Calculation
```javascript
Rule: Distance-Based Delivery Fees
base_fee = GET_ZONE_FEE(delivery.postal_code)

// Quantity multiplier
IF total_cylinders > 10 THEN
    delivery_fee = base_fee * 1.5
ELSE IF total_cylinders > 5 THEN
    delivery_fee = base_fee * 1.2
ELSE
    delivery_fee = base_fee
END IF

// Time-based surcharge
IF delivery.time_slot == 'URGENT' THEN
    delivery_fee = delivery_fee * 1.5
ELSE IF delivery.time_slot == 'EVENING' THEN
    delivery_fee = delivery_fee * 1.3
END IF

// Free delivery conditions
IF customer.type == 'VIP' AND order.total_amount > 5000 THEN
    delivery_fee = 0
END IF
```

### BR-004: Order Modification Rules

#### BR-004.1: Status-Based Modifications
```javascript
Rule: Modification Permissions by Status
CASE order.status:
    'DRAFT':
        ALLOW all modifications
        
    'CONFIRMED':
        ALLOW:
        - Delivery date/time changes
        - Add products (with credit check)
        - Reduce quantities
        - Payment method change
        DENY:
        - Price modifications (without manager approval)
        - Customer change
        
    'DISPATCHED':
        ALLOW with supervisor approval:
        - Emergency cancellation
        - Delivery redirect
        DENY all other changes
        
    'IN_DELIVERY':
        DENY all modifications
        Create new order for changes
        
    'DELIVERED':
        DENY all modifications
        Handle through return process
END CASE
```

#### BR-004.2: Modification Audit Requirements
```javascript
Rule: Change Documentation
FOR each modification DO
    RECORD:
    - Original value
    - New value
    - Modification reason (required)
    - User ID and timestamp
    - Customer confirmation method
    - Manager approval (if required)
    
    IF modification.type == 'PRICE_CHANGE' THEN
        REQUIRE manager_approval
        DOCUMENT pricing_exception_reason
    END IF
END FOR
```

### BR-005: Order Cancellation Rules

#### BR-005.1: Cancellation Policy
```javascript
Rule: Cancellation Charges
CASE order.status:
    'DRAFT':
        charge = 0
        
    'CONFIRMED':
        IF hours_until_delivery > 24 THEN
            charge = 0
        ELSE IF hours_until_delivery > 4 THEN
            charge = delivery_fee * 0.5
        ELSE
            charge = delivery_fee
        END IF
        
    'DISPATCHED':
        IF time_since_dispatch < 30 MINUTES THEN
            charge = delivery_fee
        ELSE
            charge = delivery_fee + (order.total * 0.1)
        END IF
        
    'IN_DELIVERY':
        charge = delivery_fee + (order.total * 0.15)
        REQUIRE manager approval
        
    'DELIVERED':
        NOT cancellable
        Use return process
END CASE

// Waive charges for
IF cancellation.reason IN ('PRODUCT_DEFECT', 'COMPANY_ERROR', 'EMERGENCY') THEN
    charge = 0
END IF
```

### BR-006: Delivery Rules

#### BR-006.1: Service Area Validation
```javascript
Rule: Delivery Zone Check
zone = GET_DELIVERY_ZONE(address.postal_code)

CASE zone:
    'PRIMARY':
        surcharge = 0
        delivery_days = [MON-SAT]
        
    'SECONDARY':
        surcharge = 100
        delivery_days = [MON-FRI]
        
    'REMOTE':
        surcharge = 300
        delivery_days = [TUE, THU]
        minimum_order = 2000
        
    'OUTSIDE':
        IF customer.type == 'VIP' THEN
            REQUIRE special_approval
            surcharge = negotiate
        ELSE
            REJECT order
        END IF
END CASE
```

#### BR-006.2: Time Slot Management
```javascript
Rule: Delivery Capacity
max_deliveries_per_slot = {
    'MORNING': 50,
    'AFTERNOON': 60,
    'EVENING': 30,
    'URGENT': 10
}

IF COUNT(orders WHERE delivery_date = requested_date 
    AND time_slot = requested_slot) >= max_deliveries_per_slot THEN
    SUGGEST alternative slots
END IF

// Driver assignment
IF order.total_cylinders > 20 THEN
    REQUIRE truck (not motorcycle)
END IF
```

### BR-007: Inventory Management Rules

#### BR-007.1: Stock Reservation
```javascript
Rule: Inventory Allocation
WHEN order.status changes to 'CONFIRMED' THEN
    FOR each line IN order.lines DO
        product.reserved_quantity += line.quantity
        product.available_quantity -= line.quantity
    END FOR
END WHEN

WHEN order.status changes to 'CANCELLED' THEN
    FOR each line IN order.lines DO
        product.reserved_quantity -= line.quantity
        product.available_quantity += line.quantity
    END FOR
END WHEN
```

#### BR-007.2: Cylinder Tracking
```javascript
Rule: Cylinder Exchange Validation
IF product.requires_empty_return THEN
    IF customer.cylinders_out > 0 THEN
        expected_returns = MIN(order.quantity, customer.cylinders_out)
    ELSE
        REQUIRE deposit per cylinder
        deposit_amount = cylinder.size * deposit_rate
    END IF
END IF

// Quality check on returns
IF returned_cylinder.condition IN ('DAMAGED', 'EXPIRED') THEN
    CHARGE cylinder_replacement_fee
    LOG safety_incident
END IF
```

### BR-008: Financial Rules

#### BR-008.1: Tax Calculation
```javascript
Rule: VAT Application
// Taiwan VAT rate
VAT_RATE = 0.05

// B2B transactions
IF customer.has_tax_id THEN
    tax_amount = order.subtotal * VAT_RATE
    invoice_type = 'TRIPLICATE' // 三聯式發票
ELSE
    tax_amount = 0 // Tax included in price
    invoice_type = 'DUPLICATE' // 二聯式發票
END IF

// Tax exemptions
IF customer.type == 'DIPLOMATIC' THEN
    tax_amount = 0
    REQUIRE exemption_certificate
END IF
```

#### BR-008.2: Invoice Generation
```javascript
Rule: e-Invoice Requirements
// Government mandate for e-invoices
IF order.status == 'DELIVERED' AND payment.status == 'COLLECTED' THEN
    GENERATE e_invoice WITH:
    - Uniform Invoice Number (發票號碼)
    - Period (期別): Current bi-monthly period
    - Seller Tax ID: 12345678
    - Buyer Tax ID: If provided
    - Carrier Type: Mobile/Natural Person/None
    
    TRANSMIT to government platform within 48 hours
END IF
```

### BR-009: Data Quality Rules

#### BR-009.1: Address Validation
```javascript
Rule: Taiwan Address Format
VALIDATE address WITH:
- Postal code: 3 or 5 digits
- City/County: Must be in valid list
- District: Must match postal code
- Street: Traditional Chinese characters
- Building/Floor/Room: Optional but specific format

IF address.is_rural THEN
    ALLOW descriptive directions
    REQUIRE landmark or GPS coordinates
END IF
```

#### BR-009.2: Phone Number Validation
```javascript
Rule: Taiwan Phone Format
// Mobile
IF phone MATCHES '^09[0-9]{8}$' THEN
    valid_mobile = TRUE
// Landline with area code
ELSE IF phone MATCHES '^0[2-9]-?[0-9]{4}-?[0-9]{4}$' THEN
    valid_landline = TRUE
ELSE
    REJECT with message "請輸入有效的台灣電話號碼"
END IF

// Require at least one valid contact
IF NOT (valid_mobile OR valid_landline) THEN
    BLOCK order creation
END IF
```

### BR-010: Compliance Rules

#### BR-010.1: Safety Regulations
```javascript
Rule: Gas Safety Compliance
// Maximum cylinders per household per month
IF customer.type == 'RESIDENTIAL' THEN
    monthly_limit = 4 cylinders
    
    IF monthly_total + order.quantity > monthly_limit THEN
        REQUIRE safety_declaration
        FLAG for inspection
    END IF
END IF

// Expired cylinder handling
IF cylinder.expiry_date < TODAY THEN
    PROHIBIT refill
    REQUIRE replacement
    NOTIFY safety_department
END IF
```

#### BR-010.2: Environmental Compliance
```javascript
Rule: Cylinder Disposal
IF cylinder.status == 'UNREPAIRABLE' THEN
    FOLLOW disposal_protocol:
    1. Ensure completely empty
    2. Remove valve
    3. Mark as scrap
    4. Send to certified recycler
    5. Maintain disposal records for 5 years
END IF
```

## 🌏 Taiwan-Specific Business Rules

### TW-001: Holiday Handling
```javascript
Rule: Taiwan Holiday Delivery
holidays = [
    'LUNAR_NEW_YEAR',    // 7-10 days
    'TOMB_SWEEPING',     // 4 days
    'DRAGON_BOAT',       // 3 days
    'MID_AUTUMN',        // 3 days
    'DOUBLE_TEN'         // 1 day
]

IF delivery_date IN holidays THEN
    IF holiday == 'LUNAR_NEW_YEAR' THEN
        // Pre-holiday rush
        IF days_before_holiday <= 7 THEN
            APPLY surge_pricing(1.2)
            EXTEND delivery_hours
        END IF
    END IF
    
    SUGGEST pre or post holiday delivery
END IF
```

### TW-002: Lucky Number Preferences
```javascript
Rule: Auspicious Number Handling
// Customer preferences
IF customer.prefers_lucky_numbers THEN
    AVOID order_total ending in '4' // 四 sounds like 死
    PREFER order_total ending in '8' // 八 sounds like 發
    
    IF total ENDS WITH '4' THEN
        SUGGEST add small item or round discount
    END IF
END IF
```

### TW-003: Business Gift Orders
```javascript
Rule: Corporate Gift Protocol
IF order.is_gift AND order.gift_recipient.is_business THEN
    REQUIRE:
    - Formal recipient title
    - Company chop authorization
    - Gift message in traditional Chinese
    - Red envelope packaging option
    - Auspicious delivery date
    
    PROHIBIT:
    - White packaging (funeral association)
    - Clock-related gifts (送鐘 = 送終)
    - Quantities of 4
END IF
```

## 📊 Rule Performance Metrics

| Rule Category | Violations/Month | Impact | Action Threshold |
|---------------|------------------|---------|------------------|
| Credit Limits | 45 | High | > 50 |
| Delivery Rules | 23 | Medium | > 30 |
| Pricing Rules | 12 | High | > 15 |
| Data Quality | 156 | Low | > 200 |
| Compliance | 2 | Critical | > 5 |

## 🔧 Rule Configuration

### Dynamic Parameters
```yaml
# Configurable without code changes
minimum_order_values:
  residential: 800
  commercial: 2000
  industrial: 5000

delivery_cutoff_times:
  same_day: "14:00"
  next_day: "18:00"
  
credit_limit_defaults:
  new_customer: 5000
  regular: 30000
  corporate: 100000
  
surge_pricing_multipliers:
  typhoon: 1.5
  holiday: 1.2
  evening: 1.3
```

## 📝 Rule Change Management

### Change Approval Matrix
| Rule Type | Business Impact | Approver | Testing Required |
|-----------|----------------|----------|------------------|
| Pricing | High | CEO | Full regression |
| Credit | High | CFO | Financial testing |
| Delivery | Medium | Operations Manager | Route testing |
| Validation | Low | IT Manager | Unit tests |

### Version Control
- All rule changes tracked in system
- Effective date management
- Grandfather clause handling
- Rollback procedures

---

**Note**: These business rules are living documentation and must be updated whenever business processes change. Regular reviews ensure alignment with business objectives and regulatory requirements.