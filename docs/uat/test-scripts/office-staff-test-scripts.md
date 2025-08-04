# Office Staff UAT Test Scripts
## 辦公室人員 UAT 測試腳本

**Test Environment:** https://uat.luckygas.com.tw  
**Test Date:** _______________  
**Tester Name:** _______________

---

## Test Script 1: New Customer and Order Creation
### 測試腳本 1：新客戶與訂單建立

**Objective:** Verify office staff can create new customers and process orders efficiently.

### Pre-conditions:
- Logged in as Office Staff role
- Test data sheet available

### Test Steps:

| Step | Action | Expected Result | Pass/Fail | Notes |
|------|--------|-----------------|-----------|-------|
| 1 | Click "新增客戶" button | Customer creation form opens | ☐ | |
| 2 | Enter customer details:<br>- Name: 測試客戶001<br>- Phone: 0912-345-678<br>- Address: 台北市信義區信義路五段7號 | All fields accept Taiwan format | ☐ | |
| 3 | Select customer type "家庭用戶" | Dropdown shows correct options | ☐ | |
| 4 | Click "儲存" | Success message "客戶新增成功" | ☐ | |
| 5 | Search for created customer | Customer appears in search results | ☐ | |
| 6 | Click "新增訂單" for this customer | Order form pre-fills customer data | ☐ | |
| 7 | Select:<br>- Product: 16公斤瓦斯<br>- Quantity: 1<br>- Delivery date: Tomorrow | Form validates selections | ☐ | |
| 8 | Add delivery note: "下午配送" | Note field accepts Chinese text | ☐ | |
| 9 | Click "建立訂單" | Order created with order number | ☐ | |
| 10 | Verify order in "今日訂單" list | Order shows correct status "待分配" | ☐ | |

**Post-conditions:** New customer and order created successfully

---

## Test Script 2: Route Assignment and Management
### 測試腳本 2：路線分配與管理

**Objective:** Verify efficient route assignment workflow.

### Pre-conditions:
- Multiple unassigned orders exist
- At least 2 drivers available

### Test Steps:

| Step | Action | Expected Result | Pass/Fail | Notes |
|------|--------|-----------------|-----------|-------|
| 1 | Navigate to "路線管理" | Route management page loads | ☐ | |
| 2 | View "未分配訂單" section | Shows all unassigned orders | ☐ | |
| 3 | Select 5 orders using checkboxes | Orders highlighted | ☐ | |
| 4 | Click "智慧分配" | AI suggests optimal driver | ☐ | |
| 5 | Review suggested route on map | Map shows delivery sequence | ☐ | |
| 6 | Modify sequence by dragging order | Route updates dynamically | ☐ | |
| 7 | Assign to "司機A" | Assignment confirmed | ☐ | |
| 8 | Check driver's mobile notification | Driver receives route update | ☐ | |
| 9 | Move one order to "司機B" | Transfer completes successfully | ☐ | |
| 10 | Print route sheet | PDF generates with QR codes | ☐ | |

**Post-conditions:** Orders assigned to drivers with optimized routes

---

## Test Script 3: Order Modification and Cancellation
### 測試腳本 3：訂單修改與取消

**Objective:** Test order lifecycle management capabilities.

### Pre-conditions:
- Existing order in "待配送" status
- Customer request for changes

### Test Steps:

| Step | Action | Expected Result | Pass/Fail | Notes |
|------|--------|-----------------|-----------|-------|
| 1 | Search order by number or phone | Order found quickly | ☐ | |
| 2 | Click "編輯" on order | Edit form opens with current data | ☐ | |
| 3 | Change delivery time to "上午" | Time slot updates | ☐ | |
| 4 | Add rush delivery flag | Priority indicator shows | ☐ | |
| 5 | Save changes | "訂單更新成功" message | ☐ | |
| 6 | Verify driver notification | Driver app shows update | ☐ | |
| 7 | Select different order to cancel | Order details display | ☐ | |
| 8 | Click "取消訂單" | Cancellation dialog appears | ☐ | |
| 9 | Select reason: "客戶要求" | Reason recorded | ☐ | |
| 10 | Confirm cancellation | Order status changes to "已取消" | ☐ | |

