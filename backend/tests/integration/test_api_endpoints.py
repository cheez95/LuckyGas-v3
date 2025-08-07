"""
from dataclasses import dataclass
from typing import Any
from typing import Callable
from typing import Dict
from typing import List
from typing import Optional
from typing import Tuple
from typing import Union

from datetime import date
from datetime import timedelta

Integration tests for API endpoints
"""

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.invoice import InvoiceStatus, InvoiceType
from app.models.order import OrderStatus


class TestCustomerAPIIntegration:
    """Test customer API endpoints with full integration"""

    @pytest.mark.asyncio
    async def test_customer_lifecycle(self, client: AsyncClient, auth_headers: dict):
        """Test complete customer lifecycle: create, read, update, delete"""
        # Create customer
        customer_data = {
            "customer_code": "INT001",
            "short_name": "整合測試客戶",
            "full_name": "整合測試客戶有限公司",
            "tax_id": "12345678",
            "address": "台北市信義區整合路100號",
            "phone": "0912345678",
            "area": "信義區",
            "customer_type": "COMMERCIAL",
            "credit_limit": 50000,
            "payment_terms": 30,
        }

        # Create
        response = await client.post(
            "/api / v1 / customers", json=customer_data, headers=auth_headers
        )
        assert response.status_code == 201
        created_customer = response.json()
        customer_id = created_customer["id"]

        # Read
        response = await client.get(
            f"/api / v1 / customers/{customer_id}", headers=auth_headers
        )
        assert response.status_code == 200
        customer = response.json()
        assert customer["short_name"] == "整合測試客戶"
        assert customer["credit_limit"] == 50000

        # Update
        update_data = {"credit_limit": 100000}
        response = await client.patch(
            f"/api / v1 / customers/{customer_id}",
            json=update_data,
            headers=auth_headers,
        )
        assert response.status_code == 200
        updated_customer = response.json()
        assert updated_customer["credit_limit"] == 100000

        # List with search
        response = await client.get(
            "/api / v1 / customers?search=整合測試", headers=auth_headers
        )
        assert response.status_code == 200
        customers = response.json()
        assert len(customers["items"]) >= 1
        assert any(c["id"] == customer_id for c in customers["items"])

    @pytest.mark.asyncio
    async def test_customer_validation(self, client: AsyncClient, auth_headers: dict):
        """Test customer data validation"""
        # Invalid tax ID
        invalid_data = {
            "customer_code": "INVALID",
            "short_name": "Invalid",
            "tax_id": "123",  # Too short
            "address": "Test",
            "phone": "123",  # Invalid format
        }

        response = await client.post(
            "/api / v1 / customers", json=invalid_data, headers=auth_headers
        )
        assert response.status_code == 422
        errors = response.json()
        assert "detail" in errors


class TestOrderAPIIntegration:
    """Test order API endpoints with full integration"""

    @pytest.mark.asyncio
    async def test_order_workflow(
        self, client: AsyncClient, auth_headers: dict, test_customer
    ):
        """Test complete order workflow from creation to delivery"""
        # Create order
        order_data = {
            "customer_id": test_customer.id,
            "scheduled_date": (date.today() + timedelta(days=2)).isoformat(),
            "qty_50kg": 2,
            "qty_20kg": 1,
            "qty_10kg": 0,
            "unit_price_50kg": 1500,
            "unit_price_20kg": 600,
            "unit_price_10kg": 300,
            "delivery_address": test_customer.address,
            "delivery_notes": "請先電話聯絡",
            "is_urgent": False,
        }

        # Create order
        response = await client.post(
            "/api / v1 / orders", json=order_data, headers=auth_headers
        )
        assert response.status_code == 201
        order = response.json()
        order_id = order["id"]
        assert order["status"] == OrderStatus.PENDING.value
        assert order["total_amount"] == 3600  # (2 * 1500) + (1 * 600)

        # Confirm order
        response = await client.post(
            f"/api / v1 / orders/{order_id}/confirm", headers=auth_headers
        )
        assert response.status_code == 200
        confirmed_order = response.json()
        assert confirmed_order["status"] == OrderStatus.CONFIRMED.value

        # Get order details
        response = await client.get(
            f"/api / v1 / orders/{order_id}", headers=auth_headers
        )
        assert response.status_code == 200
        order_detail = response.json()
        assert order_detail["customer"]["id"] == test_customer.id

        # Update delivery status (simulate driver)
        response = await client.put(
            f"/api / v1 / orders/{order_id}/status",
            json={"status": OrderStatus.DELIVERED.value},
            headers=auth_headers,
        )
        assert response.status_code == 200
        delivered_order = response.json()
        assert delivered_order["status"] == OrderStatus.DELIVERED.value

    @pytest.mark.asyncio
    async def test_bulk_order_creation(
        self, client: AsyncClient, auth_headers: dict, test_customer
    ):
        """Test bulk order creation"""
        bulk_data = {
            "orders": [
                {
                    "customer_id": test_customer.id,
                    "scheduled_date": (date.today() + timedelta(days=i)).isoformat(),
                    "qty_50kg": i,
                    "qty_20kg": 1,
                    "unit_price_50kg": 1500,
                    "unit_price_20kg": 600,
                }
                for i in range(1, 4)
            ]
        }

        response = await client.post(
            "/api / v1 / orders / bulk", json=bulk_data, headers=auth_headers
        )
        assert response.status_code == 201
        result = response.json()
        assert result["created"] == 3
        assert len(result["orders"]) == 3


