"""
Integration tests for Taiwan Government E-Invoice API

These tests simulate the full lifecycle of e-invoice operations with
mocked government API responses to ensure proper integration behavior.
"""
import asyncio
import json
from datetime import date, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from app.core.einvoice_config import EINVOICE_ERROR_CODES
from app.models.invoice import Invoice, InvoiceItem, InvoiceStatus, InvoiceType
from app.services.einvoice_service import EInvoiceService, get_einvoice_service


class TestEInvoiceIntegration:
    """Integration tests for e-invoice service with mocked government API"""
    
    @pytest.fixture
    def mock_government_api(self):
        """Mock government API responses"""
        class MockResponse:
            def __init__(self, status_code, json_data):
                self.status_code = status_code
                self._json_data = json_data
            
            def json(self):
                return self._json_data
            
            def raise_for_status(self):
                if self.status_code >= 400:
                    raise httpx.HTTPError(f"HTTP {self.status_code}")
        
        return MockResponse
    
    @pytest.fixture
    def production_invoice(self):
        """Create a production-ready invoice"""
        invoice = MagicMock(spec=Invoice)
        invoice.id = 1
        invoice.invoice_number = "XY98765432"
        invoice.invoice_track = "XY"
        invoice.invoice_no = "98765432"
        invoice.invoice_date = date.today()
        invoice.random_code = "5678"
        invoice.invoice_type = InvoiceType.B2B
        invoice.status = InvoiceStatus.DRAFT
        
        # Financial details
        invoice.sales_amount = 5000.0
        invoice.tax_type = "1"  # 應稅
        invoice.tax_rate = 0.05
        invoice.tax_amount = 250.0
        invoice.total_amount = 5250.0
        
        # Buyer information
        invoice.buyer_tax_id = "53212539"  # Valid Taiwan tax ID
        invoice.buyer_name = "台灣測試公司"
        invoice.buyer_address = "台北市信義區信義路五段7號"
        invoice.is_printed = True
        
        # Items
        item1 = MagicMock(spec=InvoiceItem)
        item1.sequence = 1
        item1.product_name = "液化石油氣 20公斤"
        item1.quantity = 5
        item1.unit = "桶"
        item1.unit_price = 1000
        item1.amount = 5000
        item1.tax_type = "1"
        
        invoice.items = [item1]
        
        return invoice
    
    @pytest.mark.asyncio
    async def test_full_invoice_lifecycle(self, mock_government_api, production_invoice):
        """Test complete invoice lifecycle: create -> submit -> query -> void"""
        
        # Configure service for production mode
        with patch('app.core.einvoice_config.get_einvoice_config') as mock_config:
            mock_config.return_value = {
                "app_id": "PROD_APP_ID",
                "api_key": "PROD_API_KEY",
                "b2b_api_url": "https://www.einvoice.nat.gov.tw/BIZAPIVAN/biz",
                "b2c_api_url": "https://www.einvoice.nat.gov.tw/INVAPIVAN/invapp",
                "timeout": 30,
                "max_retries": 3,
                "retry_delay": 1,
                "cert_path": "",
                "key_path": ""
            }
            
            service = EInvoiceService(environment="production")
            
            with patch('httpx.AsyncClient') as mock_client:
                # Step 1: Submit invoice
                submit_response = mock_government_api(200, {
                    "RtnCode": "1",
                    "RtnMsg": "發票開立成功",
                    "InvoiceNo": "XY98765432",
                    "InvoiceDate": date.today().strftime("%Y/%m/%d"),
                    "RandomNumber": "5678",
                    "QRCode_Left": "**XY98765432:5678:20250726:5250",
                    "QRCode_Right": "5250:5000:250:53212539:AESEncryptedData",
                    "BarCode": "11201XY987654325678"
                })
                
                mock_async_client = AsyncMock()
                mock_async_client.post.return_value = submit_response
                mock_client.return_value.__aenter__.return_value = mock_async_client
                
                with patch('app.core.config.settings') as mock_settings:
                    mock_settings.ENVIRONMENT = "production"
                    
                    # Submit invoice
                    result = await service.submit_invoice(production_invoice)
                    
                    assert result["status"] == "success"
                    assert result["einvoice_id"] == "XY98765432"
                    assert result["qr_code_left"] is not None
                    assert result["qr_code_right"] is not None
                    assert result["bar_code"] is not None
                
                # Step 2: Query invoice status
                query_response = mock_government_api(200, {
                    "RtnCode": "1",
                    "RtnMsg": "查詢成功",
                    "Data": {
                        "InvoiceNo": "XY98765432",
                        "InvoiceStatus": "1",  # Issued
                        "InvoiceDate": date.today().strftime("%Y/%m/%d"),
                        "BuyerName": "台灣測試公司",
                        "BuyerId": "53212539",
                        "TotalAmount": "5250",
                        "VoidStatus": "0",
                        "VoidDate": ""
                    }
                })
                
                mock_async_client.post.return_value = query_response
                
                query_result = await service.query_invoice("XY98765432")
                
                assert query_result["status"] == "success"
                assert query_result["invoice_status"] == InvoiceStatus.ISSUED.value
                assert query_result["buyer_name"] == "台灣測試公司"
                assert query_result["total_amount"] == "5250"
                
                # Step 3: Void invoice
                void_response = mock_government_api(200, {
                    "RtnCode": "1",
                    "RtnMsg": "發票作廢成功",
                    "InvoiceNo": "XY98765432",
                    "VoidDate": date.today().strftime("%Y/%m/%d")
                })
                
                mock_async_client.post.return_value = void_response
                
                void_result = await service.void_invoice("XY98765432", "客戶退貨")
                
                assert void_result["status"] == "success"
                assert "作廢成功" in void_result["message"]
    
    @pytest.mark.asyncio
    async def test_b2c_invoice_submission(self, mock_government_api):
        """Test B2C invoice submission without tax ID"""
        
        # Create B2C invoice
        invoice = MagicMock(spec=Invoice)
        invoice.invoice_number = "AB11111111"
        invoice.invoice_track = "AB"
        invoice.invoice_no = "11111111"
        invoice.invoice_date = date.today()
        invoice.random_code = "1111"
        invoice.invoice_type = InvoiceType.B2C
        invoice.sales_amount = 100.0
        invoice.tax_type = "1"
        invoice.tax_rate = 0.05
        invoice.tax_amount = 5.0
        invoice.total_amount = 105.0
        invoice.buyer_tax_id = None  # B2C - no tax ID
        invoice.buyer_name = "消費者"
        invoice.buyer_address = ""
        invoice.is_printed = False
        
        item = MagicMock(spec=InvoiceItem)
        item.sequence = 1
        item.product_name = "瓦斯"
        item.quantity = 1
        item.unit = "罐"
        item.unit_price = 100
        item.amount = 100
        item.tax_type = "1"
        
        invoice.items = [item]
        
        with patch('app.core.einvoice_config.get_einvoice_config') as mock_config:
            mock_config.return_value = {
                "app_id": "PROD_APP_ID",
                "api_key": "PROD_API_KEY",
                "b2b_api_url": "https://www.einvoice.nat.gov.tw/BIZAPIVAN/biz",
                "b2c_api_url": "https://www.einvoice.nat.gov.tw/INVAPIVAN/invapp",
                "timeout": 30,
                "max_retries": 3,
                "retry_delay": 1,
                "cert_path": "",
                "key_path": ""
            }
            
            service = EInvoiceService(environment="production")
            
            with patch('httpx.AsyncClient') as mock_client:
                response = mock_government_api(200, {
                    "RtnCode": "1",
                    "RtnMsg": "B2C發票開立成功",
                    "InvoiceNo": "AB11111111",
                    "QRCode_Left": "**AB11111111:1111",
                    "QRCode_Right": "105:100:5::AESData",
                    "BarCode": "11201AB111111111111"
                })
                
                mock_async_client = AsyncMock()
                mock_async_client.post.return_value = response
                mock_client.return_value.__aenter__.return_value = mock_async_client
                
                with patch('app.core.config.settings') as mock_settings:
                    mock_settings.ENVIRONMENT = "production"
                    
                    result = await service.submit_invoice(invoice)
                    
                    assert result["status"] == "success"
                    assert result["einvoice_id"] == "AB11111111"
                    
                    # Verify B2C endpoint was used
                    call_args = mock_async_client.post.call_args
                    assert "/INVAPIVAN/invapp" in call_args[0][0]
    
    @pytest.mark.asyncio
    async def test_error_scenarios(self, mock_government_api):
        """Test various error scenarios with government API"""
        
        test_cases = [
            {
                "name": "Duplicate invoice number",
                "response": {"RtnCode": "5000001", "RtnMsg": "發票號碼重複"},
                "expected_error": "發票開立失敗 [5000001]: 發票號碼重複"
            },
            {
                "name": "Invalid tax ID",
                "response": {"RtnCode": "5000004", "RtnMsg": "買方統編錯誤"},
                "expected_error": "發票開立失敗 [5000004]: 買方統編錯誤"
            },
            {
                "name": "Invalid amount",
                "response": {"RtnCode": "5000006", "RtnMsg": "發票金額錯誤"},
                "expected_error": "發票開立失敗 [5000006]: 發票金額錯誤"
            },
            {
                "name": "Authentication failure",
                "response": {"RtnCode": "7000002", "RtnMsg": "簽章驗證失敗"},
                "expected_error": "發票開立失敗 [7000002]: 簽章驗證失敗"
            }
        ]
        
        with patch('app.core.einvoice_config.get_einvoice_config') as mock_config:
            mock_config.return_value = {
                "app_id": "PROD_APP_ID",
                "api_key": "PROD_API_KEY",
                "b2b_api_url": "https://www.einvoice.nat.gov.tw/BIZAPIVAN/biz",
                "b2c_api_url": "https://www.einvoice.nat.gov.tw/INVAPIVAN/invapp",
                "timeout": 30,
                "max_retries": 3,
                "retry_delay": 1,
                "cert_path": "",
                "key_path": ""
            }
            
            service = EInvoiceService(environment="production")
            
            for test_case in test_cases:
                with patch('httpx.AsyncClient') as mock_client:
                    response = mock_government_api(200, test_case["response"])
                    
                    mock_async_client = AsyncMock()
                    mock_async_client.post.return_value = response
                    mock_client.return_value.__aenter__.return_value = mock_async_client
                    
                    with patch('app.core.config.settings') as mock_settings:
                        mock_settings.ENVIRONMENT = "production"
                        
                        invoice = MagicMock(spec=Invoice)
                        invoice.invoice_number = "XX12345678"
                        invoice.invoice_type = InvoiceType.B2B
                        invoice.items = []
                        
                        with pytest.raises(Exception) as exc_info:
                            await service.submit_invoice(invoice)
                        
                        assert test_case["expected_error"] in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_allowance_issuance(self, mock_government_api):
        """Test credit note (allowance) issuance"""
        
        with patch('app.core.einvoice_config.get_einvoice_config') as mock_config:
            mock_config.return_value = {
                "app_id": "PROD_APP_ID",
                "api_key": "PROD_API_KEY",
                "b2b_api_url": "https://www.einvoice.nat.gov.tw/BIZAPIVAN/biz",
                "b2c_api_url": "https://www.einvoice.nat.gov.tw/INVAPIVAN/invapp",
                "timeout": 30,
                "max_retries": 3,
                "retry_delay": 1,
                "cert_path": "",
                "key_path": ""
            }
            
            service = EInvoiceService(environment="production")
            
            with patch('httpx.AsyncClient') as mock_client:
                response = mock_government_api(200, {
                    "RtnCode": "1",
                    "RtnMsg": "折讓單開立成功",
                    "AllowanceNo": "D20250126123456"
                })
                
                mock_async_client = AsyncMock()
                mock_async_client.post.return_value = response
                mock_client.return_value.__aenter__.return_value = mock_async_client
                
                with patch('app.core.config.settings') as mock_settings:
                    mock_settings.ENVIRONMENT = "production"
                    
                    items = [
                        {
                            "description": "退貨-液化石油氣",
                            "quantity": 1,
                            "unit": "桶",
                            "unit_price": 1000,
                            "amount": 1000,
                            "tax_type": "1"
                        }
                    ]
                    
                    result = await service.issue_allowance(
                        "XY98765432",
                        1000.0,
                        50.0,
                        "客戶退貨",
                        items
                    )
                    
                    assert result["status"] == "success"
                    assert result["allowance_number"] is not None
                    assert "折讓單開立成功" in result["message"]
    
    @pytest.mark.asyncio
    async def test_network_resilience(self, mock_government_api):
        """Test network error handling and retry mechanism"""
        
        with patch('app.core.einvoice_config.get_einvoice_config') as mock_config:
            mock_config.return_value = {
                "app_id": "PROD_APP_ID",
                "api_key": "PROD_API_KEY",
                "b2b_api_url": "https://www.einvoice.nat.gov.tw/BIZAPIVAN/biz",
                "b2c_api_url": "https://www.einvoice.nat.gov.tw/INVAPIVAN/invapp",
                "timeout": 30,
                "max_retries": 3,
                "retry_delay": 0.1,  # Faster for testing
                "cert_path": "",
                "key_path": ""
            }
            
            service = EInvoiceService(environment="production")
            
            with patch('httpx.AsyncClient') as mock_client:
                # Simulate network errors followed by success
                mock_async_client = AsyncMock()
                mock_async_client.post.side_effect = [
                    httpx.ConnectError("Connection failed"),
                    httpx.TimeoutException("Request timeout"),
                    mock_government_api(200, {
                        "RtnCode": "1",
                        "RtnMsg": "發票開立成功",
                        "InvoiceNo": "AB12345678"
                    })
                ]
                mock_client.return_value.__aenter__.return_value = mock_async_client
                
                invoice = MagicMock(spec=Invoice)
                invoice.invoice_number = "AB12345678"
                invoice.invoice_type = InvoiceType.B2B
                invoice.items = []
                
                # Should succeed after retries
                with patch('app.core.config.settings') as mock_settings:
                    mock_settings.ENVIRONMENT = "production"
                    
                    result = await service.submit_invoice(invoice)
                    
                    assert result["status"] == "success"
                    assert mock_async_client.post.call_count == 3
    
    @pytest.mark.asyncio
    async def test_concurrent_submissions(self, mock_government_api):
        """Test handling of concurrent invoice submissions"""
        
        with patch('app.core.einvoice_config.get_einvoice_config') as mock_config:
            mock_config.return_value = {
                "app_id": "PROD_APP_ID",
                "api_key": "PROD_API_KEY",
                "b2b_api_url": "https://www.einvoice.nat.gov.tw/BIZAPIVAN/biz",
                "b2c_api_url": "https://www.einvoice.nat.gov.tw/INVAPIVAN/invapp",
                "timeout": 30,
                "max_retries": 3,
                "retry_delay": 1,
                "cert_path": "",
                "key_path": ""
            }
            
            service = EInvoiceService(environment="production")
            
            # Create 10 different invoices
            invoices = []
            for i in range(10):
                invoice = MagicMock(spec=Invoice)
                invoice.invoice_number = f"AB0000000{i}"
                invoice.invoice_track = "AB"
                invoice.invoice_no = f"0000000{i}"
                invoice.invoice_type = InvoiceType.B2B
                invoice.buyer_tax_id = "53212539"
                invoice.total_amount = 1000 + i * 100
                invoice.items = []
                invoices.append(invoice)
            
            with patch('httpx.AsyncClient') as mock_client:
                async def mock_post(url, json):
                    # Simulate some processing time
                    await asyncio.sleep(0.1)
                    invoice_no = json.get("InvoiceNo", "")
                    return mock_government_api(200, {
                        "RtnCode": "1",
                        "RtnMsg": "發票開立成功",
                        "InvoiceNo": invoice_no
                    })
                
                mock_async_client = AsyncMock()
                mock_async_client.post.side_effect = mock_post
                mock_client.return_value.__aenter__.return_value = mock_async_client
                
                with patch('app.core.config.settings') as mock_settings:
                    mock_settings.ENVIRONMENT = "production"
                    
                    # Submit all invoices concurrently
                    tasks = [service.submit_invoice(inv) for inv in invoices]
                    results = await asyncio.gather(*tasks)
                    
                    # All should succeed
                    assert all(r["status"] == "success" for r in results)
                    assert len(set(r["einvoice_id"] for r in results)) == 10  # All unique
    
    @pytest.mark.asyncio
    async def test_circuit_breaker_activation(self, mock_government_api):
        """Test circuit breaker activation after repeated failures"""
        
        with patch('app.core.einvoice_config.get_einvoice_config') as mock_config:
            mock_config.return_value = {
                "app_id": "PROD_APP_ID",
                "api_key": "PROD_API_KEY",
                "b2b_api_url": "https://www.einvoice.nat.gov.tw/BIZAPIVAN/biz",
                "b2c_api_url": "https://www.einvoice.nat.gov.tw/INVAPIVAN/invapp",
                "timeout": 30,
                "max_retries": 1,  # Reduce retries for faster testing
                "retry_delay": 0.1,
                "cert_path": "",
                "key_path": ""
            }
            
            service = EInvoiceService(environment="production")
            
            with patch('httpx.AsyncClient') as mock_client:
                # Simulate consistent failures
                mock_async_client = AsyncMock()
                mock_async_client.post.side_effect = httpx.HTTPError("Server Error")
                mock_client.return_value.__aenter__.return_value = mock_async_client
                
                invoice = MagicMock(spec=Invoice)
                invoice.invoice_number = "XX12345678"
                invoice.invoice_type = InvoiceType.B2B
                invoice.items = []
                
                with patch('app.core.config.settings') as mock_settings:
                    mock_settings.ENVIRONMENT = "production"
                    
                    # Fail 5 times to open circuit
                    for i in range(5):
                        with pytest.raises(Exception):
                            await service.submit_invoice(invoice)
                    
                    # Next call should fail immediately with circuit open
                    with pytest.raises(Exception) as exc_info:
                        await service.submit_invoice(invoice)
                    
                    assert "電子發票服務暫時無法使用" in str(exc_info.value)


