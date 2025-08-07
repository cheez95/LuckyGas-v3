# Business Logic Clarifications Needed for Lucky Gas Data Migration

**Prepared by**: Mary (Business Analyst)  
**Date**: 2025-01-29  
**Priority**: HIGH - Blocking migration development

## 📋 Overview

This document lists all business logic questions that need clarification from Lucky Gas management before proceeding with data migration. These items are critical for ensuring the migrated system accurately reflects current business operations.

## 🔴 Critical Clarifications (Migration Blockers)

### 1. Customer Status Management
**Current Situation**: Customer records have status fields but no clear lifecycle rules

**Questions**:
- What triggers a customer to become "Inactive"? 
  - [ ] No orders for X days?
  - [ ] Payment overdue > X days?
  - [ ] Manual deactivation only?
  - [ ] Other: ___________

- Can inactive customers place new orders?
  - [ ] Yes, automatically reactivates
  - [ ] Yes, but requires approval
  - [ ] No, must be manually reactivated
  - [ ] Other: ___________

- What happens to customer data after deactivation?
  - [ ] Keep forever
  - [ ] Archive after ___ months
  - [ ] Delete after ___ years
  - [ ] Other: ___________

### 2. Pricing Conflict Resolution
**Current Situation**: Multiple pricing methods exist (定價, 特價, 合約價, 量價)

**Questions**:
- If a customer has both contract price and qualifies for volume discount, which applies?
  - [ ] Always use contract price
  - [ ] Use whichever is lower
  - [ ] Let customer choose
  - [ ] Other: ___________

- Can promotional prices override contract prices?
  - [ ] Never
  - [ ] Yes, if promotion is better
  - [ ] Yes, with customer consent
  - [ ] Manager discretion

- Who can approve selling below cost?
  - [ ] Sales staff (up to __% below cost)
  - [ ] Manager (up to __% below cost)
  - [ ] Director (up to __% below cost)
  - [ ] CEO only
  - [ ] Never allowed

### 3. Credit Management
**Current Situation**: Credit limits exist but enforcement rules unclear

**Questions**:
- What happens when an order exceeds available credit?
  - [ ] Block order completely
  - [ ] Allow with prepayment for excess
  - [ ] Allow with manager approval (up to __% over)
  - [ ] Convert to COD automatically

- Interest charges on overdue accounts:
  - [ ] No interest charged
  - [ ] __% per month after __ days
  - [ ] Fixed penalty of NTD ___
  - [ ] Other: ___________

- Bad debt write-off criteria:
  - [ ] After ___ days overdue
  - [ ] After legal action fails
  - [ ] Amount < NTD ___
  - [ ] Other: ___________

## 🟡 Important Clarifications (Post-Migration Tuning)

### 4. Delivery Operations
**Current Situation**: Delivery slots and preferences captured but capacity rules unknown

**Questions**:
- Maximum cylinders per delivery truck:
  - Small truck: ___ cylinders (or ___ kg total)
  - Medium truck: ___ cylinders (or ___ kg total)
  - Large truck: ___ cylinders (or ___ kg total)

- How to handle route capacity conflicts?
  - [ ] First-come, first-served
  - [ ] Priority by customer type (VIP > Regular)
  - [ ] Priority by order size
  - [ ] Manual dispatcher decision

- Can orders be split across multiple deliveries?
  - [ ] Yes, automatically if exceeds truck capacity
  - [ ] Yes, but requires customer approval
  - [ ] No, must deliver complete order
  - [ ] Other: ___________

### 5. Cylinder Management
**Current Situation**: Cylinder quantities tracked but lifecycle management unclear

**Questions**:
- Cylinder inspection requirements:
  - [ ] Every ___ years
  - [ ] After ___ refills
  - [ ] Based on manufacture date
  - [ ] No systematic tracking

- What happens to "lost" cylinders?
  - [ ] Charge full deposit immediately
  - [ ] Grace period of ___ days
  - [ ] Investigation required
  - [ ] Write off as business loss

- Empty cylinder return credits:
  - [ ] Apply to current order
  - [ ] Apply to next order
  - [ ] Cash refund option
  - [ ] Store credit only

### 6. Equipment Rental
**Current Situation**: Flow meters and smart scales tracked but rental rules unclear

**Questions**:
- Equipment rental fees:
  - Flow meter (50kg): NTD ___/month
  - Flow meter (20kg): NTD ___/month
  - Smart scale: NTD ___/month
  - Auto-switch: NTD ___/month

