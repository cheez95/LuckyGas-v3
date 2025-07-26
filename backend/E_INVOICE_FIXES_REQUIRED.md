# E-Invoice Implementation - Required Fixes

## Critical Issues to Fix Before Production

### 1. Fix PrintMark Dictionary Usage 🚨

**File**: `app/services/einvoice_service.py`
**Line**: 252

**Current Code**:
```python
"PrintMark": PRINT_MARKS.get("Y" if invoice.is_printed else "N", "N"),
```

**Issue**: This returns Chinese characters "列印" or "不列印" instead of "Y"/"N"

**Fix**:
```python
"PrintMark": "Y" if invoice.is_printed else "N",
```

### 2. Fix Carrier Validation Regex ⚠️

**File**: `app/services/einvoice_service.py`
**Method**: `validate_carrier()`

**Current Code**:
```python
validators = {
    "3J0002": r'^[A-Z0-9+\-\.]{7}$',      # 手機條碼
    ...
}
```

**Issue**: Mobile barcode should be 8 characters including the leading slash

**Fix**:
```python
validators = {
    "3J0002": r'^/[A-Z0-9+\-\.]{7}$',      # 手機條碼 (includes leading /)
    ...
}
```

### 3. Fix Async Mock Issues in Tests ⚠️

**File**: `tests/services/test_einvoice_service.py`
**Multiple test methods**

**Issue**: Incorrect async mock setup causing RuntimeWarning

**Fix Example**:
```python
# Instead of:
mock_response.raise_for_status.side_effect = [
    httpx.HTTPError("Network error"),
    httpx.HTTPError("Network error"),
    None  # Success on third attempt
]

# Use:
async def raise_for_status_mock():
    if self.call_count < 3:
        raise httpx.HTTPError("Network error")
    return None

mock_response.raise_for_status = raise_for_status_mock
```

### 4. Add Missing Invoice Fields

**File**: `app/services/einvoice_service.py`
**Method**: `_prepare_invoice_data()`

**Add these fields for complete compliance**:
```python
# Add after line 267
data["BuyerEmail"] = invoice.buyer_email or ""
data["BuyerPhone"] = invoice.buyer_phone or ""

# Update seller information with actual company data
data["SellerId"] = settings.COMPANY_TAX_ID or "12345678"  # Must be valid
data["SellerName"] = settings.COMPANY_NAME or "幸福氣有限公司"
data["SellerAddress"] = settings.COMPANY_ADDRESS or ""
data["SellerPhone"] = settings.COMPANY_PHONE or ""
data["SellerEmail"] = settings.COMPANY_EMAIL or ""
```

### 5. Add Invoice Number Sequence Management

**New File**: `app/services/invoice_number_service.py`

```python
"""
Invoice number sequence management for Taiwan e-invoice compliance
"""
import asyncio
from datetime import datetime
from typing import Optional
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.invoice import Invoice


class InvoiceNumberService:
    """Manages invoice number sequences and tracks"""
    
    def __init__(self):
        self._lock = asyncio.Lock()
        self._current_track = None
        self._current_number = None
        self._track_end_number = None
    
    async def get_next_invoice_number(
        self,
        db: AsyncSession,
        invoice_type: str = "B2B"
    ) -> tuple[str, str, str]:
        """
        Get next available invoice number
        
        Returns:
            Tuple of (full_number, track, number)
            e.g., ("AB12345678", "AB", "12345678")
        """
        async with self._lock:
            # Initialize if needed
            if not self._current_track:
                await self._initialize_sequence(db)
            
            # Check if we need new track
            if self._current_number >= self._track_end_number:
                raise ValueError(
                    "發票號碼用罄，請聯繫稅務單位申請新字軌"
                )
            
            # Increment number
            self._current_number += 1
            number_str = str(self._current_number).zfill(8)
            full_number = f"{self._current_track}{number_str}"
            
            return full_number, self._current_track, number_str
    
    async def _initialize_sequence(self, db: AsyncSession):
        """Initialize sequence from database"""
        # Get last used invoice
        stmt = select(Invoice).order_by(
            Invoice.invoice_track.desc(),
            Invoice.invoice_no.desc()
        ).limit(1)
        
        result = await db.execute(stmt)
        last_invoice = result.scalar_one_or_none()
        
        if last_invoice:
            self._current_track = last_invoice.invoice_track
            self._current_number = int(last_invoice.invoice_no)
        else:
            # Start with configured initial values
            self._current_track = "AB"  # Should come from config
            self._current_number = 0
        
        # Set track limits (should come from config)
        self._track_end_number = 99999999
```

