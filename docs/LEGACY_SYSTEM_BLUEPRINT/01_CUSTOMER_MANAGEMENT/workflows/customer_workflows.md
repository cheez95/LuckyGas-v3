# Customer Management Workflows

## 🔄 Core Business Workflows

### 1. New Customer Registration Workflow

```mermaid
flowchart TD
    Start([Customer Contact]) --> Check{Existing<br/>Customer?}
    
    Check -->|Yes| Update[Update Information<br/>if Needed]
    Check -->|No| NewCust[Click 新增客戶]
    
    NewCust --> BasicInfo[Fill Basic Information<br/>- Name 客戶名稱<br/>- Type 客戶類型<br/>- Tax ID 統一編號]
    
    BasicInfo --> Validate1{Validate<br/>Tax ID?}
    Validate1 -->|Invalid| BasicInfo
    Validate1 -->|Valid| ContactInfo
    
    ContactInfo[Fill Contact Info<br/>- Phone 電話<br/>- Mobile 手機<br/>- Contact Person 聯絡人] --> AddressInfo
    
    AddressInfo[Fill Address Info<br/>- Postal Code 郵遞區號<br/>- City/District 縣市/區<br/>- Street Address 地址] --> DeliveryCheck{Same as<br/>Registration?}
    
    DeliveryCheck -->|No| DeliveryInfo[Fill Delivery Address<br/>- Delivery Zone 配送區域<br/>- Special Instructions 備註]
    DeliveryCheck -->|Yes| FinancialInfo
    DeliveryInfo --> FinancialInfo
    
    FinancialInfo[Set Financial Terms<br/>- Payment Terms 付款條件<br/>- Credit Limit 信用額度<br/>- Price Level 價格等級] --> SaveAttempt
    
    SaveAttempt[Save Customer] --> SaveCheck{Save<br/>Successful?}
    
    SaveCheck -->|No| ErrorMsg[Show Error<br/>Message]
    ErrorMsg --> BasicInfo
    
    SaveCheck -->|Yes| GenerateCode[System Generates<br/>Customer Code<br/>C000001]
    
    GenerateCode --> CreditCheck{Credit Limit<br/>> 50,000?}
    
    CreditCheck -->|Yes| ManagerApproval[Manager<br/>Approval Required]
    CreditCheck -->|No| Complete
    
    ManagerApproval --> ApprovalCheck{Approved?}
    ApprovalCheck -->|No| FinancialInfo
    ApprovalCheck -->|Yes| Complete
    
    Complete[Customer Ready<br/>for Orders] --> End([End])
    Update --> End
    
    style Start fill:#90EE90
    style End fill:#FFB6C1
    style GenerateCode fill:#87CEEB
    style ManagerApproval fill:#FFD700
```

### 2. Customer Search and Inquiry Workflow

```mermaid
flowchart TD
    Start([Customer Inquiry]) --> SearchType{Search<br/>Method?}
    
    SearchType -->|Quick| QuickSearch[Enter Phone Number<br/>or Customer Code]
    SearchType -->|Advanced| AdvSearch[Enter Multiple Criteria<br/>- Name<br/>- Address<br/>- Tax ID]
    
    QuickSearch --> ExecuteSearch1[Execute Search]
    AdvSearch --> ExecuteSearch2[Execute Search]
    
    ExecuteSearch1 --> Results{Results<br/>Found?}
    ExecuteSearch2 --> Results
    
    Results -->|No| NoResults[Display<br/>'No Records Found']
    Results -->|Single| SingleResult[Display Customer<br/>Details]
    Results -->|Multiple| MultiResults[Display Result<br/>Grid]
    
    NoResults --> Retry{Try<br/>Again?}
    Retry -->|Yes| SearchType
    Retry -->|No| End([End])
    
    MultiResults --> Select[Select Customer<br/>from List]
    Select --> SingleResult
    
    SingleResult --> Actions{Customer<br/>Action?}
    
    Actions -->|View Orders| OrderHistory[Display Order<br/>History]
    Actions -->|Check Balance| Balance[Show Outstanding<br/>Balance]
    Actions -->|Update Info| UpdateFlow[Enter Edit<br/>Mode]
    Actions -->|Print| PrintReport[Generate Customer<br/>Report]
    
    OrderHistory --> MoreActions{More<br/>Actions?}
    Balance --> MoreActions
    UpdateFlow --> SaveChanges[Save Updated<br/>Information]
    PrintReport --> MoreActions
    
    SaveChanges --> MoreActions
    
    MoreActions -->|Yes| Actions
    MoreActions -->|No| End
    
    style Start fill:#90EE90
    style End fill:#FFB6C1
    style SingleResult fill:#87CEEB
```

### 3. Customer Update Workflow

