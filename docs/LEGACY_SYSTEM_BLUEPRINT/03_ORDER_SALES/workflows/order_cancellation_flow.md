# Order Cancellation Flow (訂單取消流程)

**Process Code**: ORDER_FLOW_003  
**Business Critical**: ⭐⭐⭐⭐ (Financial and customer impact)  
**Average Duration**: 2-5 minutes depending on status  
**Cancellation Rate**: 3-5% of all orders

## 📋 Overview

The order cancellation flow manages the systematic cancellation of orders while ensuring proper inventory release, credit restoration, customer notification, and financial reconciliation. The complexity varies significantly based on the order's current status.

## 🔄 Process Flow

```mermaid
graph TD
    Start([Cancellation Request<br/>取消要求]) --> A[Receive Request<br/>接收要求]
    
    A --> B{Request Source?<br/>要求來源?}
    B -->|Customer<br/>客戶| C[Verify Identity<br/>驗證身份]
    B -->|Internal<br/>內部| D[Check Authority<br/>檢查權限]
    B -->|System<br/>系統| E[Auto Trigger<br/>自動觸發]
    
    C --> F{Verification OK?<br/>驗證成功?}
    F -->|No<br/>否| G[Reject Request<br/>拒絕要求]
    F -->|Yes<br/>是| H[Find Order<br/>查找訂單]
    
    D --> H
    E --> H
    G --> End1([End Process<br/>結束流程])
    
    H --> I{Order Found?<br/>找到訂單?}
    I -->|No<br/>否| J[Error Response<br/>錯誤回應]
    I -->|Yes<br/>是| K[Load Order Details<br/>載入訂單明細]
    
    J --> End1
    
    K --> L[Check Current Status<br/>檢查當前狀態]
    
    L --> M{Order Status?<br/>訂單狀態?}
    M -->|Draft<br/>草稿| N[Simple Cancel<br/>簡單取消]
    M -->|Confirmed<br/>已確認| O[Standard Cancel<br/>標準取消]
    M -->|Dispatched<br/>已派送| P[Complex Cancel<br/>複雜取消]
    M -->|In Delivery<br/>配送中| Q[Emergency Cancel<br/>緊急取消]
    M -->|Delivered<br/>已送達| R[Return Process<br/>退貨流程]
    M -->|Cancelled<br/>已取消| S[Already Cancelled<br/>已經取消]
    
    S --> T[Show Message<br/>顯示訊息]
    T --> End1
    
    N --> U[Delete Draft<br/>刪除草稿]
    U --> V[Release Resources<br/>釋放資源]
    
    O --> W[Reason Required<br/>需要原因]
    W --> X{Reason Valid?<br/>原因有效?}
    X -->|No<br/>否| Y[Request Reason<br/>要求原因]
    X -->|Yes<br/>是| Z[Process Standard<br/>處理標準]
    
    Y --> W
    
    P --> AA[Check Dispatch<br/>檢查派送]
    AA --> AB{Can Recall?<br/>可召回?}
    AB -->|Yes<br/>是| AC[Recall Order<br/>召回訂單]
    AB -->|No<br/>否| AD[Manager Approval<br/>主管核准]
    
    Q --> AE[Urgent Check<br/>緊急檢查]
    AE --> AF{Driver Status?<br/>司機狀態?}
    AF -->|Not Arrived<br/>未到達| AG[Stop Delivery<br/>停止配送]
    AF -->|At Location<br/>在現場| AH[Contact Driver<br/>聯絡司機]
    AF -->|Completed<br/>已完成| R
    
    R --> AI[Return Authorization<br/>退貨授權]
    AI --> AJ{Return Approved?<br/>退貨核准?}
    AJ -->|No<br/>否| AK[Explain Policy<br/>說明政策]
    AJ -->|Yes<br/>是| AL[Schedule Pickup<br/>安排取貨]
    
    AK --> End1
    
    Z --> AM[Calculate Refund<br/>計算退款]
    AC --> AM
    AD --> AD1{Approved?<br/>核准?}
    AD1 -->|No<br/>否| AD2[Cannot Cancel<br/>無法取消]
    AD1 -->|Yes<br/>是| AM
    
    AD2 --> End1
    
    AG --> AM
    AH --> AH1{Driver Confirms?<br/>司機確認?}
    AH1 -->|Stopped<br/>已停止| AM
    AH1 -->|Too Late<br/>太晚| R
    
    AL --> AL1[Create Return Order<br/>建立退貨單]
    AL1 --> AM
    
    AM --> AN[Release Inventory<br/>釋放庫存]
    AN --> AO[Restore Credit<br/>恢復信用]
    AO --> AP[Update Status<br/>更新狀態]
    
    AP --> AQ[Record Reason<br/>記錄原因]
    AQ --> AR[Calculate Charges<br/>計算費用]
    
    AR --> AS{Any Charges?<br/>有費用嗎?}
    AS -->|Yes<br/>是| AT[Apply Charges<br/>收取費用]
    AS -->|No<br/>否| AU[Full Refund<br/>全額退款]
    
    AT --> AV[Partial Refund<br/>部分退款]
    
    AU --> AW[Process Refund<br/>處理退款]
    AV --> AW
    
    AW --> AX[Send Notifications<br/>發送通知]
    AX --> AY[Update Reports<br/>更新報表]
    AY --> AZ[Audit Log<br/>稽核日誌]
    
    AZ --> BA{Related Orders?<br/>相關訂單?}
    BA -->|Yes<br/>是| BB[Handle Related<br/>處理相關]
    BA -->|No<br/>否| BC[Complete Cancel<br/>完成取消]
    
    BB --> BC
    BC --> Success([Cancellation Complete<br/>取消完成])
    
    V --> Success
```

