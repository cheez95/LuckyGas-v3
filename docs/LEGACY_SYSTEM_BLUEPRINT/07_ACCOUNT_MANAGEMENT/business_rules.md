# Account Management Business Rules - Lucky Gas Legacy System

## 📋 Overview

This document defines the comprehensive business rules governing the Account Management module. These rules ensure consistent financial operations, regulatory compliance, and effective credit control across all account-related processes in the Lucky Gas system.

## 🎯 Core Principles

### Financial Integrity
- **Accuracy First**: All financial transactions must balance to zero
- **Audit Trail**: Complete documentation required for all changes
- **Segregation**: Duties separated between entry, approval, and posting
- **Consistency**: Same rules applied across all customer types
- **Compliance**: Follow Taiwan GAAP and tax regulations

### Customer Focus
- **Fair Treatment**: Consistent application of credit policies
- **Clear Communication**: Transparent terms and timely notifications
- **Relationship Balance**: Firm but respectful collection practices
- **Service Continuity**: Minimize disruption while managing risk
- **Cultural Sensitivity**: Respect local business customs

## 💳 Credit Management Rules

### New Customer Credit

**Rule CR-001: Initial Credit Assessment**
```yaml
Requirement: All new customers must undergo credit evaluation
Conditions:
  - Complete application required
  - Financial documents mandatory for >NT$100,000
  - Trade references for business accounts
  - Identity verification for individuals
Timeline: 5-7 business days
Exception: COD terms for urgent starts
```

**Rule CR-002: Credit Limit Calculation**
```yaml
Formula: Monthly Volume × Payment Terms ÷ 30 × Risk Factor
Risk Factors:
  Category A: 1.0-1.2
  Category B: 0.8-1.0
  Category C: 0.5-0.8
  Category D: COD only
Minimum: NT$30,000 for business accounts
Maximum: 10% of total AR portfolio
```

**Rule CR-003: Documentation Requirements**
```yaml
Corporate Customers:
  - Business registration (統一編號)
  - Financial statements (2 years minimum)
  - Bank reference letter
  - Authorized signatory list
  
Individual Customers:
  - National ID copy
  - Income proof (last 3 months)
  - Utility bill for address
  - Employment verification
```

### Credit Monitoring

**Rule CR-004: Review Frequency**
```yaml
Mandatory Reviews:
  Annual: All active accounts
  Semi-annual: Category B customers
  Quarterly: Category C customers
  Monthly: Watch list accounts
  
Triggered Reviews:
  - Payment delays >30 days
  - Returned checks
  - Credit limit breach
  - Ownership changes
```

**Rule CR-005: Limit Adjustments**
```yaml
Increase Criteria:
  - 6 months good payment history
  - Utilization >70% consistently
  - No disputes or returns
  - Updated financials provided
  
Decrease Triggers:
  - Payment delays >15 days (2 occurrences)
  - Deteriorating financials
  - Industry downturn
  - Management changes
```

**Rule CR-006: Credit Hold**
```yaml
Automatic Hold:
  - Overdue >30 days
  - Over credit limit >10%
  - NSF check received
  - Bankruptcy filing
  
Release Conditions:
  - Full payment of overdue
  - Within credit limit
  - Management approval
  - New payment terms agreed
```

## 💰 Payment Processing Rules

### Payment Acceptance

**Rule PP-001: Valid Payment Methods**
```yaml
Accepted Methods:
  Bank Transfer: No limit
  Check: Up to credit limit
  Cash: Up to NT$100,000
  Credit Card: Up to NT$50,000
  Post-dated: Maximum 90 days
  
Restrictions:
  - Foreign currency requires approval
  - Third-party payments need verification
  - Post-dated checks require history
```

**Rule PP-002: Payment Validation**
```yaml
Required Validations:
  - Customer account exists
  - Amount is positive
  - Payment date not future (except PDC)
  - No duplicate payment ID
  - Bank account verified
  
Automatic Rejection:
  - Invalid customer code
  - Zero or negative amount
  - Duplicate reference number
  - Blocked payment methods
```

**Rule PP-003: Unidentified Payments**
```yaml
Handling Process:
  Hold Period: 5 business days
  Research: Daily review list
  Escalation: After 5 days to supervisor
  
Resolution Options:
  - Match to customer
  - Return to sender
  - Post to suspense account
  - Write to revenue (after 90 days)
```

