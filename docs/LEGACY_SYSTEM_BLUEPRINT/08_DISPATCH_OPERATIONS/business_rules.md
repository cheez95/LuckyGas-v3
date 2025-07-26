# Dispatch Operations Business Rules - Lucky Gas Legacy System

## 📋 Overview

This document defines the comprehensive business rules governing the Dispatch Operations module. These rules ensure safe, efficient, and compliant delivery operations while maintaining high service standards and optimizing resource utilization across Lucky Gas's distribution network.

## 🎯 Core Principles

### Operational Excellence
- **Safety First**: No compromise on safety standards
- **Service Quality**: On-time delivery with professional service
- **Cost Efficiency**: Optimize resources without sacrificing quality
- **Regulatory Compliance**: Strict adherence to all regulations
- **Continuous Improvement**: Data-driven optimization

### Customer Focus
- **Reliability**: Consistent and predictable service
- **Communication**: Proactive updates and transparency
- **Flexibility**: Accommodate reasonable requests
- **Professionalism**: Courteous and knowledgeable drivers
- **Responsiveness**: Quick resolution of issues

## 🚛 Vehicle Management Rules

### Vehicle Assignment

**Rule VM-001: Vehicle-Route Matching**
```yaml
Requirements:
  - Vehicle capacity ≥ Route demand + 10% buffer
  - Vehicle type matches access requirements
  - Valid inspection and insurance
  - GPS tracking functional
  - Safety equipment complete

Priority Order:
  1. Exact capacity match
  2. Fuel efficiency
  3. Maintenance schedule
  4. Driver familiarity
  5. Vehicle age
```

**Rule VM-002: Vehicle Capacity Limits**
```yaml
Load Limits:
  Motorcycle:
    - Maximum: 6 cylinders (20kg each)
    - Volume: 0.5 cubic meters
    - Weight: 120kg total
    
  Van:
    - Maximum: 30 cylinders
    - Volume: 5 cubic meters
    - Weight: 1,500kg
    
  3.5T Truck:
    - Maximum: 80 cylinders
    - Volume: 15 cubic meters
    - Weight: 3,000kg
    
  5T+ Truck:
    - Maximum: 150 cylinders
    - Volume: 25 cubic meters
    - Weight: 5,000kg

Safety Buffer: 5% under maximum always
```

**Rule VM-003: Vehicle Maintenance**
```yaml
Scheduled Maintenance:
  Daily Checks:
    - Tire pressure
    - Fluid levels
    - Lights and signals
    - Safety equipment
    - GPS device
    
  Weekly Inspection:
    - Brake system
    - Load securing equipment
    - Communication devices
    - First aid kit
    
  Monthly Service:
    - Oil change (per schedule)
    - Filter replacement
    - Comprehensive inspection
    - Emissions check
    
Breakdown Protocol:
  - Immediate driver safety
  - Dispatch notification
  - Customer communication
  - Replacement vehicle
  - Incident documentation
```

## 👨‍✈️ Driver Management Rules

### Driver Assignment

**Rule DM-001: License Requirements**
```yaml
Vehicle Requirements:
  Motorcycle:
    - Regular motorcycle license
    - 1 year experience minimum
    
  Van/Light Truck:
    - Commercial license (職業小型車)
    - 2 years experience
    
  Medium Truck (3.5T):
    - Commercial truck license (職業大貨車)
    - 3 years experience
    - Safety certification
    
  Heavy Truck (5T+):
    - Professional truck license
    - 5 years experience
    - Hazmat certification
    - Advanced safety training
```

**Rule DM-002: Work Hour Regulations**
```yaml
Daily Limits:
  Driving Time: Maximum 9 hours
  Total Work: Maximum 12 hours
  Continuous Driving: Maximum 4 hours
  
Break Requirements:
  After 4 hours: 30 minutes minimum
  Lunch Break: 60 minutes (11:30-13:30)
  Between Shifts: 8 hours minimum
  
Weekly Limits:
  Regular Hours: 48 hours
  With Overtime: 60 hours maximum
  Days Off: 1 per week minimum
  
Monthly Limits:
  Overtime: 46 hours maximum
  Total Hours: 200 hours maximum
```

