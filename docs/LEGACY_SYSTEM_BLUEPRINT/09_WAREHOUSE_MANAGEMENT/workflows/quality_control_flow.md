# Quality Control Workflow - Lucky Gas Legacy System

## 🎯 Workflow Purpose

The Quality Control workflow ensures gas cylinder safety, compliance, and fitness for use through systematic inspection, testing, and certification processes. This critical workflow maintains product integrity, prevents safety incidents, and ensures regulatory compliance while managing the lifecycle of gas cylinders from receipt through disposal.

## 📊 Workflow Overview

```mermaid
graph TB
    Start([Quality Control Start]) --> QCTrigger[QC Trigger Event]
    
    QCTrigger --> TriggerType{Trigger Type}
    
    TriggerType -->|Receiving| ReceivingQC[Receiving Inspection]
    TriggerType -->|Periodic| PeriodicInspection[Periodic Inspection]
    TriggerType -->|Return| ReturnInspection[Return Inspection]
    TriggerType -->|Incident| IncidentInspection[Incident-Based QC]
    TriggerType -->|Customer| CustomerComplaint[Customer Complaint]
    
    ReceivingQC --> DetermineInspectionLevel[Determine Inspection Level]
    
    DetermineInspectionLevel --> SupplierHistory{Supplier History}
    
    SupplierHistory -->|New Supplier| FullInspection[100% Inspection]
    SupplierHistory -->|Trusted| SampleInspection[Sample Inspection]
    SupplierHistory -->|Problem History| EnhancedInspection[Enhanced Inspection]
    
    FullInspection --> SelectAllUnits[Select All Units]
    SampleInspection --> CalculateSampleSize[Calculate Sample Size]
    EnhancedInspection --> IncreasedSample[Increased Sample Size]
    
    CalculateSampleSize --> SamplingMethod{Sampling Method}
    
    SamplingMethod -->|Statistical| StatisticalSampling[AQL Sampling]
    SamplingMethod -->|Random| RandomSelection[Random Selection]
    SamplingMethod -->|Systematic| SystematicSelection[Every Nth Unit]
    
    StatisticalSampling --> GenerateSampleList
    RandomSelection --> GenerateSampleList
    SystematicSelection --> GenerateSampleList
    
    SelectAllUnits --> GenerateSampleList[Generate Sample List]
    IncreasedSample --> GenerateSampleList
    
    GenerateSampleList --> PrepareInspection[Prepare for Inspection]
    
    PrepareInspection --> InspectionSetup{Setup Tasks}
    
    InspectionSetup --> GatherEquipment[Gather Test Equipment]
    InspectionSetup --> PrepareArea[Prepare Inspection Area]
    InspectionSetup --> ReviewStandards[Review Standards]
    InspectionSetup --> AssignInspector[Assign Inspector]
    
    GatherEquipment --> EquipmentCheck[Equipment Calibration Check]
    PrepareArea --> SafetyCheck[Safety Equipment Check]
    ReviewStandards --> StandardsAvailable[Ensure Standards Available]
    AssignInspector --> VerifyCertification[Verify Certification]
    
    EquipmentCheck --> EquipmentReady{Equipment OK?}
    
    EquipmentReady -->|No| CalibrateEquipment[Calibrate Equipment]
    EquipmentReady -->|Yes| BeginInspection
    
    CalibrateEquipment --> EquipmentCheck
    
    SafetyCheck --> BeginInspection
    StandardsAvailable --> BeginInspection
    VerifyCertification --> CertificationValid{Valid?}
    
    CertificationValid -->|No| AssignDifferentInspector[Assign Different Inspector]
    CertificationValid -->|Yes| BeginInspection
    
    AssignDifferentInspector --> AssignInspector
    
    BeginInspection[Begin Inspection Process] --> VisualInspection[Visual Inspection]
    
    VisualInspection --> VisualChecks{Visual Checks}
    
    VisualChecks --> CylinderBody[Cylinder Body Check]
    VisualChecks --> ValveCondition[Valve Condition]
    VisualChecks --> PaintMarkings[Paint & Markings]
    VisualChecks --> BaseCondition[Base Condition]
    
    CylinderBody --> BodyDefects{Defects Found?}
    
    BodyDefects -->|None| RecordBodyOK[Record Body OK]
    BodyDefects -->|Minor| RecordMinorDefects[Record Minor Defects]
    BodyDefects -->|Major| RecordMajorDefects[Record Major Defects]
    
    RecordBodyOK --> ValveInspection
    RecordMinorDefects --> AssessImpact[Assess Impact]
    RecordMajorDefects --> FailVisual[Fail Visual Inspection]
    
    AssessImpact --> ImpactLevel{Impact Level}
    
    ImpactLevel -->|Cosmetic| ContinueInspection[Continue Inspection]
    ImpactLevel -->|Functional| RequireRepair[Require Repair]
    
    ContinueInspection --> ValveInspection
    RequireRepair --> ScheduleRepair[Schedule Repair]
    FailVisual --> QuarantineProduct[Quarantine Product]
    
    ValveCondition --> ValveDefects{Valve Issues?}
    
    ValveDefects -->|None| RecordValveOK[Record Valve OK]
    ValveDefects -->|Leak| ValveLeak[Valve Leak Detected]
    ValveDefects -->|Damage| ValveDamage[Valve Damaged]
    
    RecordValveOK --> MarkingInspection
    ValveLeak --> SafetyProtocol[Safety Protocol]
    ValveDamage --> ValveReplacement[Schedule Valve Replacement]
    
    SafetyProtocol --> IsolateProduct[Isolate Product]
    IsolateProduct --> QuarantineProduct
    ValveReplacement --> QuarantineProduct
    
    PaintMarkings --> MarkingInspection[Inspect Markings]
    
    MarkingInspection --> MarkingLegible{Markings Legible?}
    
    MarkingLegible -->|No| RequireRemarking[Require Remarking]
    MarkingLegible -->|Yes| VerifyCompliance[Verify Compliance]
    
    RequireRemarking --> ScheduleRemarking[Schedule Remarking]
    VerifyCompliance --> ComplianceCheck{Compliant?}
    
    ComplianceCheck -->|No| ComplianceIssue[Compliance Issue]
    ComplianceCheck -->|Yes| RecordMarkingsOK[Record Markings OK]
    
    ComplianceIssue --> QuarantineProduct
    RecordMarkingsOK --> BaseInspection
    ScheduleRemarking --> BaseInspection
    
    BaseCondition --> BaseInspection[Inspect Base Ring]
    
    BaseInspection --> BaseIntegrity{Base Integrity?}
    
    BaseIntegrity -->|Good| RecordBaseOK[Record Base OK]
    BaseIntegrity -->|Damaged| BaseDamage[Base Damage]
    BaseIntegrity -->|Missing| MissingBase[Missing Base Ring]
    
    RecordBaseOK --> ValveInspection
    BaseDamage --> StabilityRisk[Assess Stability Risk]
    MissingBase --> RequireBaseInstall[Require Base Installation]
    
    StabilityRisk --> RiskLevel{Risk Level}
    
    RiskLevel -->|Low| NoteForRepair[Note for Repair]
    RiskLevel -->|High| RemoveFromService[Remove from Service]
    
    NoteForRepair --> ValveInspection
    RemoveFromService --> QuarantineProduct
    RequireBaseInstall --> QuarantineProduct
    
    ValveInspection[Valve Function Test] --> ValveOperation[Operate Valve]
    
    ValveOperation --> ValveFunctions{Functions Properly?}
    
    ValveFunctions -->|Yes| RecordValvePass[Record Pass]
    ValveFunctions -->|No| ValveFailure[Valve Failure]
    
    RecordValvePass --> PressureTest
    ValveFailure --> FailureType{Failure Type}
    
    FailureType -->|Stuck Open| StuckOpen[Safety Hazard]
    FailureType -->|Stuck Closed| StuckClosed[Cannot Dispense]
    FailureType -->|Leaking| LeakingValve[Leak Detected]
    
    StuckOpen --> EmergencyProtocol[Emergency Protocol]
    StuckClosed --> ValveReplacement
    LeakingValve --> EmergencyProtocol
    
    EmergencyProtocol --> QuarantineProduct
    
    PressureTest[Pressure Testing] --> TestRequired{Test Required?}
    
    TestRequired -->|No| SkipPressureTest[Skip Pressure Test]
    TestRequired -->|Yes| PreparePressureTest[Prepare Test]
    
    SkipPressureTest --> WeightVerification
    
    PreparePressureTest --> ConnectGauges[Connect Test Gauges]
    
    ConnectGauges --> ApplyTestPressure[Apply Test Pressure]
    
    ApplyTestPressure --> MonitorPressure[Monitor Pressure]
    
    MonitorPressure --> PressureHold{Pressure Holds?}
    
    PressureHold -->|Yes| RecordPressurePass[Record Pass]
    PressureHold -->|No| PressureLoss[Pressure Loss Detected]
    
    RecordPressurePass --> CheckTestDate[Check Test Date]
    PressureLoss --> LeakLocation[Locate Leak]
    
    LeakLocation --> LeakSource{Leak Source}
    
    LeakSource -->|Valve| ValveLeakConfirmed[Valve Leak]
    LeakSource -->|Body| BodyLeak[Body Leak]
    LeakSource -->|Thread| ThreadLeak[Thread Leak]
    
    ValveLeakConfirmed --> ValveReplacement
    BodyLeak --> CondemnCylinder[Condemn Cylinder]
    ThreadLeak --> ThreadRepair[Schedule Thread Repair]
    
    CondemnCylinder --> QuarantineProduct
    ThreadRepair --> QuarantineProduct
    
    CheckTestDate --> TestDateValid{Test Date Valid?}
    
    TestDateValid -->|No| RequireHydrotest[Require Hydrotest]
    TestDateValid -->|Yes| RecordTestDate[Record Test Date]
    
    RequireHydrotest --> ScheduleHydrotest[Schedule Hydrotest]
    RecordTestDate --> WeightVerification
    ScheduleHydrotest --> QuarantineProduct
    
    WeightVerification[Weight Verification] --> CheckTareWeight[Check Tare Weight]
    
    CheckTareWeight --> WeightCorrect{Weight Correct?}
    
    WeightCorrect -->|No| WeightDiscrepancy[Weight Discrepancy]
    WeightCorrect -->|Yes| CalculateGasWeight[Calculate Gas Weight]
    
    WeightDiscrepancy --> InvestigateWeight[Investigate Discrepancy]
    InvestigateWeight --> WeightCause{Cause?}
    
    WeightCause -->|Wrong Label| UpdateLabel[Update Label]
    WeightCause -->|Modified| ModifiedCylinder[Modified Cylinder]
    WeightCause -->|Unknown| UnknownIssue[Unknown Issue]
    
    UpdateLabel --> CalculateGasWeight
    ModifiedCylinder --> QuarantineProduct
    UnknownIssue --> QuarantineProduct
    
    CalculateGasWeight --> GasWeightOK{Gas Weight OK?}
    
    GasWeightOK -->|No| GasWeightIssue[Gas Weight Issue]
    GasWeightOK -->|Yes| CertificationCheck[Certification Check]
    
    GasWeightIssue --> GasIssueType{Issue Type}
    
    GasIssueType -->|Overfilled| OverfilledCylinder[Safety Risk]
    GasIssueType -->|Underfilled| UnderfilledCylinder[Short Fill]
    
    OverfilledCylinder --> EmergencyProtocol
    UnderfilledCylinder --> NoteShortFill[Note Short Fill]
    NoteShortFill --> CertificationCheck
    
    CertificationCheck --> VerifyCertificates[Verify Certificates]
    
    VerifyCertificates --> CertificatesValid{Certificates Valid?}
    
    CertificatesValid -->|No| CertificationIssue[Certification Issue]
    CertificatesValid -->|Yes| DateVerification[Verify Dates]
    
    CertificationIssue --> CertIssueType{Issue Type}
    
    CertIssueType -->|Missing| MissingCert[Missing Certificate]
    CertIssueType -->|Expired| ExpiredCert[Expired Certificate]
    CertIssueType -->|Invalid| InvalidCert[Invalid Certificate]
    
    MissingCert --> RequestCertificate[Request Certificate]
    ExpiredCert --> RequireRecertification[Require Recertification]
    InvalidCert --> RejectProduct[Reject Product]
    
    RequestCertificate --> HoldForCert[Hold for Certificate]
    RequireRecertification --> QuarantineProduct
    RejectProduct --> QuarantineProduct
    HoldForCert --> QuarantineProduct
    
    DateVerification --> ManufactureDate[Check Manufacture Date]
    
    ManufactureDate --> DateAcceptable{Date Acceptable?}
    
    DateAcceptable -->|No| TooOld[Cylinder Too Old]
    DateAcceptable -->|Yes| ExpiryCheck[Check Expiry Date]
    
    TooOld --> RetireFromService[Retire from Service]
    RetireFromService --> QuarantineProduct
    
    ExpiryCheck --> ExpiryStatus{Expiry Status}
    
    ExpiryStatus -->|Expired| ExpiredProduct[Product Expired]
    ExpiryStatus -->|Near Expiry| NearExpiry[Near Expiry Warning]
    ExpiryStatus -->|Good| RecordExpiryOK[Record Expiry OK]
    
    ExpiredProduct --> QuarantineProduct
    NearExpiry --> FlagLimitedLife[Flag Limited Life]
    RecordExpiryOK --> CompileResults
    FlagLimitedLife --> CompileResults
    
    PeriodicInspection --> SelectInventory[Select Inventory for Inspection]
    
    SelectInventory --> SelectionCriteria{Selection Criteria}
    
    SelectionCriteria -->|Age Based| AgeBasedSelection[Select by Age]
    SelectionCriteria -->|Usage Based| UsageBasedSelection[Select by Usage]
    SelectionCriteria -->|Risk Based| RiskBasedSelection[Select by Risk]
    SelectionCriteria -->|Random| RandomInventory[Random Selection]
    
    AgeBasedSelection --> GenerateInspectionList
    UsageBasedSelection --> GenerateInspectionList
    RiskBasedSelection --> GenerateInspectionList
    RandomInventory --> GenerateInspectionList
    
    GenerateInspectionList[Generate Inspection List] --> ScheduleInspections[Schedule Inspections]
    
    ScheduleInspections --> NotifyOperations[Notify Operations]
    NotifyOperations --> PrepareInspection
    
    ReturnInspection --> AssessReturnCondition[Assess Return Condition]
    
    AssessReturnCondition --> ReturnCondition{Return Condition}
    
    ReturnCondition -->|Normal Wear| NormalWearInspection[Standard Inspection]
    ReturnCondition -->|Damage Reported| DamageInspection[Damage Assessment]
    ReturnCondition -->|Quality Issue| QualityIssueInspection[Quality Investigation]
    
    NormalWearInspection --> BeginInspection
    DamageInspection --> DocumentDamage[Document Damage]
    QualityIssueInspection --> InvestigateIssue[Investigate Issue]
    
    DocumentDamage --> PhotoEvidence[Photo Evidence]
    InvestigateIssue --> RootCauseAnalysis[Root Cause Analysis]
    
    PhotoEvidence --> BeginInspection
    RootCauseAnalysis --> BeginInspection
    
    IncidentInspection --> IncidentType{Incident Type}
    
    IncidentType -->|Accident| AccidentInvestigation[Accident Investigation]
    IncidentType -->|Near Miss| NearMissReview[Near Miss Review]
    IncidentType -->|Equipment Failure| FailureAnalysis[Failure Analysis]
    
    AccidentInvestigation --> SecureEvidence[Secure Evidence]
    NearMissReview --> IdentifyInvolved[Identify Involved Units]
    FailureAnalysis --> CollectFailedParts[Collect Failed Parts]
    
    SecureEvidence --> CoordinateWithSafety[Coordinate with Safety]
    IdentifyInvolved --> ExpandInspection[Expand Inspection Scope]
    CollectFailedParts --> TechnicalAnalysis[Technical Analysis]
    
    CoordinateWithSafety --> BeginInspection
    ExpandInspection --> BeginInspection
    TechnicalAnalysis --> BeginInspection
    
    CustomerComplaint --> ComplaintNature{Complaint Nature}
    
    ComplaintNature -->|Quality| QualityComplaint[Quality Issue]
    ComplaintNature -->|Safety| SafetyComplaint[Safety Concern]
    ComplaintNature -->|Performance| PerformanceComplaint[Performance Issue]
    
    QualityComplaint --> RecallBatch[Recall Batch]
    SafetyComplaint --> ImmediateAction[Immediate Action]
    PerformanceComplaint --> TestPerformance[Test Performance]
    
    RecallBatch --> BatchInspection[Inspect Entire Batch]
    ImmediateAction --> StopDistribution[Stop Distribution]
    TestPerformance --> PerformanceTests[Run Performance Tests]
    
    BatchInspection --> BeginInspection
    StopDistribution --> BeginInspection
    PerformanceTests --> BeginInspection
    
    CompileResults[Compile Inspection Results] --> OverallAssessment{Overall Assessment}
    
    OverallAssessment -->|Pass| PassInspection[Pass Inspection]
    OverallAssessment -->|Conditional| ConditionalPass[Conditional Pass]
    OverallAssessment -->|Fail| FailInspection[Fail Inspection]
    
    PassInspection --> UpdateQualityStatus[Update Status to Good]
    ConditionalPass --> DefineConditions[Define Conditions]
    FailInspection --> DetermineDisposition[Determine Disposition]
    
    DefineConditions --> ConditionType{Condition Type}
    
    ConditionType -->|Limited Use| LimitedUseRestriction[Restrict Usage]
    ConditionType -->|Repair Required| RepairBeforeUse[Repair Before Use]
    ConditionType -->|Monitoring| RequireMonitoring[Require Monitoring]
    
    LimitedUseRestriction --> UpdateQualityStatus
    RepairBeforeUse --> ScheduleRepairWork[Schedule Repair Work]
    RequireMonitoring --> SetMonitoringPlan[Set Monitoring Plan]
    
    ScheduleRepairWork --> UpdateQualityStatus
    SetMonitoringPlan --> UpdateQualityStatus
    
    DetermineDisposition --> DispositionOptions{Disposition}
    
    DispositionOptions -->|Repair| SendToRepair[Send to Repair]
    DispositionOptions -->|Scrap| ScrapCylinder[Scrap Cylinder]
    DispositionOptions -->|Return Supplier| ReturnToSupplier[Return to Supplier]
    
    SendToRepair --> CreateRepairOrder[Create Repair Order]
    ScrapCylinder --> ScrapProcess[Initiate Scrap Process]
    ReturnToSupplier --> CreateReturn[Create Return Authorization]
    
    CreateRepairOrder --> UpdateQualityStatus
    ScrapProcess --> UpdateQualityStatus
    CreateReturn --> UpdateQualityStatus
    
    QuarantineProduct --> UpdateQualityStatus
    
    UpdateQualityStatus --> RecordInspection[Record Inspection Details]
    
    RecordInspection --> InspectionData{Record Data}
    
    InspectionData --> InspectionResults[Results & Findings]
    InspectionData --> PhotoDocumentation[Photos & Evidence]
    InspectionData --> CertificateStatus[Certificate Status]
    InspectionData --> NextActionRequired[Next Action Required]
    
    InspectionResults --> UpdateDatabase
    PhotoDocumentation --> UpdateDatabase
    CertificateStatus --> UpdateDatabase
    NextActionRequired --> UpdateDatabase
    
    UpdateDatabase[Update Database] --> GenerateReports[Generate Reports]
    
    GenerateReports --> ReportTypes{Report Types}
    
    ReportTypes -->|Inspection Report| InspectionReport[Inspection Report]
    ReportTypes -->|Exception Report| ExceptionReport[Exception Report]
    ReportTypes -->|Compliance Report| ComplianceReport[Compliance Report]
    ReportTypes -->|Trend Report| TrendReport[Trend Analysis]
    
    InspectionReport --> DistributeReports
    ExceptionReport --> DistributeReports
    ComplianceReport --> DistributeReports
    TrendReport --> DistributeReports
    
    DistributeReports[Distribute Reports] --> NotifyStakeholders[Notify Stakeholders]
    
    NotifyStakeholders --> StakeholderTypes{Stakeholder Types}
    
    StakeholderTypes -->|Operations| NotifyOperations[Notify Operations]
    StakeholderTypes -->|Suppliers| NotifySuppliers[Notify Suppliers]
    StakeholderTypes -->|Customers| NotifyCustomers[Notify Customers]
    StakeholderTypes -->|Regulatory| NotifyRegulatory[Notify Regulatory]
    
    NotifyOperations --> UpdateMetrics
    NotifySuppliers --> UpdateMetrics
    NotifyCustomers --> UpdateMetrics
    NotifyRegulatory --> UpdateMetrics
    
    UpdateMetrics[Update Quality Metrics] --> MetricCategories{Metric Categories}
    
    MetricCategories -->|Pass Rate| UpdatePassRate[Update Pass Rate]
    MetricCategories -->|Defect Types| UpdateDefectTypes[Update Defect Analysis]
    MetricCategories -->|Supplier Performance| UpdateSupplierMetrics[Update Supplier Metrics]
    MetricCategories -->|Cost Impact| UpdateCostMetrics[Update Cost Metrics]
    
    UpdatePassRate --> Success
    UpdateDefectTypes --> Success
    UpdateSupplierMetrics --> Success
    UpdateCostMetrics --> Success
    
    Success[Process Complete] --> End([End])
    
    %% Styling
    classDef errorStyle fill:#ff6b6b,stroke:#c92a2a,stroke-width:2px,color:#fff
    classDef successStyle fill:#51cf66,stroke:#2f9e44,stroke-width:2px,color:#fff
    classDef processStyle fill:#4dabf7,stroke:#1864ab,stroke-width:2px,color:#fff
    classDef decisionStyle fill:#ffd43b,stroke:#fab005,stroke-width:2px
    classDef warningStyle fill:#ff922b,stroke:#e8590c,stroke-width:2px,color:#fff
    
    class QuarantineProduct,FailInspection,EmergencyProtocol,CondemnCylinder errorStyle
    class Success,PassInspection,UpdateQualityStatus,RecordInspection successStyle
    class BeginInspection,PressureTest,WeightVerification,CompileResults processStyle
    class TriggerType,SupplierHistory,OverallAssessment,DispositionOptions decisionStyle
    class SafetyProtocol,RequireRepair,NearExpiry,ImmediateAction warningStyle
```