```mermaid
flowchart TD
    Start([Update Request]) --> FindCustomer[Search and Select<br/>Customer]
    
    FindCustomer --> LoadData[Load Customer<br/>Data into Form]
    
    LoadData --> TabSelect{Which<br/>Tab?}
    
    TabSelect -->|Basic| BasicTab[基本資料 Tab<br/>- Name<br/>- Type<br/>- Tax ID]
    TabSelect -->|Contact| ContactTab[聯絡資訊 Tab<br/>- Phone<br/>- Email<br/>- Contact Person]
    TabSelect -->|Delivery| DeliveryTab[配送資訊 Tab<br/>- Address<br/>- Zone<br/>- Instructions]
    TabSelect -->|Payment| PaymentTab[付款資訊 Tab<br/>- Terms<br/>- Credit Limit<br/>- Invoice Type]
    
    BasicTab --> MakeChanges1[Make Changes]
    ContactTab --> MakeChanges2[Make Changes]
    DeliveryTab --> MakeChanges3[Make Changes]
    PaymentTab --> MakeChanges4[Make Changes]
    
    MakeChanges1 --> ValidateChanges
    MakeChanges2 --> ValidateChanges
    MakeChanges3 --> ValidateChanges
    MakeChanges4 --> ValidateChanges
    
    ValidateChanges{Validate<br/>Changes} -->|Invalid| ShowErrors[Display Validation<br/>Errors]
    ShowErrors --> TabSelect
    
    ValidateChanges -->|Valid| CreditChange{Credit Limit<br/>Changed?}
    
    CreditChange -->|No| SaveChanges
    CreditChange -->|Yes| CheckNewLimit{New Limit<br/>> 50,000?}
    
    CheckNewLimit -->|No| SaveChanges
    CheckNewLimit -->|Yes| ManagerApprove[Require Manager<br/>Approval]
    
    ManagerApprove --> Approved{Approved?}
    Approved -->|No| TabSelect
    Approved -->|Yes| SaveChanges
    
    SaveChanges[Save to Database] --> UpdateAudit[Update Audit Fields<br/>- UPDATE_USER<br/>- UPDATE_DATE]
    
    UpdateAudit --> Success{Save<br/>Successful?}
    
    Success -->|No| ErrorHandle[Handle Error<br/>Show Message]
    Success -->|Yes| RefreshDisplay[Refresh Customer<br/>Display]
    
    ErrorHandle --> TabSelect
    RefreshDisplay --> End([Update Complete])
    
    style Start fill:#90EE90
    style End fill:#FFB6C1
    style ManagerApprove fill:#FFD700
```

### 4. Customer Deactivation/Deletion Workflow

```mermaid
flowchart TD
    Start([Deactivation Request]) --> FindCust[Search and Select<br/>Customer]
    
    FindCust --> CheckStatus{Check<br/>Dependencies}
    
    CheckStatus --> ActiveOrders{Active<br/>Orders?}
    ActiveOrders -->|Yes| BlockDelete[Cannot Delete<br/>Active Orders Exist]
    ActiveOrders -->|No| Outstanding{Outstanding<br/>Balance?}
    
    BlockDelete --> End1([Cancel Operation])
    
    Outstanding -->|Yes| BlockDelete2[Cannot Delete<br/>Outstanding Balance]
    Outstanding -->|No| Cylinders{Cylinders<br/>On Loan?}
    
    BlockDelete2 --> End1
    
    Cylinders -->|Yes| BlockDelete3[Cannot Delete<br/>Cylinders Not Returned]
    Cylinders -->|No| ProceedDelete
    
    BlockDelete3 --> End1
    
    ProceedDelete[Display Delete<br/>Confirmation] --> Reason[Enter Reason<br/>for Deletion]
    
    Reason --> FinalConfirm{Final<br/>Confirmation}
    
    FinalConfirm -->|Cancel| End1
    FinalConfirm -->|Confirm| DeleteType{Delete<br/>Type?}
    
    DeleteType -->|Soft Delete| SoftDelete[Set DELETE_FLAG = 'Y'<br/>Status = '02:停用']
    DeleteType -->|Blacklist| Blacklist[Status = '03:黑名單'<br/>Enter Blacklist Reason]
    
    SoftDelete --> AuditLog[Create Audit Log<br/>- User<br/>- Timestamp<br/>- Reason]
    Blacklist --> AuditLog
    
    AuditLog --> NotifyTeam[Notify Relevant<br/>Team Members]
    
    NotifyTeam --> End2([Deactivation Complete])
    
    style Start fill:#90EE90
    style End1 fill:#FFB6C1
    style End2 fill:#FFB6C1
    style BlockDelete fill:#FF6347
    style BlockDelete2 fill:#FF6347
    style BlockDelete3 fill:#FF6347
```

## 📊 Reporting Workflows

### 5. Customer Report Generation Workflow

