"""
Integration tests for financial modules
Tests invoice generation, payment processing, and financial reporting
"""

from datetime import date, datetime, timedelta
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import get_password_hash
from app.models.customer import Customer, CustomerType
from app.models.gas_product import GasProduct
from app.models.invoice import (
    Invoice,
    InvoicePaymentStatus,
    InvoiceStatus,
    InvoiceType,
    PaymentMethod,
)
from app.models.order import Order, OrderStatus, PaymentStatus
from app.models.user import User, UserRole


class TestFinancialIntegration:
    """Test financial operations with integrated components"""

    @pytest_asyncio.fixture
    async def financial_test_data(self, db_session: AsyncSession):
        """Create test data for financial operations"""
        # Create admin user
        admin = User(
            email="admin@test.com",
            hashed_password=get_password_hash("password"),
            full_name="Admin",
            role=UserRole.SUPER_ADMIN,
            is_active=True,
        )

        # Create office staff
        office = User(
            email="office@test.com",
            hashed_password=get_password_hash("password"),
            full_name="Office Staff",
            role=UserRole.OFFICE_STAFF,
            is_active=True,
        )

        db_session.add_all([admin, office])
        await db_session.commit()

        # Create gas products with prices
        products = [
            GasProduct(
                product_code="50KG",
                name="50公斤鋼瓶",
                size_kg=50,
                unit_price=1200.0,
                is_active=True,
            ),
            GasProduct(
                product_code="20KG",
                name="20公斤鋼瓶",
                size_kg=20,
                unit_price=600.0,
                is_active=True,
            ),
            GasProduct(
                product_code="16KG",
                name="16公斤鋼瓶",
                size_kg=16,
                unit_price=500.0,
                is_active=True,
            ),
        ]

        db_session.add_all(products)
        await db_session.commit()

        # Create customers with different payment terms
        customers = [
            Customer(
                customer_code="CASH001",
                name="現金客戶",
                customer_type=CustomerType.RESIDENTIAL,
                phone="0912345678",
                address="台北市大安區現金路1號",
                area="大安區",
                payment_terms="cash",
                credit_limit=0,
                current_balance=0,
            ),
            Customer(
                customer_code="CREDIT001",
                name="月結客戶",
                customer_type=CustomerType.BUSINESS,
                phone="0223456789",
                address="台北市信義區月結路100號",
                area="信義區",
                business_tax_id="12345678",
                payment_terms="monthly",
                credit_limit=100000,
                current_balance=25000,
            ),
            Customer(
                customer_code="OVERDUE001",
                name="逾期客戶",
                customer_type=CustomerType.BUSINESS,
                phone="0234567890",
                address="台北市中山區逾期路50號",
                area="中山區",
                business_tax_id="87654321",
                payment_terms="monthly",
                credit_limit=50000,
                current_balance=55000,  # Over credit limit
                overdue_amount=30000,
            ),
        ]

        db_session.add_all(customers)
        await db_session.commit()

        return {
            "admin": admin,
            "office": office,
            "products": products,
            "customers": customers,
        }

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_order_to_invoice_workflow(
        self, client: AsyncClient, financial_test_data, db_session: AsyncSession
    ):
        """Test complete workflow from order creation to invoice generation"""
        data = financial_test_data

        # Login as office staff
        response = await client.post(
            "/api/v1/auth/login",
            data={"username": "office@test.com", "password": "password"},
        )
        token = response.json()["access_token"]
        client.headers["Authorization"] = f"Bearer {token}"

        # Create a delivered order
        customer = data["customers"][1]  # Monthly payment customer
        order_data = {
            "customer_id": customer.id,
            "scheduled_date": date.today().isoformat(),
            "delivery_time_start": "09:00",
            "delivery_time_end": "12:00",
            "qty_50kg": 2,
            "qty_20kg": 3,
            "delivery_address": customer.address,
            "delivery_notes": "月結客戶訂單",
        }

        response = await client.post("/api/v1/orders", json=order_data)
        assert response.status_code == 200
        order = response.json()

        # Calculate expected total
        expected_total = (2 * 1200.0) + (3 * 600.0)  # 2*50kg + 3*20kg
        assert order["total_amount"] == expected_total

        # Mark order as delivered
        order_update = {"status": OrderStatus.DELIVERED.value}
        response = await client.put(f"/api/v1/orders/{order['id']}", json=order_update)
        assert response.status_code == 200

        # Generate invoice
        invoice_data = {
            "order_id": order["id"],
            "invoice_type": InvoiceType.B2B.value,
            "buyer_tax_id": customer.business_tax_id,
        }

        response = await client.post("/api/v1/invoices", json=invoice_data)
        assert response.status_code == 200
        invoice = response.json()

        # Verify invoice details
        assert invoice["sales_amount"] == expected_total
        assert invoice["tax_amount"] == expected_total * 0.05  # 5% tax
        assert invoice["total_amount"] == expected_total * 1.05
        assert invoice["buyer_tax_id"] == customer.business_tax_id
        assert invoice["status"] == InvoiceStatus.ISSUED.value

        # Verify Taiwan invoice format
        assert len(invoice["invoice_track"]) == 2  # e.g., "AB"
        assert len(invoice["invoice_no"]) == 8  # e.g., "12345678"
        assert invoice["qr_code_left"] is not None
        assert invoice["qr_code_right"] is not None

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_payment_processing_workflow(
        self, client: AsyncClient, financial_test_data, db_session: AsyncSession
    ):
        """Test payment recording and customer balance updates"""
        data = financial_test_data

        # Login as admin
        response = await client.post(
            "/api/v1/auth/login",
            data={"username": "admin@test.com", "password": "password"},
        )
        token = response.json()["access_token"]
        client.headers["Authorization"] = f"Bearer {token}"

        # Create and deliver an order for credit customer
        customer = data["customers"][1]
        order = Order(
            customer_id=customer.id,
            order_number=f"ORD{datetime.now().strftime('%Y%m%d%H%M%S')}",
            scheduled_date=date.today(),
            qty_50kg=1,
            qty_20kg=2,
            total_amount=2400.0,  # 1*1200 + 2*600
            final_amount=2400.0,
            status=OrderStatus.DELIVERED,
            payment_status=PaymentStatus.UNPAID,
        )
        db_session.add(order)
        await db_session.commit()

        # Create invoice
        invoice = Invoice(
            invoice_number="AB12345678",
            invoice_track="AB",
            invoice_no="12345678",
            customer_id=customer.id,
            order_id=order.id,
            invoice_type=InvoiceType.B2B,
            invoice_date=date.today(),
            period=date.today().strftime("%Y%m"),
            buyer_tax_id=customer.business_tax_id,
            buyer_name=customer.name,
            sales_amount=2400.0,
            tax_amount=120.0,
            total_amount=2520.0,
            status=InvoiceStatus.ISSUED,
            payment_status=InvoicePaymentStatus.PENDING,
        )
        db_session.add(invoice)
        await db_session.commit()

        # Record payment
        payment_data = {
            "invoice_id": invoice.id,
            "payment_date": date.today().isoformat(),
            "payment_method": PaymentMethod.TRANSFER.value,
            "amount": 2520.0,
            "reference_number": "TRF20240120001",
            "bank_account": "123-456789-0",
        }

        response = await client.post("/api/v1/payments", json=payment_data)
        assert response.status_code == 200
        payment = response.json()

        # Verify payment recorded
        assert payment["amount"] == 2520.0
        assert payment["payment_method"] == PaymentMethod.TRANSFER.value

        # Verify invoice payment status updated
        response = await client.get(f"/api/v1/invoices/{invoice.id}")
        updated_invoice = response.json()
        assert updated_invoice["payment_status"] == InvoicePaymentStatus.PAID.value
        assert updated_invoice["paid_amount"] == 2520.0

        # Verify customer balance updated
        response = await client.get(f"/api/v1/customers/{customer.id}")
        updated_customer = response.json()
        assert (
            updated_customer["current_balance"] == 25000 - 2520
        )  # Original balance - payment

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_credit_limit_enforcement(
        self, client: AsyncClient, financial_test_data, db_session: AsyncSession
    ):
        """Test credit limit checking during order creation"""
        data = financial_test_data

        # Login as office staff
        response = await client.post(
            "/api/v1/auth/login",
            data={"username": "office@test.com", "password": "password"},
        )
        token = response.json()["access_token"]
        client.headers["Authorization"] = f"Bearer {token}"

        # Try to create order for overdue customer
        overdue_customer = data["customers"][2]
        order_data = {
            "customer_id": overdue_customer.id,
            "scheduled_date": date.today().isoformat(),
            "delivery_time_start": "09:00",
            "delivery_time_end": "12:00",
            "qty_50kg": 10,  # Large order
            "delivery_address": overdue_customer.address,
        }

        # Should fail due to credit limit
        response = await client.post("/api/v1/orders", json=order_data)
        assert response.status_code == 400
        assert "credit limit" in response.json()["detail"].lower()

        # Login as admin (can override credit limit)
        response = await client.post(
            "/api/v1/auth/login",
            data={"username": "admin@test.com", "password": "password"},
        )
        admin_token = response.json()["access_token"]
        client.headers["Authorization"] = f"Bearer {admin_token}"

        # Admin should be able to create order with override
        order_data["override_credit_limit"] = True
        response = await client.post("/api/v1/orders", json=order_data)
        assert response.status_code == 200

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_financial_reporting(
        self, client: AsyncClient, financial_test_data, db_session: AsyncSession
    ):
        """Test financial reporting functionality"""
        data = financial_test_data

        # Create historical data
        for i in range(10):
            order = Order(
                customer_id=data["customers"][i % 3].id,
                order_number=f"HIST{i:04d}",
                scheduled_date=date.today() - timedelta(days=i),
                qty_20kg=2,
                total_amount=1200.0,
                final_amount=1200.0,
                status=OrderStatus.DELIVERED,
                payment_status=PaymentStatus.PAID,
                delivered_at=datetime.now() - timedelta(days=i),
            )
            db_session.add(order)

        await db_session.commit()

        # Login as admin
        response = await client.post(
            "/api/v1/auth/login",
            data={"username": "admin@test.com", "password": "password"},
        )
        token = response.json()["access_token"]
        client.headers["Authorization"] = f"Bearer {token}"

        # Get revenue summary
        response = await client.get(
            "/api/v1/financial-reports/revenue-summary",
            params={
                "start_date": (date.today() - timedelta(days=30)).isoformat(),
                "end_date": date.today().isoformat(),
            },
        )
        assert response.status_code == 200
        revenue_report = response.json()

        assert revenue_report["total_revenue"] == 12000.0  # 10 orders * 1200
        assert len(revenue_report["daily_revenue"]) > 0
        assert revenue_report["order_count"] == 10

        # Get accounts receivable aging
        response = await client.get("/api/v1/financial-reports/ar-aging")
        assert response.status_code == 200
        ar_report = response.json()

        assert "current" in ar_report
        assert "overdue_30_days" in ar_report
        assert "overdue_60_days" in ar_report
        assert "overdue_90_days" in ar_report

        # Get customer statement
        customer = data["customers"][1]
        response = await client.get(
            f"/api/v1/financial-reports/customer-statement/{customer.id}",
            params={
                "start_date": (date.today() - timedelta(days=30)).isoformat(),
                "end_date": date.today().isoformat(),
            },
        )
        assert response.status_code == 200
        statement = response.json()

        assert statement["customer"]["id"] == customer.id
        assert "beginning_balance" in statement
        assert "ending_balance" in statement
        assert "transactions" in statement

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_einvoice_submission(
        self, client: AsyncClient, financial_test_data, db_session: AsyncSession
    ):
        """Test e-invoice submission to government API"""
        data = financial_test_data

        # Mock e-invoice API
        with patch(
            "app.services.einvoice_service.EInvoiceService.submit_invoice"
        ) as mock_submit:
            mock_submit.return_value = {
                "success": True,
                "invoice_id": "EINV2024012000001",
                "submission_time": datetime.now().isoformat(),
            }

            # Login and create invoice
            response = await client.post(
                "/api/v1/auth/login",
                data={"username": "admin@test.com", "password": "password"},
            )
            token = response.json()["access_token"]
            client.headers["Authorization"] = f"Bearer {token}"

            # Create invoice
            invoice = Invoice(
                invoice_number="CD12345678",
                invoice_track="CD",
                invoice_no="12345678",
                customer_id=data["customers"][1].id,
                invoice_type=InvoiceType.B2B,
                invoice_date=date.today(),
                period=date.today().strftime("%Y%m"),
                buyer_tax_id="12345678",
                buyer_name=data["customers"][1].name,
                sales_amount=1000.0,
                tax_amount=50.0,
                total_amount=1050.0,
                status=InvoiceStatus.ISSUED,
            )
            db_session.add(invoice)
            await db_session.commit()

            # Submit to government
            response = await client.post(
                f"/api/v1/invoices/{invoice.id}/submit-einvoice"
            )
            assert response.status_code == 200
            result = response.json()

            assert result["success"] is True
            assert result["einvoice_id"] is not None

            # Verify invoice updated
            await db_session.refresh(invoice)
            assert invoice.einvoice_id == "EINV2024012000001"
            assert invoice.submitted_at is not None