## 🔄 Process Steps

### 1. Inspection Triggers and Planning

**Step 1.1: Trigger Management**
```yaml
Inspection Triggers:
  Receiving Inspection:
    - New shipments
    - Supplier deliveries
    - Transfer receipts
    - Return processing
    
  Periodic Inspection:
    - Age-based schedules
    - Usage cycles
    - Regulatory requirements
    - Risk assessments
    
  Event-Driven:
    - Customer complaints
    - Safety incidents
    - Quality alerts
    - Supplier issues
```

**Step 1.2: Sampling Strategy**
```yaml
Sampling Methods:
  Statistical Sampling:
    - AQL tables (Acceptable Quality Limit)
    - Confidence levels: 95%
    - Lot size considerations
    - Risk-based adjustments
    
  Supplier Classification:
    - New: 100% inspection
    - Certified: 2.5% AQL
    - Problem: 10% minimum
    - Critical products: 100%
    
  Sample Selection:
    - Random number generation
    - Stratified by lot
    - Representative coverage
    - Documentation required
```

### 2. Visual Inspection Process

**Step 2.1: External Inspection**
```yaml
Visual Inspection Points:
  Cylinder Body:
    - Dents and deformation
    - Corrosion assessment
    - Impact damage
    - Weld integrity
    - Surface defects
    
  Valve Assembly:
    - Valve body condition
    - Thread damage
    - Leak indicators
    - Safety devices
    - Proper seating
    
  Markings and Labels:
    - Manufacturer data
    - Test dates
    - Pressure ratings
    - Product identification
    - Regulatory compliance
```

