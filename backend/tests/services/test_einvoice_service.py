"""
Tests for Taiwan Government E-Invoice API Service

Tests cover:
- Invoice submission (B2B and B2C)
- Invoice voiding
- Allowance issuance
- Invoice querying
- Circuit breaker functionality
- Retry logic
- Mock mode behavior
- Validation functions
"""
import pytest
import httpx
from unittest.mock import AsyncMock, MagicMock, patch, call
from datetime import datetime, date
import json
import time

from app.services.einvoice_service import (
    EInvoiceService,
    CircuitBreaker,
    CircuitState,
    get_einvoice_service
)
from app.models.invoice import Invoice, InvoiceItem, InvoiceType, InvoiceStatus
from app.core.einvoice_config import EINVOICE_ERROR_CODES


# Test fixtures
@pytest.fixture
def mock_invoice():
    """Create a mock invoice for testing"""
    invoice = MagicMock(spec=Invoice)
    invoice.invoice_number = "AB12345678"
    invoice.invoice_track = "AB"
    invoice.invoice_no = "12345678"
    invoice.invoice_date = date(2025, 1, 20)
    invoice.random_code = "1234"
    invoice.sales_amount = 1000.0
    invoice.tax_type = "1"
    invoice.tax_rate = 0.05
    invoice.tax_amount = 50.0
    invoice.total_amount = 1050.0
    invoice.invoice_type = InvoiceType.B2B
    invoice.buyer_tax_id = "53212539"  # Valid Taiwan tax ID
    invoice.buyer_name = "測試公司"
    invoice.buyer_address = "台北市信義區信義路五段7號"
    invoice.is_printed = True
    
    # Mock items
    item1 = MagicMock(spec=InvoiceItem)
    item1.sequence = 1
    item1.product_name = "瓦斯桶 20kg"
    item1.quantity = 2
    item1.unit = "桶"
    item1.unit_price = 500
    item1.amount = 1000
    item1.tax_type = "1"
    
    invoice.items = [item1]
    
    return invoice


@pytest.fixture
def einvoice_service():
    """Create E-Invoice service instance for testing"""
    with patch('app.core.config.settings') as mock_settings:
        mock_settings.ENVIRONMENT = "test"
        mock_settings.COMPANY_TAX_ID = "87654321"
        mock_settings.COMPANY_NAME = "幸福氣有限公司"
        mock_settings.COMPANY_ADDRESS = "台北市信義區"
        
        service = EInvoiceService(environment="test")
        return service


class TestCircuitBreaker:
    """Test circuit breaker functionality"""
    
    @pytest.mark.asyncio
    async def test_circuit_breaker_closed_state(self):
        """Test circuit breaker in closed state allows calls"""
        breaker = CircuitBreaker(failure_threshold=3, recovery_timeout=60)
        
        @breaker
        async def test_function():
            return "success"
        
        result = await test_function()
        assert result == "success"
        assert breaker.state == CircuitState.CLOSED
    
    @pytest.mark.asyncio
    async def test_circuit_breaker_opens_after_failures(self):
        """Test circuit breaker opens after threshold failures"""
        breaker = CircuitBreaker(failure_threshold=3, recovery_timeout=60)
        
        @breaker
        async def failing_function():
            raise Exception("Test failure")
        
        # Fail 3 times to open circuit
        for _ in range(3):
            with pytest.raises(Exception):
                await failing_function()
        
        assert breaker.state == CircuitState.OPEN
        assert breaker.failure_count == 3
        
        # Next call should fail immediately
        with pytest.raises(Exception) as exc_info:
            await failing_function()
        
        assert "電子發票服務暫時無法使用" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_circuit_breaker_half_open_recovery(self):
        """Test circuit breaker recovery to half-open state"""
        breaker = CircuitBreaker(failure_threshold=2, recovery_timeout=0.1)
        
        @breaker
        async def test_function(should_fail=False):
            if should_fail:
                raise Exception("Test failure")
            return "success"
        
        # Open the circuit
        for _ in range(2):
            with pytest.raises(Exception):
                await test_function(should_fail=True)
        
        assert breaker.state == CircuitState.OPEN
        
        # Wait for recovery timeout
        time.sleep(0.2)
        
        # Should allow one attempt (half-open)
        result = await test_function(should_fail=False)
        assert result == "success"
        assert breaker.state == CircuitState.CLOSED
        assert breaker.failure_count == 0


