# Customer Portal UAT Test Scripts
## 客戶入口網站 UAT 測試腳本

**Test Environment:** https://uat.luckygas.com.tw/customer  
**Test Date:** _______________  
**Tester Name:** _______________  
**Role:** Customer/End User

---

## Test Script 1: Customer Registration and Login
### 測試腳本 1：客戶註冊與登入

**Objective:** Verify new customer can register and access portal.

### Pre-conditions:
- Clean browser session
- Valid mobile phone for OTP
- Test email address

### Test Steps:

| Step | Action | Expected Result | Pass/Fail | Notes |
|------|--------|-----------------|-----------|-------|
| 1 | Navigate to customer portal | Landing page loads | ☐ | |
| 2 | Click "註冊新帳號" | Registration form displays | ☐ | |
| 3 | Enter details:<br>- Name: 測試用戶<br>- Phone: 0912-XXX-XXX<br>- Email: test@email.com | Form accepts Taiwan formats | ☐ | |
| 4 | Enter address with autocomplete | Google address suggestion works | ☐ | |
| 5 | Click "發送驗證碼" | SMS received within 1 minute | ☐ | |
| 6 | Enter OTP code | Code validates correctly | ☐ | |
| 7 | Set password (8+ chars) | Password strength indicator | ☐ | |
| 8 | Accept terms and conditions | Chinese T&C displays | ☐ | |
| 9 | Click "完成註冊" | Success message shows | ☐ | |
| 10 | Login with new credentials | Dashboard displays | ☐ | |

**Post-conditions:** New customer account created and accessible

---

## Test Script 2: Order Tracking and History
### 測試腳本 2：訂單追蹤與歷史記錄

**Objective:** Test order visibility and tracking features.

### Pre-conditions:
- Logged in as customer
- Active order in system
- Historical orders exist

### Test Steps:

| Step | Action | Expected Result | Pass/Fail | Notes |
|------|--------|-----------------|-----------|-------|
| 1 | View "我的訂單" page | Current orders display first | ☐ | |
| 2 | Check active order status | Shows "配送中" with icon | ☐ | |
| 3 | Click "追蹤配送" | Real-time map opens | ☐ | |
| 4 | View driver location | Moving icon on map | ☐ | |
| 5 | Check ETA display | Shows "預計到達: 14:30" | ☐ | |
| 6 | Tap notification bell | Recent updates listed | ☐ | |
| 7 | Switch to "歷史訂單" tab | Past orders show | ☐ | |
| 8 | Filter by date range | Calendar picker works | ☐ | |
| 9 | View order details | Invoice downloadable | ☐ | |
| 10 | Check order frequency | Shows monthly pattern | ☐ | |

**Post-conditions:** Customer can track and review orders

---

## Test Script 3: Quick Reorder Function
### 測試腳本 3：快速重新訂購功能

**Objective:** Verify repeat order functionality.

### Pre-conditions:
- Previous order history exists
- Standard products in system
- Delivery slots available

### Test Steps:

| Step | Action | Expected Result | Pass/Fail | Notes |
|------|--------|-----------------|-----------|-------|
| 1 | Go to "快速訂購" | Favorite orders show | ☐ | |
| 2 | View last order details | Products and quantity display | ☐ | |
| 3 | Click "重新訂購" | Order form pre-fills | ☐ | |
| 4 | Modify quantity to 2 | Price updates automatically | ☐ | |
| 5 | Select delivery date | Calendar shows available dates | ☐ | |
| 6 | Choose "下午 2-5點" | Time slot selectable | ☐ | |
| 7 | Add note "請按門鈴" | Note field accepts Chinese | ☐ | |
| 8 | Review order summary | All details correct | ☐ | |
| 9 | Click "確認訂購" | Order confirmation shows | ☐ | |
| 10 | Check SMS confirmation | Message received immediately | ☐ | |

**Post-conditions:** Repeat order placed successfully

---

## Test Script 4: Profile Management
### 測試腳本 4：個人資料管理

**Objective:** Test account settings and updates.

### Pre-conditions:
- Logged in to portal
- Current profile populated
- Multiple addresses possible

### Test Steps:

| Step | Action | Expected Result | Pass/Fail | Notes |
|------|--------|-----------------|-----------|-------|
| 1 | Navigate to "帳戶設定" | Profile page loads | ☐ | |
| 2 | Update phone number | Requires OTP verification | ☐ | |
| 3 | Add alternate address | Address form appears | ☐ | |
| 4 | Label as "辦公室" | Custom labels allowed | ☐ | |
| 5 | Set as default address | Radio button updates | ☐ | |
| 6 | Change email preferences | Newsletter options show | ☐ | |
| 7 | Update password | Old password required | ☐ | |
| 8 | Enable SMS notifications | Toggle switches work | ☐ | |
| 9 | Add emergency contact | Additional contact saved | ☐ | |
| 10 | Save all changes | Success confirmation | ☐ | |

**Post-conditions:** Profile updates saved successfully

---

## Test Script 5: Payment and Billing
### 測試腳本 5：付款與帳單