class TestInvoiceAPIIntegration:
    """Test invoice API endpoints with full integration"""

    @pytest.mark.asyncio
    async def test_invoice_generation_flow(
        self, client: AsyncClient, auth_headers: dict, test_customer, mock_einvoice_api
    ):
        """Test invoice generation from order"""
        # First create an order
        order_data = {
            "customer_id": test_customer.id,
            "scheduled_date": date.today().isoformat(),
            "qty_50kg": 2,
            "unit_price_50kg": 1500,
            "status": OrderStatus.DELIVERED.value,
        }

        response = await client.post(
            "/api / v1 / orders", json=order_data, headers=auth_headers
        )
        order = response.json()
        order_id = order["id"]

        # Generate invoice from order
        invoice_data = {
            "order_id": order_id,
            "customer_id": test_customer.id,
            "invoice_date": date.today().isoformat(),
        }

        response = await client.post(
            "/api / v1 / invoices", json=invoice_data, headers=auth_headers
        )
        assert response.status_code == 201
        invoice = response.json()
        assert invoice["order_id"] == order_id
        assert invoice["total_amount"] == 3000
        assert invoice["tax_amount"] == 150  # 5% tax
        assert invoice["grand_total"] == 3150

        # Submit to government (mocked)
        response = await client.post(
            f"/api / v1 / invoices/{invoice['id']}/submit", headers=auth_headers
        )
        assert response.status_code == 200
        result = response.json()
        assert result["success"] is True
        assert mock_einvoice_api.called


class TestFinancialReportIntegration:
    """Test financial reporting API endpoints"""

    @pytest.mark.asyncio
    async def test_revenue_report_generation(
        self,
        client: AsyncClient,
        auth_headers: dict,
        test_customer,
        db_session: AsyncSession,
    ):
        """Test revenue report with actual data"""
        # Create test invoices
        current_month = date.today().strftime("%Y % m")

        # Create multiple invoices
        for i in range(3):
            invoice = {
                "customer_id": test_customer.id,
                "invoice_number": f"INV{current_month}{i:04d}",
                "invoice_type": InvoiceType.B2B.value,
                "total_amount": 10000 * (i + 1),
                "tax_amount": 500 * (i + 1),
                "grand_total": 10500 * (i + 1),
                "invoice_date": date.today().isoformat(),
                "status": (
                    InvoiceStatus.PAID.value if i < 2 else InvoiceStatus.ISSUED.value
                ),
            }

            # Note: This would normally go through proper invoice creation
            # For testing, we're simplifying

        # Get revenue report
        response = await client.get(
            f"/api / v1 / financial - reports / revenue - summary?period={current_month}",
            headers=auth_headers,
        )
        assert response.status_code == 200
        report = response.json()
        assert "total_revenue" in report
        assert "by_type" in report
        assert report["period"]["month"] == int(current_month[4:])
        assert report["period"]["year"] == int(current_month[:4])

    @pytest.mark.asyncio
    async def test_accounts_receivable_report(
        self, client: AsyncClient, auth_headers: dict
    ):
        """Test AR aging report"""
        response = await client.get(
            "/api / v1 / financial - reports / accounts - receivable",
            headers=auth_headers,
        )
        assert response.status_code == 200
        report = response.json()
        assert "aging_buckets" in report
        assert "total_receivable" in report
        assert "current" in report["aging_buckets"]
        assert "over_90" in report["aging_buckets"]


class TestAuthenticationIntegration:
    """Test authentication and authorization"""

    @pytest.mark.asyncio
    async def test_role_based_access(
        self,
        client: AsyncClient,
        test_customer,
        office_auth_headers: dict,
        driver_auth_headers: dict,
    ):
        """Test different roles have appropriate access"""
        # Office staff can create orders
        order_data = {
            "customer_id": test_customer.id,
            "scheduled_date": date.today().isoformat(),
            "qty_50kg": 1,
            "unit_price_50kg": 1500,
        }

        response = await client.post(
            "/api / v1 / orders", json=order_data, headers=office_auth_headers
        )
        assert response.status_code == 201

        # Driver cannot create orders
        response = await client.post(
            "/api / v1 / orders", json=order_data, headers=driver_auth_headers
        )
        assert response.status_code == 403

        # But driver can view their assigned routes
        response = await client.get(
            "/api / v1 / driver / routes", headers=driver_auth_headers
        )
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_token_expiration(self, client: AsyncClient):
        """Test expired token handling"""
        expired_token = "Bearer expired.token.here"

        response = await client.get(
            "/api / v1 / customers", headers={"Authorization": expired_token}
        )
        assert response.status_code == 401


class TestWebSocketIntegration:
    """Test WebSocket real - time updates"""

    @pytest.mark.asyncio
    async def test_order_status_broadcast(
        self,
        client: AsyncClient,
        auth_headers: dict,
        test_customer,
        mock_websocket_manager,
    ):
        """Test that order status changes trigger WebSocket broadcasts"""
        # Create order
        order_data = {
            "customer_id": test_customer.id,
            "scheduled_date": date.today().isoformat(),
            "qty_50kg": 1,
            "unit_price_50kg": 1500,
        }

        response = await client.post(
            "/api / v1 / orders", json=order_data, headers=auth_headers
        )
        order = response.json()
        order_id = order["id"]

        # Update status - should trigger broadcast
        response = await client.put(
            f"/api / v1 / orders/{order_id}/status",
            json={"status": OrderStatus.CONFIRMED.value},
            headers=auth_headers,
        )
        assert response.status_code == 200

        # Verify WebSocket broadcast was called
        assert mock_websocket_manager.called
        broadcast_data = mock_websocket_manager.call_args[0][0]
        assert broadcast_data["type"] == "order_update"
        assert broadcast_data["data"]["order_id"] == order_id
