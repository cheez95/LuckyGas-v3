# Payment Processing Workflow - Lucky Gas Legacy System

## 🎯 Workflow Purpose

The Payment Processing workflow manages the complete lifecycle of customer payments from receipt through allocation to specific invoices, ensuring accurate account updates, proper cash application, and timely financial reporting while supporting multiple payment channels common in Taiwan.

## 📊 Workflow Overview

```mermaid
graph TB
    Start([Payment Receipt]) --> PaymentSource{Payment Source?}
    
    PaymentSource -->|Bank Transfer| BankTransfer[Bank File Import]
    PaymentSource -->|Cash| CashPayment[Cash Receipt]
    PaymentSource -->|Check| CheckPayment[Check Receipt]
    PaymentSource -->|Credit Card| CardPayment[Card Processing]
    PaymentSource -->|Post-dated| PostDatedCheck[Post-dated Entry]
    
    %% Bank Transfer Path
    BankTransfer --> ImportBankFile[Import Bank Statement]
    ImportBankFile --> ParseTransactions[Parse Transactions]
    ParseTransactions --> MatchCustomer[Match to Customer]
    
    MatchCustomer --> CustomerFound{Customer Found?}
    CustomerFound -->|No| UnidentifiedPayment[Unidentified Payment Queue]
    CustomerFound -->|Yes| CreatePaymentRecord
    
    %% Cash Payment Path
    CashPayment --> VerifyCash[Verify Cash Amount]
    VerifyCash --> CountCash[Count and Validate]
    CountCash --> CashReceipt[Issue Cash Receipt]
    CashReceipt --> CreatePaymentRecord
    
    %% Check Payment Path
    CheckPayment --> ValidateCheck[Validate Check Details]
    ValidateCheck --> CheckValid{Check Valid?}
    CheckValid -->|No| RejectCheck[Reject Check]
    CheckValid -->|Yes| RecordCheckDetails[Record Check Info]
    
    RecordCheckDetails --> CheckType{Check Type?}
    CheckType -->|Current| CurrentCheck[Process Immediately]
    CheckType -->|Post-dated| ScheduleCheck[Schedule for Future]
    
    CurrentCheck --> CreatePaymentRecord
    ScheduleCheck --> PostDatedQueue[Post-dated Queue]
    
    %% Credit Card Path
    CardPayment --> AuthorizeCard[Authorize Card]
    AuthorizeCard --> AuthSuccess{Authorized?}
    AuthSuccess -->|No| DeclineCard[Decline Transaction]
    AuthSuccess -->|Yes| ProcessCardPayment[Process Payment]
    ProcessCardPayment --> CreatePaymentRecord
    
    %% Post-dated Check Path
    PostDatedCheck --> ValidateFutureDate[Validate Future Date]
    ValidateFutureDate --> RecordPDC[Record PDC Details]
    RecordPDC --> PDCVault[Store in PDC Vault]
    PDCVault --> PostDatedQueue
    
    PostDatedQueue --> CheckMaturity[Check Maturity Daily]
    CheckMaturity --> IsMature{Due Date Reached?}
    IsMature -->|No| WaitNextDay[Wait Next Day]
    IsMature -->|Yes| CreatePaymentRecord
    
    %% Create Payment Record
    CreatePaymentRecord[Create Payment Record] --> AssignPaymentID[Assign Payment ID]
    AssignPaymentID --> RecordPaymentDetails[Record Payment Details]
    
    RecordPaymentDetails --> PaymentData{Payment Data}
    PaymentData --> SetPaymentDate[Payment Date]
    SetPaymentDate --> SetCustomerID[Customer ID]
    SetCustomerID --> SetPaymentType[Payment Type]
    SetPaymentType --> SetAmount[Payment Amount]
    SetAmount --> SetReference[Reference Number]
    SetReference --> SetBankDetails[Bank/Check Details]
    
    %% Validation
    SetBankDetails --> ValidatePayment[Validate Payment Data]
    ValidatePayment --> ValidationCheck{Valid?}
    
    ValidationCheck -->|No| PaymentError[Payment Error]
    ValidationCheck -->|Yes| CheckDuplicate[Check Duplicate]
    
    CheckDuplicate --> IsDuplicate{Duplicate?}
    IsDuplicate -->|Yes| DuplicateWarning[Duplicate Warning]
    IsDuplicate -->|No| SavePayment[Save Payment]
    
    DuplicateWarning --> OverrideDuplicate{Override?}
    OverrideDuplicate -->|No| RejectDuplicate[Reject Payment]
    OverrideDuplicate -->|Yes| SavePayment
    
    %% Customer Account Update
    SavePayment --> UpdateCustomerAccount[Update Customer Account]
    UpdateCustomerAccount --> GetCurrentBalance[Get Current Balance]
    GetCurrentBalance --> CheckCreditLimit[Check Credit Status]
    
    CheckCreditLimit --> CreditHold{On Credit Hold?}
    CreditHold -->|Yes| EvaluateRelease[Evaluate Hold Release]
    CreditHold -->|No| ProceedAllocation
    
    EvaluateRelease --> ReleaseHold{Release Hold?}
    ReleaseHold -->|Yes| ReleaseCreditHold[Release Credit Hold]
    ReleaseHold -->|No| MaintainHold[Maintain Hold]
    
    ReleaseCreditHold --> ProceedAllocation
    MaintainHold --> ProceedAllocation
    
    %% Payment Allocation
    ProceedAllocation[Proceed to Allocation] --> AllocationStrategy{Allocation Method?}
    
    AllocationStrategy -->|Auto| AutoAllocation[Automatic Allocation]
    AllocationStrategy -->|Manual| ManualAllocation[Manual Allocation]
    AllocationStrategy -->|None| UnappliedPayment[Hold as Unapplied]
    
    %% Automatic Allocation
    AutoAllocation --> GetOpenInvoices[Get Open Invoices]
    GetOpenInvoices --> SortInvoices[Sort by Strategy]
    
    SortInvoices --> SortMethod{Sort Method?}
    SortMethod -->|FIFO| SortByDate[Sort by Invoice Date]
    SortMethod -->|Due Date| SortByDueDate[Sort by Due Date]
    SortMethod -->|Amount| SortByAmount[Sort by Amount]
    
    SortByDate --> AllocateLoop
    SortByDueDate --> AllocateLoop
    SortByAmount --> AllocateLoop
    
    AllocateLoop[Allocation Loop] --> NextInvoice{Next Invoice?}
    NextInvoice -->|No| AllocationComplete
    NextInvoice -->|Yes| CheckInvoiceBalance[Check Invoice Balance]
    
    CheckInvoiceBalance --> CalculateAllocation[Calculate Allocation Amount]
    CalculateAllocation --> PaymentRemaining{Payment Remaining?}
    
    PaymentRemaining -->|Full| AllocateFull[Allocate Full Invoice]
    PaymentRemaining -->|Partial| AllocatePartial[Allocate Partial]
    PaymentRemaining -->|None| AllocationComplete
    
    AllocateFull --> UpdateInvoiceStatus[Update Invoice Status]
    AllocatePartial --> UpdateInvoiceBalance[Update Invoice Balance]
    
    UpdateInvoiceStatus --> RecordAllocation
    UpdateInvoiceBalance --> RecordAllocation
    
    RecordAllocation[Record Allocation] --> AllocationDetails{Allocation Details}
    AllocationDetails --> LinkPaymentInvoice[Link Payment-Invoice]
    LinkPaymentInvoice --> SetAllocatedAmount[Set Allocated Amount]
    SetAllocatedAmount --> SetAllocationDate[Set Allocation Date]
    SetAllocationDate --> CheckDiscount[Check Early Payment Discount]
    
    CheckDiscount --> DiscountApplicable{Discount Applicable?}
    DiscountApplicable -->|Yes| CalculateDiscount[Calculate Discount]
    DiscountApplicable -->|No| NoDiscount[No Discount]
    
    CalculateDiscount --> ApplyDiscount[Apply Discount]
    ApplyDiscount --> UpdatePaymentAmount[Adjust Payment Amount]
    UpdatePaymentAmount --> AllocateLoop
    
    NoDiscount --> AllocateLoop
    
    %% Manual Allocation
    ManualAllocation --> SelectInvoices[Select Target Invoices]
    SelectInvoices --> SpecifyAmounts[Specify Allocation Amounts]
    SpecifyAmounts --> ValidateAllocations[Validate Allocations]
    
    ValidateAllocations --> AllocationsValid{Valid?}
    AllocationsValid -->|No| AllocationError[Show Errors]
    AllocationsValid -->|Yes| ApplyManualAllocations[Apply Allocations]
    
    AllocationError --> SpecifyAmounts
    ApplyManualAllocations --> RecordAllocation
    
    %% Unapplied Payment
    UnappliedPayment --> RecordUnapplied[Record as Unapplied]
    RecordUnapplied --> SetForFutureUse[Available for Future]
    SetForFutureUse --> AllocationComplete
    
    %% Allocation Complete
    AllocationComplete[Allocation Complete] --> CalculateTotals[Calculate Totals]
    CalculateTotals --> TotalAllocated[Total Allocated Amount]
    TotalAllocated --> TotalUnallocated[Total Unallocated]
    TotalUnallocated --> UpdatePaymentStatus[Update Payment Status]
    
    %% Generate Receipt
    UpdatePaymentStatus --> GenerateReceipt{Generate Receipt?}
    GenerateReceipt -->|Yes| CreateReceipt[Create Receipt Document]
    GenerateReceipt -->|No| SkipReceipt[Skip Receipt]
    
    CreateReceipt --> ReceiptFormat{Format?}
    ReceiptFormat -->|Print| PrintReceipt[Print Receipt]
    ReceiptFormat -->|Email| EmailReceipt[Email Receipt]
    ReceiptFormat -->|Both| BothFormats[Print & Email]
    
    PrintReceipt --> DeliveryComplete
    EmailReceipt --> DeliveryComplete
    BothFormats --> DeliveryComplete
    SkipReceipt --> DeliveryComplete
    
    %% Update AR Aging
    DeliveryComplete[Delivery Complete] --> UpdateARAging[Update AR Aging]
    UpdateARAging --> RecalculateAging[Recalculate Aging Buckets]
    RecalculateAging --> UpdateDSO[Update DSO Metrics]
    UpdateDSO --> CheckCollectionStatus[Check Collection Status]
    
    CheckCollectionStatus --> InCollection{In Collection?}
    InCollection -->|Yes| UpdateCollectionCase[Update Collection Case]
    InCollection -->|No| NormalStatus[Maintain Normal Status]
    
    UpdateCollectionCase --> NotifyCollector[Notify Collector]
    NotifyCollector --> PostToGL
    NormalStatus --> PostToGL
    
    %% GL Posting
    PostToGL[Post to General Ledger] --> CreateJournalEntry[Create Journal Entry]
    CreateJournalEntry --> JournalLines{Journal Lines}
    
    JournalLines --> DebitLine[Dr: Cash/Bank]
    DebitLine --> CreditLine[Cr: Accounts Receivable]
    CreditLine --> DiscountLine[Dr: Discount (if any)]
    
    DiscountLine --> ValidateJournal[Validate Journal]
    ValidateJournal --> JournalBalanced{Balanced?}
    
    JournalBalanced -->|No| JournalError[Journal Error]
    JournalBalanced -->|Yes| PostJournal[Post Journal]
    
    PostJournal --> UpdateGLStatus[Update GL Status]
    UpdateGLStatus --> NotifyAccounting[Notify Accounting]
    
    %% Bank Reconciliation
    NotifyAccounting --> BankReconciliation[Bank Reconciliation Queue]
    BankReconciliation --> MatchBankStatement[Match to Statement]
    MatchBankStatement --> ReconcileItems[Reconcile Items]
    
    %% Customer Notification
    ReconcileItems --> NotifyCustomer[Notify Customer]
    NotifyCustomer --> NotificationMethod{Method?}
    
    NotificationMethod -->|Email| SendEmailConfirm[Send Email]
    NotificationMethod -->|SMS| SendSMSConfirm[Send SMS]
    NotificationMethod -->|Portal| UpdatePortal[Update Portal]
    NotificationMethod -->|None| NoNotification[No Notification]
    
    SendEmailConfirm --> LogCommunication
    SendSMSConfirm --> LogCommunication
    UpdatePortal --> LogCommunication
    NoNotification --> LogCommunication[Log Communication]
    
    %% Complete Process
    LogCommunication --> UpdateReports[Update Reports]
    UpdateReports --> RefreshDashboard[Refresh Dashboard]
    RefreshDashboard --> Success[Payment Processed]
    
    %% Error Handling
    UnidentifiedPayment --> ManualMatch[Manual Matching]
    ManualMatch --> MatchFound{Match Found?}
    MatchFound -->|Yes| CreatePaymentRecord
    MatchFound -->|No| SuspenseAccount[Post to Suspense]
    
    RejectCheck --> ReturnToCustomer[Return Check]
    DeclineCard --> NotifyDecline[Notify Customer]
    PaymentError --> ErrorLog[Log Error]
    RejectDuplicate --> End
    JournalError --> ManualCorrection[Manual Correction]
    
    SuspenseAccount --> End([End])
    ReturnToCustomer --> End
    NotifyDecline --> End
    ErrorLog --> End
    ManualCorrection --> End
    WaitNextDay --> End
    Success --> End
    
    %% Styling
    classDef errorStyle fill:#ff6b6b,stroke:#c92a2a,stroke-width:2px,color:#fff
    classDef successStyle fill:#51cf66,stroke:#2f9e44,stroke-width:2px,color:#fff
    classDef processStyle fill:#4dabf7,stroke:#1864ab,stroke-width:2px,color:#fff
    classDef decisionStyle fill:#ffd43b,stroke:#fab005,stroke-width:2px
    classDef warningStyle fill:#ff922b,stroke:#e8590c,stroke-width:2px,color:#fff
    
    class RejectCheck,DeclineCard,PaymentError,RejectDuplicate,JournalError,ErrorLog errorStyle
    class Success,UpdatePaymentStatus,PostJournal successStyle
    class CreatePaymentRecord,SavePayment,AutoAllocation,RecordAllocation processStyle
    class PaymentSource,CustomerFound,ValidationCheck,AllocationStrategy,JournalBalanced decisionStyle
    class UnidentifiedPayment,DuplicateWarning,ManualCorrection warningStyle
```