**Post-conditions:** Orders successfully modified and cancelled with audit trail

---

## Test Script 4: Bulk Order Import
### 測試腳本 4：批量訂單匯入

**Objective:** Verify Excel import functionality for bulk orders.

### Pre-conditions:
- Excel template downloaded
- Test data prepared in Excel

### Test Steps:

| Step | Action | Expected Result | Pass/Fail | Notes |
|------|--------|-----------------|-----------|-------|
| 1 | Click "批量匯入" | Import dialog opens | ☐ | |
| 2 | Download template file | Excel template downloads | ☐ | |
| 3 | Fill template with 10 orders | Excel accepts data | ☐ | |
| 4 | Upload filled Excel file | File uploads successfully | ☐ | |
| 5 | System validates data | Validation results show | ☐ | |
| 6 | Fix any validation errors | Error messages are clear | ☐ | |
| 7 | Click "確認匯入" | Import progress shows | ☐ | |
| 8 | Check import results | "成功匯入 10 筆訂單" | ☐ | |
| 9 | Verify orders in system | All orders created correctly | ☐ | |
| 10 | Check customer matching | Existing customers linked | ☐ | |

**Post-conditions:** Bulk orders imported successfully

---

## Test Script 5: Emergency Order Handling
### 測試腳本 5：緊急訂單處理

**Objective:** Test urgent delivery request workflow.

### Pre-conditions:
- Customer calls with urgent need
- Drivers on active routes

### Test Steps:

| Step | Action | Expected Result | Pass/Fail | Notes |
|------|--------|-----------------|-----------|-------|
| 1 | Click "緊急訂單" button | Urgent order form opens | ☐ | |
| 2 | Enter customer phone | System auto-fills if exists | ☐ | |
| 3 | Mark as "2小時內送達" | Urgency flag activated | ☐ | |
| 4 | System suggests nearest driver | Driver location considered | ☐ | |
| 5 | View driver's current route | Current deliveries shown | ☐ | |
| 6 | Insert urgent order in route | Route re-optimizes | ☐ | |
| 7 | Send notification to driver | Immediate alert sent | ☐ | |
| 8 | Driver confirms receipt | Acknowledgment received | ☐ | |
| 9 | Monitor delivery progress | Real-time tracking works | ☐ | |
| 10 | Verify on-time delivery | Delivery within 2 hours | ☐ | |

**Post-conditions:** Emergency order delivered successfully

---

## Test Script 6: Daily Operations Closure
### 測試腳本 6：每日營運結算

**Objective:** Verify end-of-day procedures and reporting.

### Pre-conditions:
- Day's deliveries mostly complete
- Some orders pending

### Test Steps:

| Step | Action | Expected Result | Pass/Fail | Notes |
|------|--------|-----------------|-----------|-------|
| 1 | Navigate to "日結作業" | Daily closure page opens | ☐ | |
| 2 | Review delivery summary | Statistics display correctly | ☐ | |
| 3 | Check incomplete orders | Pending orders highlighted | ☐ | |
| 4 | Reschedule pending orders | Orders moved to tomorrow | ☐ | |
| 5 | Verify driver check-ins | All drivers accounted for | ☐ | |
| 6 | Review cash collection | Amounts match deliveries | ☐ | |
| 7 | Generate daily report | PDF report created | ☐ | |
| 8 | Email report to manager | Email sent successfully | ☐ | |
| 9 | Archive today's data | Data backed up | ☐ | |
| 10 | Prepare tomorrow's routes | Initial routes generated | ☐ | |

**Post-conditions:** Daily operations properly closed

---

## Overall Test Summary

| Test Script | Status | Critical Issues | Notes |
|-------------|--------|-----------------|-------|
| 1. Customer & Order Creation | ☐ Pass ☐ Fail | | |
| 2. Route Assignment | ☐ Pass ☐ Fail | | |
| 3. Order Modification | ☐ Pass ☐ Fail | | |
| 4. Bulk Import | ☐ Pass ☐ Fail | | |
| 5. Emergency Orders | ☐ Pass ☐ Fail | | |
| 6. Daily Closure | ☐ Pass ☐ Fail | | |

**Tester Signature:** _______________ **Date:** _______________

**Reviewer Signature:** _______________ **Date:** _______________