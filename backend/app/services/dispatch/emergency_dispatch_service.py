import logging
from datetime import datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundException, ValidationException
from app.models.customer import Customer
from app.models.order import Order
from app.models.route_plan import RoutePlan, RouteStop
from app.models.user import User
from app.services.dispatch.route_optimizer import RouteOptimizer
from app.services.notification_service import NotificationService

logger = logging.getLogger(__name__)


class EmergencyDispatchService:
    """Service for handling emergency dispatch operations"""

    def __init__(self):
        self.notification_service = NotificationService()
        self.route_optimizer = RouteOptimizer()

    async def create_emergency_dispatch(
        self, db: AsyncSession, emergency_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Create an emergency dispatch order

        Args:
            db: Database session
            emergency_data: Emergency dispatch details

        Returns:
            Created emergency dispatch details
        """
        try:
            # Validate emergency type
            valid_types = [
                "gas_leak",
                "urgent_delivery",
                "customer_emergency",
                "driver_emergency",
            ]
            if emergency_data.get("type") not in valid_types:
                raise ValidationException(
                    f"Invalid emergency type: {emergency_data.get('type')}"
                )

            # Get customer details
            customer = await db.get(Customer, emergency_data["customerId"])
            if not customer:
                raise NotFoundException("Customer not found")

            # Create emergency order
            emergency_order = Order(
                customer_id=customer.id,
                order_date=datetime.now(),
                scheduled_date=datetime.now().date(),
                delivery_time_slot="immediate",
                is_urgent=True,
                status="confirmed",
                delivery_address=emergency_data.get("address", customer.address),
                delivery_notes=f"EMERGENCY: {emergency_data['type']} - {emergency_data['description']}",
                payment_method="cash",
                payment_status="unpaid",
                created_by=emergency_data.get("created_by", 1),
                updated_by=emergency_data.get("created_by", 1),
            )

            db.add(emergency_order)
            await db.flush()

            # If driver is assigned, create immediate route
            if emergency_data.get("driverId"):
                driver = await db.get(User, emergency_data["driverId"])
                if not driver or driver.role != "driver":
                    raise ValidationException("Invalid driver")

                # Create emergency route plan
                route_plan = RoutePlan(
                    route_date=datetime.now().date(),
                    route_number=f"EM-{emergency_order.id}",
                    driver_id=driver.id,
                    vehicle_id=driver.vehicle_id,
                    status="assigned",
                    total_stops=1,
                    total_distance=0,
                    total_duration=0,
                    is_emergency=True,
                    created_by=emergency_data.get("created_by", 1),
                )
                db.add(route_plan)
                await db.flush()

                # Create route stop
                route_stop = RouteStop(
                    route_plan_id=route_plan.id,
                    order_id=emergency_order.id,
                    sequence=1,
                    estimated_arrival=datetime.now() + timedelta(minutes=15),
                    created_by=emergency_data.get("created_by", 1),
                )
                db.add(route_stop)

                # Send notifications
                await self._send_emergency_notifications(
                    emergency_data["type"],
                    customer,
                    driver,
                    emergency_data.get("priority", "high"),
                )

            await db.commit()

            return {
                "id": f"em-{emergency_order.id}",
                "orderId": emergency_order.id,
                "type": emergency_data["type"],
                "priority": emergency_data.get("priority", "high"),
                "status": "assigned" if emergency_data.get("driverId") else "pending",
                "customerId": customer.id,
                "customerName": customer.short_name,
                "customerCode": customer.customer_code,
                "address": emergency_order.delivery_address,
                "contactPhone": emergency_data.get("contactPhone", customer.phone),
                "description": emergency_data["description"],
                "createdAt": emergency_order.created_at.isoformat(),
                "assignedDriverId": emergency_data.get("driverId"),
                "assignedDriverName": (
                    driver.full_name if emergency_data.get("driverId") else None
                ),
            }

        except Exception as e:
            await db.rollback()
            logger.error(f"Error creating emergency dispatch: {str(e)}")
            raise

    async def get_emergency_queue(
        self, db: AsyncSession, status: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Get current emergency dispatch queue

        Args:
            db: Database session
            status: Optional status filter

        Returns:
            List of emergency orders
        """
        query = (
            select(Order)
            .join(Customer)
            .where(Order.is_urgent, Order.delivery_notes.like("EMERGENCY:%"))
        )

        if status:
            query = query.where(Order.status == status)
        else:
            query = query.where(
                Order.status.in_(["pending", "confirmed", "assigned", "in_delivery"])
            )

        query = query.order_by(Order.created_at.desc())

        result = await db.execute(query)
        orders = result.scalars().all()

        emergency_queue = []
        for order in orders:
            # Parse emergency details from delivery notes
            notes_parts = order.delivery_notes.split(" - ", 1)
            emergency_type = (
                notes_parts[0].replace("EMERGENCY: ", "")
                if notes_parts
                else "urgent_delivery"
            )
            description = (
                notes_parts[1] if len(notes_parts) > 1 else order.delivery_notes
            )

            # Get assigned driver if any
            driver_info = None
            if order.route_stops:
                route_stop = order.route_stops[0]
                if route_stop.route_plan and route_stop.route_plan.driver:
                    driver = route_stop.route_plan.driver
                    driver_info = {"id": driver.id, "name": driver.full_name}

            emergency_queue.append(
                {
                    "id": f"em-{order.id}",
                    "orderId": order.id,
                    "type": emergency_type,
                    "priority": "critical" if "gas_leak" in emergency_type else "high",
                    "status": self._map_order_status_to_emergency_status(order.status),
                    "customerId": order.customer.id,
                    "customerName": order.customer.short_name,
                    "customerCode": order.customer.customer_code,
                    "address": order.delivery_address,
                    "contactPhone": order.customer.phone,
                    "description": description,
                    "createdAt": order.created_at.isoformat(),
                    "assignedDriverId": driver_info["id"] if driver_info else None,
                    "assignedDriverName": driver_info["name"] if driver_info else None,
                    "location": (
                        {
                            "lat": order.customer.latitude,
                            "lng": order.customer.longitude,
                        }
                        if order.customer.latitude and order.customer.longitude
                        else None
                    ),
                }
            )

        return emergency_queue

    async def update_emergency_status(
        self,
        db: AsyncSession,
        emergency_id: str,
        status: str,
        notes: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Update emergency dispatch status

        Args:
            db: Database session
            emergency_id: Emergency ID (format: em - XXX)
            status: New status
            notes: Optional status notes

        Returns:
            Updated emergency details
        """
        # Extract order ID from emergency ID
        order_id = int(emergency_id.replace("em-", ""))

        order = await db.get(Order, order_id)
        if not order or not order.is_urgent:
            raise NotFoundException("Emergency order not found")

        # Map emergency status to order status
        status_mapping = {
            "pending": "pending",
            "assigned": "assigned",
            "dispatched": "in_delivery",
            "completed": "delivered",
            "cancelled": "cancelled",
        }

        if status not in status_mapping:
            raise ValidationException(f"Invalid status: {status}")

        order.status = status_mapping[status]
        if notes:
            order.delivery_notes += (
                f"\n[{datetime.now().strftime('%Y-%m-%d %H:%M')}] {notes}"
            )

        await db.commit()

        return {
            "id": emergency_id,
            "orderId": order.id,
            "status": status,
            "updatedAt": datetime.now().isoformat(),
        }

    async def get_emergency_statistics(
        self,
        db: AsyncSession,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None,
    ) -> Dict[str, Any]:
        """
        Get emergency dispatch statistics

        Args:
            db: Database session
            date_from: Start date filter
            date_to: End date filter

        Returns:
            Emergency statistics
        """
        if not date_from:
            date_from = datetime.now().replace(hour=0, minute=0, second=0)
        if not date_to:
            date_to = datetime.now()

        # Total emergencies
        total_query = select(func.count(Order.id)).where(
            Order.is_urgent,
            Order.delivery_notes.like("EMERGENCY:%"),
            Order.created_at >= date_from,
            Order.created_at <= date_to,
        )
        total_result = await db.execute(total_query)
        total_emergencies = total_result.scalar() or 0

        # Active emergencies
        active_query = select(func.count(Order.id)).where(
            Order.is_urgent,
            Order.delivery_notes.like("EMERGENCY:%"),
            Order.status.in_(["pending", "confirmed", "assigned", "in_delivery"]),
        )
        active_result = await db.execute(active_query)
        active_emergencies = active_result.scalar() or 0

        # Average response time (time from creation to assignment)
        response_time_query = (
            select(
                func.avg(
                    func.extract("epoch", RoutePlan.created_at - Order.created_at) / 60
                )
            )
            .select_from(Order)
            .join(RouteStop, Order.id == RouteStop.order_id)
            .join(RoutePlan, RouteStop.route_plan_id == RoutePlan.id)
            .where(
                Order.is_urgent,
                Order.delivery_notes.like("EMERGENCY:%"),
                Order.created_at >= date_from,
                Order.created_at <= date_to,
            )
        )
        response_result = await db.execute(response_time_query)
        avg_response_time = response_result.scalar() or 0

        # Resolved today
        resolved_query = select(func.count(Order.id)).where(
            Order.is_urgent,
            Order.delivery_notes.like("EMERGENCY:%"),
            Order.status == "delivered",
            func.date(Order.updated_at) == datetime.now().date(),
        )
        resolved_result = await db.execute(resolved_query)
        resolved_today = resolved_result.scalar() or 0

        return {
            "totalEmergencies": total_emergencies,
            "activeEmergencies": active_emergencies,
            "averageResponseTime": round(avg_response_time, 1),
            "resolvedToday": resolved_today,
        }

    def _map_order_status_to_emergency_status(self, order_status: str) -> str:
        """Map order status to emergency status"""
        mapping = {
            "pending": "pending",
            "confirmed": "pending",
            "assigned": "assigned",
            "in_delivery": "dispatched",
            "delivered": "completed",
            "cancelled": "cancelled",
        }
        return mapping.get(order_status, "pending")

    async def _send_emergency_notifications(
        self,
        emergency_type: str,
        customer: Customer,
        driver: Optional[User],
        priority: str,
    ):
        """Send notifications for emergency dispatch"""
        try:
            # Notify driver
            if driver:
                await self.notification_service.send_notification(
                    user_id=driver.id,
                    title="緊急派遣通知",
                    message=f"您有一個{self._get_emergency_type_chinese(emergency_type)}的緊急任務，請立即前往",
                    type="emergency",
                    data={
                        "type": emergency_type,
                        "customer": customer.short_name,
                        "address": customer.address,
                        "priority": priority,
                    },
                )

            # Notify dispatch managers
            # This would typically notify all users with dispatch manager role
            logger.info(f"Emergency dispatch notification sent for {emergency_type}")

        except Exception as e:
            logger.error(f"Error sending emergency notifications: {str(e)}")

    def _get_emergency_type_chinese(self, emergency_type: str) -> str:
        """Get Chinese translation for emergency type"""
        translations = {
            "gas_leak": "瓦斯洩漏",
            "urgent_delivery": "緊急配送",
            "customer_emergency": "客戶緊急",
            "driver_emergency": "司機緊急",
        }
        return translations.get(emergency_type, "緊急")
