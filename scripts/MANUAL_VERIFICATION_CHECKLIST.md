# Lucky Gas System - Manual Verification Checklist

**Purpose**: Systematic manual verification of all 102 leaf nodes identified in the complete navigation analysis  
**Target**: 100% system coverage verification  
**Method**: Manual navigation and screenshot documentation

---

## 📋 Verification Instructions

For each item below:
1. ✅ Check the box when verified
2. 📸 Take screenshot and save as `{section}_{subsection}_{feature}.png`
3. 📝 Note any additional sub-features found
4. ⚠️ Mark any access issues or errors

---

## 1. 會員作業 (Customer Management) - 11 Leaf Nodes

### 客戶資料維護 (Customer Data Maintenance)
- [ ] **新增客戶 Form** - Verify all 76 fields load correctly
  - [ ] Basic information fields
  - [ ] Contact information fields  
  - [ ] Delivery preferences
  - [ ] Payment settings
  - [ ] Custom fields
  - Screenshot: `customer_add_form.png`

- [ ] **修改客戶 - 基本資料 Tab**
  - [ ] All fields editable
  - [ ] Validation working
  - Screenshot: `customer_edit_basic.png`

- [ ] **修改客戶 - 聯絡資訊 Tab**
  - [ ] Phone number format validation
  - [ ] Address auto-complete (if exists)
  - Screenshot: `customer_edit_contact.png`

- [ ] **修改客戶 - 配送資訊 Tab**
  - [ ] Delivery time preferences
  - [ ] Special instructions field
  - Screenshot: `customer_edit_delivery.png`

- [ ] **修改客戶 - 付款資訊 Tab**
  - [ ] Payment method options
  - [ ] Credit terms
  - Screenshot: `customer_edit_payment.png`

- [ ] **刪除客戶 Confirmation**
  - [ ] Confirmation dialog appears
  - [ ] Soft delete implemented
  - Screenshot: `customer_delete_confirm.png`

### 客戶查詢 (Customer Search)
- [ ] **簡易查詢 Interface**
  - [ ] Search by name/phone/ID
  - [ ] Quick results display
  - Screenshot: `customer_search_simple.png`

- [ ] **進階查詢 Interface**
  - [ ] Multiple filter criteria
  - [ ] Date range filters
  - Screenshot: `customer_search_advanced.png`

- [ ] **查詢結果 Pagination**
  - [ ] Results per page selector
  - [ ] Page navigation working
  - Screenshot: `customer_search_results.png`

### 客戶報表 (Customer Reports)
- [ ] **客戶清單 Report**
  - [ ] Export to CSV/Excel
  - [ ] Print preview
  - Screenshot: `customer_report_list.png`

- [ ] **客戶交易記錄 Report**
  - [ ] Date range selection
  - [ ] Transaction details visible
  - Screenshot: `customer_report_transactions.png`

- [ ] **客戶統計分析 Report**
  - [ ] Charts/graphs display
  - [ ] Statistical summaries
  - Screenshot: `customer_report_statistics.png`

---

## 2. 資料維護 (Data Maintenance) - 12 Leaf Nodes

### 產品資料 (Product Data)
- [ ] **20kg 瓦斯桶 Settings**
  - [ ] Price configuration
  - [ ] Stock settings
  - Screenshot: `product_gas_20kg.png`

- [ ] **50kg 瓦斯桶 Settings**
  - [ ] Price configuration
  - [ ] Stock settings
  - Screenshot: `product_gas_50kg.png`

- [ ] **其他規格 Settings**
  - [ ] Custom product types
  - [ ] Special configurations
  - Screenshot: `product_gas_other.png`

- [ ] **標準價格 Configuration**
  - [ ] Base pricing rules
  - [ ] Effective dates
  - Screenshot: `product_price_standard.png`

- [ ] **特殊價格 Configuration**
  - [ ] Customer-specific pricing
  - [ ] Volume discounts
  - Screenshot: `product_price_special.png`

