"""
Example of OrderService updated with simple WebSocket and notification integration
This shows how to integrate the simplified services
"""

import logging
from datetime import datetime
from typing import Optional

from app.models.order import OrderStatus
from app.services.order_service import OrderService as BaseOrderService
from app.services.simple_notifications import (notification_service,
                                               send_order_sms)
from app.services.simple_websocket import (notify_order_updated,
                                           websocket_manager)

logger = logging.getLogger(__name__)


class UpdatedOrderService(BaseOrderService):
    """
    OrderService with integrated simple notifications and WebSocket events.

    This demonstrates how to add real-time updates and notifications
    to existing services without complex queuing.
    """

    async def create_order(self, order_data, created_by: int, **kwargs):
        """Create order with notification"""
        # Create order using base implementation
        order = await super().create_order(order_data, created_by, **kwargs)

        # Send WebSocket notification
        await notify_order_updated(
            order_id=order.id,
            status="created",
            details={
                "order_number": order.order_number,
                "customer_id": order.customer_id,
                "customer_name": order.customer.short_name if order.customer else None,
                "scheduled_date": order.scheduled_date.isoformat(),
            },
        )

        # Send SMS confirmation (fire and forget)
        try:
            await send_order_sms(order, "confirmed")
        except Exception as e:
            logger.error(f"Failed to send order confirmation SMS: {e}")
            # Don't fail the order creation if SMS fails

        return order

    async def update_order_status(
        self,
        order_id: int,
        status: str,
        notes: Optional[str] = None,
        updated_by: int = None,
    ):
        """Update order status with notifications"""
        # Update using base implementation
        order = await super().update_delivery_status(
            order_id=order_id, status=status, notes=notes, updated_by=updated_by
        )

        if not order:
            return None

        # Send WebSocket update
        await notify_order_updated(
            order_id=order_id,
            status=status,
            details={
                "order_number": order.order_number,
                "notes": notes,
                "updated_at": datetime.now().isoformat(),
            },
        )

        # Send SMS based on status
        if status == OrderStatus.ASSIGNED.value:
            # Driver assigned - notify customer
            message = (
                f"【幸福氣】您的訂單 {order.order_number} 已安排配送\n"
                f"預計送達時間：{order.scheduled_date.strftime('%m月%d日')}"
            )
            await notification_service.send_sms(order.customer.phone, message)

        elif status == OrderStatus.OUT_FOR_DELIVERY.value:
            # Driver on the way
            await send_order_sms(order, "arriving")

        elif status == OrderStatus.DELIVERED.value:
            # Order delivered
            await send_order_sms(order, "delivered")

        return order

    async def assign_orders_to_routes(self, scheduled_date, area=None):
        """Assign orders to routes with notifications"""
        # Use base implementation
        result = await super().assign_orders_to_routes(scheduled_date, area)

        # Send WebSocket notification about route assignment
        await websocket_manager.broadcast_event(
            "routes_assigned",
            {
                "date": scheduled_date.isoformat(),
                "area": area,
                "total_orders": result["total_orders"],
                "assigned_orders": result["assigned_orders"],
                "routes_created": result["routes_created"],
            },
        )

        return result

    async def update_driver_location(
        self,
        driver_id: int,
        latitude: float,
        longitude: float,
        heading: float = 0,
        speed: float = 0,
    ):
        """Update driver location and broadcast"""
        # Store in cache/database if needed
        # For now, just broadcast

        await websocket_manager.broadcast_event(
            "driver_location",
            {
                "driver_id": driver_id,
                "latitude": latitude,
                "longitude": longitude,
                "heading": heading,
                "speed": speed,
                "timestamp": datetime.now().isoformat(),
            },
        )

        # Check if driver is near any delivery location
        # and send "arriving soon" SMS if needed
        # (simplified - in production would check actual routes)

        return True


# Example usage in API endpoint
"""
from app.services.order_service_updated import UpdatedOrderService

@router.post("/orders")
async def create_order(
    order_data: OrderCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    service = UpdatedOrderService(db)
    order = await service.create_order(
        order_data=order_data,
        created_by=current_user.id
    )
    return order


@router.put("/orders/{order_id}/status")
async def update_order_status(
    order_id: int,
    status: str,
    notes: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    service = UpdatedOrderService(db)
    order = await service.update_order_status(
        order_id=order_id,
        status=status,
        notes=notes,
        updated_by=current_user.id
    )
    
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    
    return order
"""