**Rule DM-003: Performance Standards**
```yaml
Minimum Requirements:
  On-time Delivery: >90%
  Customer Rating: >4.0/5.0
  Safety Score: >95%
  Fuel Efficiency: Within 10% of target
  Route Adherence: >85%
  
Performance Tracking:
  Daily: Delivery completion
  Weekly: Customer feedback
  Monthly: Comprehensive review
  Quarterly: Safety assessment
  Annual: Full evaluation
```

## 📍 Route Planning Rules

### Route Design

**Rule RP-001: Route Optimization Criteria**
```yaml
Primary Objectives:
  1. Minimize total distance
  2. Maximize on-time delivery
  3. Balance driver workload
  4. Optimize vehicle utilization
  5. Reduce fuel consumption
  
Constraints:
  - Customer time windows
  - Vehicle capacity
  - Driver work hours
  - Traffic patterns
  - Geographic zones
```

**Rule RP-002: Stop Sequencing**
```yaml
Priority Order:
  1. Emergency/Safety critical
  2. Medical facilities
  3. Time-specific appointments
  4. Commercial (business hours)
  5. Residential flexible
  
Sequencing Rules:
  - Hospitals before 10:00
  - Restaurants before 11:00
  - Offices 09:00-17:00
  - Residential avoid 12:00-14:00
  - Industrial follow shift patterns
```

**Rule RP-003: Geographic Zones**
```yaml
Zone Definitions:
  Urban Core:
    - Stop density: >10/km²
    - Average speed: 25 km/h
    - Parking time: +5 minutes
    
  Suburban:
    - Stop density: 5-10/km²
    - Average speed: 40 km/h
    - Standard parking
    
  Rural:
    - Stop density: <5/km²
    - Average speed: 60 km/h
    - Easy parking
    
  Mountain:
    - Special vehicle required
    - Weather dependent
    - Extended time allowance
    - Safety equipment mandatory
```

## 🚚 Delivery Execution Rules

### Delivery Process

**Rule DE-001: Pre-Departure Checklist**
```yaml
Mandatory Checks:
  Vehicle Inspection:
    ☐ Safety equipment present
    ☐ GPS functioning
    ☐ Communication device ready
    ☐ Load secured properly
    ☐ Documents complete
    
  Route Verification:
    ☐ Customer list accurate
    ☐ Product quantities confirmed
    ☐ Special instructions noted
    ☐ Time windows understood
    ☐ Emergency contacts available
    
  Driver Readiness:
    ☐ Proper rest taken
    ☐ Safety gear worn
    ☐ Route familiar
    ☐ Weather checked
    ☐ Health status good
```

**Rule DE-002: Customer Interaction**
```yaml
Service Standards:
  Arrival:
    - Announce arrival professionally
    - Wear company uniform
    - Display ID badge
    - Maintain safe distance
    
  Delivery:
    - Verify customer identity
    - Confirm order details
    - Handle products carefully
    - Explain safety if needed
    
  Completion:
    - Obtain signature/confirmation
    - Provide receipt
    - Collect empty cylinders
    - Thank customer
    
  Communication:
    - Speak politely
    - Use preferred language
    - Answer questions
    - Note special requests
```

**Rule DE-003: Safety Protocols**
```yaml
Product Handling:
  - No smoking within 10 meters
  - Check for leaks before/after
  - Secure cylinders upright
  - Use proper lifting technique
  - Never drag cylinders
  
  Vehicle Safety:
  - Park safely off traffic
  - Use hazard lights
  - Place warning signs
  - Secure vehicle
  - Lock when unattended
  
  Personal Safety:
  - Wear safety shoes
  - Use back support
  - High-visibility vest
  - Gloves for handling
  - Hard hat in industrial areas
```

