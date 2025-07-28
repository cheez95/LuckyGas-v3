"""
Performance tests for Taiwan E-Invoice API integration

Tests cover:
- API response time requirements
- Circuit breaker thresholds
- Retry behavior under load
- Mock mode performance
- Concurrent request handling
- Memory usage patterns
"""
import pytest
import asyncio
import time
import psutil
import os
from datetime import datetime
from unittest.mock import MagicMock, patch, AsyncMock
import httpx

from app.services.einvoice_service import EInvoiceService, get_einvoice_service
from app.models.invoice import Invoice, InvoiceItem, InvoiceType


class TestEInvoicePerformance:
    """Performance benchmarks for e-invoice service"""
    
    @pytest.fixture
    def performance_invoice(self):
        """Create invoice for performance testing"""
        invoice = MagicMock(spec=Invoice)
        invoice.invoice_number = "PERF12345678"
        invoice.invoice_track = "PE"
        invoice.invoice_no = "RF12345678"
        invoice.invoice_date = datetime.now().date()
        invoice.random_code = "9999"
        invoice.invoice_type = InvoiceType.B2B
        invoice.sales_amount = 10000.0
        invoice.tax_type = "1"
        invoice.tax_rate = 0.05
        invoice.tax_amount = 500.0
        invoice.total_amount = 10500.0
        invoice.buyer_tax_id = "53212539"
        invoice.buyer_name = "效能測試公司"
        invoice.is_printed = True
        
        # Create 10 items for more realistic payload
        invoice.items = []
        for i in range(10):
            item = MagicMock(spec=InvoiceItem)
            item.sequence = i + 1
            item.product_name = f"測試產品 {i+1}"
            item.quantity = 10
            item.unit = "個"
            item.unit_price = 100
            item.amount = 1000
            item.tax_type = "1"
            invoice.items.append(item)
        
        return invoice
    
    @pytest.mark.asyncio
    async def test_mock_mode_response_time(self, performance_invoice):
        """Test that mock mode responds within 10ms"""
        service = get_einvoice_service()
        
        # Warm up
        await service.submit_invoice(performance_invoice)
        
        # Measure response time
        times = []
        for i in range(100):
            performance_invoice.invoice_number = f"PERF{i:08d}"
            
            start = time.time()
            result = await service.submit_invoice(performance_invoice)
            end = time.time()
            
            times.append(end - start)
            assert result["status"] == "success"
        
        # Calculate statistics
        avg_time = sum(times) / len(times)
        max_time = max(times)
        min_time = min(times)
        
        print(f"\nMock Mode Performance:")
        print(f"  Average: {avg_time*1000:.2f}ms")
        print(f"  Min: {min_time*1000:.2f}ms")
        print(f"  Max: {max_time*1000:.2f}ms")
        
        # Mock mode should be very fast
        assert avg_time < 0.01  # 10ms average
        assert max_time < 0.05  # 50ms max
    
    @pytest.mark.asyncio
    async def test_production_mode_response_time(self, performance_invoice):
        """Test production mode response time with mocked API"""
        
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
                # Simulate realistic API response time (100-300ms)
                async def mock_post(*args, **kwargs):
                    await asyncio.sleep(0.1 + (i % 3) * 0.1)  # 100-300ms
                    return MagicMock(
                        status_code=200,
                        json=lambda: {
                            "RtnCode": "1",
                            "RtnMsg": "Success",
                            "InvoiceNo": performance_invoice.invoice_number
                        },
                        raise_for_status=lambda: None
                    )
                
                mock_async_client = AsyncMock()
                mock_async_client.post.side_effect = mock_post
                mock_client.return_value.__aenter__.return_value = mock_async_client
                
                with patch('app.core.config.settings') as mock_settings:
                    mock_settings.ENVIRONMENT = "production"
                    
                    times = []
                    for i in range(10):
                        performance_invoice.invoice_number = f"PROD{i:08d}"
                        
                        start = time.time()
                        result = await service.submit_invoice(performance_invoice)
                        end = time.time()
                        
                        times.append(end - start)
                        assert result["status"] == "success"
                    
                    avg_time = sum(times) / len(times)
                    print(f"\nProduction Mode Performance (with network simulation):")
                    print(f"  Average: {avg_time*1000:.2f}ms")
                    
                    # Should be under 2 seconds including network
                    assert avg_time < 2.0
    
    @pytest.mark.asyncio
    async def test_concurrent_request_handling(self, performance_invoice):
        """Test handling of concurrent requests"""
        
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
                request_times = []
                
                async def mock_post(*args, **kwargs):
                    start = time.time()
                    await asyncio.sleep(0.1)  # Simulate API delay
                    request_times.append(time.time() - start)
                    return MagicMock(
                        status_code=200,
                        json=lambda: {"RtnCode": "1", "RtnMsg": "Success"},
                        raise_for_status=lambda: None
                    )
                
                mock_async_client = AsyncMock()
                mock_async_client.post.side_effect = mock_post
                mock_client.return_value.__aenter__.return_value = mock_async_client
                
                with patch('app.core.config.settings') as mock_settings:
                    mock_settings.ENVIRONMENT = "production"
                    
                    # Create 50 concurrent requests
                    invoices = []
                    for i in range(50):
                        inv = MagicMock(spec=Invoice)
                        inv.invoice_number = f"CONC{i:08d}"
                        inv.invoice_type = InvoiceType.B2B
                        inv.items = []
                        invoices.append(inv)
                    
                    # Submit all concurrently
                    start_time = time.time()
                    tasks = [service.submit_invoice(inv) for inv in invoices]
                    results = await asyncio.gather(*tasks)
                    total_time = time.time() - start_time
                    
                    # All should succeed
                    assert all(r["status"] == "success" for r in results)
                    
                    print(f"\nConcurrent Request Performance:")
                    print(f"  Total requests: 50")
                    print(f"  Total time: {total_time:.2f}s")
                    print(f"  Throughput: {50/total_time:.2f} requests/second")
                    
                    # Should complete 50 requests in under 10 seconds
                    assert total_time < 10.0
    
    @pytest.mark.asyncio
    async def test_circuit_breaker_performance(self):
        """Test circuit breaker activation performance"""
        
        with patch('app.core.einvoice_config.get_einvoice_config') as mock_config:
            mock_config.return_value = {
                "app_id": "PROD_APP_ID",
                "api_key": "PROD_API_KEY",
                "b2b_api_url": "https://www.einvoice.nat.gov.tw/BIZAPIVAN/biz",
                "b2c_api_url": "https://www.einvoice.nat.gov.tw/INVAPIVAN/invapp",
                "timeout": 30,
                "max_retries": 1,  # Reduce for faster testing
                "retry_delay": 0.1,
                "cert_path": "",
                "key_path": ""
            }
            
            service = EInvoiceService(environment="production")
            
            with patch('httpx.AsyncClient') as mock_client:
                # Always fail to trigger circuit breaker
                mock_async_client = AsyncMock()
                mock_async_client.post.side_effect = httpx.HTTPError("Server Error")
                mock_client.return_value.__aenter__.return_value = mock_async_client
                
                invoice = MagicMock(spec=Invoice)
                invoice.invoice_number = "CB12345678"
                invoice.invoice_type = InvoiceType.B2B
                invoice.items = []
                
                with patch('app.core.config.settings') as mock_settings:
                    mock_settings.ENVIRONMENT = "production"
                    
                    # Time how long it takes to open circuit
                    start_time = time.time()
                    
                    # Fail 5 times to open circuit
                    for i in range(5):
                        try:
                            await service.submit_invoice(invoice)
                        except:
                            pass
                    
                    circuit_open_time = time.time() - start_time
                    
                    # Now test fast-fail when circuit is open
                    fast_fail_times = []
                    for i in range(10):
                        start = time.time()
                        try:
                            await service.submit_invoice(invoice)
                        except Exception as e:
                            assert "電子發票服務暫時無法使用" in str(e)
                        fast_fail_times.append(time.time() - start)
                    
                    avg_fail_time = sum(fast_fail_times) / len(fast_fail_times)
                    
                    print(f"\nCircuit Breaker Performance:")
                    print(f"  Time to open: {circuit_open_time:.2f}s")
                    print(f"  Fast-fail time: {avg_fail_time*1000:.2f}ms")
                    
                    # Fast-fail should be very quick
                    assert avg_fail_time < 0.001  # 1ms
    
    @pytest.mark.asyncio
    async def test_memory_usage_pattern(self, performance_invoice):
        """Test memory usage doesn't grow excessively"""
        
        service = get_einvoice_service()
        process = psutil.Process(os.getpid())
        
        # Get initial memory
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB
        
        # Submit 1000 invoices
        for i in range(1000):
            performance_invoice.invoice_number = f"MEM{i:08d}"
            await service.submit_invoice(performance_invoice)
        
        # Get final memory
        final_memory = process.memory_info().rss / 1024 / 1024  # MB
        memory_growth = final_memory - initial_memory
        
        print(f"\nMemory Usage Pattern:")
        print(f"  Initial: {initial_memory:.2f} MB")
        print(f"  Final: {final_memory:.2f} MB")
        print(f"  Growth: {memory_growth:.2f} MB")
        
        # Memory growth should be reasonable (less than 50MB for 1000 invoices)
        assert memory_growth < 50
    
    @pytest.mark.asyncio
    async def test_batch_processing_optimization(self, performance_invoice):
        """Test batch processing performance"""
        
        service = get_einvoice_service()
        
        # Test different batch sizes
        batch_sizes = [1, 10, 50, 100]
        results = {}
        
        for batch_size in batch_sizes:
            invoices = []
            for i in range(batch_size):
                inv = MagicMock(spec=Invoice)
                inv.invoice_number = f"BATCH{i:08d}"
                inv.invoice_type = InvoiceType.B2B
                inv.items = performance_invoice.items
                invoices.append(inv)
            
            start_time = time.time()
            
            # Process batch
            tasks = [service.submit_invoice(inv) for inv in invoices]
            await asyncio.gather(*tasks)
            
            total_time = time.time() - start_time
            per_invoice_time = total_time / batch_size
            
            results[batch_size] = {
                'total_time': total_time,
                'per_invoice': per_invoice_time,
                'throughput': batch_size / total_time
            }
        
        print(f"\nBatch Processing Performance:")
        for size, metrics in results.items():
            print(f"  Batch size {size}:")
            print(f"    Total time: {metrics['total_time']:.3f}s")
            print(f"    Per invoice: {metrics['per_invoice']*1000:.2f}ms")
            print(f"    Throughput: {metrics['throughput']:.2f} invoices/s")
        
        # Larger batches should be more efficient
        assert results[100]['per_invoice'] < results[1]['per_invoice']
    
    @pytest.mark.asyncio
    async def test_retry_performance_impact(self):
        """Test performance impact of retry mechanism"""
        
        with patch('app.core.einvoice_config.get_einvoice_config') as mock_config:
            mock_config.return_value = {
                "app_id": "PROD_APP_ID",
                "api_key": "PROD_API_KEY",
                "b2b_api_url": "https://www.einvoice.nat.gov.tw/BIZAPIVAN/biz",
                "b2c_api_url": "https://www.einvoice.nat.gov.tw/INVAPIVAN/invapp",
                "timeout": 30,
                "max_retries": 3,
                "retry_delay": 0.1,  # Fast for testing
                "cert_path": "",
                "key_path": ""
            }
            
            service = EInvoiceService(environment="production")
            
            with patch('httpx.AsyncClient') as mock_client:
                # Fail twice, then succeed
                call_count = 0
                
                async def mock_post(*args, **kwargs):
                    nonlocal call_count
                    call_count += 1
                    if call_count < 3:
                        raise httpx.HTTPError("Temporary failure")
                    return MagicMock(
                        status_code=200,
                        json=lambda: {"RtnCode": "1", "RtnMsg": "Success"},
                        raise_for_status=lambda: None
                    )
                
                mock_async_client = AsyncMock()
                mock_async_client.post.side_effect = mock_post
                mock_client.return_value.__aenter__.return_value = mock_async_client
                
                invoice = MagicMock(spec=Invoice)
                invoice.invoice_number = "RETRY123456"
                invoice.invoice_type = InvoiceType.B2B
                invoice.items = []
                
                with patch('app.core.config.settings') as mock_settings:
                    mock_settings.ENVIRONMENT = "production"
                    
                    start_time = time.time()
                    result = await service.submit_invoice(invoice)
                    retry_time = time.time() - start_time
                    
                    assert result["status"] == "success"
                    assert call_count == 3
                    
                    print(f"\nRetry Performance Impact:")
                    print(f"  Retries: 2")
                    print(f"  Total time: {retry_time:.2f}s")
                    print(f"  Expected minimum: {0.1 + 0.2:.2f}s (exponential backoff)")
                    
                    # Should include retry delays
                    assert retry_time >= 0.3  # At least the sum of delays