**Step 2.2: Defect Classification**
```yaml
Defect Categories:
  Critical Defects:
    - Structural damage
    - Valve malfunction
    - Pressure loss
    - Safety device failure
    - Certification invalid
    
  Major Defects:
    - Significant corrosion
    - Thread damage
    - Marking illegibility
    - Base ring damage
    - Expired testing
    
  Minor Defects:
    - Surface rust
    - Paint damage
    - Label wear
    - Cosmetic issues
    - Documentation gaps
```

### 3. Functional Testing

**Step 3.1: Valve Testing**
```yaml
Valve Function Tests:
  Operation Test:
    - Open/close cycles: 3x
    - Torque requirements
    - Smooth operation
    - Full seating
    - No binding
    
  Leak Testing:
    - Soap bubble test
    - Pressure decay
    - Electronic detection
    - Thread inspection
    - Safety relief check
    
  Flow Testing:
    - Flow rate verification
    - Pressure drop
    - Regulator function
    - Safety shutoff
    - Gauge accuracy
```

**Step 3.2: Pressure Testing**
```yaml
Pressure Test Procedures:
  Test Requirements:
    - Test pressure: 1.5x working
    - Hold time: 1 minute minimum
    - Pressure drop: <2% allowed
    - Safety protocols mandatory
    - Certified equipment only
    
  Test Frequency:
    - Initial: All cylinders
    - Periodic: Per regulations
    - Post-repair: Mandatory
    - Incident: As required
    - Sample: Per AQL
```