- Damage/loss responsibility:
  - [ ] Customer pays full replacement cost
  - [ ] Depreciated value based on age
  - [ ] Insurance covers
  - [ ] Case-by-case basis

## 🟢 Nice-to-Have Clarifications (Future Enhancement)

### 7. Seasonal Adjustments
- Peak season months: ___________
- Peak season pricing adjustment: ___%
- Advance booking requirements during peak season?

### 8. Loyalty Programs
- VIP customer criteria:
  - [ ] Monthly volume > ___ cylinders
  - [ ] Annual revenue > NTD ___
  - [ ] Years as customer > ___
  - [ ] Manual designation only

- VIP benefits:
  - [ ] Priority delivery
  - [ ] Discount: ___%
  - [ ] Extended credit terms
  - [ ] Free equipment rental
  - [ ] Other: ___________

### 9. Emergency Procedures
- Emergency delivery surcharge: NTD ___ or ___%
- After-hours delivery availability?
- Weekend delivery policy?
- Holiday delivery policy?

## 📊 Data Mapping Clarifications

### 10. Field Interpretations
Please confirm the meaning of these data fields:

| Field Name | Our Understanding | Correct? | Actual Meaning |
|------------|------------------|----------|----------------|
| 訂閱會員 | Subscription member flag | [ ] Yes [ ] No | _____________ |
| 當送 | Same-day delivery flag | [ ] Yes [ ] No | _____________ |
| 營50 | Commercial 50kg cylinders | [ ] Yes [ ] No | _____________ |
| 好運 | "Good Luck" brand cylinders | [ ] Yes [ ] No | _____________ |
| 器量 | Equipment quantity? | [ ] Yes [ ] No | _____________ |
| 其他瓦斯行 | Competitor gas supplier? | [ ] Yes [ ] No | _____________ |

### 11. Code Mappings
Please provide the meaning of these codes:

**Payment Method Codes**:
- Code 1: ___________
- Code 2: ___________
- Code 3: ___________
- Code 4: ___________

**Pricing Method Codes**:
- Code A: ___________
- Code B: ___________
- Code C: ___________
- Code D: ___________

**Delivery Time Period Codes**:
- 早1: Morning (08:00-12:00)? [ ] Confirm [ ] Different: ___________
- 午2: Afternoon (13:00-17:00)? [ ] Confirm [ ] Different: ___________
- 晚3: Evening (17:00-20:00)? [ ] Confirm [ ] Different: ___________
- 全天0: All day (08:00-20:00)? [ ] Confirm [ ] Different: ___________

## 📝 Additional Information Needed

### 12. Historical Data Handling
- How many years of delivery history should we migrate?
  - [ ] All available data
  - [ ] Last ___ years only
  - [ ] Last ___ months only

- Should we migrate data for inactive customers?
  - [ ] Yes, all customers
  - [ ] Only if active in last ___ years
  - [ ] No, active only

### 13. System Integration
- Any external systems that need customer codes to remain unchanged?
  - [ ] Accounting system
  - [ ] Banking system
  - [ ] Government reporting
  - [ ] Other: ___________

- E-invoice requirements:
  - [ ] All customers
  - [ ] Commercial only
  - [ ] Optional
  - [ ] Other: ___________

## 🚨 Risk Mitigation Questions

### 14. Compliance Requirements
- Any industry regulations for cylinder tracking?
- Safety inspection documentation requirements?
- Government reporting requirements?
- Tax compliance special handling?

### 15. Business Continuity
- Acceptable downtime for migration: ___ hours
- Preferred migration window:
  - [ ] Weekday night (specify hours: _______)
  - [ ] Weekend (specify: _______)
  - [ ] Holiday period
  - [ ] Other: ___________

- Rollback decision criteria:
  - [ ] Any data discrepancy
  - [ ] Discrepancy > ___%
  - [ ] Critical feature failure
  - [ ] Other: ___________

## 📋 Next Steps

1. **Meeting Required**: Schedule clarification session with:
   - Operations Manager (for delivery/inventory rules)
   - Finance Manager (for credit/pricing rules)
   - Sales Manager (for customer management rules)
   - IT Manager (for system integration requirements)

2. **Documentation**: Once clarified, update:
   - Business rules document
   - Migration scripts
   - Validation test cases
   - Training materials

3. **Timeline Impact**: 
   - Current: Cannot proceed with final migration scripts
   - Estimated delay: 2-3 days pending clarifications
   - Risk: Each day of delay may impact go-live date

---

**Contact**: Mary (Business Analyst)  
**Escalation**: Winston (Solution Architect) - for technical implications  
**Deadline**: Need responses by _______ to maintain project timeline