### Payment Allocation

**Rule PP-004: Allocation Priority**
```yaml
Standard Order (FIFO):
  1. Oldest invoice first
  2. Within invoice: Principal before charges
  3. Apply to base amount
  4. Then to tax amount
  5. Finally to penalties/interest
  
Override Allowed:
  - Customer specific request
  - Legal requirement
  - Management directive
```

**Rule PP-005: Partial Payments**
```yaml
Allocation Rules:
  <50% of invoice: Hold as partial
  ≥50% of invoice: Apply and track balance
  Multiple invoices: Oldest first
  
Documentation:
  - Record partial payment
  - Note on invoice
  - Update aging accordingly
  - Notify collection team
```

**Rule PP-006: Overpayments**
```yaml
Handling Options:
  Automatic: Hold as credit balance
  Customer Request: Apply to future invoices
  Refund: If requested and >NT$1,000
  
Refund Process:
  - Customer written request
  - Verification of overpayment
  - Approval per authority matrix
  - Process within 10 days
```

### Discounts

**Rule PP-007: Early Payment Discounts**
```yaml
Standard Terms:
  2/10 Net 30: 2% if paid within 10 days
  1/15 Net 45: 1% if paid within 15 days
  
Calculation:
  - From invoice date
  - Calendar days
  - Full payment required
  - Automatic application
  
Exceptions:
  - Disputed invoices excluded
  - Partial payments no discount
  - Service charges excluded
```

**Rule PP-008: Settlement Discounts**
```yaml
Authority Levels:
  Collector: Up to 5%
  Supervisor: Up to 10%
  Manager: Up to 20%
  Director: Up to 30%
  CFO: Above 30%
  
Documentation:
  - Written agreement required
  - Reason documented
  - Approval attached
  - One-time only
```

## 📑 Invoice Management Rules

### Invoice Creation

**Rule IM-001: Invoice Requirements**
```yaml
Mandatory Fields:
  - Customer name and 統一編號
  - Invoice date and number
  - Delivery details
  - Product description
  - Unit price and quantity
  - Tax calculation
  - Payment terms
  
Validation:
  - Delivery confirmed
  - Pricing verified
  - Tax rate correct
  - Terms match customer
```

**Rule IM-002: Tax Calculation**
```yaml
VAT Application:
  Standard Rate: 5%
  Zero Rate: Exports only
  Exempt: Government entities
  
Calculation:
  - Round to nearest dollar
  - Show tax separately
  - Include tax ID numbers
  - Monthly reporting required
```

**Rule IM-003: Credit Notes**
```yaml
Issuance Criteria:
  - Returned goods
  - Pricing errors
  - Quality issues
  - Billing mistakes
  
Approval Required:
  <NT$10,000: Supervisor
  <NT$50,000: Manager
  ≥NT$50,000: Director
  
Timeline: Within 5 days of approval
```

## 🔄 Collection Management Rules

### Collection Timing

**Rule CM-001: Collection Schedule**
```yaml
Day 1-7: Soft reminder (SMS/Email)
Day 8-15: First notice (Formal letter)
Day 16-30: Second notice (Urgent)
Day 31-45: Final notice (Legal warning)
Day 46-60: Pre-legal assessment
Day 61+: Legal action initiated

Exceptions:
  - Disputes pause collection
  - Payment plans reset schedule
  - VIP customers special handling
```

**Rule CM-002: Contact Restrictions**
```yaml
Allowed Hours: 9:00 AM - 8:00 PM
Frequency: Maximum once per day
Methods: Phone, email, SMS, mail, visit
  
Prohibited:
  - Harassment or threats
  - Contact at workplace (unless approved)
  - Third party disclosure
  - Weekend calls (except Saturday AM)
```

**Rule CM-003: Collection Messages**
```yaml
Tone Requirements:
  First Contact: Friendly reminder
  Second Contact: Professional concern
  Third Contact: Firm but respectful
  Final Contact: Legal consequences
  
Content Rules:
  - State amount clearly
  - Reference invoice numbers
  - Provide payment options
  - Include contact information
```

### Payment Arrangements

**Rule CM-004: Payment Plans**
```yaml
Eligibility:
  - First request only
  - Good history (>6 months)
  - Genuine hardship
  - Down payment required (20%)
  
Standard Terms:
  3 months: No interest
  6 months: 1% per month
  12 months: Requires director approval
  
Documentation:
  - Written agreement
  - Signed by both parties
  - Payment schedule clear
  - Default consequences stated
```