## 🔄 Process Steps

### 1. Payment Receipt

**Step 1.1: Payment Channels**
```yaml
Bank Transfer:
  - Electronic fund transfer
  - ACH payments
  - Wire transfers
  - Mobile banking apps
  - ATM deposits
  
Cash Payments:
  - Office counter
  - Driver collection
  - Bank deposit
  - Drop box
  
Check Payments:
  - Personal checks
  - Company checks
  - Cashier's checks
  - Post-dated checks
  
Credit Cards:
  - Online portal
  - Phone payments
  - Recurring charges
  - POS terminals
```

**Step 1.2: Payment Identification**
```yaml
Required Information:
  - Customer identification
  - Payment amount
  - Payment date
  - Reference number
  - Payment method
  
Validation Rules:
  - Positive amount
  - Valid customer
  - Future date check
  - Duplicate detection
```

### 2. Payment Recording

**Step 2.1: Data Entry**
```yaml
Manual Entry:
  - Payment form completion
  - Customer selection
  - Amount verification
  - Reference recording
  
Automated Import:
  - Bank file parsing
  - Format validation
  - Exception handling
  - Batch processing
```

**Step 2.2: Validation Process**
```yaml
System Checks:
  - Customer existence
  - Amount validation
  - Date validation
  - Duplicate check
  - Currency validation
  
Business Rules:
  - Payment limits
  - Method restrictions
  - Approval requirements
  - Hold conditions
```