```mermaid
flowchart TD
    Start([Report Request]) --> ReportType{Select Report<br/>Type}
    
    ReportType -->|Customer List| ListReport[客戶清單]
    ReportType -->|Transaction History| TransReport[客戶交易記錄]
    ReportType -->|Statistical Analysis| StatsReport[客戶統計分析]
    
    ListReport --> ListCriteria[Set Criteria<br/>- Status<br/>- Zone<br/>- Type]
    TransReport --> TransCriteria[Set Criteria<br/>- Date Range<br/>- Customer<br/>- Product]
    StatsReport --> StatsCriteria[Set Criteria<br/>- Period<br/>- Metrics<br/>- Grouping]
    
    ListCriteria --> Generate1[Generate Report]
    TransCriteria --> Generate2[Generate Report]
    StatsCriteria --> Generate3[Generate Report]
    
    Generate1 --> Display
    Generate2 --> Display
    Generate3 --> Display
    
    Display[Display Report<br/>Preview] --> ExportOptions{Export<br/>Format?}
    
    ExportOptions -->|View Only| ViewReport[Display in<br/>Grid View]
    ExportOptions -->|Excel| ExcelExport[Export to<br/>Excel File]
    ExportOptions -->|PDF| PDFExport[Export to<br/>PDF File]
    ExportOptions -->|CSV| CSVExport[Export to<br/>CSV File]
    ExportOptions -->|Print| PrintPreview[Print Preview<br/>Window]
    
    ViewReport --> End([Complete])
    ExcelExport --> Download[Download File]
    PDFExport --> Download
    CSVExport --> Download
    PrintPreview --> Print[Send to Printer]
    
    Download --> End
    Print --> End
    
    style Start fill:#90EE90
    style End fill:#FFB6C1
    style Display fill:#87CEEB
```

## 🔐 Validation Rules

### Field Validation Matrix

| Field | Validation Rule | Error Message |
|-------|----------------|---------------|
| Tax ID (統一編號) | 8 digits, checksum validation | "統一編號格式錯誤" |
| Phone (電話) | Taiwan landline format | "電話號碼格式錯誤" |
| Mobile (手機) | 09XX-XXX-XXX format | "手機號碼格式錯誤" |
| Email | Standard email regex | "Email格式錯誤" |
| Postal Code | 3 or 5 digits | "郵遞區號格式錯誤" |
| Credit Limit | Numeric, > 0 | "信用額度必須大於0" |

### Business Rule Validations

1. **Duplicate Prevention**
   - Check Tax ID uniqueness (business customers)
   - Warning on duplicate phone numbers
   - Check for similar names (fuzzy match)

2. **Credit Management**
   - Default limit: NT$ 10,000
   - Limits > NT$ 50,000 require manager approval
   - Cannot exceed limit on new orders

3. **Address Validation**
   - Postal code must match city/district
   - Delivery zone must be active service area
   - Multiple addresses allowed per customer

4. **Status Management**
   - Cannot delete with active orders
   - Cannot delete with outstanding balance
   - Blacklist prevents all transactions

## 🚨 Exception Handling

### Common Exceptions and Resolutions

```mermaid
flowchart TD
    Error[Exception Occurs] --> ErrorType{Error Type}
    
    ErrorType -->|Duplicate Tax ID| Dup1[Show "統一編號已存在"<br/>Display Existing Customer]
    ErrorType -->|Invalid Format| Format1[Show Field-Specific<br/>Error Message]
    ErrorType -->|Credit Limit| Credit1[Route to Manager<br/>Approval Workflow]
    ErrorType -->|System Error| System1[Log Error<br/>Show Generic Message]
    
    Dup1 --> Resolution1[Option to Update<br/>Existing Record]
    Format1 --> Resolution2[Highlight Field<br/>Show Correct Format]
    Credit1 --> Resolution3[Wait for Approval<br/>or Reduce Limit]
    System1 --> Resolution4[Retry Operation<br/>or Contact IT]
    
    Resolution1 --> Continue[Continue Process]
    Resolution2 --> Continue
    Resolution3 --> Continue
    Resolution4 --> Continue
    
    style Error fill:#FF6347
    style Continue fill:#90EE90
```

## 💡 Best Practices

### For Customer Service Staff

1. **Always Search First**
   - Prevents duplicate records
   - Finds existing customer quickly
   - Updates are better than new records

2. **Complete Information**
   - Fill all required fields
   - Verify phone numbers
   - Confirm delivery addresses

3. **Notes Are Important**
   - Document special requirements
   - Record customer preferences
   - Note any issues or concerns

### For Managers

1. **Regular Reviews**
   - Check credit limit utilization
   - Review blacklisted customers
   - Monitor inactive accounts

2. **Approval Workflows**
   - Respond to credit approvals promptly
   - Document approval reasons
   - Review patterns for policy updates

3. **Report Analysis**
   - Weekly customer acquisition reports
   - Monthly retention analysis
   - Quarterly business reviews

---

These workflows represent the current state of the Lucky Gas customer management system. Each workflow includes validation points, error handling, and business rule enforcement as implemented in the legacy system.