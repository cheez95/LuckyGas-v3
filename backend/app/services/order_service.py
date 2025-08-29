"""
Order service layer for business logic
Handles order creation, updates, and route assignment
"""

import logging
from datetime import date, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.metrics import background_tasks_counter, orders_created_counter
from app.core.service_utils import (
    handle_service_errors,
    transactional,
    validate_pagination
)
from app.models.order import Order, OrderStatus, PaymentStatus
from app.repositories.customer_repository import CustomerRepository
from app.repositories.order_repository import OrderRepository
from app.services.credit_service import CreditService

# Removed during compaction
# from app.api.v1.socketio_handler import notify_order_update, notify_driver_assigned
from app.services.google_cloud.routes_service import google_routes_service
from app.schemas.order import OrderCreate
from app.schemas.order import OrderUpdate

logger = logging.getLogger(__name__)


class OrderService:
    """
    Service layer for order business logic
    Handles order lifecycle and coordination with other services
    """

    def __init__(self, session: AsyncSession):
        self.session = session
        self.order_repo = OrderRepository(session)
        self.customer_repo = CustomerRepository(session)

    @handle_service_errors(operation="建立訂單")
    @transactional()
    async def create_order(
        self,
        order_data: OrderCreate,
        created_by: int,
        skip_credit_check: bool = False,
        created_by_role: Optional[str] = None,
    ) -> Order:
        """
        Create new order with validation, credit checking, and pricing

        Args:
            order_data: Order creation data
            created_by: User ID creating the order
            skip_credit_check: Skip credit check (for manager override)
            created_by_role: Role of user creating order

        Returns:
            Created order

        Raises:
            ValueError: If validation fails
        """
        # Validate customer exists and is active
        customer = await self.customer_repo.get(order_data.customer_id)
        if not customer:
            raise ValueError("客戶不存在")
        if customer.is_terminated:
            raise ValueError("客戶已停用")

        # Calculate pricing
        pricing = self._calculate_order_pricing(order_data)

        # Check credit limit
        credit_result = await CreditService.check_credit_limit(
            db=self.session,
            customer_id=order_data.customer_id,
            order_amount=pricing["final_amount"],
            skip_check=skip_credit_check or created_by_role == "super_admin",
        )

        if not credit_result["approved"]:
            raise ValueError(
                f"信用額度檢查失敗: {credit_result['reason']}. "
                + f"可用額度: NT${credit_result['details'].get('available_credit', 0):, .0f}, "
                + f"訂單金額: NT${credit_result['details'].get('requested_amount', 0):, .0f}"
            )

        # Generate order number
        order_number = self._generate_order_number()

        # Create order
        order_dict = order_data.model_dump()
        order_dict.update(
            {
                "order_number": order_number,
                "status": OrderStatus.PENDING,
                "payment_status": PaymentStatus.UNPAID,
                "total_amount": pricing["total_amount"],
                "discount_amount": pricing["discount_amount"],
                "final_amount": pricing["final_amount"],
            }
        )

        # Use delivery address from order or customer
        if not order_dict.get("delivery_address"):
            order_dict["delivery_address"] = customer.address

        order = await self.order_repo.create(**order_dict)

        # Track metrics
        orders_created_counter.labels(
            order_type="manual", customer_type=customer.customer_type or "regular"
        ).inc()

        # Removed during compaction
        # Notify relevant parties
        # await notify_order_update(
        #     order_id=order.id,
        #     status="created",
        #     details={
        #         "order_number": order.order_number,
        #         "customer_name": customer.short_name,
        #         "scheduled_date": order.scheduled_date.isoformat()
        #     }
        # )

        logger.info(
            f"Created order {order.order_number} for customer {customer.customer_code}"
        )

        return order

    @handle_service_errors(operation="更新訂單")
    @transactional()
    async def update_order(
        self, order_id: int, order_update: OrderUpdate, updated_by: int
    ) -> Optional[Order]:
        """
        Update order with validation

        Args:
            order_id: Order ID
            order_update: Update data
            updated_by: User ID updating the order

        Returns:
            Updated order or None
        """
        # Get existing order
        order = await self.order_repo.get_with_details(order_id)
        if not order:
            return None

        # Check if order can be updated
        if order.status in [OrderStatus.DELIVERED, OrderStatus.CANCELLED]:
            raise ValueError(f"無法更新{order.status.value}狀態的訂單")

        # Extract update data
        update_data = order_update.model_dump(exclude_unset=True)

        # Recalculate pricing if quantities changed
        quantity_fields = ["qty_50kg", "qty_20kg", "qty_16kg", "qty_10kg", "qty_4kg"]
        if any(field in update_data for field in quantity_fields):
            # Create temporary order data for pricing calculation
            temp_order_data = OrderCreate(
                customer_id=order.customer_id,
                scheduled_date=order.scheduled_date,
                qty_50kg=update_data.get("qty_50kg", order.qty_50kg),
                qty_20kg=update_data.get("qty_20kg", order.qty_20kg),
                qty_16kg=update_data.get("qty_16kg", order.qty_16kg),
                qty_10kg=update_data.get("qty_10kg", order.qty_10kg),
                qty_4kg=update_data.get("qty_4kg", order.qty_4kg),
            )
            pricing = self._calculate_order_pricing(temp_order_data)
            update_data.update(pricing)

        # Update order
        updated_order = await self.order_repo.update(order_id, **update_data)

        # Removed during compaction
        # Notify if status changed
        # if "status" in update_data:
        #     await notify_order_update(
        #         order_id=order_id,
        #         status=update_data["status"],
        #         details={"updated_by": updated_by}
        #     )

        logger.info(f"Updated order {order_id} by user {updated_by}")

        return updated_order

    @handle_service_errors(operation="查詢訂單")
    @validate_pagination(max_page_size=500)
    async def get_orders_for_date(
        self,
        scheduled_date: date,
        status: Optional[OrderStatus] = None,
        area: Optional[str] = None,
        page: int = 1,
        page_size: int = 100,
    ) -> Tuple[List[Order], int]:
        """
        Get orders for a specific date with filters

        Args:
            scheduled_date: Date to query
            status: Optional status filter
            area: Optional area filter
            page: Page number
            page_size: Items per page

        Returns:
            Tuple of (orders list, total count)
        """
        skip = (page - 1) * page_size
        return await self.order_repo.get_orders_by_date(
            scheduled_date, status, area, skip, page_size
        )

    async def assign_orders_to_routes(
        self, scheduled_date: date, area: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Automatically assign unassigned orders to routes

        Args:
            scheduled_date: Date to process
            area: Optional area filter

        Returns:
            Assignment results
        """
        # Get unassigned orders
        unassigned_orders = await self.order_repo.get_unassigned_orders(
            scheduled_date, area
        )

        if not unassigned_orders:
            return {"total_orders": 0, "assigned_orders": 0, "routes_created": 0}

        # Get available drivers (simplified for now)
        # In production, would check driver availability
        drivers = [
            {"id": 1, "name": "司機A"},
            {"id": 2, "name": "司機B"},
            {"id": 3, "name": "司機C"},
        ]

        # Use route optimization service
        optimized_routes = await google_routes_service.optimize_multiple_routes(
            orders=unassigned_orders, drivers=drivers, date=scheduled_date
        )

        # Create routes and assign orders
        assigned_count = 0
        for route_data in optimized_routes:
            # In production, would create Route records in database
            route_id = route_data["route_number"].split("-")[-1]  # Simplified

            # Get order IDs from route stops
            order_ids = [stop["order_id"] for stop in route_data["stops"]]

            # Bulk assign orders
            count = await self.order_repo.bulk_assign_to_route(
                order_ids=order_ids,
                route_id=int(route_id),
                driver_id=route_data["driver_id"],
            )
            assigned_count += count

            # Removed during compaction
            # Notify driver
            # await notify_driver_assigned(
            #     driver_id=route_data["driver_id"],
            #     route_id=int(route_id),
            #     details={
            #         "total_stops": route_data["total_stops"],
            #         "estimated_duration": route_data["estimated_duration_minutes"]
            #     }
            # )

        logger.info(
            f"Assigned {assigned_count} orders to {len(optimized_routes)} routes"
        )

        # Track metrics
        background_tasks_counter.labels(
            task_type="route_assignment", status="completed"
        ).inc()

        return {
            "total_orders": len(unassigned_orders),
            "assigned_orders": assigned_count,
            "routes_created": len(optimized_routes),
        }

    @handle_service_errors(operation="更新配送狀態")
    @transactional()
    async def update_delivery_status(
        self,
        order_id: int,
        status: str,
        notes: Optional[str] = None,
        updated_by: int = None,
    ) -> Optional[Order]:
        """
        Update order delivery status

        Args:
            order_id: Order ID
            status: New status
            notes: Optional delivery notes
            updated_by: User ID updating status

        Returns:
            Updated order or None
        """
        # Validate status
        try:
            order_status = OrderStatus(status)
        except ValueError:
            raise ValueError(f"無效的訂單狀態: {status}")

        # Set delivery timestamp if delivered
        delivered_at = (
            datetime.utcnow() if order_status == OrderStatus.DELIVERED else None
        )

        # Update order
        order = await self.order_repo.update_delivery_status(
            order_id=order_id,
            status=order_status,
            delivered_at=delivered_at,
            delivery_notes=notes,
        )

        if order:
            # Removed during compaction
            # Notify updates
            # await notify_order_update(
            #     order_id=order_id,
            #     status=status,
            #     details={
            #         "updated_by": updated_by,
            #         "notes": notes
            #     }
            # )

            logger.info(f"Updated order {order_id} status to {status}")

        return order

    async def get_order_statistics(
        self, start_date: date, end_date: date, area: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Get order statistics for date range

        Args:
            start_date: Start date
            end_date: End date
            area: Optional area filter

        Returns:
            Statistics dictionary
        """
        stats = await self.order_repo.get_order_statistics(start_date, end_date, area)

        # Add additional calculations
        stats["date_range"] = {
            "start": start_date.isoformat(),
            "end": end_date.isoformat(),
            "days": (end_date - start_date).days + 1,
        }

        # Daily averages
        days = stats["date_range"]["days"]
        stats["daily_averages"] = {
            "orders_per_day": stats["total_orders"] / days if days > 0 else 0,
            "revenue_per_day": stats["total_revenue"] / days if days > 0 else 0,
        }

        return stats

    async def get_pending_payments(
        self, customer_id: Optional[int] = None, days_overdue: int = 0
    ) -> List[Dict[str, Any]]:
        """
        Get orders with pending payments

        Args:
            customer_id: Optional customer filter
            days_overdue: Minimum days overdue

        Returns:
            List of pending payment details
        """
        orders = await self.order_repo.get_pending_payments(customer_id, days_overdue)

        pending_payments = []
        for order in orders:
            days_pending = (
                (datetime.now() - order.delivered_at).days if order.delivered_at else 0
            )

            pending_payments.append(
                {
                    "order": order,
                    "customer_name": (
                        order.customer.short_name if order.customer else "Unknown"
                    ),
                    "amount_due": order.final_amount,
                    "days_pending": days_pending,
                    "is_overdue": days_pending > 7,  # 7 day payment terms
                }
            )

        return pending_payments

    def _calculate_order_pricing(self, order_data: OrderCreate) -> Dict[str, float]:
        """
        Calculate order pricing based on quantities

        Args:
            order_data: Order data with quantities

        Returns:
            Pricing dictionary
        """
        # Base prices per cylinder type (TWD)
        prices = {"50kg": 2500, "20kg": 1200, "16kg": 1000, "10kg": 700, "4kg": 350}

        # Calculate total
        total = 0
        total += order_data.qty_50kg * prices["50kg"]
        total += order_data.qty_20kg * prices["20kg"]
        total += order_data.qty_16kg * prices["16kg"]
        total += order_data.qty_10kg * prices["10kg"]
        total += order_data.qty_4kg * prices["4kg"]

        # Apply discounts
        discount = 0

        # Volume discount: 5% off for orders over 10, 000 TWD
        if total > 10000:
            discount = total * 0.05

        # Urgent order surcharge
        if order_data.is_urgent:
            total *= 1.1  # 10% surcharge

        return {
            "total_amount": total,
            "discount_amount": discount,
            "final_amount": total - discount,
        }

    def _generate_order_number(self) -> str:
        """Generate unique order number"""
        timestamp = datetime.now()
        return f"ORD-{timestamp.strftime('%Y % m % d')}-{timestamp.microsecond:06d}"

    @handle_service_errors(operation="批量建立訂單")
    @transactional()
    async def create_bulk_orders(
        self, orders_data: List[OrderCreate], created_by: int
    ) -> List[Order]:
        """
        Create multiple orders efficiently

        Args:
            orders_data: List of order creation data
            created_by: User ID creating orders

        Returns:
            List of created orders
        """
        created_orders = []

        # Process each order
        for order_data in orders_data:
            try:
                order = await self.create_order(order_data, created_by)
                created_orders.append(order)
            except Exception as e:
                logger.error(f"Failed to create order: {e}")
                # Continue with other orders

        logger.info(f"Created {len(created_orders)} orders in bulk")

        return created_orders
