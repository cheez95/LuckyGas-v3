# Lucky Gas Critical Action Plan - Week 1

**Generated**: 2025-07-26  
**Priority**: IMMEDIATE ACTION REQUIRED  
**Timeline**: Next 5 working days

## 🚨 Day 1 (Monday) - Test Infrastructure & API Access

### Morning (4 hours)
#### Fix Test Infrastructure
```bash
# Frontend test setup
cd frontend
npm install --save-dev jest @testing-library/react @testing-library/jest-dom
npm pkg set scripts.test="jest"

# Backend test fix
cd backend
export PYTHONPATH=$PWD:$PYTHONPATH
uv run pytest -v
```

**Owner**: Lead Developer  
**Success Criteria**: Both test suites run without import errors

#### Contact Government E-Invoice API
**Action Items**:
1. Call Taiwan Ministry of Finance: +886-2-2322-8000
2. Request test environment access for 統一發票 API
3. Documentation: https://www.einvoice.nat.gov.tw/
4. Required info:
   - Company Tax ID: 97420648
   - Test environment credentials
   - API documentation
   - XML schema files

**Owner**: Project Manager  
**Success Criteria**: Test credentials received or meeting scheduled

### Afternoon (4 hours)
#### Start GPS Integration
```typescript
// frontend/src/hooks/useGeolocation.ts
export const useGeolocation = () => {
  const [position, setPosition] = useState<GeolocationPosition | null>(null);
  const [error, setError] = useState<string | null>(null);
  
  useEffect(() => {
    if (!navigator.geolocation) {
      setError('Geolocation not supported');
      return;
    }
    
    const watchId = navigator.geolocation.watchPosition(
      (pos) => setPosition(pos),
      (err) => setError(err.message),
      { enableHighAccuracy: true, maximumAge: 0 }
    );
    
    return () => navigator.geolocation.clearWatch(watchId);
  }, []);
  
  return { position, error };
};
```

**Owner**: Frontend Developer  
**Success Criteria**: GPS coordinates displayed in driver dashboard

---

## 📅 Day 2 (Tuesday) - Data Mapping & Banking

### Morning (4 hours)
#### Complete Data Field Mapping
Create Excel mapping document with structure:
```
Module | Legacy Field | Legacy Type | New Field | New Type | Transform | Notes
Customer | 客戶編號 | varchar(10) | customer_code | string | Direct | Primary key
Customer | 統一編號 | char(8) | tax_id | string | Validate | 8-digit check
...
```

**Modules to map**:
1. Customer (會員作業) - 76 fields ✅ Partial
2. Orders (訂單銷售) - 52 fields ❌ Missing
3. Dispatch (派遣作業) - 35 fields ❌ Missing
4. Invoice (發票作業) - 38 fields ❌ Missing
5. Reports (報表作業) - 120 fields ❌ Missing

**Owner**: Data Analyst + Backend Developer  
**Success Criteria**: 100% field mapping for first 3 modules

### Afternoon (4 hours)
#### Banking SFTP Test Setup
1. Contact bank IT department
2. Request test SFTP credentials
3. Test connection:
```bash
sftp -P 22 testuser@bank-test.com.tw
```
4. Verify file format specifications
5. Create sample payment file

**Owner**: Backend Developer  
**Success Criteria**: Successful SFTP connection and file upload

---

## 📅 Day 3 (Wednesday) - Offline Mode & SMS

### Morning (4 hours)
#### Implement Service Worker for Offline Mode
```javascript
// frontend/public/service-worker.js
self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open('lucky-gas-v1').then((cache) => {
      return cache.addAll([
        '/',
        '/driver',
        '/static/js/bundle.js',
        '/api/driver/routes/offline'
      ]);
    })
  );
});

self.addEventListener('fetch', (event) => {
  event.respondWith(
    caches.match(event.request).then((response) => {
      return response || fetch(event.request);
    })
  );
});
```

**Owner**: Frontend Developer  
**Success Criteria**: Driver app works without internet

