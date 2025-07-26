# Driver Assignment Workflow - Lucky Gas Legacy System

## 🎯 Workflow Purpose

The Driver Assignment workflow ensures optimal matching of qualified drivers to planned routes based on multiple factors including skills, experience, workload balance, and regulatory compliance. This critical process maximizes delivery efficiency while maintaining safety standards and driver satisfaction in Lucky Gas's operations.

## 📊 Workflow Overview

```mermaid
graph TB
    Start([Driver Assignment Start]) --> LoadRoutes[Load Planned Routes]
    
    LoadRoutes --> RouteRequirements[Analyze Route Requirements]
    RouteRequirements --> RequirementTypes{Requirement Analysis}
    
    RequirementTypes --> VehicleReq[Vehicle Type Requirements]
    RequirementTypes --> LicenseReq[License Requirements]
    RequirementTypes --> SkillReq[Special Skills Required]
    RequirementTypes --> CustomerReq[Customer Preferences]
    
    VehicleReq --> ConsolidateReq
    LicenseReq --> ConsolidateReq
    SkillReq --> ConsolidateReq
    CustomerReq --> ConsolidateReq[Consolidate Requirements]
    
    ConsolidateReq --> LoadDriverPool[Load Available Drivers]
    
    LoadDriverPool --> CheckAvailability[Check Driver Availability]
    CheckAvailability --> AvailabilityStatus{Availability Check}
    
    AvailabilityStatus --> OnDuty[On Duty]
    AvailabilityStatus --> OffDuty[Off Duty]
    AvailabilityStatus --> OnLeave[On Leave]
    AvailabilityStatus --> Restricted[Restricted]
    
    OnDuty --> WorkHourCheck[Check Work Hours]
    OffDuty --> ExcludeDriver[Exclude from Pool]
    OnLeave --> ExcludeDriver
    Restricted --> CheckRestriction[Check Restriction Type]
    
    CheckRestriction --> RestrictionType{Restriction}
    RestrictionType -->|Medical| MedicalCheck[Medical Clearance]
    RestrictionType -->|Disciplinary| DisciplinaryCheck[Review Status]
    RestrictionType -->|Training| TrainingCheck[Training Status]
    
    MedicalCheck --> RestrictionValid{Can Work?}
    DisciplinaryCheck --> RestrictionValid
    TrainingCheck --> RestrictionValid
    
    RestrictionValid -->|No| ExcludeDriver
    RestrictionValid -->|Yes| WorkHourCheck
    
    WorkHourCheck --> HourCalculation[Calculate Hours Worked]
    HourCalculation --> HourLimit{Within Legal Limit?}
    
    HourLimit -->|Daily Exceeded| ExcludeDaily[Exclude - Daily Limit]
    HourLimit -->|Weekly Exceeded| ExcludeWeekly[Exclude - Weekly Limit]
    HourLimit -->|OK| LicenseValidation
    
    ExcludeDaily --> ExcludeDriver
    ExcludeWeekly --> ExcludeDriver
    
    LicenseValidation[Validate License] --> LicenseCheck{License Status}
    
    LicenseCheck --> ValidLicense[Valid & Current]
    LicenseCheck --> ExpiringSoon[Expiring <30 days]
    LicenseCheck --> Expired[Expired]
    
    ValidLicense --> LicenseTypeMatch
    ExpiringSoon --> NotifyHR[Notify HR]
    NotifyHR --> LicenseTypeMatch
    Expired --> ExcludeDriver
    
    LicenseTypeMatch[Match License Type] --> VehicleMatch{Vehicle Compatible?}
    
    VehicleMatch -->|No| ExcludeVehicle[Exclude - Wrong License]
    VehicleMatch -->|Yes| SkillAssessment
    
    ExcludeVehicle --> ExcludeDriver
    
    SkillAssessment[Assess Driver Skills] --> SkillMatrix{Skill Evaluation}
    
    SkillMatrix --> RouteKnowledge[Route Familiarity]
    SkillMatrix --> CustomerRelations[Customer Knowledge]
    SkillMatrix --> SpecialHandling[Special Skills]
    SkillMatrix --> SafetyRecord[Safety Score]
    
    RouteKnowledge --> CalculateScore
    CustomerRelations --> CalculateScore
    SpecialHandling --> CalculateScore
    SafetyRecord --> CalculateScore
    
    CalculateScore[Calculate Match Score] --> ScoreComponents{Score Factors}
    
    ScoreComponents --> ExperienceScore[Experience (30%)]
    ScoreComponents --> PerformanceScore[Performance (25%)]
    ScoreComponents --> CustomerScore[Customer Rating (20%)]
    ScoreComponents --> EfficiencyScore[Efficiency (15%)]
    ScoreComponents --> SafetyScore[Safety (10%)]
    
    ExperienceScore --> TotalScore
    PerformanceScore --> TotalScore
    CustomerScore --> TotalScore
    EfficiencyScore --> TotalScore
    SafetyScore --> TotalScore
    
    TotalScore[Total Match Score] --> CreateCandidateList[Create Candidate List]
    
    ExcludeDriver --> DriverPoolUpdate[Update Available Pool]
    DriverPoolUpdate --> PoolSufficient{Sufficient Drivers?}
    
    PoolSufficient -->|No| ExpandSearch[Expand Search Criteria]
    PoolSufficient -->|Yes| CreateCandidateList
    
    ExpandSearch --> ExpandOptions{Expansion Options}
    ExpandOptions --> CallOffDuty[Call Off-Duty Drivers]
    ExpandOptions --> UseFloaters[Use Floater Pool]
    ExpandOptions --> Overtime[Approve Overtime]
    ExpandOptions --> CrossTrain[Use Cross-Trained]
    
    CallOffDuty --> LoadDriverPool
    UseFloaters --> LoadDriverPool
    Overtime --> LoadDriverPool
    CrossTrain --> LoadDriverPool
    
    CreateCandidateList --> RankCandidates[Rank by Score]
    RankCandidates --> OptimizationEngine[Run Assignment Optimization]
    
    OptimizationEngine --> OptimizationFactors{Optimization Criteria}
    
    OptimizationFactors --> MinimizeDistance[Minimize Home-Route Distance]
    OptimizationFactors --> BalanceWorkload[Balance Workload]
    OptimizationFactors --> MaximizeEfficiency[Maximize Efficiency]
    OptimizationFactors --> RespectPreferences[Respect Preferences]
    
    MinimizeDistance --> RunAlgorithm
    BalanceWorkload --> RunAlgorithm
    MaximizeEfficiency --> RunAlgorithm
    RespectPreferences --> RunAlgorithm
    
    RunAlgorithm[Run Assignment Algorithm] --> AlgorithmType{Algorithm}
    
    AlgorithmType -->|Hungarian| HungarianMethod[Hungarian Algorithm]
    AlgorithmType -->|Greedy| GreedyAssignment[Greedy Assignment]
    AlgorithmType -->|Genetic| GeneticOptimization[Genetic Algorithm]
    
    HungarianMethod --> GenerateAssignments
    GreedyAssignment --> GenerateAssignments
    GeneticOptimization --> GenerateAssignments
    
    GenerateAssignments[Generate Assignments] --> ValidateAssignments[Validate Assignments]
    
    ValidateAssignments --> ValidationChecks{Validation}
    
    ValidationChecks --> CheckCoverage[All Routes Covered]
    ValidationChecks --> CheckCompliance[Compliance Check]
    ValidationChecks --> CheckBalance[Workload Balance]
    ValidationChecks --> CheckConstraints[Constraint Satisfaction]
    
    CheckCoverage --> ValidationResult
    CheckCompliance --> ValidationResult
    CheckBalance --> ValidationResult
    CheckConstraints --> ValidationResult
    
    ValidationResult{Valid Assignment?} -->|No| IdentifyGaps[Identify Gaps]
    ValidationResult -->|Yes| FinalizeAssignments
    
    IdentifyGaps --> GapType{Gap Type}
    
    GapType -->|Missing Driver| FindBackup[Find Backup Driver]
    GapType -->|Skill Gap| TrainDriver[Schedule Training]
    GapType -->|Compliance| AdjustSchedule[Adjust Schedule]
    
    FindBackup --> BackupSearch{Backup Available?}
    BackupSearch -->|No| EscalateManager[Escalate to Manager]
    BackupSearch -->|Yes| AssignBackup[Assign Backup]
    
    TrainDriver --> TemporaryAssign[Temporary Assignment]
    AdjustSchedule --> RescheduleRoute[Reschedule Route]
    
    EscalateManager --> ManagerDecision{Manager Decision}
    ManagerDecision -->|Approve OT| ApproveOvertime[Approve Overtime]
    ManagerDecision -->|Combine Routes| CombineRoutes[Combine Routes]
    ManagerDecision -->|Delay Route| DelayDelivery[Delay Delivery]
    
    ApproveOvertime --> GenerateAssignments
    CombineRoutes --> OptimizationEngine
    DelayDelivery --> NotifyAffected[Notify Affected Parties]
    
    AssignBackup --> FinalizeAssignments
    TemporaryAssign --> FinalizeAssignments
    RescheduleRoute --> FinalizeAssignments
    NotifyAffected --> FinalizeAssignments
    
    FinalizeAssignments[Finalize Assignments] --> GenerateDocuments[Generate Assignment Docs]
    
    GenerateDocuments --> DocumentTypes{Documents}
    
    DocumentTypes --> AssignmentSheet[Assignment Sheet]
    DocumentTypes --> DriverSchedule[Driver Schedule]
    DocumentTypes --> VehicleAllocation[Vehicle Assignment]
    DocumentTypes --> RoutePackage[Route Package]
    
    AssignmentSheet --> PrepareNotifications
    DriverSchedule --> PrepareNotifications
    VehicleAllocation --> PrepareNotifications
    RoutePackage --> PrepareNotifications
    
    PrepareNotifications[Prepare Notifications] --> NotificationChannels{Notify Via}
    
    NotificationChannels --> SMSNotify[SMS to Drivers]
    NotificationChannels --> AppNotify[Mobile App Push]
    NotificationChannels --> EmailNotify[Email Summary]
    NotificationChannels --> SystemUpdate[System Update]
    
    SMSNotify --> ConfirmReceipt
    AppNotify --> ConfirmReceipt
    EmailNotify --> ConfirmReceipt
    SystemUpdate --> ConfirmReceipt
    
    ConfirmReceipt[Confirm Receipt] --> ReceiptStatus{Confirmation Status}
    
    ReceiptStatus -->|Not Confirmed| ResendNotification[Resend Notification]
    ReceiptStatus -->|Rejected| HandleRejection[Handle Rejection]
    ReceiptStatus -->|Confirmed| UpdateRecords
    
    ResendNotification --> FollowUp[Follow Up Call]
    FollowUp --> ReceiptStatus
    
    HandleRejection --> RejectionReason{Rejection Reason}
    
    RejectionReason -->|Sick| MedicalLeave[Process Medical Leave]
    RejectionReason -->|Emergency| PersonalEmergency[Handle Emergency]
    RejectionReason -->|Dispute| ResolveDispute[Resolve Dispute]
    
    MedicalLeave --> FindReplacement
    PersonalEmergency --> FindReplacement
    ResolveDispute --> FindReplacement[Find Replacement]
    
    FindReplacement --> OptimizationEngine
    
    UpdateRecords[Update All Records] --> SystemUpdates{Update Systems}
    
    SystemUpdates --> HRSystem[HR System]
    SystemUpdates --> PayrollSystem[Payroll System]
    SystemUpdates --> GPSSystem[GPS Tracking]
    SystemUpdates --> CustomerSystem[Customer Portal]
    
    HRSystem --> FinalChecks
    PayrollSystem --> FinalChecks
    GPSSystem --> FinalChecks
    CustomerSystem --> FinalChecks
    
    FinalChecks[Final Assignment Checks] --> PublishAssignments[Publish Final Assignments]
    
    PublishAssignments --> Success[Assignment Complete]
    
    Success --> End([End])
    
    %% Styling
    classDef errorStyle fill:#ff6b6b,stroke:#c92a2a,stroke-width:2px,color:#fff
    classDef successStyle fill:#51cf66,stroke:#2f9e44,stroke-width:2px,color:#fff
    classDef processStyle fill:#4dabf7,stroke:#1864ab,stroke-width:2px,color:#fff
    classDef decisionStyle fill:#ffd43b,stroke:#fab005,stroke-width:2px
    classDef warningStyle fill:#ff922b,stroke:#e8590c,stroke-width:2px,color:#fff
    
    class ExcludeDriver,Expired,DelayDelivery errorStyle
    class Success,FinalizeAssignments,PublishAssignments successStyle
    class LoadRoutes,CheckAvailability,CalculateScore,OptimizationEngine processStyle
    class AvailabilityStatus,HourLimit,VehicleMatch,ValidationResult decisionStyle
    class ExpiringSoon,ExpandSearch,EscalateManager warningStyle
```

