# Manager Analytics Dashboard UAT Test Scripts
## 管理人員分析儀表板 UAT 測試腳本

**Test Environment:** https://uat.luckygas.com.tw  
**Test Date:** _______________  
**Tester Name:** _______________  
**Role:** Manager/Supervisor

---

## Test Script 1: Dashboard Overview and KPIs
### 測試腳本 1：儀表板總覽與關鍵績效指標

**Objective:** Verify manager can view real-time business metrics.

### Pre-conditions:
- Logged in as Manager role
- Current day has active operations
- Historical data available

### Test Steps:

| Step | Action | Expected Result | Pass/Fail | Notes |
|------|--------|-----------------|-----------|-------|
| 1 | Navigate to Manager Dashboard | Dashboard loads < 3 seconds | ☐ | |
| 2 | View "今日總覽" widget | Shows current date metrics | ☐ | |
| 3 | Check KPI cards display:<br>- 今日訂單數<br>- 完成率<br>- 營收<br>- 活躍司機 | All metrics show values | ☐ | |
| 4 | Hover over completion rate | Tooltip shows calculation | ☐ | |
| 5 | Click refresh icon | Data updates with timestamp | ☐ | |
| 6 | View "即時地圖" | Driver locations display | ☐ | |
| 7 | Check auto-refresh | Updates every 30 seconds | ☐ | |
| 8 | Verify data accuracy | Compare with office records | ☐ | |
| 9 | Check responsive layout | Adjusts to screen size | ☐ | |
| 10 | Test on mobile/tablet | Dashboard remains usable | ☐ | |

**Post-conditions:** Manager has real-time visibility of operations

---

## Test Script 2: Real-time Monitoring and Alerts
### 測試腳本 2：即時監控與警示

**Objective:** Test live tracking and alert systems.

### Pre-conditions:
- Active deliveries in progress
- Multiple drivers on routes
- Alert conditions configured

### Test Steps:

| Step | Action | Expected Result | Pass/Fail | Notes |
|------|--------|-----------------|-----------|-------|
| 1 | Open "即時監控" page | Live tracking map loads | ☐ | |
| 2 | View driver markers on map | Each driver shows location | ☐ | |
| 3 | Click on driver icon | Driver details popup:<br>- Name<br>- Route progress<br>- Current status | ☐ | |
| 4 | Filter by "延遲配送" | Only delayed deliveries show | ☐ | |
| 5 | Check alert panel | Active alerts listed | ☐ | |
| 6 | Click on delay alert | Shows affected orders | ☐ | |
| 7 | Test "司機離線" alert | Alert triggers when offline | ☐ | |
| 8 | View delivery timeline | Shows planned vs actual | ☐ | |
| 9 | Monitor completion rate | Updates as deliveries finish | ☐ | |
| 10 | Export current status | Excel file downloads | ☐ | |

**Post-conditions:** Real-time monitoring functioning correctly

---

## Test Script 3: Performance Analytics
### 測試腳本 3：績效分析

**Objective:** Analyze driver and route performance metrics.

### Pre-conditions:
- Historical data for past 30 days
- Multiple drivers with varying performance
- Completed routes data available

### Test Steps:

| Step | Action | Expected Result | Pass/Fail | Notes |
|------|--------|-----------------|-----------|-------|
| 1 | Navigate to "績效分析" | Analytics page loads | ☐ | |
| 2 | Select date range "本月" | Data filters to current month | ☐ | |
| 3 | View driver ranking table | Drivers sorted by efficiency | ☐ | |
| 4 | Click on top performer | Detailed metrics show:<br>- 配送數量<br>- 準時率<br>- 客戶評分 | ☐ | |
| 5 | Compare two drivers | Side-by-side comparison | ☐ | |
| 6 | View route efficiency map | Heat map of delivery times | ☐ | |
| 7 | Analyze "尖峰時段" chart | Hourly distribution shows | ☐ | |
| 8 | Check fuel efficiency | Cost per delivery calculated | ☐ | |
| 9 | View customer feedback | Ratings and comments | ☐ | |
| 10 | Generate performance report | PDF report created | ☐ | |

**Post-conditions:** Performance insights available for decision-making

---

## Test Script 4: Predictive Analytics and AI Insights
### 測試腳本 4：預測分析與 AI 洞察

**Objective:** Test AI-powered predictions and recommendations.

### Pre-conditions:
- ML models deployed
- Historical patterns available
- Next day planning mode

### Test Steps:

| Step | Action | Expected Result | Pass/Fail | Notes |
|------|--------|-----------------|-----------|-------|
| 1 | Open "需求預測" module | Prediction dashboard loads | ☐ | |
| 2 | View tomorrow's forecast | Shows predicted order volume | ☐ | |
| 3 | Check confidence score | Displays prediction accuracy % | ☐ | |
| 4 | View by area breakdown | Map shows demand hotspots | ☐ | |
| 5 | Review "建議配置" | AI suggests driver allocation | ☐ | |
| 6 | Adjust parameters:<br>- Service level: 95%<br>- Cost priority: Medium | Predictions recalculate | ☐ | |
| 7 | View seasonal trends | Graph shows patterns | ☐ | |
| 8 | Check weather impact | Correlation with orders shown | ☐ | |
| 9 | Export predictions | Excel with formulas downloads | ☐ | |
| 10 | Schedule auto-report | Email configuration saves | ☐ | |