class TestEInvoiceService:
    """Test E-Invoice service functionality"""
    
    def test_service_initialization(self, einvoice_service):
        """Test service initialization"""
        assert einvoice_service.app_id == "PLACEHOLDER_TEST_APP_ID"
        assert einvoice_service.api_key == "PLACEHOLDER_TEST_API_KEY"
        assert einvoice_service.mock_mode == True  # Should be in mock mode with placeholder
        assert einvoice_service.timeout == 30
        assert einvoice_service.max_retries == 3
    
    def test_signature_generation(self, einvoice_service):
        """Test HMAC signature generation"""
        data = {
            "MerchantID": "TEST123",
            "InvoiceNo": "AB12345678",
            "TimeStamp": "1234567890"
        }
        
        signature = einvoice_service._generate_signature(data)
        
        # Signature should be base64 encoded
        assert isinstance(signature, str)
        assert len(signature) > 0
        
        # Same data should produce same signature
        signature2 = einvoice_service._generate_signature(data)
        assert signature == signature2
    
    def test_signature_generation_with_arrays(self, einvoice_service):
        """Test signature generation with array parameters"""
        data = {
            "MerchantID": "TEST123",
            "ItemDescription": ["Item1", "Item2"],
            "ItemAmount": ["100", "200"]
        }
        
        signature = einvoice_service._generate_signature(data)
        assert isinstance(signature, str)
    
    def test_prepare_invoice_data(self, einvoice_service, mock_invoice):
        """Test invoice data preparation"""
        data = einvoice_service._prepare_invoice_data(mock_invoice)
        
        assert data["MerchantID"] == einvoice_service.app_id
        assert data["InvoiceNo"] == "AB12345678"
        assert data["InvoiceDate"] == "2025/01/20"
        assert data["RandomNumber"] == "1234"
        assert data["SalesAmount"] == 1000
        assert data["TaxAmount"] == 50
        assert data["TotalAmount"] == 1050
        assert data["BuyerId"] == "53212539"
        assert data["BuyerName"] == "測試公司"
        assert data["PrintMark"] == "Y"
        assert data["ItemCount"] == "1"
        assert len(data["ItemDescription"]) == 1
        assert data["ItemDescription"][0] == "瓦斯桶 20kg"
        assert "CheckMacValue" in data
    
    def test_prepare_invoice_data_b2c(self, einvoice_service, mock_invoice):
        """Test B2C invoice data preparation"""
        mock_invoice.invoice_type = InvoiceType.B2C
        mock_invoice.buyer_tax_id = None
        
        data = einvoice_service._prepare_invoice_data(mock_invoice)
        
        assert "BuyerId" not in data or data["BuyerId"] == ""
        assert data["BuyerName"] == "測試公司"
    
    @pytest.mark.asyncio
    async def test_submit_invoice_mock_mode(self, einvoice_service, mock_invoice):
        """Test invoice submission in mock mode"""
        result = await einvoice_service.submit_invoice(mock_invoice)
        
        assert result["status"] == "success"
        assert "TEST" in result["einvoice_id"]
        assert result["message"] == "測試環境 - 發票開立成功"
        assert result["qr_code_left"] == "**AB12345678:1234"
        assert result["qr_code_right"] == "1050:53212539"
        assert result["bar_code"] == "AB12345678"
        assert result["api_response"]["RtnCode"] == "1"
    
    @pytest.mark.asyncio
    async def test_submit_invoice_validation_error(self, einvoice_service, mock_invoice):
        """Test invoice submission with validation error"""
        mock_invoice.invoice_number = ""
        
        with pytest.raises(ValueError) as exc_info:
            await einvoice_service.submit_invoice(mock_invoice)
        
        assert "發票號碼不能為空" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_submit_invoice_invalid_tax_id(self, einvoice_service, mock_invoice):
        """Test invoice submission with invalid tax ID"""
        mock_invoice.buyer_tax_id = "12345678"  # Invalid checksum
        
        with pytest.raises(ValueError) as exc_info:
            await einvoice_service.submit_invoice(mock_invoice)
        
        assert "買方統一編號格式錯誤" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_void_invoice_mock_mode(self, einvoice_service):
        """Test invoice voiding in mock mode"""
        result = await einvoice_service.void_invoice("AB12345678", "測試作廢")
        
        assert result["status"] == "success"
        assert "測試環境 - 發票作廢成功：測試作廢" in result["message"]
        assert "void_time" in result
        assert result["api_response"]["RtnCode"] == "1"
    
    @pytest.mark.asyncio
    async def test_issue_allowance_mock_mode(self, einvoice_service):
        """Test allowance issuance in mock mode"""
        result = await einvoice_service.issue_allowance(
            "AB12345678",
            100.0,
            5.0,
            "退貨"
        )
        
        assert result["status"] == "success"
        assert "ALLOW" in result["allowance_number"]
        assert "測試環境 - 折讓單開立成功：退貨" in result["message"]
        assert "allowance_time" in result
        assert result["api_response"]["RtnCode"] == "1"
    
    @pytest.mark.asyncio
    async def test_query_invoice_mock_mode(self, einvoice_service):
        """Test invoice query in mock mode"""
        result = await einvoice_service.query_invoice("AB12345678")
        
        assert result["status"] == "success"
        assert result["invoice_status"] == "issued"
        assert result["buyer_name"] == "測試買方"
        assert result["total_amount"] == "1000"
        assert result["void_status"] == "0"
        assert result["message"] == "測試環境 - 發票查詢成功"
    
    def test_validate_carrier(self, einvoice_service):
        """Test carrier validation"""
        # Valid mobile barcode
        assert einvoice_service.validate_carrier("3J0002", "/ABC123")
        
        # Invalid mobile barcode (too long)
        assert not einvoice_service.validate_carrier("3J0002", "/ABC12345")
        
        # Valid natural person certificate
        assert einvoice_service.validate_carrier("CQ0001", "AB12345678901234")
        
        # Invalid natural person certificate
        assert not einvoice_service.validate_carrier("CQ0001", "1234567890123456")
        
        # Unknown carrier type (allow by default)
        assert einvoice_service.validate_carrier("UNKNOWN", "anything")
    
    def test_validate_tax_id(self, einvoice_service):
        """Test Taiwan tax ID validation"""
        # Valid tax IDs
        assert einvoice_service.validate_tax_id("53212539")  # Real company
        assert einvoice_service.validate_tax_id("04595257")  # Real company
        
        # Invalid tax IDs
        assert not einvoice_service.validate_tax_id("12345678")  # Invalid checksum
        assert not einvoice_service.validate_tax_id("1234567")   # Too short
        assert not einvoice_service.validate_tax_id("123456789") # Too long
        assert not einvoice_service.validate_tax_id("ABCD1234")  # Non-numeric
        assert not einvoice_service.validate_tax_id("")          # Empty
    
    @pytest.mark.asyncio
    async def test_retry_logic(self, einvoice_service):
        """Test retry logic with exponential backoff"""
        with patch('httpx.AsyncClient') as mock_client:
            mock_response = AsyncMock()
            mock_response.raise_for_status.side_effect = [
                httpx.HTTPError("Network error"),
                httpx.HTTPError("Network error"),
                None  # Success on third attempt
            ]
            mock_response.json.return_value = {"RtnCode": "1"}
            
            mock_client.return_value.__aenter__.return_value.post.return_value = mock_response
            
            # Override mock mode
            einvoice_service.mock_mode = False
            
            with patch('app.core.config.settings') as mock_settings:
                mock_settings.ENVIRONMENT = "production"
                
                # Should succeed after retries
                start_time = time.time()
                await einvoice_service._make_request("POST", "http://test.com", {})
                duration = time.time() - start_time
                
                # Should have some delay due to retries
                assert duration >= einvoice_service.retry_delay * 3  # 1 + 2 seconds
    
    @pytest.mark.asyncio
    async def test_make_request_max_retries_exceeded(self, einvoice_service):
        """Test request fails after max retries"""
        with patch('httpx.AsyncClient') as mock_client:
            mock_response = AsyncMock()
            mock_response.raise_for_status.side_effect = httpx.HTTPError("Network error")
            
            mock_client.return_value.__aenter__.return_value.post.return_value = mock_response
            
            with pytest.raises(httpx.HTTPError):
                await einvoice_service._make_request("POST", "http://test.com", {})
    
    def test_service_singleton(self):
        """Test service singleton pattern"""
        service1 = get_einvoice_service()
        service2 = get_einvoice_service()
        
        assert service1 is service2