## 🔄 Process Steps

### 1. Route Requirement Analysis

**Step 1.1: Load Route Requirements**
```yaml
Route Data Collection:
  - Route ID and description
  - Vehicle type required
  - Total stops and distance
  - Time windows
  - Special requirements
  
Special Requirements:
  - Hazmat certification
  - Heavy lifting capability
  - Customer language preference
  - Access restrictions
  - Security clearance
```

**Step 1.2: Skill Mapping**
```yaml
Required Skills Matrix:
  Basic Delivery:
    - Valid driver's license
    - Physical fitness
    - Customer service skills
    
  Special Routes:
    - Mountain driving experience
    - Night delivery certification
    - Industrial site training
    - Hospital protocol knowledge
    
  Premium Service:
    - VIP customer handling
    - English/Japanese speaking
    - Professional appearance
    - Conflict resolution
```

### 2. Driver Availability Assessment

**Step 2.1: Work Hour Calculation**
```yaml
Legal Limits (Taiwan):
  Daily Maximum: 10 hours driving
  Weekly Maximum: 48 hours total
  Rest Period: 8 continuous hours
  Break Requirement: 30 min per 4 hours
  
Calculation includes:
  - Previous day carryover
  - Current week total
  - Scheduled time off
  - Overtime allowance
```