- [ ] **促銷價格 Configuration**
  - [ ] Promotion periods
  - [ ] Discount rules
  - Screenshot: `product_price_promotion.png`

### 員工資料 (Employee Data)
- [ ] **司機資料 Management**
  - [ ] Driver profiles
  - [ ] License information
  - [ ] Vehicle assignment
  - Screenshot: `employee_drivers.png`

- [ ] **業務人員 Management**
  - [ ] Sales staff profiles
  - [ ] Territory assignment
  - Screenshot: `employee_sales.png`

- [ ] **辦公室人員 Management**
  - [ ] Office staff profiles
  - [ ] Role assignment
  - Screenshot: `employee_office.png`

### 系統參數 (System Parameters)
- [ ] **營業時間設定**
  - [ ] Business hours configuration
  - [ ] Holiday settings
  - Screenshot: `system_business_hours.png`

- [ ] **配送區域設定**
  - [ ] Delivery zones
  - [ ] Zone pricing
  - Screenshot: `system_delivery_zones.png`

- [ ] **付款條件設定**
  - [ ] Payment terms
  - [ ] Credit limits
  - Screenshot: `system_payment_terms.png`

---

## 3. 訂單銷售 (Order Sales) - 13 Leaf Nodes

### 新增訂單 Workflow
- [ ] **選擇客戶 Step**
  - [ ] Customer search/selection
  - [ ] Customer details display
  - Screenshot: `order_new_customer.png`

- [ ] **選擇產品 Step**
  - [ ] Product catalog
  - [ ] Stock availability
  - Screenshot: `order_new_products.png`

- [ ] **設定數量 Step**
  - [ ] Quantity input
  - [ ] Price calculation
  - Screenshot: `order_new_quantity.png`

- [ ] **配送資訊 Step**
  - [ ] Delivery date/time
  - [ ] Special instructions
  - Screenshot: `order_new_delivery.png`

- [ ] **確認訂單 Final Step**
  - [ ] Order summary
  - [ ] Confirmation button
  - Screenshot: `order_new_confirm.png`

### 修改/取消訂單
- [ ] **修改訂單 Interface**
  - [ ] All fields editable
  - [ ] Change history tracking
  - Screenshot: `order_edit.png`

- [ ] **取消訂單 Process**
  - [ ] Cancellation reason
  - [ ] Confirmation required
  - Screenshot: `order_cancel.png`

### 訂單查詢 (Order Search)
- [ ] **依日期查詢**
  - [ ] Date range picker
  - [ ] Results display
  - Screenshot: `order_search_date.png`

- [ ] **依客戶查詢**
  - [ ] Customer selector
  - [ ] Order history
  - Screenshot: `order_search_customer.png`

- [ ] **依狀態查詢**
  - [ ] Status filters
  - [ ] Status updates
  - Screenshot: `order_search_status.png`

- [ ] **綜合查詢**
  - [ ] Multiple criteria
  - [ ] Advanced filters
  - Screenshot: `order_search_combined.png`

### 訂單報表 (Order Reports)
- [ ] **日報表**
  - [ ] Daily summary
  - [ ] Export options
  - Screenshot: `order_report_daily.png`

- [ ] **月報表**
  - [ ] Monthly trends
  - [ ] Comparison data
  - Screenshot: `order_report_monthly.png`

- [ ] **年度報表**
  - [ ] Annual overview
  - [ ] YoY comparison
  - Screenshot: `order_report_annual.png`

---

## 4. 報表作業 (Reports) - 15 Leaf Nodes

### 營業報表 (Business Reports)
- [ ] **銷售統計 - 按產品**
  - [ ] Product breakdown
  - [ ] Volume charts
  - Screenshot: `report_sales_product.png`

- [ ] **銷售統計 - 按客戶**
  - [ ] Customer ranking
  - [ ] Revenue distribution
  - Screenshot: `report_sales_customer.png`

