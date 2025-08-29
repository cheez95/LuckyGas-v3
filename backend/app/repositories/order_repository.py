"""
Order repository for data access operations
Implements order - specific queries and operations
"""

import logging
from datetime import date, datetime, timedelta

from sqlalchemy import and_, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload, selectinload

from app.core.metrics import orders_created_counter
from app.models.customer import Customer
from app.models.order import Order, OrderStatus, PaymentStatus
from app.models.order_item import OrderItem
from app.repositories.base import BaseRepository

logger = logging.getLogger(__name__)


class OrderRepository(BaseRepository[Order]):
    """
    Repository for order data operations
    Handles complex order queries and bulk operations
    """

    def __init__(self, session: AsyncSession):
        super().__init__(Order, session)

    async def get_with_details(self, order_id: int) -> Optional[Order]:
        """
        Get order with all related data loaded

        Args:
            order_id: Order ID

        Returns:
            Order with customer, items, and route loaded
        """
        query = (
            select(Order)
            .where(Order.id == order_id)
            .options(
                joinedload(Order.customer),
                selectinload(Order.order_items).joinedload(OrderItem.gas_product),
            )
        )

        result = await self.session.execute(query)
        return result.unique().scalar_one_or_none()

    async def get_orders_by_date(
        self,
        scheduled_date: date,
        status: Optional[OrderStatus] = None,
        area: Optional[str] = None,
        skip: int = 0,
        limit: int = 100,
    ) -> Tuple[List[Order], int]:
        """
        Get orders for a specific date with filtering

        Args:
            scheduled_date: Date to filter by
            status: Optional status filter
            area: Optional area filter (via customer)
            skip: Pagination offset
            limit: Pagination limit

        Returns:
            Tuple of (orders list, total count)
        """
        # Base query with customer join for area filtering
        base_query = (
            select(Order)
            .join(Customer)
            .where(func.date(Order.scheduled_date) == scheduled_date)
            .options(joinedload(Order.customer))
        )

        count_query = (
            select(func.count())
            .select_from(Order)
            .join(Customer)
            .where(func.date(Order.scheduled_date) == scheduled_date)
        )

        # Apply filters
        if status:
            base_query = base_query.where(Order.status == status)
            count_query = count_query.where(Order.status == status)

        if area:
            base_query = base_query.where(Customer.area == area)
            count_query = count_query.where(Customer.area == area)

        # Get total count
        count_result = await self.session.execute(count_query)
        total = count_result.scalar() or 0

        # Apply pagination and ordering
        query = base_query.order_by(Order.created_at.desc()).offset(skip).limit(limit)

        result = await self.session.execute(query)
        orders = result.unique().scalars().all()

        return orders, total

    async def get_unassigned_orders(
        self, scheduled_date: date, area: Optional[str] = None
    ) -> List[Order]:
        """
        Get orders that haven't been assigned to routes

        Args:
            scheduled_date: Date to filter by
            area: Optional area filter

        Returns:
            List of unassigned orders
        """
        query = (
            select(Order)
            .join(Customer)
            .where(
                and_(
                    func.date(Order.scheduled_date) == scheduled_date,
                    Order.route_id.is_(None),
                    Order.status.in_([OrderStatus.PENDING, OrderStatus.CONFIRMED]),
                )
            )
            .options(joinedload(Order.customer))
        )

        if area:
            query = query.where(Customer.area == area)

        query = query.order_by(Order.is_urgent.desc(), Order.created_at)

        result = await self.session.execute(query)
        return result.unique().scalars().all()

    async def bulk_assign_to_route(
        self, order_ids: List[int], route_id: int, driver_id: Optional[int] = None
    ) -> int:
        """
        Bulk assign orders to a route

        Args:
            order_ids: List of order IDs
            route_id: Route ID to assign to
            driver_id: Optional driver ID

        Returns:
            Number of orders updated
        """
        if not order_ids:
            return 0

        stmt = (
            update(Order)
            .where(Order.id.in_(order_ids))
            .values(
                route_id=route_id,
                driver_id=driver_id,
                status=OrderStatus.ASSIGNED,
                updated_at=datetime.utcnow(),
            )
        )

        result = await self.session.execute(stmt)
        await self.session.commit()

        updated_count = result.rowcount
        logger.info(f"Assigned {updated_count} orders to route {route_id}")

        return updated_count

    async def update_delivery_status(
        self,
        order_id: int,
        status: OrderStatus,
        delivered_at: Optional[datetime] = None,
        delivery_notes: Optional[str] = None,
    ) -> Optional[Order]:
        """
        Update order delivery status

        Args:
            order_id: Order ID
            status: New status
            delivered_at: Delivery timestamp
            delivery_notes: Optional delivery notes

        Returns:
            Updated order or None
        """
        order = await self.get(order_id)
        if not order:
            return None

        order.status = status
        order.updated_at = datetime.utcnow()

        if delivered_at:
            order.delivered_at = delivered_at

        if delivery_notes:
            if order.delivery_notes:
                order.delivery_notes += f"\n{delivery_notes}"
            else:
                order.delivery_notes = delivery_notes

        # Update payment status if delivered and COD
        if status == OrderStatus.DELIVERED and order.payment_method == "現金":
            order.payment_status = PaymentStatus.PAID

        await self.session.commit()
        await self.session.refresh(order)

        return order

    async def get_customer_order_history(
        self, customer_id: int, days: int = 90, limit: int = 50
    ) -> List[Order]:
        """
        Get customer's order history

        Args:
            customer_id: Customer ID
            days: Number of days to look back
            limit: Maximum orders to return

        Returns:
            List of orders
        """
        cutoff_date = datetime.now() - timedelta(days=days)

        query = (
            select(Order)
            .where(
                and_(Order.customer_id == customer_id, Order.created_at >= cutoff_date)
            )
            .order_by(Order.created_at.desc())
            .limit(limit)
        )

        result = await self.session.execute(query)
        return result.scalars().all()

    async def get_order_statistics(
        self, start_date: date, end_date: date, area: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Get order statistics for a date range

        Args:
            start_date: Start date
            end_date: End date
            area: Optional area filter

        Returns:
            Dictionary with statistics
        """
        # Base query
        base_conditions = [
            func.date(Order.scheduled_date) >= start_date,
            func.date(Order.scheduled_date) <= end_date,
        ]

        if area:
            # Would need to join with Customer for area filter
            pass

        # Total orders
        total_query = (
            select(func.count()).select_from(Order).where(and_(*base_conditions))
        )
        total_result = await self.session.execute(total_query)
        total_orders = total_result.scalar() or 0

        # Orders by status
        status_query = (
            select(Order.status, func.count())
            .where(and_(*base_conditions))
            .group_by(Order.status)
        )
        status_result = await self.session.execute(status_query)
        status_counts = {status.value: count for status, count in status_result.all()}

        # Revenue calculation
        revenue_query = select(func.sum(Order.final_amount)).where(
            and_(*base_conditions, Order.status == OrderStatus.DELIVERED)
        )
        revenue_result = await self.session.execute(revenue_query)
        total_revenue = revenue_result.scalar() or 0.0

        # Average order value
        avg_value = total_revenue / total_orders if total_orders > 0 else 0.0

        return {
            "total_orders": total_orders,
            "status_breakdown": status_counts,
            "total_revenue": float(total_revenue),
            "average_order_value": float(avg_value),
            "delivery_rate": (
                status_counts.get("delivered", 0) / total_orders
                if total_orders > 0
                else 0
            ),
        }

    async def get_pending_payments(
        self, customer_id: Optional[int] = None, days_overdue: int = 0
    ) -> List[Order]:
        """
        Get orders with pending payments

        Args:
            customer_id: Optional customer filter
            days_overdue: Minimum days overdue

        Returns:
            List of orders with pending payments
        """
        cutoff_date = datetime.now() - timedelta(days=days_overdue)

        query = (
            select(Order)
            .where(
                and_(
                    Order.payment_status == PaymentStatus.UNPAID,
                    Order.status == OrderStatus.DELIVERED,
                    Order.delivered_at <= cutoff_date,
                )
            )
            .options(joinedload(Order.customer))
        )

        if customer_id:
            query = query.where(Order.customer_id == customer_id)

        query = query.order_by(Order.delivered_at)

        result = await self.session.execute(query)
        return result.unique().scalars().all()

    async def calculate_route_totals(self, route_id: int) -> Dict[str, Any]:
        """
        Calculate totals for all orders in a route

        Args:
            route_id: Route ID

        Returns:
            Dictionary with route totals
        """
        # Get all orders for the route
        query = (
            select(Order)
            .where(Order.route_id == route_id)
            .options(selectinload(Order.order_items))
        )

        result = await self.session.execute(query)
        orders = result.scalars().all()

        # Calculate totals
        total_amount = sum(order.final_amount for order in orders)
        total_orders = len(orders)

        # Count cylinders by type
        cylinder_counts = {
            "50kg": sum(order.qty_50kg for order in orders),
            "20kg": sum(order.qty_20kg for order in orders),
            "16kg": sum(order.qty_16kg for order in orders),
            "10kg": sum(order.qty_10kg for order in orders),
            "4kg": sum(order.qty_4kg for order in orders),
        }

        return {
            "total_orders": total_orders,
            "total_amount": float(total_amount),
            "cylinder_counts": cylinder_counts,
            "total_cylinders": sum(cylinder_counts.values()),
        }

    async def create_recurring_order(
        self, customer_id: int, template_order: Dict[str, Any], scheduled_date: datetime
    ) -> Order:
        """
        Create order from recurring template

        Args:
            customer_id: Customer ID
            template_order: Template with standard order details
            scheduled_date: Scheduled delivery date

        Returns:
            Created order
        """
        # Generate order number
        order_number = f"ORD-{datetime.now().strftime('%Y % m % d')}-{datetime.now().microsecond:04d}"

        order_data = {
            **template_order,
            "customer_id": customer_id,
            "scheduled_date": scheduled_date,
            "order_number": order_number,
            "status": OrderStatus.PENDING,
            "payment_status": PaymentStatus.UNPAID,
        }

        order = await self.create(**order_data)

        # Track metrics
        orders_created_counter.labels(
            order_type="recurring", customer_type="subscription"
        ).inc()

        return order