**Step 2.2: License Validation**
```yaml
License Categories:
  Regular (普通小型車):
    - Motorcycle routes
    - Light van routes
    
  Professional (職業小型車):
    - All commercial vehicles
    - Required for hire
    
  Large Vehicle (大貨車):
    - Trucks over 3.5T
    - Special endorsements
    
Validation Checks:
  - Expiry date >30 days
  - No suspensions
  - Medical certificate current
  - Points balance check
```

### 3. Driver-Route Matching

**Step 3.1: Scoring Algorithm**
```yaml
Match Score Components:
  Experience (30%):
    - Years of service: 0-10 points
    - Routes completed: 0-10 points
    - Zone familiarity: 0-10 points
    
  Performance (25%):
    - On-time rate: 0-25 points
    - Delivery accuracy: 0-25 points
    - Efficiency metrics: 0-25 points
    
  Customer Rating (20%):
    - Service scores: 0-50 points
    - Complaint history: -10 to 0
    - Compliments: 0-10 bonus
    
  Efficiency (15%):
    - Fuel economy: 0-30 points
    - Time management: 0-30 points
    - Route optimization: 0-30 points
    
  Safety (10%):
    - Accident-free days: 0-50 points
    - Violation record: -20 to 0
    - Safety training: 0-20 bonus
```

