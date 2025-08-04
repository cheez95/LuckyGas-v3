import json
import logging
from datetime import datetime

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db
from app.models.delivery_photo import DeliveryPhoto
from app.models.order import Order, OrderStatus
from app.models.user import User
from app.schemas.delivery import (

from sqlalchemy import select
from typing import Dict
from typing import Optional

    DeliveryConfirmation,
    DeliveryLocationUpdate,
    DeliveryResponse,
    DeliveryStatusUpdate,
)
from app.services.file_storage import upload_delivery_photo, upload_signature
from app.services.notification_service import NotificationType, notification_service
from app.services.websocket_service import websocket_manager

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/location")
async def update_driver_location(
    location_update: DeliveryLocationUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Dict[str, str]:
    """Update driver location (for driver app)"""
    if current_user.role != "driver":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="只有司機可以更新位置"
        )

    # Broadcast location update via WebSocket
    await websocket_manager.handle_driver_location(
        driver_id=str(current_user.id),
        message={
            "latitude": location_update.latitude,
            "longitude": location_update.longitude,
            "speed": location_update.speed,
            "heading": location_update.heading,
            "accuracy": location_update.accuracy,
            "timestamp": location_update.timestamp or datetime.now(),
        },
    )

    return {"message": "位置更新成功"}


@router.post("/status/{order_id}")
async def update_delivery_status(
    order_id: int,
    status_update: DeliveryStatusUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> DeliveryResponse:
    """Update delivery status (for driver app)"""
    if current_user.role != "driver":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="只有司機可以更新配送狀態"
        )

    # Get order
    stmt = select(Order).where(Order.id == order_id)
    result = await db.execute(stmt)
    order = result.scalar_one_or_none()

    if not order:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="訂單不存在")

    # Verify driver is assigned to this order
    if order.driver_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="您未被指派此訂單"
        )

    # Update order status
    old_status = order.status
    order.status = OrderStatus(status_update.status)
    order.updated_at = datetime.now()

    if status_update.notes:
        order.delivery_notes = status_update.notes

    await db.commit()

    # Send notifications based on status
    notification_type = None
    if status_update.status == OrderStatus.IN_DELIVERY.value:
        notification_type = NotificationType.DELIVERY_ON_WAY
    elif status_update.status == OrderStatus.DELIVERED.value:
        notification_type = NotificationType.DELIVERY_ARRIVED

    if notification_type:
        await notification_service.send_order_notifications(
            order={
                "order_number": order.order_number,
                "customer_name": order.customer_name,
                "customer_phone": order.customer_phone,
                "customer_email": order.customer_email,
                "customer_id": str(order.customer_id),
                "driver_name": current_user.full_name or current_user.email,
                "eta_minutes": 30,  # Default ETA
            },
            event_type=notification_type,
        )

    # Broadcast status update
    await websocket_manager.notify_order_update(
        order_id=str(order_id),
        status=status_update.status,
        details={
            "old_status": old_status.value,
            "new_status": status_update.status,
            "updated_by": current_user.id,
            "driver_name": current_user.full_name or current_user.email,
        },
    )

    return DeliveryResponse(
        order_id=order.id,
        status=order.status.value,
        message=f"訂單狀態已更新為: {order.status.value}",
    )


