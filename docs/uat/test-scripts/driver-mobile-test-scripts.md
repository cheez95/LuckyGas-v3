# Driver Mobile App UAT Test Scripts
## 司機手機應用程式 UAT 測試腳本

**Test Device:** _______________ (Android/iOS)  
**App Version:** _______________  
**Test Date:** _______________  
**Tester Name:** _______________

---

## Test Script 1: App Setup and Login
### 測試腳本 1：應用程式設定與登入

**Objective:** Verify driver can install and access the mobile app.

### Pre-conditions:
- Test device ready
- Test driver account created
- Internet connection available

### Test Steps:

| Step | Action | Expected Result | Pass/Fail | Notes |
|------|--------|-----------------|-----------|-------|
| 1 | Download app from TestFlight/Play Store | App downloads successfully | ☐ | |
| 2 | Open Lucky Gas Driver app | Splash screen shows logo | ☐ | |
| 3 | Select "繁體中文" language | UI switches to Traditional Chinese | ☐ | |
| 4 | Enter credentials:<br>- Username: driver001<br>- Password: **** | Login fields work properly | ☐ | |
| 5 | Toggle "記住我" option | Checkbox responds | ☐ | |
| 6 | Tap "登入" | Loading indicator shows | ☐ | |
| 7 | Accept location permissions | Permission dialog appears | ☐ | |
| 8 | View home dashboard | Today's route summary shows | ☐ | |
| 9 | Check notification permissions | System asks for permission | ☐ | |
| 10 | Verify driver name displayed | Shows "司機：王小明" | ☐ | |

**Post-conditions:** Driver successfully logged into app

---

## Test Script 2: Daily Route Management
### 測試腳本 2：每日路線管理

**Objective:** Test route viewing and navigation features.

### Pre-conditions:
- Logged in successfully
- Routes assigned for today
- GPS enabled

### Test Steps:

| Step | Action | Expected Result | Pass/Fail | Notes |
|------|--------|-----------------|-----------|-------|
| 1 | Tap "今日路線" | Route list displays | ☐ | |
| 2 | View route statistics | Shows "總配送: 15 戶" | ☐ | |
| 3 | Tap "地圖檢視" | Map opens with all stops | ☐ | |
| 4 | Pinch to zoom on map | Map responds smoothly | ☐ | |
| 5 | Tap first delivery pin | Customer details popup | ☐ | |
| 6 | Tap "開始導航" | Google Maps/Apple Maps opens | ☐ | |
| 7 | Return to app | App resumes correctly | ☐ | |
| 8 | Swipe to see route list | List scrolls smoothly | ☐ | |
| 9 | Use search to find "陳先生" | Search filters results | ☐ | |
| 10 | Tap "優化路線" | Route reorders efficiently | ☐ | |

**Post-conditions:** Driver can view and navigate routes effectively

---

## Test Script 3: Delivery Execution Workflow
### 測試腳本 3：配送執行工作流程

**Objective:** Complete end-to-end delivery process.

### Pre-conditions:
- At customer location
- Customer available
- Network connection (test offline too)

### Test Steps:

| Step | Action | Expected Result | Pass/Fail | Notes |
|------|--------|-----------------|-----------|-------|
| 1 | Select customer from list | Delivery details show | ☐ | |
| 2 | Verify customer info displayed | Name, address, order details | ☐ | |
| 3 | Tap "開始配送" | Timer starts, status updates | ☐ | |
| 4 | Tap "掃描 QR Code" | Camera opens | ☐ | |
| 5 | Scan cylinder QR code | Code recognized, beep sounds | ☐ | |
| 6 | Enter manual code if scan fails | Keyboard shows, accepts input | ☐ | |
| 7 | Select "16kg 瓦斯桶 x1" | Product confirmed | ☐ | |
| 8 | Tap "客戶簽名" | Signature pad appears | ☐ | |
| 9 | Customer signs on screen | Signature captures smoothly | ☐ | |
| 10 | Tap "完成配送" | Success message, next delivery | ☐ | |

**Post-conditions:** Delivery completed and recorded

---

## Test Script 4: Payment Collection
### 測試腳本 4：收款處理

**Objective:** Test various payment scenarios.

### Pre-conditions:
- Delivery completed
- Payment pending
- Multiple payment methods available

### Test Steps:

| Step | Action | Expected Result | Pass/Fail | Notes |
|------|--------|-----------------|-----------|-------|
| 1 | View payment amount "NT$ 800" | Amount displays clearly | ☐ | |
| 2 | Select "現金" payment | Cash option highlighted | ☐ | |
| 3 | Enter received "NT$ 1000" | Keypad works properly | ☐ | |
| 4 | View change "找零 NT$ 200" | Calculation correct | ☐ | |
| 5 | Confirm cash payment | Payment recorded | ☐ | |
| 6 | Test "行動支付" option | QR code displays | ☐ | |
| 7 | Test "月結" customer | No payment required shown | ☐ | |
| 8 | Add payment note "已收現金" | Note field accepts Chinese | ☐ | |
| 9 | View daily collection summary | Total collected amount shows | ☐ | |
| 10 | Generate receipt | Receipt preview displays | ☐ | |

