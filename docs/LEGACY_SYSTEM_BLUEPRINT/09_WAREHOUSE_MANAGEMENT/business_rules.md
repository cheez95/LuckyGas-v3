# Warehouse Management Business Rules - Lucky Gas Legacy System

## 📋 Overview

This document defines the comprehensive business rules governing all warehouse operations for Lucky Gas. These rules ensure safety compliance, operational efficiency, inventory accuracy, and regulatory adherence across all warehouse facilities.

## 🏢 Warehouse Operations Rules

### Operating Hours and Shifts

**Standard Operations**
- Primary Shift: 07:00 - 15:30 (Monday - Friday)
- Secondary Shift: 15:30 - 24:00 (Monday - Friday)
- Weekend Shift: 08:00 - 16:00 (Saturday only)
- Emergency Operations: 24/7 on-call support
- Holiday Schedule: Published 30 days in advance

**Receiving Windows**
- Standard Receiving: 08:00 - 16:00 (appointments required)
- Express Receiving: 08:00 - 12:00 (small deliveries <10 cylinders)
- No Receiving: 12:00 - 13:00 (lunch break)
- After-Hours: Emergency only with manager approval
- ASN Required: 24 hours advance for deliveries >50 cylinders

### Facility Access Control

**Authorization Levels**
1. **Level 1 - General Access**: Office areas, break rooms
2. **Level 2 - Warehouse Floor**: Certified operators only
3. **Level 3 - Hazmat Zones**: Special certification required
4. **Level 4 - Management Areas**: Supervisors and above
5. **Level 5 - Restricted**: Security and executives only

**Visitor Policies**
- All visitors must sign in and wear badges
- Safety briefing mandatory before warehouse entry
- PPE required for all warehouse areas
- Escort required at all times
- Photography prohibited without permission

## 📦 Receiving Management Rules

### Supplier Requirements

**Documentation Standards**
- ASN submission: Minimum 24 hours advance
- Delivery documents: Must match PO exactly
- Certificates: Original copies required
- Packing lists: Detailed with serial numbers
- Safety documentation: MSDS for all products

**Quality Thresholds**
- New suppliers: 100% inspection mandatory
- Certified suppliers: Minimum 2.5% AQL sampling
- Problem suppliers: Enhanced inspection (>10%)
- Medical gas suppliers: 100% inspection always
- Quality failure rate: <2% to maintain certification

### Receiving Process Rules

**Verification Requirements**
1. **Quantity Match**: ±2% tolerance acceptable
2. **Serial Numbers**: 100% capture and validation
3. **Visual Inspection**: All cylinders checked
4. **Documentation**: Complete before system entry
5. **Discrepancies**: Reported within 2 hours

**Rejection Criteria**
- Wrong product delivered
- Quantity variance >2%
- Missing or invalid certificates
- Visible damage or defects
- Expired products

## 🏪 Storage Management Rules

### Location Assignment Logic

**Storage Hierarchy**
1. **Zone A - High Velocity**: A-items, daily picks
2. **Zone B - Medium Velocity**: B-items, weekly picks
3. **Zone C - Low Velocity**: C-items, monthly picks
4. **Zone H - Hazmat**: Segregated dangerous goods
5. **Zone Q - Quarantine**: Failed QC or returns

**Capacity Constraints**
- Maximum weight per location: As per rack specifications
- Maximum cylinders per location: Based on size
- Stacking limits: 2 levels for large cylinders
- Aisle clearance: Minimum 4 feet maintained
- Emergency access: Clear paths to all exits

### Slotting Optimization Rules

**ABC Classification**
- **A-Items**: 80% of movements, 20% of SKUs
- **B-Items**: 15% of movements, 30% of SKUs  
- **C-Items**: 5% of movements, 50% of SKUs
- Review frequency: Monthly for A, Quarterly for B/C
- Reslotting trigger: >15% efficiency improvement

**Product Segregation**
- Medical gases: Separate clean room area
- Flammable gases: Designated hazmat zone
- Inert gases: General storage allowed
- Empty cylinders: Separate return area
- Customer-owned: Dedicated storage section