class TestEInvoicePerformance:
    """Performance tests for e-invoice service"""
    
    @pytest.mark.asyncio
    async def test_batch_submission_performance(self):
        """Test performance of batch invoice submissions"""
        
        # Create 100 test invoices
        invoices = []
        for i in range(100):
            invoice = MagicMock(spec=Invoice)
            invoice.invoice_number = f"PERF{i:08d}"
            invoice.invoice_type = InvoiceType.B2B
            invoice.total_amount = 1000.0
            invoice.items = []
            invoices.append(invoice)
        
        service = get_einvoice_service()
        
        # Time the batch submission
        start_time = datetime.now()
        
        # Submit all invoices (in mock mode)
        results = []
        for invoice in invoices:
            result = await service.submit_invoice(invoice)
            results.append(result)
        
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()
        
        # All should succeed in mock mode
        assert all(r["status"] == "success" for r in results)
        
        # Should complete within 50ms for 100 invoices in mock mode
        assert duration < 0.05, f"Batch submission too slow: {duration}s"
    
    @pytest.mark.asyncio
    async def test_memory_usage_under_load(self):
        """Test memory usage doesn't grow excessively under load"""
        import gc
        import sys
        
        service = get_einvoice_service()
        
        # Force garbage collection
        gc.collect()
        initial_objects = len(gc.get_objects())
        
        # Submit 1000 invoices
        for i in range(1000):
            invoice = MagicMock(spec=Invoice)
            invoice.invoice_number = f"MEM{i:08d}"
            invoice.invoice_type = InvoiceType.B2C
            invoice.items = []
            
            await service.submit_invoice(invoice)
            
            # Periodic garbage collection
            if i % 100 == 0:
                gc.collect()
        
        # Final garbage collection
        gc.collect()
        final_objects = len(gc.get_objects())
        
        # Object count shouldn't grow significantly
        object_growth = final_objects - initial_objects
        assert object_growth < 10000, f"Too many objects created: {object_growth}"