## 📊 Cancellation Rules by Status

### Status-Specific Requirements

| Order Status | Reason Required | Approval Needed | Charges Apply | Refund Type | Complexity |
|--------------|----------------|-----------------|---------------|-------------|------------|
| Draft | No | No | No | N/A | ⭐ |
| Confirmed | Yes | No | No | Full | ⭐⭐ |
| Dispatched | Yes | Supervisor | Maybe | Partial/Full | ⭐⭐⭐ |
| In Delivery | Yes | Manager | Yes | Partial | ⭐⭐⭐⭐ |
| Delivered | Yes | Manager | Yes | Varies | ⭐⭐⭐⭐⭐ |

## 🎯 Cancellation Reasons

### Standard Reasons (代碼)
```
01 - 客戶改變心意 (Customer changed mind)
02 - 找到更好價格 (Found better price)
03 - 不需要了 (No longer needed)
04 - 訂錯產品 (Wrong product ordered)
05 - 訂錯數量 (Wrong quantity ordered)
06 - 配送時間不合 (Delivery time unsuitable)
07 - 配送地址錯誤 (Wrong delivery address)
08 - 重複訂單 (Duplicate order)
09 - 付款問題 (Payment issues)
10 - 其他 (Other - specify)
```

### System Reasons (系統)
```
S1 - 庫存不足 (Insufficient stock)
S2 - 超出配送範圍 (Outside delivery area)
S3 - 信用額度不足 (Credit limit exceeded)
S4 - 系統錯誤 (System error)
S5 - 價格錯誤 (Pricing error)
```

### Operational Reasons (營運)
```
O1 - 無司機可用 (No driver available)
O2 - 車輛故障 (Vehicle breakdown)
O3 - 天氣因素 (Weather conditions)
O4 - 道路封閉 (Road closure)
O5 - 安全考量 (Safety concerns)
```

## 💰 Cancellation Charges

### Charge Calculation Logic
```
IF Status = 'Draft' OR 'Confirmed' THEN
    Charge = 0
ELSE IF Status = 'Dispatched' THEN
    IF Time_Since_Dispatch < 30 minutes THEN
        Charge = 0
    ELSE
        Charge = Delivery_Fee * 0.5
    END IF
ELSE IF Status = 'In Delivery' THEN
    Charge = Delivery_Fee + (Product_Total * 0.1)
ELSE IF Status = 'Delivered' THEN
    Charge = Delivery_Fee + Return_Fee + (Product_Total * 0.15)
END IF

// Waive charges for system/operational reasons
IF Reason_Category IN ('System', 'Operational') THEN
    Charge = 0
END IF
```

### Charge Waiver Authority
| Charge Amount | Operator | Supervisor | Manager |
|---------------|----------|------------|---------|
| $0 - $100 | ✅ Auto | ✅ | ✅ |
| $101 - $500 | ❌ | ✅ | ✅ |
| $501+ | ❌ | ❌ | ✅ |