**Post-conditions:** Payment processed correctly

---

## Test Script 5: Offline Mode Operation
### 測試腳本 5：離線模式操作

**Objective:** Verify app functions without internet.

### Pre-conditions:
- Routes loaded while online
- Airplane mode ready to enable
- Some deliveries pending

### Test Steps:

| Step | Action | Expected Result | Pass/Fail | Notes |
|------|--------|-----------------|-----------|-------|
| 1 | Enable airplane mode | Offline indicator shows | ☐ | |
| 2 | Navigate to route list | Cached routes display | ☐ | |
| 3 | Select a delivery | Customer details available | ☐ | |
| 4 | Complete delivery process | Works without internet | ☐ | |
| 5 | Capture signature | Signature saves locally | ☐ | |
| 6 | Record payment | Payment data cached | ☐ | |
| 7 | Try to view new route | Message: "離線模式" shows | ☐ | |
| 8 | Check sync queue | Shows "待同步: 3 筆" | ☐ | |
| 9 | Disable airplane mode | Auto-sync begins | ☐ | |
| 10 | Verify sync complete | "同步成功" notification | ☐ | |

**Post-conditions:** Offline deliveries synced successfully

---

## Test Script 6: Communication Features
### 測試腳本 6：通訊功能

**Objective:** Test driver communication capabilities.

### Pre-conditions:
- Active route with customers
- Phone permissions granted
- Office staff available

### Test Steps:

| Step | Action | Expected Result | Pass/Fail | Notes |
|------|--------|-----------------|-----------|-------|
| 1 | Tap customer phone icon | Dialer opens with number | ☐ | |
| 2 | Make test call | Call connects properly | ☐ | |
| 3 | Return to app after call | App state preserved | ☐ | |
| 4 | Tap "聯絡辦公室" | Office number shows | ☐ | |
| 5 | Send route delay message | Predefined messages available | ☐ | |
| 6 | Select "塞車延遲30分鐘" | Message sends to office | ☐ | |
| 7 | Report delivery issue | Issue form opens | ☐ | |
| 8 | Select "客戶不在" | Common issues listed | ☐ | |
| 9 | Add photo of situation | Camera/gallery works | ☐ | |
| 10 | Submit issue report | Report sent successfully | ☐ | |

**Post-conditions:** Communications tested successfully

---

## Test Script 7: End of Day Procedures
### 測試腳本 7：每日結束程序

**Objective:** Complete daily driver check-out process.

### Pre-conditions:
- All deliveries attempted
- Some returns if applicable
- Near end of shift

### Test Steps:

| Step | Action | Expected Result | Pass/Fail | Notes |
|------|--------|-----------------|-----------|-------|
| 1 | Tap "日結作業" | Summary page opens | ☐ | |
| 2 | Review delivery statistics | Shows completed/pending/failed | ☐ | |
| 3 | Enter cylinder returns | Return form works | ☐ | |
| 4 | Review cash collected | Total matches deliveries | ☐ | |
| 5 | Take photo of cash bag | Camera captures image | ☐ | |
| 6 | Enter final odometer | Numeric keyboard shows | ☐ | |
| 7 | Add shift notes | Text field accepts input | ☐ | |
| 8 | Tap "提交日結" | Confirmation dialog | ☐ | |
| 9 | Confirm submission | "日結完成" message | ☐ | |
| 10 | Verify logout | Returns to login screen | ☐ | |

**Post-conditions:** Daily operations properly closed

---

## Performance and Usability Tests

### Performance Metrics:
| Metric | Target | Actual | Pass/Fail |
|--------|--------|--------|-----------|
| App launch time | < 3 sec | _____ | ☐ |
| Route list load | < 2 sec | _____ | ☐ |
| Map rendering | < 3 sec | _____ | ☐ |
| Sync time (10 deliveries) | < 10 sec | _____ | ☐ |
| Battery usage (8 hours) | < 30% | _____ | ☐ |

### Usability Checklist:
- ☐ Text readable in sunlight
- ☐ Buttons large enough for gloves
- ☐ Works with one hand
- ☐ Chinese text displays correctly
- ☐ Error messages helpful
- ☐ No crashes during test

---

## Overall Test Summary

| Test Script | Status | Critical Issues | Notes |
|-------------|--------|-----------------|-------|
| 1. Setup & Login | ☐ Pass ☐ Fail | | |
| 2. Route Management | ☐ Pass ☐ Fail | | |
| 3. Delivery Workflow | ☐ Pass ☐ Fail | | |
| 4. Payment Collection | ☐ Pass ☐ Fail | | |
| 5. Offline Mode | ☐ Pass ☐ Fail | | |
| 6. Communication | ☐ Pass ☐ Fail | | |
| 7. End of Day | ☐ Pass ☐ Fail | | |

**Tester Signature:** _______________ **Date:** _______________

**Reviewer Signature:** _______________ **Date:** _______________