### Afternoon (4 hours)
#### Configure SMS Gateway
1. Provider: Twilio or local (every8d.com)
2. Get API credentials
3. Test implementation:
```python
# backend/app/services/sms_service.py
import httpx

async def send_sms(phone: str, message: str):
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "https://api.every8d.com/send",
            data={
                "UID": os.getenv("SMS_UID"),
                "PWD": os.getenv("SMS_PWD"),
                "SB": phone,
                "MSG": message
            }
        )
    return response.status_code == 200
```

**Owner**: Backend Developer  
**Success Criteria**: Test SMS sent successfully

---

## 📅 Day 4 (Thursday) - Integration & Testing

### Morning (4 hours)
#### E-Invoice API Integration Start
```python
# backend/app/services/einvoice_service.py
class EInvoiceService:
    def __init__(self):
        self.api_url = "https://api-test.einvoice.nat.gov.tw"
        self.app_id = os.getenv("EINVOICE_APP_ID")
        self.api_key = os.getenv("EINVOICE_API_KEY")
    
    async def issue_invoice(self, invoice_data: dict):
        # Convert to government XML format
        xml_data = self.convert_to_xml(invoice_data)
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.api_url}/Invoice/Issue",
                headers={"Content-Type": "application/xml"},
                content=xml_data
            )
        return response
```

**Owner**: Senior Backend Developer  
**Success Criteria**: Successfully call test API endpoint

### Afternoon (4 hours)
#### Fix and Run E2E Tests
```bash
cd tests/e2e
npm test -- --timeout=30000

# Focus on critical paths:
# 1. User login
# 2. Customer creation
# 3. Order placement
# 4. Driver delivery flow
```

**Owner**: QA Engineer  
**Success Criteria**: 4 critical test scenarios passing

---

## 📅 Day 5 (Friday) - Documentation & Planning

### Morning (4 hours)
#### Create User Training Materials
1. Screenshot current system pages
2. Create side-by-side comparison
3. Write step-by-step guides in Traditional Chinese:
   - 客戶管理操作手冊
   - 訂單處理流程
   - 司機配送指南
   - 報表使用說明

**Owner**: Technical Writer + UX Designer  
**Success Criteria**: First module guide completed

### Afternoon (4 hours)
#### Sprint Planning & Risk Review
1. Update migration timeline based on findings
2. Identify additional resources needed
3. Schedule vendor meetings
4. Create detailed Sprint 2 plan
5. Stakeholder communication

**Owner**: Project Manager + Tech Lead  
**Success Criteria**: Revised timeline approved

---

## 📊 Success Metrics for Week 1

| Task | Target | Actual | Status |
|------|--------|--------|--------|
| Test Infrastructure | 100% fixed | - | 🔄 |
| E-Invoice API Access | Credentials obtained | - | 🔄 |
| GPS Integration | Working prototype | - | 🔄 |
| Data Mapping | 3 modules complete | - | 🔄 |
| Banking SFTP | Test connection | - | 🔄 |
| Offline Mode | Service worker active | - | 🔄 |
| SMS Gateway | Test message sent | - | 🔄 |
| E2E Tests | 4 scenarios pass | - | 🔄 |
| Training Docs | 1 module complete | - | 🔄 |

---

## 🚨 Escalation Points

### If Blocked:
1. **E-Invoice API**: Escalate to Legal/Finance Director
2. **Banking Integration**: Contact bank relationship manager
3. **Technical Issues**: Schedule vendor support calls
4. **Resource Constraints**: Request additional developers

### Daily Standup Topics:
- Blocker resolution
- Progress on critical path
- Risk identification
- Resource needs

---

## 📞 Key Contacts

| System | Contact | Phone | Email |
|--------|---------|-------|-------|
| E-Invoice | Ministry of Finance | +886-2-2322-8000 | - |
| Banking | TBD | TBD | TBD |
| SMS Gateway | Every8D Support | +886-2-2655-2030 | support@every8d.com |
| Google Maps | Cloud Support | - | Via console |

---

**Next Review**: Friday 4 PM  
**Escalation**: If ANY critical item blocked by Day 3