## 🔄 Loading & Dispatch Rules

### Loading Operations

**Rule LD-001: Loading Sequence**
```yaml
Loading Order:
  1. Emergency orders first
  2. Medical gas priority
  3. Route sequence (LIFO)
  4. Heavy items bottom
  5. Fragile items secured
  
  Weight Distribution:
    - Front-to-back balance
    - Side-to-side even
    - Secure all items
    - Access paths clear
    - Emergency items accessible
```

**Rule LD-002: Product Verification**
```yaml
Verification Process:
  Check Against Order:
    - Product type correct
    - Quantity matches
    - Quality acceptable
    - Accessories included
    - Documentation complete
    
  Serial Tracking:
    - Scan cylinder codes
    - Record in system
    - Match to customer
    - Update inventory
    - Note any issues
```

**Rule LD-003: Documentation Requirements**
```yaml
Required Documents:
  Loading Sheet:
    - Route number
    - Driver name
    - Vehicle ID
    - Product list
    - Customer sequence
    
  Delivery Manifest:
    - Customer details
    - Product specifications
    - Special instructions
    - Payment status
    - Safety notes
    
  Safety Checklist:
    - Vehicle inspection
    - Load security
    - Equipment check
    - Driver briefing
    - Weather assessment
```

## 📊 Performance Monitoring Rules

### KPI Tracking

**Rule PM-001: Delivery Metrics**
```yaml
Core Metrics:
  On-Time Delivery:
    - Target: >95%
    - Measurement: Within promised window
    - Grace period: 15 minutes
    
  Delivery Success:
    - Target: >98%
    - First attempt success
    - Redelivery <2%
    
  Customer Wait Time:
    - Target: <10 minutes
    - From arrival to departure
    - Include paperwork
```

**Rule PM-002: Efficiency Metrics**
```yaml
Operational Efficiency:
  Route Completion:
    - Target: 100% daily
    - Exceptions documented
    - Recovery plan required
    
  Fuel Efficiency:
    - Target by vehicle type
    - Monitor variations
    - Investigate >10% deviation
    
  Time Utilization:
    - Driving: 60-70%
    - Delivery: 25-30%
    - Breaks: 10-15%
    - Admin: <5%
```

**Rule PM-003: Quality Metrics**
```yaml
Service Quality:
  Customer Satisfaction:
    - Target: >4.5/5.0
    - Monthly surveys
    - Address all complaints
    
  Safety Record:
    - Zero tolerance accidents
    - Minor incidents <0.5%
    - Near-miss reporting
    
  Product Handling:
    - Zero damage target
    - Proper procedures
    - Customer training
```

## 🚨 Emergency Response Rules

### Emergency Protocols

**Rule ER-001: Emergency Classification**
```yaml
Priority Levels:
  Level 1 - Critical (30 min):
    - Gas leak
    - Fire risk
    - Medical emergency
    - Safety hazard
    
  Level 2 - Urgent (1 hour):
    - Medical facility need
    - Critical business
    - Service recovery
    
  Level 3 - High (2 hours):
    - Important customer
    - Time-sensitive
    - Reputation risk
    
  Level 4 - Standard (4 hours):
    - General urgent
    - Customer request
    - Competitive response
```

**Rule ER-002: Resource Allocation**
```yaml
Emergency Resources:
  Dedicated Units:
    - 1 emergency vehicle per zone
    - Experienced driver assigned
    - Full safety equipment
    - Priority dispatch
    
  Backup Options:
    - Divert nearest unit
    - Call standby driver
    - Partner resources
    - Management vehicle
```

**Rule ER-003: Communication Protocol**
```yaml
Notification Requirements:
  Customer:
    - Immediate acknowledgment
    - ETA within 5 minutes
    - Updates every 15 minutes
    - Arrival notification
    
  Internal:
    - Dispatch alert
    - Management notification
    - Safety team (if needed)
    - Update systems
```