## 🔄 Inventory & Credit Management

### Inventory Release
```
FOR each order line:
    IF product.track_inventory THEN
        inventory.available += line.quantity
        inventory.reserved -= line.quantity
    END IF
    
    IF line.deposit_required THEN
        Process deposit return
    END IF
END FOR
```

### Credit Restoration
```
customer.credit_used -= order.final_amount
customer.credit_available += order.final_amount

IF customer.credit_hold AND 
   customer.credit_available > 0 THEN
    Review credit hold status
END IF
```

## 🔔 Notification Templates

### Customer Notification (SMS)
```
訂單取消確認
訂單號: [ORDER_ID]
取消原因: [REASON]
退款金額: NT$ [REFUND]
預計退款: [REFUND_DATE]
客服: 0800-XXX-XXX
```

### Customer Notification (Email)
```
Subject: 訂單取消確認 - [ORDER_ID]

親愛的 [CUSTOMER_NAME] 您好,

您的訂單已成功取消。

訂單詳情:
- 訂單編號: [ORDER_ID]
- 訂單日期: [ORDER_DATE]
- 原訂金額: NT$ [ORIGINAL_AMOUNT]
- 取消原因: [REASON]
- 取消費用: NT$ [CHARGES]
- 退款金額: NT$ [REFUND_AMOUNT]

退款處理:
- 處理方式: [REFUND_METHOD]
- 預計時間: [REFUND_TIMELINE]

如有任何問題，請聯絡客服。

幸福氣 Lucky Gas
```

### Internal Notifications
1. **Dispatch Team**: Remove from route planning
2. **Warehouse**: Update stock levels
3. **Finance**: Process refund
4. **Management**: Daily cancellation report

## 🚨 Special Scenarios

### Scenario 1: Customer No-Show
- **Trigger**: Driver arrives, customer unavailable
- **Process**: Attempt contact, wait 15 minutes
- **Result**: Mark as failed delivery, return to warehouse

### Scenario 2: Product Quality Issue
- **Trigger**: Customer reports defect
- **Process**: Immediate cancellation, quality investigation
- **Result**: Full refund, no charges

### Scenario 3: Emergency Cancellation
- **Trigger**: Safety issue or emergency
- **Process**: Immediate stop, all charges waived
- **Result**: Full refund, priority handling

### Scenario 4: Bulk Cancellation
- **Trigger**: System error or major issue
- **Process**: Batch cancellation with management approval
- **Result**: Automated processing, bulk notifications

## 📈 Performance Metrics

| Metric | Target | Current | Alert |
|--------|--------|---------|-------|
| Cancellation Rate | < 3% | 3.5% | > 5% |
| Processing Time | < 3 min | 2.8 min | > 5 min |
| Refund Accuracy | 100% | 99.8% | < 99% |
| Customer Satisfaction | > 4.0/5 | 4.2/5 | < 3.5/5 |

## 🔒 Fraud Prevention

### Red Flags
1. Multiple cancellations from same customer
2. High-value orders cancelled repeatedly
3. Cancellations after product price changes
4. Pattern of last-minute cancellations

### Prevention Measures
1. Track cancellation history by customer
2. Require prepayment for habitual cancellers
3. Implement cancellation limits
4. Flag suspicious patterns for review

## 💡 Best Practices

1. **Always Document**: Record specific reason for cancellation
2. **Verify Before Processing**: Confirm customer identity
3. **Communicate Clearly**: Explain charges and refund timeline
4. **Act Quickly**: Process cancellations promptly
5. **Follow Up**: Ensure refund is received

## 🔧 System Integration

### Real-time Updates
1. **Inventory System**: Immediate stock release
2. **Credit System**: Instant limit restoration  
3. **Dispatch System**: Remove from routes
4. **Payment Gateway**: Initiate refunds

### Reporting Integration
1. **Daily Cancellation Report**: By reason and status
2. **Financial Impact Report**: Revenue loss analysis
3. **Customer Behavior Report**: Cancellation patterns
4. **Operational Report**: System vs customer cancellations

## 📊 Cancellation Analytics

### Key Insights Tracked
- Most common cancellation reasons
- Cancellation timing patterns
- Customer segments with high cancellation
- Financial impact by reason
- Seasonal cancellation trends

---

**Note**: This workflow emphasizes customer service while protecting business interests. Always prioritize customer satisfaction within policy guidelines.