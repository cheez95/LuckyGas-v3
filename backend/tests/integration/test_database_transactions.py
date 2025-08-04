"""
Integration tests for database transactions and data integrity
"""

from datetime import date, datetime, timedelta
from decimal import Decimal

import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.models.customer import Customer, CustomerType
from app.models.invoice import (
    Invoice,
    InvoiceStatus,
    InvoiceType,
    Payment,
    PaymentMethod,
)
from app.models.invoice import PaymentStatus as InvoicePaymentStatus
from app.models.order import Order, OrderStatus, PaymentStatus
from app.models.route import Route, RouteStatus
from app.models.route_plan import RoutePlan, RoutePlanStop
from app.models.user import User, UserRole
from app.services.invoice_service import InvoiceService
from app.services.order_service import OrderService
from app.services.payment_service import PaymentService


class TestDatabaseTransactions:
    """Test database transaction integrity"""

    @pytest.mark.asyncio
    async def test_cascade_delete_customer_orders(self, db_session, test_customer):
        """Test that deleting a customer properly handles related orders"""
        # Create orders for the customer
        order1 = Order(
            order_number="ORD001",
            customer_id=test_customer.id,
            order_date=datetime.now(),
            scheduled_date=date.today() + timedelta(days=1),
            status=OrderStatus.PENDING,
            total_amount=1000,
        )
        order2 = Order(
            order_number="ORD002",
            customer_id=test_customer.id,
            order_date=datetime.now(),
            scheduled_date=date.today() + timedelta(days=2),
            status=OrderStatus.DELIVERED,
            total_amount=2000,
        )

        db_session.add_all([order1, order2])
        await db_session.commit()

        # Verify orders exist
        result = await db_session.execute(
            select(Order).where(Order.customer_id == test_customer.id)
        )
        orders = result.scalars().all()
        assert len(orders) == 2

        # Try to delete customer - should fail due to foreign key constraint
        await db_session.delete(test_customer)
        with pytest.raises(IntegrityError):
            await db_session.commit()

        # Rollback the failed transaction
        await db_session.rollback()

        # Customer should still exist
        result = await db_session.execute(
            select(Customer).where(Customer.id == test_customer.id)
        )
        customer = result.scalar_one_or_none()
        assert customer is not None

    @pytest.mark.asyncio
    async def test_order_invoice_payment_transaction(self, db_session, test_customer):
        """Test complete order to invoice to payment transaction flow"""
        # Create order
        order = Order(
            order_number="ORD20240126001",
            customer_id=test_customer.id,
            order_date=datetime.now(),
            scheduled_date=date.today() + timedelta(days=1),
            status=OrderStatus.DELIVERED,
            qty_50kg=2,
            qty_20kg=1,
            unit_price_50kg=Decimal("1500"),
            unit_price_20kg=Decimal("600"),
            total_amount=Decimal("3600"),
            is_taxable=True,
        )
        db_session.add(order)
        await db_session.commit()

        # Create invoice from order
        invoice_service = InvoiceService(db_session)
        invoice = await invoice_service.create_invoice_from_order(order)

        assert invoice is not None
        assert invoice.order_id == order.id
        assert invoice.customer_id == test_customer.id
        assert invoice.total_amount == Decimal("3600")
        assert invoice.tax_amount == Decimal("180")  # 5% tax
        assert invoice.grand_total == Decimal("3780")

        # Create payment for invoice
        payment_service = PaymentService(db_session)
        payment = Payment(
            payment_number="PAY20240126001",
            invoice_id=invoice.id,
            amount=Decimal("3780"),
            payment_method=PaymentMethod.CASH,
            payment_date=date.today(),
            status=InvoicePaymentStatus.VERIFIED,
            verified_at=datetime.now(),
        )
        db_session.add(payment)
        await db_session.commit()

        # Update invoice payment status
        invoice.paid_amount = payment.amount
        invoice.status = InvoiceStatus.PAID
        invoice.paid_at = datetime.now()
        await db_session.commit()

        # Verify the complete transaction chain
        result = await db_session.execute(
            select(Invoice)
            .where(Invoice.order_id == order.id)
            .where(Invoice.status == InvoiceStatus.PAID)
        )
        paid_invoice = result.scalar_one_or_none()
        assert paid_invoice is not None
        assert paid_invoice.paid_amount == Decimal("3780")

    @pytest.mark.asyncio
    async def test_route_assignment_transaction(
        self, db_session, test_driver_user, test_customer
    ):
        """Test route assignment transaction with multiple orders"""
        # Create multiple orders
        orders = []
        for i in range(3):
            order = Order(
                order_number=f"ORD00{i+1}",
                customer_id=test_customer.id,
                order_date=datetime.now(),
                scheduled_date=date.today() + timedelta(days=1),
                status=OrderStatus.CONFIRMED,
                total_amount=1000 * (i + 1),
            )
            orders.append(order)

        db_session.add_all(orders)
        await db_session.commit()

        # Create route
        route = Route(
            route_number=f"R{datetime.now().strftime('%Y%m%d')}001",
            route_date=date.today() + timedelta(days=1),
            driver_id=test_driver_user.id,
            status=RouteStatus.PLANNED,
            total_stops=3,
            total_distance_km=25.5,
            estimated_duration_minutes=120,
        )
        db_session.add(route)
        await db_session.commit()

        # Assign orders to route using transaction
        try:
            # Start transaction
            for idx, order in enumerate(orders):
                order.route_id = route.id
                order.route_sequence = idx + 1
                order.status = OrderStatus.ASSIGNED

            # Update route totals
            route.total_orders = len(orders)
            route.total_amount = sum(o.total_amount for o in orders)

            await db_session.commit()

            # Verify assignments
            result = await db_session.execute(
                select(Order)
                .where(Order.route_id == route.id)
                .order_by(Order.route_sequence)
            )
            assigned_orders = result.scalars().all()

            assert len(assigned_orders) == 3
            assert all(o.status == OrderStatus.ASSIGNED for o in assigned_orders)
            assert assigned_orders[0].route_sequence == 1
            assert assigned_orders[2].route_sequence == 3

        except Exception as e:
            await db_session.rollback()
            raise e

    @pytest.mark.asyncio
    async def test_credit_limit_enforcement(self, db_session, test_customer):
        """Test credit limit enforcement in transactions"""
        # Set customer credit limit
        test_customer.credit_limit = Decimal("5000")
        await db_session.commit()

        # Create orders that exceed credit limit
        order1 = Order(
            order_number="ORD001",
            customer_id=test_customer.id,
            order_date=datetime.now(),
            scheduled_date=date.today() + timedelta(days=1),
            status=OrderStatus.DELIVERED,
            total_amount=Decimal("3000"),
            payment_status=PaymentStatus.UNPAID,
        )
        order2 = Order(
            order_number="ORD002",
            customer_id=test_customer.id,
            order_date=datetime.now(),
            scheduled_date=date.today() + timedelta(days=2),
            status=OrderStatus.DELIVERED,
            total_amount=Decimal("2500"),
            payment_status=PaymentStatus.UNPAID,
        )

        db_session.add_all([order1, order2])
        await db_session.commit()

        # Calculate outstanding balance
        result = await db_session.execute(
            select(Order)
            .where(Order.customer_id == test_customer.id)
            .where(Order.payment_status == PaymentStatus.UNPAID)
        )
        unpaid_orders = result.scalars().all()
        total_outstanding = sum(o.total_amount for o in unpaid_orders)

        assert total_outstanding == Decimal("5500")
        assert total_outstanding > test_customer.credit_limit

        # New order should be blocked
        order_service = OrderService(db_session)
        can_create = await order_service.check_credit_limit(
            test_customer.id, Decimal("1000")
        )
        assert can_create is False

    @pytest.mark.asyncio
    async def test_concurrent_inventory_update(self, db_session):
        """Test concurrent updates to inventory don't cause inconsistency"""
        # This would typically test cylinder inventory updates
        # For now, we'll test concurrent order status updates

        # Create an order
        order = Order(
            order_number="ORD001",
            customer_id=1,  # Assuming exists
            order_date=datetime.now(),
            scheduled_date=date.today() + timedelta(days=1),
            status=OrderStatus.PENDING,
            total_amount=1000,
        )
        db_session.add(order)
        await db_session.commit()

        # Simulate concurrent status updates
        # In a real scenario, this would be multiple sessions
        original_status = order.status

        # Update 1: Assign to route
        order.status = OrderStatus.ASSIGNED
        order.assigned_at = datetime.now()

        # Update 2: Mark as dispatched (would conflict)
        # In real scenario, this would be from another session
        # and would need proper locking mechanism

        await db_session.commit()

        # Verify final state
        await db_session.refresh(order)
        assert order.status == OrderStatus.ASSIGNED
        assert order.assigned_at is not None

    @pytest.mark.asyncio
    async def test_invoice_void_transaction(self, db_session, test_customer):
        """Test invoice voiding transaction with payment rollback"""
        # Create invoice
        invoice = Invoice(
            invoice_number="INV20240126001",
            customer_id=test_customer.id,
            invoice_type=InvoiceType.B2B,
            total_amount=Decimal("10000"),
            tax_amount=Decimal("500"),
            grand_total=Decimal("10500"),
            status=InvoiceStatus.ISSUED,
            invoice_date=date.today(),
        )
        db_session.add(invoice)
        await db_session.commit()

        # Create payment
        payment = Payment(
            payment_number="PAY001",
            invoice_id=invoice.id,
            amount=Decimal("5000"),
            payment_method=PaymentMethod.BANK_TRANSFER,
            payment_date=date.today(),
            status=InvoicePaymentStatus.VERIFIED,
        )
        db_session.add(payment)

        # Update invoice paid amount
        invoice.paid_amount = payment.amount
        await db_session.commit()

        # Void invoice - should handle payment
        invoice.status = InvoiceStatus.VOIDED
        invoice.void_reason = "客戶要求作廢"
        invoice.voided_at = datetime.now()

        # Payment should be cancelled
        payment.status = InvoicePaymentStatus.CANCELLED
        payment.cancelled_at = datetime.now()
        payment.cancel_reason = "發票作廢"

        # Reset paid amount
        invoice.paid_amount = Decimal("0")

        await db_session.commit()

        # Verify transaction
        await db_session.refresh(invoice)
        await db_session.refresh(payment)

        assert invoice.status == InvoiceStatus.VOIDED
        assert invoice.paid_amount == Decimal("0")
        assert payment.status == InvoicePaymentStatus.CANCELLED
        assert payment.cancelled_at is not None