- [ ] **銷售統計 - 按區域**
  - [ ] Geographic analysis
  - [ ] Heat maps (if available)
  - Screenshot: `report_sales_region.png`

- [ ] **應收帳款 Report**
  - [ ] Outstanding amounts
  - [ ] Aging analysis
  - Screenshot: `report_receivables.png`

- [ ] **已收帳款 Report**
  - [ ] Collection summary
  - [ ] Payment methods
  - Screenshot: `report_collected.png`

- [ ] **逾期帳款 Report**
  - [ ] Overdue list
  - [ ] Collection priority
  - Screenshot: `report_overdue.png`

- [ ] **毛利分析 Report**
  - [ ] Profit margins
  - [ ] Cost analysis
  - Screenshot: `report_profit.png`

### 配送報表 (Delivery Reports)
- [ ] **司機績效 Report**
  - [ ] Delivery counts
  - [ ] Efficiency metrics
  - Screenshot: `report_driver_performance.png`

- [ ] **路線分析 Report**
  - [ ] Route efficiency
  - [ ] Time analysis
  - Screenshot: `report_route_analysis.png`

- [ ] **配送統計 Report**
  - [ ] Delivery success rate
  - [ ] Issue tracking
  - Screenshot: `report_delivery_stats.png`

### 管理報表 (Management Reports)
- [ ] **經營分析 Report**
  - [ ] Business KPIs
  - [ ] Executive summary
  - Screenshot: `report_business_analysis.png`

- [ ] **趨勢分析 Report**
  - [ ] Trend charts
  - [ ] Predictive data
  - Screenshot: `report_trends.png`

- [ ] **異常報表**
  - [ ] Exception alerts
  - [ ] Action items
  - Screenshot: `report_exceptions.png`

---

## 5. 熱氣球作業 (Hot Air Balloon) - 4 Leaf Nodes

- [ ] **活動登記 Form**
  - [ ] Event details
  - [ ] Gas requirements
  - Screenshot: `balloon_event_register.png`

- [ ] **活動查詢 Interface**
  - [ ] Event calendar
  - [ ] Search filters
  - Screenshot: `balloon_event_search.png`

- [ ] **供應登記 Form**
  - [ ] Supply details
  - [ ] Delivery schedule
  - Screenshot: `balloon_supply_register.png`

- [ ] **供應記錄 List**
  - [ ] Historical data
  - [ ] Export options
  - Screenshot: `balloon_supply_records.png`

---

## 6. 幸福氣APP (Lucky Gas APP) - 4 Leaf Nodes

- [ ] **版本管理 Interface**
  - [ ] Version history
  - [ ] Update controls
  - Screenshot: `app_version_control.png`

- [ ] **下載統計 Dashboard**
  - [ ] Download counts
  - [ ] Platform breakdown
  - Screenshot: `app_download_stats.png`

- [ ] **註冊用戶 List**
  - [ ] User profiles
  - [ ] Registration dates
  - Screenshot: `app_registered_users.png`

- [ ] **使用記錄 Analytics**
  - [ ] Usage patterns
  - [ ] Feature adoption
  - Screenshot: `app_usage_records.png`

---

## 7. 發票作業 (Invoice Operations) - 10 Leaf Nodes

### 發票開立 (Invoice Issuance)
- [ ] **手動開立 Form**
  - [ ] Invoice details
  - [ ] Tax calculation
  - Screenshot: `invoice_manual_issue.png`

- [ ] **批次開立 Process**
  - [ ] Batch selection
  - [ ] Processing status
  - Screenshot: `invoice_batch_issue.png`

- [ ] **補開發票 Form**
  - [ ] Reissue reasons
  - [ ] Original reference
  - Screenshot: `invoice_reissue.png`

### 發票管理 (Invoice Management)
- [ ] **作廢發票 Process**
  - [ ] Void reasons
  - [ ] Approval workflow
  - Screenshot: `invoice_void.png`