## 💰 Cost Control Rules

### Financial Management

**Rule CC-001: Cost Allocation**
```yaml
Cost Categories:
  Direct Costs:
    - Fuel: Track per km
    - Driver wages: Per hour
    - Vehicle wear: Per km
    - Tolls: Actual
    
  Indirect Costs:
    - Insurance: Daily rate
    - Maintenance: Allocated
    - Depreciation: Standard
    - Administration: Overhead
```

**Rule CC-002: Overtime Control**
```yaml
Overtime Limits:
  Regular Overtime:
    - Maximum 2 hours/day
    - Approval: Supervisor
    - Rate: 1.33x first 2 hrs
    - Rate: 1.67x beyond
    
  Emergency Overtime:
    - Safety/Medical only
    - Approval: Manager
    - Rate: 2.0x all hours
    - Document reason
```

**Rule CC-003: Efficiency Targets**
```yaml
Cost Targets:
  Cost per Delivery:
    - Urban: <NT$80
    - Suburban: <NT$100
    - Rural: <NT$150
    - Emergency: Cost + 50%
    
  Fuel Efficiency:
    - Motorcycle: 30 km/l
    - Van: 12 km/l
    - 3.5T: 8 km/l
    - 5T+: 6 km/l
```

## 🔐 Security & Compliance Rules

### Regulatory Compliance

**Rule SC-001: Legal Requirements**
```yaml
Licensing:
  - Valid driver licenses
  - Vehicle registrations
  - Operating permits
  - Insurance coverage
  - Safety certifications
  
  Inspections:
    - Vehicle: Every 6 months
    - Safety: Quarterly
    - Emissions: Annual
    - Fire equipment: Monthly
```

**Rule SC-002: Data Protection**
```yaml
Customer Data:
  - Secure storage required
  - Access control enforced
  - No unauthorized sharing
  - Retention limits apply
  - Audit trail maintained
  
  Operational Data:
    - GPS tracking consented
    - Route data protected
    - Performance confidential
    - System access logged
```

**Rule SC-003: Safety Compliance**
```yaml
Safety Standards:
  Training Requirements:
    - Initial: 40 hours
    - Refresher: 8 hours/year
    - Hazmat: 16 hours
    - First aid: Current
    
  Equipment Standards:
    - Fire extinguisher: ABC type
    - First aid kit: Complete
    - Safety gear: Personal
    - Communication: Two-way
    - Emergency tools: Full set
```

## 📈 Continuous Improvement Rules

### Innovation Management

**Rule CI-001: Process Improvement**
```yaml
Improvement Process:
  Idea Collection:
    - Driver suggestions
    - Customer feedback
    - Data analysis
    - Benchmark studies
    
  Evaluation:
    - Cost-benefit analysis
    - Risk assessment
    - Pilot testing
    - Impact measurement
    
  Implementation:
    - Phased rollout
    - Training provided
    - Results monitored
    - Adjustments made
```

**Rule CI-002: Technology Adoption**
```yaml
Technology Standards:
  Mandatory Systems:
    - GPS tracking
    - Mobile communication
    - Digital documentation
    - Route optimization
    
  Evaluation Criteria:
    - ROI > 20%
    - Payback < 2 years
    - User acceptance
    - Integration capability
```

**Rule CI-003: Training Requirements**
```yaml
Continuous Education:
  Monthly Topics:
    - Safety updates
    - Customer service
    - Efficiency tips
    - System updates
    
  Annual Certification:
    - Defensive driving
    - Product knowledge
    - Emergency response
    - Regulation updates
```

## 🔚 Summary

These business rules ensure Lucky Gas maintains the highest standards of safety, efficiency, and customer service in dispatch operations. Regular review and updates ensure rules remain relevant and effective in supporting operational excellence and business growth. All personnel must be familiar with and adhere to these rules, with violations subject to disciplinary action as outlined in company policies.