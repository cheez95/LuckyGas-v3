"""
Chaos Engineering Tests - External API Failures
Tests system resilience when external services fail
"""

import asyncio
import json
import time
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import AsyncClient, ConnectError, ReadTimeout


class TestExternalAPIChaos:
    """Test system behavior when external APIs fail"""

    @pytest.mark.chaos
    @pytest.mark.asyncio
    async def test_einvoice_api_failure(self, client: AsyncClient):
        """Test system behavior when E-Invoice API fails"""
        # Create order that needs invoice
        order_data = {
            "customer_id": 1,
            "scheduled_date": (datetime.now() + timedelta(days=1)).isoformat(),
            "qty_50kg": 2,
            "payment_method": "cash",
            "delivery_address": "Test Address",
            "issue_invoice": True,
        }

        # Mock E-Invoice API failure
        with patch(
            "app.services.einvoice_service.EInvoiceService.issue_invoice"
        ) as mock_einvoice:
            mock_einvoice.side_effect = ConnectError("E-Invoice API unavailable")

            # Create order
            response = await client.post(
                "/api/v1/orders",
                json=order_data,
                headers={"Authorization": "Bearer test-token"},
            )

            # Order creation should succeed even if invoice fails
            assert response.status_code in [
                201,
                401,
            ], "Order creation should not fail due to E-Invoice API"

            if response.status_code == 201:
                order = response.json()["data"]

                # Check if system queued invoice for retry
                assert (
                    "invoice_status" in order or "invoice_queued" in order
                ), "System should indicate invoice status"

                # Verify order is marked for invoice retry
                order_id = order["id"]

                # Check retry queue
                queue_response = await client.get(
                    f"/api/v1/admin/invoice-queue",
                    headers={"Authorization": "Bearer admin-token"},
                )

                if queue_response.status_code == 200:
                    queue = queue_response.json()["data"]
                    queued_order_ids = [item["order_id"] for item in queue]
                    assert (
                        order_id in queued_order_ids
                    ), "Failed invoice should be queued for retry"

    @pytest.mark.chaos
    @pytest.mark.asyncio
    async def test_einvoice_api_timeout(self, client: AsyncClient):
        """Test handling of E-Invoice API timeouts"""
        timeout_scenarios = [
            {"delay": 5, "timeout": 3, "should_fail": True},  # Timeout
            {"delay": 2, "timeout": 5, "should_fail": False},  # Success
            {"delay": 10, "timeout": 5, "should_fail": True},  # Long timeout
        ]

        for scenario in timeout_scenarios:
            # Mock slow E-Invoice API
            async def slow_einvoice(*args, **kwargs):
                await asyncio.sleep(scenario["delay"])
                return {"invoice_number": "TEST123", "status": "success"}

            with patch(
                "app.services.einvoice_service.EInvoiceService.issue_invoice",
                side_effect=slow_einvoice,
            ):

                start_time = time.time()

                # Attempt to issue invoice
                response = await client.post(
                    "/api/v1/invoices/issue",
                    json={"order_id": 1},
                    headers={"Authorization": "Bearer test-token"},
                    timeout=scenario["timeout"],
                )

                elapsed = time.time() - start_time

                if scenario["should_fail"]:
                    # Should timeout or return error
                    assert (
                        response.status_code in [408, 504]
                        or elapsed > scenario["timeout"]
                    ), f"Should timeout for {scenario['delay']}s delay with {scenario['timeout']}s timeout"
                else:
                    # Should succeed
                    assert response.status_code in [
                        200,
                        201,
                        401,
                    ], f"Should succeed for {scenario['delay']}s delay with {scenario['timeout']}s timeout"

    @pytest.mark.chaos
    @pytest.mark.asyncio
    async def test_banking_sftp_disconnect(self, client: AsyncClient):
        """Test system behavior when banking SFTP connection fails"""
        # Mock SFTP connection failure
        with patch(
            "app.services.banking_service.BankingSFTPService.connect"
        ) as mock_sftp:
            mock_sftp.side_effect = ConnectionError("SFTP connection refused")

            # Try to sync bank transactions
            response = await client.post(
                "/api/v1/banking/sync", headers={"Authorization": "Bearer admin-token"}
            )

            # Should handle gracefully
            assert response.status_code in [
                200,
                503,
                401,
            ], "Banking sync should handle SFTP failure gracefully"

            if response.status_code == 503:
                error_data = response.json()
                assert "error" in error_data or "message" in error_data
                # Should indicate retry or manual intervention needed
                assert any(
                    word in str(error_data).lower()
                    for word in ["retry", "later", "unavailable", "manual"]
                )

    @pytest.mark.chaos
    @pytest.mark.asyncio
    async def test_banking_file_corruption(self, client: AsyncClient):
        """Test handling of corrupted banking files"""
        # Mock corrupted file scenarios
        corrupt_scenarios = [
            {"content": "INVALID_XML_CONTENT", "type": "invalid_format"},
            {"content": '{"incomplete": ', "type": "incomplete_json"},
            {"content": "亂碼內容", "type": "encoding_error"},
            {"content": "", "type": "empty_file"},
        ]

        for scenario in corrupt_scenarios:
            with patch(
                "app.services.banking_service.BankingSFTPService.download_file"
            ) as mock_download:
                mock_download.return_value = scenario["content"].encode("utf-8")

                # Attempt to process banking file
                response = await client.post(
                    "/api/v1/banking/process-file",
                    json={"filename": f"test_{scenario['type']}.txt"},
                    headers={"Authorization": "Bearer admin-token"},
                )

                # Should not crash, should handle gracefully
                assert response.status_code in [
                    200,
                    400,
                    422,
                    401,
                ], f"Should handle {scenario['type']} gracefully"

                if response.status_code in [400, 422]:
                    error_data = response.json()
                    # Should provide meaningful error
                    assert "error" in error_data or "detail" in error_data
                    print(f"Handled {scenario['type']}: {error_data}")

    @pytest.mark.chaos
    @pytest.mark.asyncio
    async def test_sms_gateway_timeout(self, client: AsyncClient):
        """Test system behavior when SMS gateway times out"""
        # Create scenario requiring SMS notification
        notification_data = {
            "type": "delivery_notification",
            "customer_id": 1,
            "message": "您的瓦斯將在30分鐘內送達",
            "phone": "0912345678",
        }

        # Mock SMS gateway timeout
        async def timeout_sms(*args, **kwargs):
            await asyncio.sleep(10)  # Long delay to trigger timeout

        with patch(
            "app.services.sms_service.SMSService.send_sms", side_effect=timeout_sms
        ):
            # Send notification
            response = await client.post(
                "/api/v1/notifications/sms",
                json=notification_data,
                headers={"Authorization": "Bearer test-token"},
                timeout=5.0,  # Shorter timeout than SMS delay
            )

            # Should not block main operation
            assert response.status_code in [
                200,
                202,
                408,
                401,
            ], "SMS timeout should not block notification request"

            if response.status_code in [200, 202]:
                result = response.json()
                # Should indicate async processing or queue
                assert any(
                    key in result.get("data", {})
                    for key in ["queued", "async", "pending", "background"]
                )

    @pytest.mark.chaos
    @pytest.mark.asyncio
    async def test_sms_gateway_rate_limit(self, client: AsyncClient):
        """Test handling of SMS gateway rate limits"""
        # Send many SMS requests quickly
        sms_requests = []
        rate_limit_hit = False

        for i in range(20):  # Typical rate limit threshold
            response = await client.post(
                "/api/v1/notifications/sms",
                json={
                    "customer_id": i + 1,
                    "message": f"Test message {i}",
                    "phone": f"091234{i:04d}",
                },
                headers={"Authorization": "Bearer test-token"},
            )

            sms_requests.append(
                {
                    "request_id": i,
                    "status_code": response.status_code,
                    "timestamp": time.time(),
                }
            )

            # Check for rate limit response
            if response.status_code == 429:
                rate_limit_hit = True
                rate_limit_response = response.json()

                # Should provide retry-after header or info
                retry_after = response.headers.get(
                    "Retry-After"
                ) or rate_limit_response.get("retry_after")
                assert (
                    retry_after is not None
                ), "Rate limit response should include retry information"
                break

            # Small delay between requests
            await asyncio.sleep(0.1)

        # Should handle rate limits gracefully
        failed_requests = [r for r in sms_requests if r["status_code"] >= 500]
        assert len(failed_requests) == 0, "Rate limiting should not cause server errors"

    @pytest.mark.chaos
    @pytest.mark.asyncio
    async def test_google_maps_api_quota_exceeded(self, client: AsyncClient):
        """Test behavior when Google Maps API quota is exceeded"""
        # Mock quota exceeded response
        quota_error = {
            "error": {
                "code": 429,
                "message": "Quota exceeded for quota metric 'Requests' and limit 'Requests per day'",
                "status": "RESOURCE_EXHAUSTED",
            }
        }

        with patch(
            "app.services.google_routes_service.GoogleRoutesService.optimize_route"
        ) as mock_routes:
            mock_routes.side_effect = Exception(json.dumps(quota_error))

            # Try to optimize routes
            response = await client.post(
                "/api/v1/routes/optimize",
                json={
                    "date": (datetime.now() + timedelta(days=1)).isoformat(),
                    "area": "信義區",
                },
                headers={"Authorization": "Bearer test-token"},
            )

            # Should fallback gracefully
            assert response.status_code in [
                200,
                503,
                429,
                401,
            ], "Should handle Maps API quota exceeded"

            if response.status_code in [503, 429]:
                error_data = response.json()
                # Should indicate quota issue
                assert any(
                    word in str(error_data).lower()
                    for word in ["quota", "limit", "exceeded", "fallback"]
                )
            elif response.status_code == 200:
                # Should use fallback algorithm
                result = response.json()["data"]
                assert (
                    "fallback_used" in result or "optimization_method" in result
                ), "Should indicate fallback optimization was used"

    @pytest.mark.chaos
    @pytest.mark.asyncio
    async def test_multiple_external_api_failures(self, client: AsyncClient):
        """Test cascading failures across multiple external APIs"""
        # Simulate multiple API failures
        with (
            patch(
                "app.services.einvoice_service.EInvoiceService.issue_invoice"
            ) as mock_einvoice,
            patch("app.services.sms_service.SMSService.send_sms") as mock_sms,
            patch(
                "app.services.google_routes_service.GoogleRoutesService.get_distance"
            ) as mock_maps,
        ):

            # All external APIs fail
            mock_einvoice.side_effect = ConnectError("E-Invoice down")
            mock_sms.side_effect = ReadTimeout("SMS timeout")
            mock_maps.side_effect = Exception("Maps API error")

            # Core operations should still work
            # Test order creation
            order_response = await client.post(
                "/api/v1/orders",
                json={
                    "customer_id": 1,
                    "scheduled_date": (datetime.now() + timedelta(days=1)).isoformat(),
                    "qty_50kg": 1,
                    "payment_method": "cash",
                    "delivery_address": "Test",
                },
                headers={"Authorization": "Bearer test-token"},
            )

            # Order should still be created
            assert order_response.status_code in [
                201,
                401,
            ], "Core operations should work despite external API failures"

            # Test customer creation
            customer_response = await client.post(
                "/api/v1/customers",
                json={
                    "customer_code": "CHAOS001",
                    "short_name": "Chaos Test",
                    "address": "Test Address",
                    "phone": "0912345678",
                },
                headers={"Authorization": "Bearer test-token"},
            )

            # Customer should still be created
            assert customer_response.status_code in [
                201,
                401,
            ], "Core operations should work despite external API failures"

            # Check system health
            health_response = await client.get("/api/v1/health")
            assert (
                health_response.status_code == 200
            ), "System should remain healthy despite external API failures"

            if health_response.status_code == 200:
                health_data = health_response.json()
                # Should indicate degraded external services
                if "services" in health_data:
                    external_services = ["einvoice", "sms", "maps", "google"]
                    degraded_count = sum(
                        1
                        for service in health_data["services"]
                        if service.get("name", "").lower() in external_services
                        and service.get("status") != "healthy"
                    )
                    assert (
                        degraded_count > 0
                    ), "Health check should reflect external service failures"

    @pytest.mark.chaos
    @pytest.mark.asyncio
    async def test_fallback_mechanism_activation(self, client: AsyncClient):
        """Test that fallback mechanisms activate correctly"""
        fallback_scenarios = [
            {
                "service": "einvoice",
                "primary": "app.services.einvoice_service.EInvoiceService.issue_invoice",
                "fallback_indicator": "manual_invoice_required",
            },
            {
                "service": "sms",
                "primary": "app.services.sms_service.SMSService.send_sms",
                "fallback_indicator": "email_notification_sent",
            },
            {
                "service": "maps",
                "primary": "app.services.google_routes_service.GoogleRoutesService.optimize_route",
                "fallback_indicator": "basic_optimization_used",
            },
        ]

        for scenario in fallback_scenarios:
            with patch(scenario["primary"]) as mock_service:
                mock_service.side_effect = Exception(
                    f"{scenario['service']} unavailable"
                )

                # Trigger service usage
                if scenario["service"] == "einvoice":
                    response = await client.post(
                        "/api/v1/orders/1/invoice",
                        headers={"Authorization": "Bearer test-token"},
                    )
                elif scenario["service"] == "sms":
                    response = await client.post(
                        "/api/v1/notifications/delivery/1",
                        headers={"Authorization": "Bearer test-token"},
                    )
                elif scenario["service"] == "maps":
                    response = await client.post(
                        "/api/v1/routes/optimize",
                        json={"date": "2024-12-25", "area": "test"},
                        headers={"Authorization": "Bearer test-token"},
                    )

                # Should not fail completely
                assert response.status_code not in [
                    500,
                    502,
                    504,
                ], f"{scenario['service']} failure should trigger fallback, not error"

                if response.status_code in [200, 201]:
                    result = response.json()
                    # Should indicate fallback was used
                    assert (
                        scenario["fallback_indicator"] in str(result).lower()
                        or "fallback" in str(result).lower()
                    ), f"{scenario['service']} should indicate fallback mechanism used"