- [ ] **折讓單 Creation**
  - [ ] Credit note details
  - [ ] Adjustment reasons
  - Screenshot: `invoice_credit_note.png`

- [ ] **發票查詢 Interface**
  - [ ] Search criteria
  - [ ] Results display
  - Screenshot: `invoice_search.png`

### 發票報表 (Invoice Reports)
- [ ] **發票明細 Report**
  - [ ] Detailed listing
  - [ ] Export formats
  - Screenshot: `invoice_report_details.png`

- [ ] **稅務申報 Report**
  - [ ] Tax summary
  - [ ] Government format
  - Screenshot: `invoice_report_tax.png`

- [ ] **發票統計 Report**
  - [ ] Statistical analysis
  - [ ] Trends
  - Screenshot: `invoice_report_stats.png`

---

## 8. 帳務管理 (Account Management) - 10 Leaf Nodes

### 收款作業 (Collection Operations)
- [ ] **現金收款 Entry**
  - [ ] Cash receipt form
  - [ ] Receipt printing
  - Screenshot: `account_cash_collection.png`

- [ ] **支票收款 Entry**
  - [ ] Check details
  - [ ] Bank information
  - Screenshot: `account_check_collection.png`

- [ ] **匯款收款 Entry**
  - [ ] Transfer details
  - [ ] Bank reconciliation
  - Screenshot: `account_transfer_collection.png`

### 應收管理 (Receivables Management)
- [ ] **對帳單 Generation**
  - [ ] Statement format
  - [ ] Customer selection
  - Screenshot: `account_statement.png`

- [ ] **催收作業 Process**
  - [ ] Collection notices
  - [ ] Follow-up tracking
  - Screenshot: `account_collection_notice.png`

- [ ] **壞帳處理 Process**
  - [ ] Write-off approval
  - [ ] Documentation
  - Screenshot: `account_bad_debt.png`

### 帳務報表 (Accounting Reports)
- [ ] **日結報表**
  - [ ] Daily closing
  - [ ] Balance verification
  - Screenshot: `account_daily_close.png`

- [ ] **月結報表**
  - [ ] Monthly summary
  - [ ] Account reconciliation
  - Screenshot: `account_monthly_close.png`

- [ ] **年度結算**
  - [ ] Annual closing
  - [ ] Financial statements
  - Screenshot: `account_annual_close.png`

---

## 9. CSV匯出 (CSV Export) - 6 Leaf Nodes

- [ ] **客戶資料匯出**
  - [ ] Export options
  - [ ] Field selection
  - Screenshot: `csv_export_customers.png`

- [ ] **訂單資料匯出**
  - [ ] Date range
  - [ ] Status filters
  - Screenshot: `csv_export_orders.png`

- [ ] **交易記錄匯出**
  - [ ] Transaction types
  - [ ] Export format
  - Screenshot: `csv_export_transactions.png`

- [ ] **選擇欄位 Interface**
  - [ ] Field picker
  - [ ] Custom ordering
  - Screenshot: `csv_export_fields.png`

- [ ] **設定條件 Interface**
  - [ ] Filter builder
  - [ ] Condition logic
  - Screenshot: `csv_export_conditions.png`

- [ ] **執行匯出 Process**
  - [ ] Progress indicator
  - [ ] Download link
  - Screenshot: `csv_export_execute.png`

---

## 10. 派遣作業 (Dispatch Operations) - 9 Leaf Nodes

### 路線規劃 (Route Planning)
- [ ] **自動規劃 Process**
  - [ ] Algorithm settings
  - [ ] Optimization results
  - Screenshot: `dispatch_auto_planning.png`

- [ ] **拖放訂單 Interface**
  - [ ] Drag-drop UI
  - [ ] Visual feedback
  - Screenshot: `dispatch_drag_orders.png`

- [ ] **重新排序 Controls**
  - [ ] Order adjustment
  - [ ] Priority settings
  - Screenshot: `dispatch_reorder.png`

