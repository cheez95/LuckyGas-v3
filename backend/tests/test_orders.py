"""
Tests for order endpoints
"""

from datetime import datetime, timedelta

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.customer import Customer
from app.models.gas_product import DeliveryMethod, GasProduct, ProductAttribute
from app.models.order import Order, OrderStatus, PaymentStatus
from app.models.order_item import OrderItem


class TestOrders:
    """Test order endpoints"""

    @pytest.mark.asyncio
    async def test_create_order(
        self,
        client: AsyncClient,
        auth_headers: dict,
        db_session: AsyncSession,
        sample_order_data: dict,
    ):
        """Test creating a new order"""
        # Create customer first
        customer = Customer(
            customer_code="C001",
            short_name="測試客戶",
            invoice_title="測試公司",
            address="台北市信義區測試路123號",
            area="信義區",
        )
        db_session.add(customer)
        await db_session.commit()
        await db_session.refresh(customer)

        sample_order_data["customer_id"] = customer.id

        response = await client.post(
            "/api/v1/orders/", json=sample_order_data, headers=auth_headers
        )
        if response.status_code != 200:
            print(f"Response status: {response.status_code}")
            print(f"Response body: {response.json()}")
        assert response.status_code == 200
        data = response.json()
        # Handle both English field names and Chinese aliases
        customer_id = data.get("customer_id") or data.get("客戶編號")
        qty_50kg = data.get("qty_50kg") or data.get("50公斤數量")
        qty_20kg = data.get("qty_20kg") or data.get("20公斤數量")
        qty_4kg = data.get("qty_4kg") or data.get("4公斤數量")
        order_number = data.get("order_number") or data.get("訂單號碼")
        total_amount = data.get("total_amount") or data.get("總金額")
        status = data.get("status") or data.get("訂單狀態")

        assert customer_id == customer.id
        assert qty_50kg == sample_order_data["qty_50kg"]
        assert qty_20kg == sample_order_data["qty_20kg"]
        assert qty_4kg == sample_order_data["qty_4kg"]
        assert order_number.startswith("ORD-")
        assert total_amount > 0
        assert status == OrderStatus.PENDING.value

    @pytest.mark.asyncio
    async def test_create_order_nonexistent_customer(
        self, client: AsyncClient, auth_headers: dict, sample_order_data: dict
    ):
        """Test creating order with non-existent customer"""
        sample_order_data["customer_id"] = 99999

        response = await client.post(
            "/api/v1/orders/", json=sample_order_data, headers=auth_headers
        )
        assert response.status_code == 404
        assert "客戶不存在" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_list_orders(
        self, client: AsyncClient, auth_headers: dict, db_session: AsyncSession
    ):
        """Test listing orders with filters"""
        # Create customer
        customer = Customer(
            customer_code="C001",
            short_name="測試客戶",
            invoice_title="測試公司",
            address="台北市信義區測試路123號",
            area="信義區",
        )
        db_session.add(customer)
        await db_session.flush()

        # Create multiple orders
        today = datetime.now().date()
        orders = []
        for i in range(5):
            order = Order(
                order_number=f"ORD-TEST-{i:03d}",
                customer_id=customer.id,
                scheduled_date=today + timedelta(days=i),
                status=OrderStatus.PENDING if i % 2 == 0 else OrderStatus.CONFIRMED,
                is_urgent=i == 0,
                qty_50kg=i,
                qty_20kg=i + 1,
                total_amount=(i * 2500) + ((i + 1) * 1200),
                final_amount=(i * 2500) + ((i + 1) * 1200),
            )
            orders.append(order)

        db_session.add_all(orders)
        await db_session.commit()

        # Test listing all orders
        response = await client.get("/api/v1/orders/", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert len(data) >= 5

        # Test with status filter
        response = await client.get(
            "/api/v1/orders/",
            params={"status": OrderStatus.PENDING.value},
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        # Handle both English and Chinese field names
        for order in data:
            status = order.get("status") or order.get("訂單狀態")
            assert status == OrderStatus.PENDING.value

        # Test with urgent filter
        response = await client.get(
            "/api/v1/orders/", params={"is_urgent": True}, headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        # Handle both English and Chinese field names
        for order in data:
            is_urgent = order.get("is_urgent") or order.get("緊急訂單")
            assert is_urgent is True

        # Test with date range
        response = await client.get(
            "/api/v1/orders/",
            params={
                "date_from": today.isoformat(),
                "date_to": (today + timedelta(days=2)).isoformat(),
            },
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data) >= 3

    @pytest.mark.asyncio
    async def test_get_order(
        self, client: AsyncClient, auth_headers: dict, db_session: AsyncSession
    ):
        """Test getting a specific order"""
        # Create customer and order
        customer = Customer(
            customer_code="C001",
            short_name="測試客戶",
            invoice_title="測試公司",
            address="台北市信義區測試路123號",
            area="信義區",
        )
        db_session.add(customer)
        await db_session.flush()

        order = Order(
            order_number="ORD-TEST-001",
            customer_id=customer.id,
            scheduled_date=datetime.now().date(),
            status=OrderStatus.PENDING,
            qty_50kg=2,
            qty_20kg=1,
            total_amount=6200,
            final_amount=6200,
        )
        db_session.add(order)
        await db_session.commit()
        await db_session.refresh(order)

        response = await client.get(f"/api/v1/orders/{order.id}", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == order.id
        assert data["order_number"] == order.order_number
        assert data["qty_50kg"] == 2
        assert data["qty_20kg"] == 1

    @pytest.mark.asyncio
    async def test_update_order(
        self, client: AsyncClient, auth_headers: dict, db_session: AsyncSession
    ):
        """Test updating an order"""
        # Create customer and order
        customer = Customer(
            customer_code="C001",
            short_name="測試客戶",
            invoice_title="測試公司",
            address="台北市信義區測試路123號",
            area="信義區",
        )
        db_session.add(customer)
        await db_session.flush()

        order = Order(
            order_number="ORD-TEST-001",
            customer_id=customer.id,
            scheduled_date=datetime.now().date(),
            status=OrderStatus.PENDING,
            qty_50kg=2,
            qty_20kg=1,
            total_amount=6200,
            final_amount=6200,
        )
        db_session.add(order)
        await db_session.commit()
        await db_session.refresh(order)

        update_data = {
            "qty_50kg": 3,
            "qty_20kg": 2,
            "is_urgent": True,
            "delivery_notes": "請提早送達",
        }

        response = await client.put(
            f"/api/v1/orders/{order.id}", json=update_data, headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["qty_50kg"] == 3
        assert data["qty_20kg"] == 2
        assert data["is_urgent"] is True
        assert data["delivery_notes"] == "請提早送達"
        # Check that amounts are recalculated
        assert data["total_amount"] == (3 * 2500) + (2 * 1200)

    @pytest.mark.asyncio
    async def test_update_completed_order(
        self, client: AsyncClient, auth_headers: dict, db_session: AsyncSession
    ):
        """Test updating a completed order (should fail)"""
        # Create customer and completed order
        customer = Customer(
            customer_code="C001",
            short_name="測試客戶",
            invoice_title="測試公司",
            address="台北市信義區測試路123號",
            area="信義區",
        )
        db_session.add(customer)
        await db_session.flush()

        order = Order(
            order_number="ORD-TEST-001",
            customer_id=customer.id,
            scheduled_date=datetime.now().date(),
            status=OrderStatus.DELIVERED,
            qty_50kg=2,
            qty_20kg=1,
            total_amount=6200,
            final_amount=6200,
        )
        db_session.add(order)
        await db_session.commit()
        await db_session.refresh(order)

        update_data = {"qty_50kg": 3}

        response = await client.put(
            f"/api/v1/orders/{order.id}", json=update_data, headers=auth_headers
        )
        assert response.status_code == 400
        assert "已完成或已取消的訂單無法修改" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_cancel_order(
        self, client: AsyncClient, auth_headers: dict, db_session: AsyncSession
    ):
        """Test cancelling an order"""
        # Create customer and order
        customer = Customer(
            customer_code="C001",
            short_name="測試客戶",
            invoice_title="測試公司",
            address="台北市信義區測試路123號",
            area="信義區",
        )
        db_session.add(customer)
        await db_session.flush()

        order = Order(
            order_number="ORD-TEST-001",
            customer_id=customer.id,
            scheduled_date=datetime.now().date(),
            status=OrderStatus.PENDING,
            qty_50kg=2,
            qty_20kg=1,
            total_amount=6200,
            final_amount=6200,
        )
        db_session.add(order)
        await db_session.commit()
        await db_session.refresh(order)

        response = await client.delete(
            f"/api/v1/orders/{order.id}",
            params={"reason": "客戶要求取消"},
            headers=auth_headers,
        )
        assert response.status_code == 200
        assert "訂單已成功取消" in response.json()["message"]

        # Verify order is cancelled
        await db_session.refresh(order)
        assert order.status == OrderStatus.CANCELLED
        assert "客戶要求取消" in order.delivery_notes

    @pytest.mark.asyncio
    async def test_order_stats(
        self, client: AsyncClient, auth_headers: dict, db_session: AsyncSession
    ):
        """Test order statistics endpoint"""
        # Create customer
        customer = Customer(
            customer_code="C001",
            short_name="測試客戶",
            invoice_title="測試公司",
            address="台北市信義區測試路123號",
            area="信義區",
        )
        db_session.add(customer)
        await db_session.flush()

        # Create orders with different statuses
        today = datetime.now()
        orders = [
            Order(
                order_number="ORD-TEST-001",
                customer_id=customer.id,
                scheduled_date=today.date(),
                status=OrderStatus.DELIVERED,
                qty_50kg=2,
                final_amount=5000,
                created_at=today - timedelta(days=5),
            ),
            Order(
                order_number="ORD-TEST-002",
                customer_id=customer.id,
                scheduled_date=today.date(),
                status=OrderStatus.DELIVERED,
                qty_20kg=3,
                final_amount=3600,
                created_at=today - timedelta(days=3),
            ),
            Order(
                order_number="ORD-TEST-003",
                customer_id=customer.id,
                scheduled_date=today.date(),
                status=OrderStatus.PENDING,
                qty_10kg=2,
                is_urgent=True,
                final_amount=1400,
                created_at=today - timedelta(days=1),
            ),
        ]
        db_session.add_all(orders)
        await db_session.commit()

        # Get stats for last 30 days
        response = await client.get(
            "/api/v1/orders/stats/summary", headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()

        assert data["status_summary"]["delivered"] == 2
        assert data["status_summary"]["pending"] == 1
        assert data["total_revenue"] == 8600  # Only delivered orders
        assert data["urgent_orders"] == 1
        assert data["unique_customers"] == 1
        assert data["total_orders"] == 3


class TestOrdersV2:
    """Test flexible product system order endpoints"""

    @pytest.mark.asyncio
    async def test_create_order_v2(
        self, client: AsyncClient, auth_headers: dict, db_session: AsyncSession
    ):
        """Test creating order with flexible product system"""
        # Create customer
        customer = Customer(
            customer_code="C001",
            short_name="測試客戶",
            invoice_title="測試公司",
            address="台北市信義區測試路123號",
            area="信義區",
        )
        db_session.add(customer)

        # Create gas products
        product_50kg = GasProduct(
            delivery_method=DeliveryMethod.CYLINDER,
            size_kg=50,
            attribute=ProductAttribute.REGULAR,
            sku="CYL-50-REG",
            name_zh="50公斤桶裝瓦斯",
            unit_price=2500,
            is_available=True,
        )
        product_20kg = GasProduct(
            delivery_method=DeliveryMethod.CYLINDER,
            size_kg=20,
            attribute=ProductAttribute.REGULAR,
            sku="CYL-20-REG",
            name_zh="20公斤桶裝瓦斯",
            unit_price=1200,
            is_available=True,
        )
        db_session.add(product_50kg)
        db_session.add(product_20kg)
        await db_session.commit()
        await db_session.refresh(customer)
        await db_session.refresh(product_50kg)
        await db_session.refresh(product_20kg)

        # Use a future date
        from datetime import datetime, timedelta

        future_date = (datetime.now() + timedelta(days=7)).strftime("%Y-%m-%d")

        order_data = {
            "customer_id": customer.id,
            "scheduled_date": future_date,
            "order_items": [
                {
                    "gas_product_id": product_50kg.id,
                    "quantity": 2,
                    "unit_price": product_50kg.unit_price,
                    "is_exchange": True,
                    "empty_received": 2,
                },
                {
                    "gas_product_id": product_20kg.id,
                    "quantity": 3,
                    "unit_price": product_20kg.unit_price,
                    "discount_percentage": 10,
                },
            ],
            "delivery_notes": "請於下午送達",
            "is_urgent": False,
        }

        response = await client.post(
            "/api/v1/orders/v2/", json=order_data, headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()

        assert data["customer_id"] == customer.id
        assert len(data["order_items"]) == 2
        assert data["total_amount"] == (2 * 2500) + (3 * 1200)
        # Check discount on second item
        assert data["discount_amount"] == 360  # 10% of 3600
        assert data["final_amount"] == data["total_amount"] - data["discount_amount"]