## 📊 Inventory Control Rules

### Stock Level Management

**Minimum/Maximum Levels**
- Safety stock: 2 weeks average demand
- Maximum stock: 6 weeks average demand
- Reorder point: 3 weeks average demand
- Emergency stock: 10% of safety stock
- Seasonal adjustment: ±30% for known patterns

**FIFO/FEFO Enforcement**
1. **FIFO Default**: All non-dated products
2. **FEFO Required**: Products with expiry dates
3. **Override Authority**: Supervisor approval only
4. **Exception Logging**: All overrides documented
5. **Customer Specific**: May request specific lots

### Inventory Accuracy Standards

**Accuracy Targets**
- Location accuracy: >99.5%
- Quantity accuracy: >99.9%
- Serial number accuracy: 100%
- Value accuracy: >99.95%
- Audit frequency: Based on ABC classification

**Adjustment Authorities**
- <$100: Warehouse operator
- $100-$1,000: Warehouse supervisor
- $1,000-$5,000: Warehouse manager
- $5,000-$10,000: Operations director
- >$10,000: CFO approval required

## 📤 Order Fulfillment Rules

### Picking Process Standards

**Pick Accuracy Requirements**
- Target accuracy: >99.5%
- Error tolerance: <0.5%
- Verification method: Scan confirmation
- Quality check: Random 5% audit
- Error tracking: By operator and product

**Picking Priorities**
1. **Emergency Orders**: Immediate dispatch
2. **Medical Facilities**: Same-day delivery
3. **Scheduled Deliveries**: Per routing plan
4. **Standard Orders**: FIFO sequence
5. **Will-Call**: When customer arrives

### Allocation Logic

**Stock Allocation Rules**
- Customer orders: First priority
- Internal transfers: Second priority
- Stock rotation: Third priority
- Reserved stock: Customer specific only
- Substitution: Requires customer approval

**Backorder Management**
- Notification: Within 2 hours of identification
- Alternative offering: Required for all backorders
- Partial shipment: Customer approval needed
- Priority queue: Based on order date/time
- Expedite options: Offered to affected customers

## 🔍 Quality Control Rules

### Inspection Requirements

**Mandatory Inspection Points**
1. **Receipt**: All new cylinders
2. **Periodic**: Based on age and usage
3. **Return**: All customer returns
4. **Incident**: Any damaged cylinders
5. **Pre-delivery**: Medical gas cylinders

**Pass/Fail Criteria**
- Critical defects: Zero tolerance
- Major defects: Maximum 1 per cylinder
- Minor defects: Maximum 3 per cylinder
- Documentation: Must be 100% complete
- Certification: All dates must be current

### Quarantine Management

**Quarantine Triggers**
- Failed quality inspection
- Expired certifications
- Customer complaints
- Damage reports
- Recall notices

**Quarantine Procedures**
1. Immediate physical segregation
2. Red tag identification
3. System status update
4. Investigation initiation
5. Disposition within 30 days

## ⚠️ Safety and Compliance Rules

### Personal Protective Equipment

**Required PPE by Area**
- **General Warehouse**: Safety shoes, visibility vest
- **Cylinder Handling**: + Gloves, back support
- **Hazmat Zone**: + Face shield, special gloves
- **Forklift Operation**: + Hard hat
- **Quality Testing**: + Safety glasses, hearing protection

**PPE Compliance**
- 100% enforcement policy
- Daily inspection required
- Replacement available on-site
- Visitor PPE provided
- Violation = Immediate removal from area

### Hazardous Material Handling

**Segregation Requirements**
- Flammable gases: Separate ventilated area
- Oxidizing gases: Away from flammables
- Toxic gases: Locked cage access
- Inert gases: General storage OK
- Mixed loads: Prohibited

**Handling Restrictions**
1. Certified operators only
2. Two-person rule for certain products
3. Special equipment required
4. Speed limits enforced
5. Documentation for all movements