### 4. Weight and Content Verification

**Step 4.1: Weight Checks**
```yaml
Weight Verification:
  Tare Weight:
    - Compare to stamped weight
    - Tolerance: ±2%
    - Investigation if exceeded
    - Update records
    - Verify modifications
    
  Gross Weight:
    - Full cylinder weight
    - Product weight calculation
    - Fill level verification
    - Overfill detection
    - Short fill identification
```

**Step 4.2: Content Analysis**
```yaml
Content Verification:
  Purity Testing:
    - Gas chromatography
    - Moisture content
    - Contamination check
    - Specification compliance
    - Certificate validation
    
  Medical Grade:
    - USP compliance
    - Purity >99.5%
    - Moisture <10 ppm
    - Oil-free verification
    - Lot traceability
```

### 5. Certification and Documentation

**Step 5.1: Certificate Validation**
```yaml
Certificate Requirements:
  Manufacturing Certificates:
    - Material test reports
    - Pressure test certificates
    - Compliance declarations
    - Quality assurance docs
    - Traceability records
    
  Regulatory Compliance:
    - DOT certification
    - ISO compliance
    - Local regulations
    - Industry standards
    - Customer specifications
```

**Step 5.2: Date Management**
```yaml
Critical Dates:
  Manufacturing Date:
    - Maximum age limits
    - Service life tracking
    - Retirement scheduling
    - Historical reference
    
  Test Dates:
    - Hydrostatic: 5-10 years
    - Visual: Annual
    - Valve: 5 years
    - Recertification required
    
  Expiry Management:
    - Product shelf life
    - Gas stability
    - Medical gas: 2-3 years
    - Industrial: 5-10 years
    - Near-expiry warnings
```