class TestEInvoiceServiceProduction:
    """Test E-Invoice service production mode behavior"""
    
    @pytest.fixture
    def production_service(self):
        """Create service configured for production"""
        with patch('app.core.einvoice_config.get_einvoice_config') as mock_config:
            mock_config.return_value = {
                "app_id": "REAL_APP_ID",
                "api_key": "REAL_API_KEY",
                "b2b_api_url": "https://www.einvoice.nat.gov.tw/BIZAPIVAN/biz",
                "b2c_api_url": "https://www.einvoice.nat.gov.tw/INVAPIVAN/invapp",
                "timeout": 30,
                "max_retries": 3,
                "retry_delay": 1,
                "cert_path": "/path/to/cert.pem",
                "key_path": "/path/to/key.pem"
            }
            
            service = EInvoiceService(environment="production")
            return service
    
    @pytest.mark.asyncio
    async def test_submit_invoice_production_success(self, production_service, mock_invoice):
        """Test successful invoice submission in production mode"""
        with patch('httpx.AsyncClient') as mock_client:
            mock_response = AsyncMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                "RtnCode": "1",
                "RtnMsg": "發票開立成功",
                "InvoiceNo": "AB12345678",
                "QRCode_Left": "**AB12345678:1234",
                "QRCode_Right": "1050:53212539",
                "BarCode": "AB12345678"
            }
            mock_response.raise_for_status.return_value = None
            
            mock_client.return_value.__aenter__.return_value.post.return_value = mock_response
            
            with patch('app.core.config.settings') as mock_settings:
                mock_settings.ENVIRONMENT = "production"
                
                result = await production_service.submit_invoice(mock_invoice)
                
                assert result["status"] == "success"
                assert result["einvoice_id"] == "AB12345678"
                assert result["message"] == "發票開立成功"
                assert result["qr_code_left"] == "**AB12345678:1234"
    
    @pytest.mark.asyncio
    async def test_submit_invoice_production_api_error(self, production_service, mock_invoice):
        """Test API error handling in production mode"""
        with patch('httpx.AsyncClient') as mock_client:
            mock_response = AsyncMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                "RtnCode": "5000001",
                "RtnMsg": "發票號碼重複"
            }
            mock_response.raise_for_status.return_value = None
            
            mock_client.return_value.__aenter__.return_value.post.return_value = mock_response
            
            with patch('app.core.config.settings') as mock_settings:
                mock_settings.ENVIRONMENT = "production"
                
                with pytest.raises(Exception) as exc_info:
                    await production_service.submit_invoice(mock_invoice)
                
                assert "發票開立失敗 [5000001]: 發票號碼重複" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_submit_invoice_production_network_error(self, production_service, mock_invoice):
        """Test network error handling in production mode"""
        with patch('httpx.AsyncClient') as mock_client:
            mock_client.return_value.__aenter__.return_value.post.side_effect = httpx.ConnectError("Connection failed")
            
            with patch('app.core.config.settings') as mock_settings:
                mock_settings.ENVIRONMENT = "production"
                
                with pytest.raises(Exception) as exc_info:
                    await production_service.submit_invoice(mock_invoice)
                
                assert "網路連線錯誤" in str(exc_info.value)