**Post-conditions:** Predictive insights support planning decisions

---

## Test Script 5: Financial Reports and Analysis
### 測試腳本 5：財務報表與分析

**Objective:** Verify financial reporting accuracy and features.

### Pre-conditions:
- Completed transactions in system
- Multiple payment types recorded
- Month-end closing done

### Test Steps:

| Step | Action | Expected Result | Pass/Fail | Notes |
|------|--------|-----------------|-----------|-------|
| 1 | Navigate to "財務報表" | Financial dashboard opens | ☐ | |
| 2 | View "營收摘要" | Current month revenue shows | ☐ | |
| 3 | Drill down by product type | 16kg vs 20kg breakdown | ☐ | |
| 4 | Check payment methods chart | Cash/Digital/Credit splits | ☐ | |
| 5 | View accounts receivable | Outstanding payments listed | ☐ | |
| 6 | Filter overdue accounts | Aging report displays | ☐ | |
| 7 | Generate invoice summary | All invoices for period | ☐ | |
| 8 | View profit margins | By route and product | ☐ | |
| 9 | Compare YoY growth | Previous year comparison | ☐ | |
| 10 | Export to accounting | Format compatible with system | ☐ | |

**Post-conditions:** Financial data accurate and exportable

---

## Test Script 6: Route Optimization Review
### 測試腳本 6：路線優化檢視

**Objective:** Test route optimization features and controls.

### Pre-conditions:
- Tomorrow's orders entered
- Driver availability confirmed
- Optimization engine active

### Test Steps:

| Step | Action | Expected Result | Pass/Fail | Notes |
|------|--------|-----------------|-----------|-------|
| 1 | Open "路線規劃" tool | Planning interface loads | ☐ | |
| 2 | Click "自動優化" | AI generates routes | ☐ | |
| 3 | View optimization metrics:<br>- Total distance<br>- Estimated time<br>- Fuel cost | Metrics calculated | ☐ | |
| 4 | Adjust constraint:<br>"每車最多 25 戶" | Routes recalculate | ☐ | |
| 5 | Manually move 3 orders | Drag and drop works | ☐ | |
| 6 | Compare before/after | Shows impact of changes | ☐ | |
| 7 | Lock driver preference | Customer-driver maintained | ☐ | |
| 8 | Simulate traffic delays | Routes adjust for peak hours | ☐ | |
| 9 | Approve final routes | Status changes to "已確認" | ☐ | |
| 10 | Publish to drivers | Notifications sent | ☐ | |

**Post-conditions:** Optimized routes ready for next day

---

## Test Script 7: Custom Reports and Exports
### 測試腳本 7：自訂報表與匯出

**Objective:** Create and export custom analytical reports.

### Pre-conditions:
- Report builder access
- Various data sources available
- Export permissions granted

### Test Steps:

| Step | Action | Expected Result | Pass/Fail | Notes |
|------|--------|-----------------|-----------|-------|
| 1 | Open "報表產生器" | Report builder interface loads | ☐ | |
| 2 | Create new report | Blank template opens | ☐ | |
| 3 | Add data sources:<br>- Orders<br>- Customers<br>- Drivers | Sources connect successfully | ☐ | |
| 4 | Drag fields to report:<br>- 客戶區域<br>- 訂單數量<br>- 營收 | Fields added to layout | ☐ | |
| 5 | Add filter "本季" | Date filter applies | ☐ | |
| 6 | Insert pivot table | Data summarizes correctly | ☐ | |
| 7 | Add trend chart | Visualization renders | ☐ | |
| 8 | Save as "季度分析" | Report saved to library | ☐ | |
| 9 | Schedule weekly email | Automation configured | ☐ | |
| 10 | Export to PowerBI | Compatible format generated | ☐ | |

**Post-conditions:** Custom reports created and scheduled

---

## Integration and Performance Tests

### System Integration Points:
| Integration | Test Result | Notes |
|-------------|-------------|-------|
| Google Maps API | ☐ Pass ☐ Fail | |
| Weather data feed | ☐ Pass ☐ Fail | |
| SMS gateway | ☐ Pass ☐ Fail | |
| Payment systems | ☐ Pass ☐ Fail | |
| Accounting export | ☐ Pass ☐ Fail | |

### Dashboard Performance:
| Metric | Target | Actual | Pass/Fail |
|--------|--------|--------|-----------|
| Initial load time | < 3 sec | _____ | ☐ |
| Data refresh | < 1 sec | _____ | ☐ |
| Report generation | < 5 sec | _____ | ☐ |
| Export (1000 rows) | < 10 sec | _____ | ☐ |
| Concurrent users | 20 | _____ | ☐ |

---

## Overall Test Summary

| Test Script | Status | Critical Issues | Notes |
|-------------|--------|-----------------|-------|
| 1. Dashboard Overview | ☐ Pass ☐ Fail | | |
| 2. Real-time Monitoring | ☐ Pass ☐ Fail | | |
| 3. Performance Analytics | ☐ Pass ☐ Fail | | |
| 4. Predictive Analytics | ☐ Pass ☐ Fail | | |
| 5. Financial Reports | ☐ Pass ☐ Fail | | |
| 6. Route Optimization | ☐ Pass ☐ Fail | | |
| 7. Custom Reports | ☐ Pass ☐ Fail | | |

**Tester Signature:** _______________ **Date:** _______________

**Business Owner Approval:** _______________ **Date:** _______________