## 🚛 Equipment Operation Rules

### Forklift Operations

**Operator Requirements**
- Current certification mandatory
- Annual recertification
- Daily equipment inspection
- Speed limit: 5 mph in warehouse
- Load limits strictly enforced

**Maintenance Standards**
- Daily visual inspection
- Weekly detailed check
- Monthly professional service
- Annual certification
- Immediate repair for safety items

### Material Handling Equipment

**Usage Guidelines**
- Equipment matched to load weight
- Inspection before each use
- Defective equipment tagged out
- Proper storage when not in use
- Training required for all equipment

**Load Restrictions**
- Single cylinder: Hand truck OK
- 2-5 cylinders: Pallet jack required
- >5 cylinders: Forklift required
- Hazmat: Special equipment only
- Mixed loads: Heaviest item rules apply

## 📈 Performance Standards

### Productivity Metrics

**Operational Targets**
- Receiving: 30 cylinders/hour/person
- Put-away: 40 locations/hour/person
- Picking: 60 items/hour/person
- Loading: 50 cylinders/hour/person
- Cycle counting: 100 locations/hour/person

**Quality Metrics**
- Receiving accuracy: >99%
- Put-away accuracy: >99.5%
- Picking accuracy: >99.5%
- Inventory accuracy: >99.9%
- Damage rate: <0.1%

### Cost Control Measures

**Expense Management**
- Overtime: Requires daily approval
- Equipment rental: Manager approval
- Supplies: Monthly budget limits
- Repairs: Competitive quotes required
- Energy usage: Monitored and optimized

**Loss Prevention**
1. Cycle counting program
2. Security camera coverage
3. Access control systems
4. Inventory reconciliation
5. Incident investigation

## 🔄 Continuous Improvement

### Process Enhancement

**Improvement Requirements**
- Monthly performance review
- Quarterly process audit
- Annual efficiency study
- Employee suggestion program
- Best practice implementation

**Change Management**
- Documented procedures required
- Training before implementation
- Pilot testing for major changes
- Performance tracking mandatory
- Rollback plan required

### Training and Development

**Required Training**
1. New employee orientation: 40 hours
2. Annual safety refresher: 8 hours
3. Equipment certification: As needed
4. Hazmat training: 24 hours initial
5. Quality standards: 4 hours quarterly

**Skill Development**
- Cross-training encouraged
- Advancement paths defined
- External training supported
- Certification bonuses available
- Performance-based progression

## 📝 Documentation Requirements

### Record Retention

**Retention Periods**
- Receiving documents: 7 years
- Quality records: 10 years
- Training records: 5 years past employment
- Incident reports: 10 years
- Inventory adjustments: 7 years

**Documentation Standards**
- Electronic preferred over paper
- Signatures required on key documents
- Timestamps mandatory
- Change tracking enabled
- Backup procedures defined

### Reporting Requirements

**Daily Reports**
- Receiving summary
- Inventory movements
- Quality exceptions
- Safety incidents
- Equipment status

**Monthly Reports**
- Performance metrics
- Cost analysis
- Quality trends
- Safety statistics
- Improvement initiatives

## 🚨 Exception Handling

### Emergency Procedures

**Emergency Response**
1. Life safety first priority
2. Evacuation routes posted
3. Emergency contacts visible
4. Incident command structure
5. Recovery procedures defined

**Business Continuity**
- Backup systems identified
- Manual procedures documented
- Key personnel on-call
- Customer notification process
- Recovery time objectives set

### Escalation Matrix

**Issue Escalation**
- **Level 1**: Operator → Team Lead (15 minutes)
- **Level 2**: Team Lead → Supervisor (30 minutes)
- **Level 3**: Supervisor → Manager (1 hour)
- **Level 4**: Manager → Director (2 hours)
- **Level 5**: Director → Executive (4 hours)

**Resolution Requirements**
- All issues logged in system
- Root cause analysis required
- Corrective actions documented
- Prevention measures implemented
- Follow-up verification completed