**Rule CM-005: Settlement Negotiations**
```yaml
Minimum Settlement:
  0-30 days: 95% minimum
  31-60 days: 90% minimum
  61-90 days: 80% minimum
  91-180 days: 70% minimum
  >180 days: 50% minimum
  
Conditions:
  - Lump sum payment only
  - Within 48 hours
  - Full settlement letter
  - No future credit
```

### Write-offs

**Rule CM-006: Write-off Criteria**
```yaml
Automatic Write-off:
  - Amount <NT$1,000 and >365 days
  - Customer deceased (verified)
  - Company dissolved (verified)
  - Court-ordered discharge
  
Approval Matrix:
  <NT$10,000: Supervisor
  NT$10,000-50,000: Manager
  NT$50,000-100,000: Director
  NT$100,000-500,000: CFO
  >NT$500,000: Board approval
```

**Rule CM-007: Write-off Documentation**
```yaml
Required Documents:
  - Complete collection history
  - All correspondence copies
  - Legal action summary
  - Asset search results
  - Management recommendation
  - Approval documentation
  
Retention: 7 years minimum
```

## 📊 Period Closing Rules

### Closing Schedule

**Rule PC-001: Monthly Close Timeline**
```yaml
Calendar:
  Day 1-3: Final transaction processing
  Day 4: Pre-closing validation
  Day 5: Execute closing
  Day 6: Reports distribution
  
Cutoff: Last day 23:59:59
Extensions: CFO approval only
Lock Period: No backdating after close
```

**Rule PC-002: Closing Checklist**
```yaml
Mandatory Completion:
  ☐ All invoices posted
  ☐ All payments applied
  ☐ Bank reconciliation complete
  ☐ Credit notes processed
  ☐ Disputes documented
  ☐ Accruals recorded
  ☐ Aging analysis run
  ☐ GL reconciliation done
  
Sign-off Required: Finance Manager
```

### Provisions and Accruals

**Rule PC-003: Bad Debt Provision**
```yaml
Standard Rates (Taiwan GAAP):
  Current: 0%
  1-30 days: 1%
  31-60 days: 5%
  61-90 days: 10%
  91-180 days: 50%
  >180 days: 100%
  
Adjustments Allowed:
  - Secured debt: 50% of standard
  - Government: 0% provision
  - Guaranteed: Based on guarantor
  - Under dispute: Case by case
```

**Rule PC-004: Accrual Rules**
```yaml
Required Accruals:
  - Unbilled deliveries
  - Unrecorded receipts
  - Interest on overdue
  - Collection costs
  - Legal fees incurred
  
Documentation:
  - Calculation worksheet
  - Supporting evidence
  - Approval if >NT$50,000
  - Reversal in next period
```

## 🔄 Reconciliation Rules

### Customer Reconciliation

**Rule RC-001: Statement Frequency**
```yaml
Schedule:
  Top 20% customers: Monthly
  Next 30% customers: Quarterly
  Remaining active: Annually
  Inactive: No statement
  By request: Within 5 days
  
Delivery: Email preferred, mail if requested
Response Time: 15 days
Follow-up: After 7 days
```

**Rule RC-002: Dispute Resolution**
```yaml
Investigation Timeline:
  Acknowledgment: 24 hours
  Initial Response: 48 hours
  Resolution Target: 5 business days
  Maximum Time: 30 days
  
Documentation:
  - All communications
  - Evidence gathered
  - Resolution agreement
  - System adjustments
```

### Internal Reconciliation

**Rule RC-003: AR to GL Reconciliation**
```yaml
Frequency:
  Daily: Balance check
  Weekly: Detailed reconciliation
  Monthly: Full reconciliation with analysis
  
Variance Tolerance:
  Daily: NT$1,000
  Monthly: NT$100
  Year-end: Zero tolerance
  
Investigation: All variances immediately
```

**Rule RC-004: Bank Reconciliation**
```yaml
Requirements:
  - Daily for main accounts
  - Weekly for others
  - All items matched
  - Outstanding items tracked
  - Stale items investigated
  
Clearing Rules:
  Checks: 6 months validity
  Transfers: Should clear same day
  Deposits: Next business day
```