- [ ] **路線確認 Step**
  - [ ] Final review
  - [ ] Confirmation
  - Screenshot: `dispatch_route_confirm.png`

### 司機指派 (Driver Assignment)
- [ ] **查看司機狀態**
  - [ ] Availability view
  - [ ] Current assignments
  - Screenshot: `dispatch_driver_status.png`

- [ ] **指派路線 Process**
  - [ ] Assignment interface
  - [ ] Notification system
  - Screenshot: `dispatch_assign_route.png`

- [ ] **調整指派 Interface**
  - [ ] Reassignment options
  - [ ] Change tracking
  - Screenshot: `dispatch_adjust_assignment.png`

### 派遣監控 (Dispatch Monitoring)
- [ ] **即時位置 Map**
  - [ ] GPS tracking
  - [ ] Map display
  - Screenshot: `dispatch_realtime_location.png`

- [ ] **配送進度 Dashboard**
  - [ ] Progress tracking
  - [ ] Status updates
  - Screenshot: `dispatch_delivery_progress.png`

- [ ] **異常處理 Interface**
  - [ ] Issue alerts
  - [ ] Resolution workflow
  - Screenshot: `dispatch_exception_handling.png`

---

## 11. 通報作業 (Notification Operations) - 8 Leaf Nodes

### 客戶通知 (Customer Notifications)
- [ ] **配送通知 Template**
  - [ ] Message templates
  - [ ] Scheduling options
  - Screenshot: `notify_delivery_notice.png`

- [ ] **缺貨通知 Process**
  - [ ] Stock alerts
  - [ ] Customer selection
  - Screenshot: `notify_out_of_stock.png`

- [ ] **促銷通知 Campaign**
  - [ ] Promotion setup
  - [ ] Target audience
  - Screenshot: `notify_promotion.png`

### 內部通報 (Internal Notifications)
- [ ] **異常通報 System**
  - [ ] Alert configuration
  - [ ] Escalation rules
  - Screenshot: `notify_exception_alert.png`

- [ ] **逾期通報 Process**
  - [ ] Overdue triggers
  - [ ] Notification list
  - Screenshot: `notify_overdue_alert.png`

- [ ] **系統通報 Settings**
  - [ ] System alerts
  - [ ] Admin notifications
  - Screenshot: `notify_system_alert.png`

### 通報記錄 (Notification History)
- [ ] **發送記錄 Log**
  - [ ] Send history
  - [ ] Delivery status
  - Screenshot: `notify_send_history.png`

- [ ] **回應記錄 Tracking**
  - [ ] Response rates
  - [ ] Engagement metrics
  - Screenshot: `notify_response_history.png`

---

## 📊 Verification Summary

**Total Leaf Nodes to Verify**: 102

### By Section:
- 會員作業: 11 nodes
- 資料維護: 12 nodes  
- 訂單銷售: 13 nodes
- 報表作業: 15 nodes
- 熱氣球作業: 4 nodes
- 幸福氣APP: 4 nodes
- 發票作業: 10 nodes
- 帳務管理: 10 nodes
- CSV匯出: 6 nodes
- 派遣作業: 9 nodes
- 通報作業: 8 nodes

### Verification Progress:
- [ ] Started: ___/___/_____ at ___:___
- [ ] Completed: ___/___/_____ at ___:___
- [ ] Total Screenshots: ___/102
- [ ] Issues Found: ___

### Notes:
_Use this space to document any additional findings, issues, or observations during the verification process_

---

## 🚨 Issues & Blockers

Document any access issues, errors, or missing functionality here:

1. 
2. 
3. 

---

## ✅ Verification Sign-off

- [ ] All 102 leaf nodes verified
- [ ] All screenshots captured and labeled
- [ ] All issues documented
- [ ] Ready for migration planning

**Verified by**: _________________  
**Date**: _________________  
**Signature**: _________________