### 3. Payment Allocation

**Step 3.1: Allocation Strategies**
```yaml
FIFO (First In First Out):
  - Oldest invoices first
  - Default method
  - Automatic process
  - Clear aging
  
Due Date Priority:
  - Most overdue first
  - Minimize penalties
  - Collection focus
  - Risk reduction
  
Manual Selection:
  - User specified
  - Customer request
  - Dispute resolution
  - Special handling
  
Hold Unapplied:
  - Future use
  - Disputed amounts
  - Advance payments
  - Credit balance
```

**Step 3.2: Discount Handling**
```yaml
Early Payment Discount:
  Terms: "2/10 Net 30"
  Calculation:
    - Check payment date
    - Verify within discount period
    - Calculate discount amount
    - Apply to invoice
    - Adjust payment allocation
    
  Documentation:
    - Discount taken
    - GL posting
    - Customer notification
```

### 4. Account Updates

**Step 4.1: Balance Adjustments**
```yaml
Customer Account:
  - Reduce AR balance
  - Update aging
  - Refresh credit available
  - Update payment history
  
Invoice Status:
  - Mark paid/partial
  - Update balance
  - Record payment date
  - Link payment record
```

**Step 4.2: Credit Management**
```yaml
Credit Hold Release:
  Conditions:
    - Payment covers overdue
    - Below credit limit
    - Management approval
    - Hold period expired
    
  Actions:
    - Remove hold flag
    - Notify sales team
    - Update system status
    - Enable new orders
```