**Step 3.2: Preference Handling**
```yaml
Driver Preferences:
  Geographic:
    - Home proximity preference
    - Familiar zones
    - Avoid certain areas
    
  Schedule:
    - Early/late shift preference
    - Day off requests
    - Fixed route preference
    
  Workload:
    - Light/heavy preference
    - Overtime willingness
    - Helper preference
    
Customer Preferences:
  - Preferred drivers list
  - Excluded drivers list
  - Language requirements
  - Special rapport
```

### 4. Assignment Optimization

**Step 4.1: Optimization Objectives**
```yaml
Primary Objectives:
  1. Maximize total match scores
  2. Minimize home-to-route distance
  3. Balance workload fairly
  4. Respect hard constraints
  
Secondary Objectives:
  - Minimize overtime costs
  - Maximize customer satisfaction
  - Reduce fuel consumption
  - Improve driver retention
```

**Step 4.2: Algorithm Selection**
```yaml
Small Scale (<20 drivers):
  - Greedy algorithm
  - Quick execution
  - Good enough results
  
Medium Scale (20-50 drivers):
  - Hungarian method
  - Optimal assignment
  - Reasonable time
  
Large Scale (>50 drivers):
  - Genetic algorithm
  - Near-optimal solution
  - Handles complex constraints
  
Real-time Adjustments:
  - Simple reassignment
  - Local optimization
  - Quick response
```

### 5. Validation and Compliance

**Step 5.1: Assignment Validation**
```yaml
Validation Checklist:
  Coverage:
    ☐ All routes have drivers
    ☐ All drivers within limits
    ☐ Backup plans ready
    
  Compliance:
    ☐ License requirements met
    ☐ Work hour rules followed
    ☐ Safety standards met
    ☐ Union rules respected
    
  Balance:
    ☐ Fair work distribution
    ☐ Overtime spread evenly
    ☐ Preferences considered
    ☐ Skills utilized well
```