### 6. Disposition and Follow-up

**Step 6.1: Quality Decisions**
```yaml
Disposition Options:
  Pass - Good Status:
    - Clear for use
    - Update inventory
    - Reset inspection cycle
    - Document results
    
  Conditional Pass:
    - Limited use only
    - Repair required
    - Monitoring needed
    - Restricted applications
    
  Fail - Quarantine:
    - Immediate isolation
    - Investigation required
    - Repair assessment
    - Scrap evaluation
```

**Step 6.2: Corrective Actions**
```yaml
Action Management:
  Repair Process:
    - Repair feasibility
    - Cost justification
    - Vendor selection
    - Re-inspection required
    - Documentation update
    
  Scrap Process:
    - Decommissioning
    - Cylinder destruction
    - Material recovery
    - Documentation
    - Regulatory reporting
    
  Supplier Actions:
    - Quality feedback
    - Claim processing
    - Performance tracking
    - Improvement plans
    - Relationship review
```

### 7. Reporting and Analytics

**Step 7.1: Inspection Reporting**
```yaml
Report Generation:
  Individual Reports:
    - Inspection details
    - Test results
    - Photos/evidence
    - Disposition
    - Action items
    
  Batch Reports:
    - Summary statistics
    - Pass/fail rates
    - Defect analysis
    - Cost impact
    - Trend identification
```