### 6. Add Period Management

**File**: `app/services/einvoice_service.py`
**Method**: `_prepare_invoice_data()`

**Add period calculation**:
```python
# Add after line 244
# Calculate period (YYYYMM format)
current_date = invoice.invoice_date or datetime.now().date()
period_year = current_date.year - 1911  # Convert to ROC year
period_month = current_date.month
# Periods are odd months: 01-02, 03-04, 05-06, 07-08, 09-10, 11-12
period_start_month = ((period_month - 1) // 2) * 2 + 1
data["Period"] = f"{period_year:03d}{period_start_month:02d}"
```

### 7. Fix Test Configuration

**File**: `tests/services/test_einvoice_service.py`

**Fix the assertion for PrintMark**:
```python
# Line 200
assert data["PrintMark"] == "Y"  # Not "列印"
```

### 8. Add Configuration Validation on Startup

**New File**: `app/core/startup_checks.py`

```python
"""
Startup validation checks for critical services
"""
import logging
from app.services.einvoice_service import get_einvoice_service
from app.core.einvoice_config import validate_einvoice_config, get_einvoice_config

logger = logging.getLogger(__name__)


async def validate_einvoice_configuration():
    """Validate e-invoice configuration on startup"""
    try:
        config = get_einvoice_config()
        validate_einvoice_config(config)
        
        # Test service initialization
        service = get_einvoice_service()
        
        if service.mock_mode:
            logger.warning(
                "E-Invoice service running in MOCK MODE. "
                "Configure proper credentials for production."
            )
        else:
            logger.info("E-Invoice service configured successfully")
            
    except Exception as e:
        logger.error(f"E-Invoice configuration error: {e}")
        raise
```

### 9. Add Integration Tests to CI/CD

**File**: `.github/workflows/tests.yml`

**Add integration test step**:
```yaml
- name: Run E-Invoice Integration Tests
  run: |
    cd backend
    PYTHONPATH=/workspace/backend uv run pytest tests/integration/test_einvoice_integration.py -v
```

### 10. Add Monitoring Metrics

**File**: `app/services/einvoice_service.py`

**Add metrics collection**:
```python
# Add at top of file
from prometheus_client import Counter, Histogram, Gauge

# Define metrics
einvoice_requests_total = Counter(
    'einvoice_requests_total',
    'Total e-invoice API requests',
    ['operation', 'status']
)
einvoice_request_duration = Histogram(
    'einvoice_request_duration_seconds',
    'E-invoice API request duration',
    ['operation']
)
einvoice_circuit_breaker_state = Gauge(
    'einvoice_circuit_breaker_state',
    'Circuit breaker state (0=closed, 1=open, 2=half-open)'
)

# Update submit_invoice method
@einvoice_request_duration.labels(operation='submit').time()
async def submit_invoice(self, invoice: Invoice) -> Dict[str, Any]:
    try:
        result = await self._submit_invoice_internal(invoice)
        einvoice_requests_total.labels(
            operation='submit',
            status='success'
        ).inc()
        return result
    except Exception as e:
        einvoice_requests_total.labels(
            operation='submit',
            status='error'
        ).inc()
        raise
```

## Testing Commands

After implementing fixes, run these tests:

```bash
# Unit tests
cd backend
PYTHONPATH=/Users/lgee258/Desktop/LuckyGas-v3/backend uv run pytest tests/services/test_einvoice_service.py -v

# Integration tests
PYTHONPATH=/Users/lgee258/Desktop/LuckyGas-v3/backend uv run pytest tests/integration/test_einvoice_integration.py -v

# Performance tests
PYTHONPATH=/Users/lgee258/Desktop/LuckyGas-v3/backend uv run pytest tests/performance/test_einvoice_performance.py -v

# All e-invoice tests
PYTHONPATH=/Users/lgee258/Desktop/LuckyGas-v3/backend uv run pytest tests/ -k "einvoice" -v
```

## Deployment Checklist

Before deploying to production:

- [ ] All unit tests passing (22/22)
- [ ] Integration tests passing
- [ ] Performance benchmarks met
- [ ] Security checklist completed
- [ ] Configuration validated
- [ ] Monitoring metrics enabled
- [ ] Circuit breaker tested
- [ ] Mock mode disabled
- [ ] Certificates configured
- [ ] API credentials verified