**Step 5.2: Conflict Resolution**
```yaml
Common Conflicts:
  Skill Shortage:
    - Identify training needs
    - Schedule certification
    - Use supervised pairing
    
  Availability Gap:
    - Approve overtime
    - Call standby pool
    - Combine routes
    - Delay non-urgent
    
  License Issues:
    - Expedite renewals
    - Temporary reassignment
    - Supervisor override
    
  Customer Conflicts:
    - Mediation process
    - Alternative driver
    - Route swap
```

### 6. Communication and Confirmation

**Step 6.1: Notification Process**
```yaml
Notification Timeline:
  T-12 hours: Initial assignment
  T-2 hours: Final confirmation
  T-30 min: Departure reminder
  
Communication Channels:
  Primary: Mobile app push
  Secondary: SMS message
  Backup: Phone call
  Record: Email summary
  
Message Content:
  - Assignment details
  - Route summary
  - Vehicle assignment
  - Special instructions
  - Contact information
```

**Step 6.2: Confirmation Handling**
```yaml
Confirmation Required:
  - Read receipt
  - Acceptance click
  - No objections raised
  
Non-Confirmation Process:
  1. Auto-retry after 30 min
  2. SMS fallback
  3. Phone call at T-1 hour
  4. Supervisor intervention
  
Rejection Handling:
  - Document reason
  - Find replacement
  - Update records
  - Follow up required
```

## 📋 Business Rules

### Assignment Priority Rules
1. **Safety First**: Never compromise on safety qualifications
2. **Customer Preference**: Honor VIP customer requests
3. **Fair Distribution**: Rotate premium routes fairly
4. **Skill Match**: Minimum 70% match score required
5. **Home Distance**: Prefer <30 minutes from home

### Work Hour Regulations
1. **Daily Limit**: 10 hours driving, 12 hours total
2. **Weekly Limit**: 48 hours regular, 60 with overtime
3. **Rest Period**: Minimum 8 continuous hours
4. **Break Time**: 30 minutes per 4 hours
5. **Overtime Approval**: Manager required >2 hours

### Performance Standards
1. **Minimum Score**: 60/100 for route assignment
2. **Probation Period**: New drivers supervised 30 days
3. **Training Required**: Annual safety certification
4. **Medical Fitness**: Annual health check
5. **Accident Review**: Immediate reassessment needed

## 🔐 Security & Compliance

### Regulatory Compliance
- Department of Transportation rules
- Labor Standards Act compliance
- Insurance requirements met
- Union agreements honored
- Safety regulations followed

### Data Protection
- Driver personal data secured
- Medical information confidential
- Performance data restricted
- Location tracking consensual
- Assignment history retained

## 🔄 Integration Points

### Internal Systems
1. **HR System**: Driver records and status
2. **Payroll**: Work hours and overtime
3. **Training**: Certification tracking
4. **Route Planning**: Route requirements
5. **Vehicle Management**: Vehicle assignments

### External Systems
1. **DOT Database**: License verification
2. **Insurance**: Coverage confirmation
3. **Medical Providers**: Fitness certificates
4. **Union Systems**: Agreement compliance
5. **Customer Portal**: Preference management

## ⚡ Performance Optimization

### Assignment Efficiency
- Assignment time: <5 minutes for 50 drivers
- Optimization run: <30 seconds
- Notification delivery: <1 minute
- Confirmation rate: >95%
- System availability: 99.9%

### Quality Metrics
- Match score average: >80%
- Driver satisfaction: >4/5
- Customer satisfaction: >4.5/5
- On-time assignment: >98%
- Conflict rate: <5%

## 🚨 Error Handling

### Common Issues
1. **Driver No-Show**: Automatic backup activation
2. **License Expired**: Block assignment, notify HR
3. **System Timeout**: Use cached assignments
4. **Communication Failure**: Multi-channel retry
5. **Optimization Failure**: Fallback to manual

### Escalation Procedures
- Level 1: Automatic resolution
- Level 2: Supervisor intervention
- Level 3: Manager approval
- Level 4: Director decision
- Emergency: 24/7 hotline

## 📊 Success Metrics

### Operational KPIs
- Assignment completion: 100%
- First-choice assignment: >70%
- Workload variance: <10%
- Overtime percentage: <15%
- Conflict resolution: <30 minutes

### Business Impact
- Driver retention: +20%
- Customer satisfaction: +15%
- Overtime costs: -25%
- Assignment efficiency: +30%
- Safety incidents: -40%