**Step 7.2: Performance Metrics**
```yaml
Quality KPIs:
  Inspection Metrics:
    - First pass rate: >95%
    - Inspection cycle time
    - Defects per million
    - Cost of quality
    - Supplier ratings
    
  Trending Analysis:
    - Defect patterns
    - Supplier performance
    - Seasonal variations
    - Product reliability
    - Process capability
```

## 📋 Business Rules

### Inspection Standards
1. **Mandatory Inspection**: All cylinders on first receipt
2. **Sampling Plans**: Per MIL-STD-1916 or equivalent
3. **Inspector Qualification**: Certified and current
4. **Equipment Calibration**: Valid calibration required
5. **Documentation**: 100% traceability maintained

### Pass/Fail Criteria
1. **Critical Defects**: Automatic failure, zero tolerance
2. **Major Defects**: Maximum 1 per unit
3. **Minor Defects**: Maximum 3 per unit
4. **Pressure Test**: Must hold 100% for duration
5. **Certification**: All documents current and valid

### Quarantine Management
1. **Immediate Isolation**: Failed cylinders segregated
2. **Clear Identification**: Red tags and physical barriers
3. **Access Control**: QC personnel only
4. **Disposition Timeline**: 30 days maximum
5. **Documentation**: Complete audit trail

## 🔐 Security & Compliance