### 5. Receipt Generation

**Step 5.1: Receipt Creation**
```yaml
Receipt Information:
  Header:
    - Company name and logo
    - Receipt number
    - Date and time
    - Customer details
    
  Payment Details:
    - Payment method
    - Amount received
    - Reference number
    - Applied invoices
    
  Footer:
    - Authorized signature
    - Terms and conditions
    - Contact information
```

**Step 5.2: Delivery Methods**
```yaml
Print Receipt:
  - Immediate printing
  - Pre-numbered forms
  - Duplicate copies
  - Filing system
  
Email Receipt:
  - PDF generation
  - Automated sending
  - Read confirmation
  - Archive copy
  
Customer Portal:
  - Online access
  - Download option
  - Payment history
  - Real-time update
```

### 6. GL Integration

**Step 6.1: Journal Creation**
```yaml
Standard Entry:
  Dr: Cash/Bank Account    XXX
  Cr: Accounts Receivable     XXX
  
With Discount:
  Dr: Cash/Bank Account    XXX
  Dr: Sales Discount       XXX
  Cr: Accounts Receivable     XXX
  
Posting Rules:
  - Same day posting
  - Batch by payment type
  - Department allocation
  - Project tracking
```

**Step 6.2: Bank Reconciliation**
```yaml
Reconciliation Process:
  - Import bank statement
  - Match payments
  - Identify variances
  - Clear reconciled items
  
Timing:
  - Daily for major accounts
  - Weekly for others
  - Monthly close required
  - Audit trail maintained
```