## 🔐 Security and Compliance Rules

### Access Control

**Rule SC-001: System Access**
```yaml
Role-Based Access:
  View Only: Customer service, sales
  Data Entry: AR clerks
  Allocation: Senior clerks
  Adjustments: Supervisors
  Write-offs: Managers and above
  
Password: Change every 90 days
Session: Timeout after 30 minutes
Audit: All actions logged
```

**Rule SC-002: Approval Authority**
```yaml
Credit Limits:
  Supervisor: Up to NT$100,000
  Manager: Up to NT$500,000
  Director: Up to NT$1,000,000
  CFO: Up to NT$5,000,000
  Board: Above NT$5,000,000
  
Same limits apply to:
  - Write-offs
  - Adjustments
  - Settlements
  - Refunds
```

### Audit Requirements

**Rule SC-003: Documentation Standards**
```yaml
Requirements:
  - All approvals in writing
  - Changes require reason
  - Before/after values logged
  - User and timestamp captured
  - Reports archived 7 years
  
Review:
  Monthly: Supervisor review
  Quarterly: Internal audit
  Annual: External audit
```

**Rule SC-004: Compliance Monitoring**
```yaml
Regular Reviews:
  - Policy compliance check
  - Approval limit adherence
  - Segregation of duties
  - System access appropriateness
  - Exception report review
  
Violations:
  - Immediate investigation
  - Corrective action required
  - Report to management
  - Disciplinary action if warranted
```

## 📈 Performance Standards

### Service Levels

**Rule PS-001: Processing Times**
```yaml
Target Times:
  Payment entry: <5 minutes
  Credit application: <5 days
  Invoice creation: Same day
  Credit note: <2 days
  Reconciliation response: <48 hours
  
Measurement: Monthly SLA report
Accountability: Department KPIs
```

**Rule PS-002: Quality Metrics**
```yaml
Accuracy Targets:
  Payment posting: >99.5%
  Invoice accuracy: >99%
  Credit decisions: >95%
  Collection promises: >80%
  
Error Handling:
  - Root cause analysis
  - Corrective action plan
  - Training if needed
  - Process improvement
```

### Business Metrics

**Rule PS-003: Key Performance Indicators**
```yaml
Financial KPIs:
  DSO Target: <45 days
  Bad Debt: <0.5% of revenue
  Collection Rate: >98%
  Credit Utilization: 70-80%
  
Operational KPIs:
  Auto-match rate: >90%
  First call resolution: >70%
  Customer satisfaction: >85%
  Dispute rate: <2%
```

**Rule PS-004: Reporting Requirements**
```yaml
Daily Reports:
  - Cash position
  - Overdue summary
  - Collection activities
  - Credit holds
  
Monthly Reports:
  - Aging analysis
  - DSO trending
  - Bad debt provision
  - Write-off summary
  - Performance metrics
  
Distribution: Management by day 5
```

## 🚨 Exception Handling

### Override Authority

**Rule EH-001: System Overrides**
```yaml
Allowed Overrides:
  - Credit limit temporary increase
  - Payment term extension
  - Discount approval
  - Hold release
  
Requirements:
  - Business justification
  - Appropriate approval
  - Time limitation
  - Audit trail
  
Review: Monthly exception report
```

**Rule EH-002: Emergency Procedures**
```yaml
Situations:
  - System failure
  - Natural disaster
  - Key person absence
  - Urgent customer need
  
Authority:
  - Duty manager decision
  - Document when possible
  - Regularize within 24 hours
  - Report to management
```

## 📝 Change Management

### Rule Updates

**Rule CH-001: Rule Modification**
```yaml
Process:
  1. Change request submitted
  2. Impact analysis performed
  3. Stakeholder consultation
  4. Management approval
  5. System update
  6. User notification
  7. Training if required
  
Implementation: Start of month only
Notice: 2 weeks minimum
```

**Rule CH-002: Annual Review**
```yaml
Scope:
  - All rules effectiveness
  - Regulatory changes
  - Business needs
  - System capabilities
  - Industry practices
  
Participants:
  - Finance management
  - Operations team
  - Internal audit
  - External advisors
  
Output: Updated rule book
```

## 🔚 Summary

These business rules ensure consistent, compliant, and efficient operation of the Account Management module. Regular review and updates maintain their relevance and effectiveness in supporting Lucky Gas's financial operations and customer relationships.