### Safety Protocols
- PPE requirements for all inspections
- Pressure testing behind safety barriers
- Emergency procedures documented
- Gas detection systems active
- Ventilation requirements met

### Regulatory Requirements
- DOT CFR 49 compliance
- OSHA workplace safety
- EPA environmental standards
- State and local regulations
- Industry standards (CGA, NFPA)

## 🔄 Integration Points

### System Interfaces
1. **Inventory System**: Quality status updates
2. **Supplier Portal**: Performance feedback
3. **Maintenance System**: Repair scheduling
4. **Regulatory Reporting**: Compliance data
5. **Customer Systems**: Quality certificates

### Data Exchange
- Real-time status updates
- Batch result processing
- Certificate generation
- Alert notifications
- Performance dashboards

## ⚡ Performance Optimization

### Efficiency Targets
- Visual inspection: <5 minutes/cylinder
- Pressure test: <3 minutes/cylinder
- Documentation: Real-time entry
- Report generation: <2 minutes
- Decision time: <10 minutes

### Process Improvements
- Mobile inspection apps
- Automated sampling
- Digital certificates
- Photo documentation
- Predictive analytics

## 🚨 Error Handling

### Common Issues
1. **Equipment Failure**: Backup equipment ready
2. **Certificate Missing**: Supplier follow-up process
3. **System Unavailable**: Offline inspection forms
4. **Safety Incident**: Emergency response protocol
5. **Discrepancy Found**: Investigation procedure

### Escalation Procedures
- Inspector → QC Supervisor
- QC Supervisor → Quality Manager
- Quality Manager → Safety Director
- Safety Director → Executive Team
- Regulatory notification as required

## 📊 Success Metrics

### Quality Indicators
- First pass rate: >95%
- Inspection accuracy: >99%
- Cycle time achievement: >90%
- Certificate compliance: 100%
- Customer complaints: <0.1%

### Business Impact
- Reduced safety incidents
- Improved customer confidence
- Lower warranty claims
- Regulatory compliance maintained
- Cost of quality optimized