**Objective:** Manage payment methods and view billing.

### Pre-conditions:
- Account has order history
- Multiple payment options
- Invoices generated

### Test Steps:

| Step | Action | Expected Result | Pass/Fail | Notes |
|------|--------|-----------------|-----------|-------|
| 1 | Go to "付款方式" | Payment methods page loads | ☐ | |
| 2 | View current balance | Shows "應付: NT$ 0" | ☐ | |
| 3 | Add credit card | Secure form displays | ☐ | |
| 4 | Enter test card number | Validation in real-time | ☐ | |
| 5 | Save card (masked) | Shows ****1234 | ☐ | |
| 6 | Set as default | Default indicator updates | ☐ | |
| 7 | Navigate to "帳單記錄" | Invoice list displays | ☐ | |
| 8 | Download PDF invoice | File downloads correctly | ☐ | |
| 9 | View payment history | Transaction list shows | ☐ | |
| 10 | Request receipt reissue | Email sent confirmation | ☐ | |

**Post-conditions:** Payment methods configured and billing accessible

---

## Test Script 6: Support and Communication
### 測試腳本 6：客服與溝通

**Objective:** Test customer support features.

### Pre-conditions:
- Active session
- Support hours (9AM-6PM)
- Order-related query

### Test Steps:

| Step | Action | Expected Result | Pass/Fail | Notes |
|------|--------|-----------------|-----------|-------|
| 1 | Click "線上客服" button | Chat widget opens | ☐ | |
| 2 | View welcome message | Shows in Traditional Chinese | ☐ | |
| 3 | Type "訂單問題" | Auto-suggestions appear | ☐ | |
| 4 | Select current order | Order context loaded | ☐ | |
| 5 | Send message | Message sends, seen indicator | ☐ | |
| 6 | Receive agent response | Response within 2 minutes | ☐ | |
| 7 | Request callback | Phone number pre-filled | ☐ | |
| 8 | Upload image | Photo attachment works | ☐ | |
| 9 | End chat session | Transcript option given | ☐ | |
| 10 | Rate support experience | 5-star rating submits | ☐ | |

**Post-conditions:** Support interaction completed successfully

---

## Test Script 7: Mobile Responsive Testing
### 測試腳本 7：手機響應式測試

**Objective:** Verify portal works on mobile devices.

### Pre-conditions:
- Mobile device or emulator
- Various screen sizes
- Touch interface

### Test Steps:

| Step | Action | Expected Result | Pass/Fail | Notes |
|------|--------|-----------------|-----------|-------|
| 1 | Open portal on mobile | Responsive layout loads | ☐ | |
| 2 | Test hamburger menu | Navigation drawer works | ☐ | |
| 3 | Pinch to zoom disabled | Viewport fixed properly | ☐ | |
| 4 | Tap phone number | Click-to-call works | ☐ | |
| 5 | Use date picker | Mobile-friendly calendar | ☐ | |
| 6 | Test swipe gestures | Order cards swipeable | ☐ | |
| 7 | Complete order on mobile | All steps completable | ☐ | |
| 8 | View map tracking | Map touch controls work | ☐ | |
| 9 | Test portrait/landscape | Layout adjusts properly | ☐ | |
| 10 | Check load performance | Pages load < 3 seconds | ☐ | |

**Post-conditions:** Mobile experience validated

---

## Accessibility and Localization Tests

### Accessibility Checklist:
- ☐ Keyboard navigation works
- ☐ Screen reader compatible
- ☐ Color contrast sufficient
- ☐ Font size adjustable
- ☐ Focus indicators visible
- ☐ Error messages clear

### Localization Verification:
- ☐ All text in Traditional Chinese
- ☐ Date format: YYYY/MM/DD
- ☐ Currency: NT$ format
- ☐ Phone: Taiwan format
- ☐ Address: Taiwan postal system
- ☐ No broken characters

---

## Security and Privacy Tests

| Test | Result | Notes |
|------|--------|-------|
| Password complexity enforced | ☐ Pass ☐ Fail | |
| Session timeout (15 min) | ☐ Pass ☐ Fail | |
| HTTPS on all pages | ☐ Pass ☐ Fail | |
| Credit card data masked | ☐ Pass ☐ Fail | |
| Personal data protected | ☐ Pass ☐ Fail | |

---

## Overall Test Summary

| Test Script | Status | Critical Issues | Notes |
|-------------|--------|-----------------|-------|
| 1. Registration & Login | ☐ Pass ☐ Fail | | |
| 2. Order Tracking | ☐ Pass ☐ Fail | | |
| 3. Quick Reorder | ☐ Pass ☐ Fail | | |
| 4. Profile Management | ☐ Pass ☐ Fail | | |
| 5. Payment & Billing | ☐ Pass ☐ Fail | | |
| 6. Support Features | ☐ Pass ☐ Fail | | |
| 7. Mobile Testing | ☐ Pass ☐ Fail | | |

**Customer Experience Rating:** _____ / 5 stars

**Tester Signature:** _______________ **Date:** _______________

**UAT Coordinator Signature:** _______________ **Date:** _______________