## 📋 Business Rules

### Payment Acceptance
1. **Minimum Payment**: Accept any amount > 0
2. **Maximum Limits**: Based on payment method
3. **Currency**: TWD only, unless approved
4. **Post-dated Limit**: Maximum 90 days future
5. **NSF History**: Check bounce history

### Allocation Rules
1. **Auto-allocation**: FIFO unless specified
2. **Partial Payment**: Apply to oldest first
3. **Overpayment**: Hold as credit balance
4. **Disputed Amount**: Exclude from auto-allocation
5. **Write-off Limit**: < NT$100 automatic

### Approval Requirements
1. **Large Payments**: > NT$1,000,000 needs verification
2. **Unusual Method**: Manager approval required
3. **Credit Release**: Based on payment coverage
4. **Discount Override**: Supervisor approval
5. **Adjustment Entry**: Finance manager only

## 🔐 Security & Compliance

### Access Control
- Payment entry: AR clerks
- Allocation override: Supervisors
- Void payment: Managers only
- GL posting: Automated only
- Reports: Role-based access

### Audit Requirements
- All payments logged
- Changes tracked
- Approvals recorded
- Void reason required
- Daily reconciliation

### Compliance
- Tax regulations
- Banking laws
- Anti-money laundering
- Data privacy
- Internal controls

## 🔄 Integration Points

### Internal Systems
1. **Customer Master**: Validate customer
2. **Invoice System**: Get open invoices
3. **Credit Management**: Check limits
4. **GL System**: Post entries
5. **Banking Interface**: Import files

### External Systems
1. **Bank APIs**: Real-time verification
2. **Credit Card Gateway**: Authorization
3. **Customer Portal**: Payment submission
4. **Collection Agency**: Update status

## ⚡ Performance Optimization

### Processing Efficiency
- Batch import processing
- Indexed customer lookup
- Cached open invoices
- Parallel allocation
- Async GL posting

### Response Times
- Payment entry: < 2 seconds
- Auto-allocation: < 5 seconds
- Receipt generation: < 3 seconds
- GL posting: < 10 seconds batch

## 🚨 Error Handling

### Common Issues
1. **Unidentified Payment**: Manual matching queue
2. **Insufficient Amount**: Partial allocation
3. **System Timeout**: Retry mechanism
4. **Duplicate Payment**: Warning and override
5. **GL Imbalance**: Suspend and alert

### Recovery Procedures
- Transaction rollback
- Payment reversal process
- Manual allocation option
- Supervisor override
- Audit trail complete

## 📊 Success Metrics

### Operational Metrics
- Payment processing time: < 5 minutes
- Auto-match rate: > 90%
- Same-day posting: > 95%
- Receipt delivery: 100%

### Business Metrics
- DSO improvement: Target 45 days
- Collection effectiveness: > 98%
- Payment accuracy: > 99.5%
- Customer satisfaction: > 90%