@router.post("/confirm/{order_id}")
async def confirm_delivery(
    order_id: int,
    signature: Optional[str] = Form(None),
    recipient_name: Optional[str] = Form(None),
    recipient_id: Optional[str] = Form(None),
    notes: Optional[str] = Form(None),
    photo: Optional[UploadFile] = File(None),
    cylinder_data: Optional[str] = Form(None),  # JSON string of cylinder serial numbers
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> DeliveryResponse:
    """Confirm delivery completion with signature and photo"""
    if current_user.role != "driver":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="只有司機可以確認配送"
        )

    # Get order
    stmt = select(Order).where(Order.id == order_id)
    result = await db.execute(stmt)
    order = result.scalar_one_or_none()

    if not order:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="訂單不存在")

    # Verify driver is assigned to this order
    if order.driver_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="您未被指派此訂單"
        )

    # Process signature (base64 image)
    signature_url = None
    if signature:
        try:
            signature_url = await upload_signature(
                base64_data=signature, order_id=order_id, driver_id=current_user.id
            )
        except Exception as e:
            logger.error(f"Failed to upload signature: {e}")

    # Process photo
    photo_url = None
    if photo:
        try:
            photo_url = await upload_delivery_photo(
                file=photo, order_id=order_id, driver_id=current_user.id
            )

            # Save photo record
            delivery_photo = DeliveryPhoto(
                order_id=order_id,
                photo_url=photo_url,
                photo_type="delivery_proof",
                uploaded_by=current_user.id,
                uploaded_at=datetime.now(),
            )
            db.add(delivery_photo)
        except Exception as e:
            logger.error(f"Failed to upload photo: {e}")

    # Process cylinder data
    cylinder_info = None
    if cylinder_data:
        try:
            cylinder_info = json.loads(cylinder_data)
        except Exception:
            pass

    # Update order
    order.status = OrderStatus.DELIVERED
    order.delivered_at = datetime.now()
    order.signature_url = signature_url
    order.recipient_name = recipient_name or order.customer_name
    order.recipient_id = recipient_id
    order.delivery_notes = notes

    if cylinder_info:
        order.cylinder_serial_numbers = cylinder_info

    await db.commit()

    # Send delivery confirmation notifications
    await notification_service.send_order_notifications(
        order={
            "order_number": order.order_number,
            "customer_name": order.customer_name,
            "customer_phone": order.customer_phone,
            "customer_email": order.customer_email,
            "customer_id": str(order.customer_id),
            "driver_name": current_user.full_name or current_user.email,
            "signature_url": signature_url,
            "delivered_at": order.delivered_at.isoformat(),
        },
        event_type=NotificationType.DELIVERY_COMPLETED,
    )

    # Broadcast delivery confirmation
    await websocket_manager.handle_delivery_confirmation(
        driver_id=str(current_user.id),
        message={
            "order_id": str(order_id),
            "customer_id": str(order.customer_id),
            "delivered_at": order.delivered_at.isoformat(),
            "signature_url": signature_url,
            "photo_url": photo_url,
            "recipient_name": order.recipient_name,
        },
    )

    return DeliveryResponse(
        order_id=order.id,
        status=order.status.value,
        message="配送已確認完成",
        signature_url=signature_url,
        photo_url=photo_url,
    )


@router.post("/cancel/{order_id}")
async def cancel_delivery(
    order_id: int,
    reason: str = Form(...),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> DeliveryResponse:
    """Cancel delivery with reason"""
    if current_user.role not in ["driver", "office_staf", "manager", "super_admin"]:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="權限不足")

    # Get order
    stmt = select(Order).where(Order.id == order_id)
    result = await db.execute(stmt)
    order = result.scalar_one_or_none()

    if not order:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="訂單不存在")

    # For drivers, verify assignment
    if current_user.role == "driver" and order.driver_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="您未被指派此訂單"
        )

    # Update order
    order.status = OrderStatus.CANCELLED
    order.cancelled_at = datetime.now()
    order.cancelled_by = current_user.id
    order.cancellation_reason = reason

    await db.commit()

    # Send cancellation notification
    await notification_service.send_order_notifications(
        order={
            "order_number": order.order_number,
            "customer_name": order.customer_name,
            "customer_phone": order.customer_phone,
            "customer_email": order.customer_email,
            "customer_id": str(order.customer_id),
            "cancellation_reason": reason,
        },
        event_type=NotificationType.ORDER_CANCELLED,
    )

    # Broadcast cancellation
    await websocket_manager.notify_order_update(
        order_id=str(order_id),
        status=OrderStatus.CANCELLED.value,
        details={"cancelled_by": current_user.id, "reason": reason},
    )

    return DeliveryResponse(
        order_id=order.id, status=order.status.value, message=f"訂單已取消: {reason}"
    )
