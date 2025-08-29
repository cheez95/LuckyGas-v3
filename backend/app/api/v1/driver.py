"""
Driver API endpoints for mobile app functionality
"""
from typing import Any, Dict, List, Optional

import base64
from datetime import date, datetime, timedelta
from pathlib import Path

import aiofiles
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.deps import get_current_user, get_db
from app.core.security import verify_user_role
from app.models.order import Order, OrderStatus
from app.models.order_item import OrderItem
from app.models.route_delivery import (
    DeliveryStatus,
    DeliveryStatusHistory,
    RouteDelivery,
)
from app.models.user import User
from app.schemas.driver import (
    DeliveryConfirmResponse,
    DeliveryStatsResponse,
    DeliveryStatusUpdateRequest,
    DriverSyncRequest,
    DriverSyncResponse,
    LocationUpdateRequest,
    RouteDetailResponse,
    RouteListResponse,
)
from app.services.gps_service import GPSService
from app.services.notification_service import NotificationService, NotificationType
from app.services.websocket_service import websocket_manager as ws_manager
from app.models.route import Route

router = APIRouter()
notification_service = NotificationService()
gps_service = GPSService()


@router.get("/routes / today", response_model=List[RouteListResponse])
async def get_today_routes(
    db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)
) -> List[RouteListResponse]:
    """Get driver's routes for today"""
    verify_user_role(current_user, ["driver", "admin", "manager"])

    today = date.today()
    tomorrow = today + timedelta(days=1)

    # Query routes assigned to this driver for today
    stmt = (
        select(Route)
        .where(
            and_(
                Route.driver_id == current_user.id,
                Route.scheduled_date >= today,
                Route.scheduled_date < tomorrow,
                Route.is_active,
            )
        )
        .options(
            selectinload(Route.deliveries)
            .selectinload(RouteDelivery.order)
            .selectinload(Order.customer),
            selectinload(Route.deliveries)
            .selectinload(RouteDelivery.order)
            .selectinload(Order.items)
            .selectinload(OrderItem.product),
        )
    )

    result = await db.execute(stmt)
    routes = result.scalars().all()

    # Convert to response format
    route_responses = []
    for route in routes:
        total_deliveries = len(route.deliveries)
        completed_deliveries = sum(
            1 for d in route.deliveries if d.status == DeliveryStatus.DELIVERED
        )

        # Calculate estimated time based on deliveries
        estimated_minutes = total_deliveries * 15  # 15 minutes per delivery average
        estimated_time = f"{estimated_minutes // 60}小時{estimated_minutes % 60}分"

        # Calculate total distance (mock for now, would use Google Routes API)
        total_distance = total_deliveries * 3.5  # Average 3.5km between stops

        route_responses.append(
            RouteListResponse(
                id=str(route.id),
                name=route.name or f"路線 {route.route_number}",
                deliveryCount=total_deliveries,
                completedCount=completed_deliveries,
                estimatedTime=estimated_time,
                distance=round(total_distance, 1),
                status=route.status,
            )
        )

    return route_responses


@router.get("/stats / today", response_model=DeliveryStatsResponse)
async def get_today_stats(
    db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)
) -> DeliveryStatsResponse:
    """Get driver's delivery statistics for today"""
    verify_user_role(current_user, ["driver", "admin", "manager"])

    today = date.today()
    tomorrow = today + timedelta(days=1)

    # Get all deliveries for this driver today
    stmt = (
        select(RouteDelivery)
        .join(Route)
        .where(
            and_(
                Route.driver_id == current_user.id,
                Route.scheduled_date >= today,
                Route.scheduled_date < tomorrow,
                Route.is_active,
            )
        )
    )

    result = await db.execute(stmt)
    deliveries = result.scalars().all()

    # Calculate statistics
    total = len(deliveries)
    completed = sum(1 for d in deliveries if d.status == DeliveryStatus.DELIVERED)
    failed = sum(1 for d in deliveries if d.status == DeliveryStatus.FAILED)
    pending = total - completed - failed

    return DeliveryStatsResponse(
        total=total, completed=completed, pending=pending, failed=failed
    )


@router.get("/routes/{route_id}", response_model=RouteDetailResponse)
async def get_route_details(
    route_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> RouteDetailResponse:
    """Get detailed route information"""
    verify_user_role(current_user, ["driver", "admin", "manager"])

    # Get route with all related data
    stmt = (
        select(Route)
        .where(
            and_(
                Route.id == route_id,
                Route.driver_id == current_user.id,
                Route.is_active,
            )
        )
        .options(
            selectinload(Route.deliveries)
            .selectinload(RouteDelivery.order)
            .selectinload(Order.customer),
            selectinload(Route.deliveries)
            .selectinload(RouteDelivery.order)
            .selectinload(Order.items)
            .selectinload(OrderItem.product),
        )
    )

    result = await db.execute(stmt)
    route = result.scalar_one_or_none()

    if not route:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="路線不存在或無權限查看"
        )

    # Build delivery list
    deliveries = []
    for idx, route_delivery in enumerate(
        sorted(route.deliveries, key=lambda d: d.sequence)
    ):
        order = route_delivery.order
        customer = order.customer

        # Build products list
        products = [
            {"name": item.product.name, "quantity": item.quantity}
            for item in order.items
        ]

        deliveries.append(
            {
                "id": str(route_delivery.id),
                "customerName": customer.name,
                "address": order.delivery_address or customer.address,
                "phone": customer.phone,
                "products": products,
                "notes": order.notes,
                "status": route_delivery.status.value,
                "sequence": route_delivery.sequence,
            }
        )

    # Calculate route statistics
    total_deliveries = len(route.deliveries)
    completed_deliveries = sum(
        1 for d in route.deliveries if d.status == DeliveryStatus.DELIVERED
    )
    estimated_minutes = total_deliveries * 15
    estimated_time = f"{estimated_minutes // 60}小時{estimated_minutes % 60}分"
    total_distance = total_deliveries * 3.5

    return RouteDetailResponse(
        id=str(route.id),
        name=route.name or f"路線 {route.route_number}",
        totalDeliveries=total_deliveries,
        completedDeliveries=completed_deliveries,
        estimatedDuration=estimated_time,
        totalDistance=round(total_distance, 1),
        deliveries=deliveries,
    )


@router.post("/location")
async def update_driver_location(
    location: LocationUpdateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Dict[str, str]:
    """Update driver's current location"""
    verify_user_role(current_user, ["driver"])

    # Store location in GPS service
    await gps_service.update_driver_location(
        driver_id=current_user.id,
        latitude=location.latitude,
        longitude=location.longitude,
        accuracy=location.accuracy,
        speed=location.speed,
        heading=location.heading,
    )

    # Broadcast location update via WebSocket
    await ws_manager.broadcast(
        {
            "type": "driver.location",
            "driver_id": str(current_user.id),
            "location": {
                "latitude": location.latitude,
                "longitude": location.longitude,
                "accuracy": location.accuracy,
                "timestamp": location.timestamp.isoformat(),
                "speed": location.speed,
                "heading": location.heading,
            },
        }
    )

    return {"status": "success", "message": "位置更新成功"}


@router.post("/deliveries / status/{delivery_id}")
async def update_delivery_status(
    delivery_id: int,
    status_update: DeliveryStatusUpdateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Dict[str, str]:
    """Update delivery status"""
    verify_user_role(current_user, ["driver"])

    # Get delivery and verify ownership
    stmt = (
        select(RouteDelivery)
        .join(Route)
        .where(
            and_(RouteDelivery.id == delivery_id, Route.driver_id == current_user.id)
        )
        .options(selectinload(RouteDelivery.order).selectinload(Order.customer))
    )

    result = await db.execute(stmt)
    delivery = result.scalar_one_or_none()

    if not delivery:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="配送不存在或無權限更新"
        )

    # Update status
    old_status = delivery.status
    delivery.status = DeliveryStatus(status_update.status)

    if status_update.notes:
        delivery.notes = status_update.notes

    if status_update.issue_type:
        delivery.issue_type = status_update.issue_type

    # Create history record
    history = DeliveryStatusHistory(
        delivery_id=delivery.id,
        status=delivery.status,
        notes=status_update.notes,
        created_by=current_user.id,
        created_at=datetime.utcnow(),
    )
    db.add(history)

    # Update order status if needed
    if delivery.status == DeliveryStatus.DELIVERED:
        delivery.order.status = OrderStatus.DELIVERED
        delivery.delivered_at = datetime.utcnow()
    elif delivery.status == DeliveryStatus.FAILED:
        delivery.order.status = OrderStatus.FAILED

    await db.commit()

    # Send WebSocket notification
    await ws_manager.broadcast(
        {
            "type": "delivery.status",
            "delivery_id": str(delivery_id),
            "order_id": str(delivery.order_id),
            "old_status": old_status.value,
            "new_status": delivery.status.value,
            "driver": current_user.full_name,
            "customer": delivery.order.customer.name,
            "timestamp": datetime.utcnow().isoformat(),
        }
    )

    # Send customer notification if delivered or failed
    if delivery.status in [DeliveryStatus.DELIVERED, DeliveryStatus.FAILED]:
        await notification_service.send_notification(
            recipient={
                "user_id": str(delivery.order.customer_id),
                "email": (
                    delivery.order.customer.email
                    if hasattr(delivery.order.customer, "email")
                    else None
                ),
                "phone": delivery.order.customer.phone,
                "name": delivery.order.customer.name,
            },
            event_type=(
                NotificationType.DELIVERY_COMPLETED
                if delivery.status == DeliveryStatus.DELIVERED
                else NotificationType.DELIVERY_FAILED
            ),
            context={
                "order_number": delivery.order.order_number,
                "customer_name": delivery.order.customer.name,
                "status": (
                    "已送達"
                    if delivery.status == DeliveryStatus.DELIVERED
                    else "配送失敗"
                ),
                "driver_name": current_user.full_name,
                "notes": status_update.notes or "",
            },
        )

    return {"status": "success", "message": "狀態更新成功"}


@router.post(
    "/deliveries / confirm/{delivery_id}", response_model=DeliveryConfirmResponse
)
async def confirm_delivery(
    delivery_id: int,
    recipient_name: Optional[str] = Form(None),
    notes: Optional[str] = Form(None),
    signature: Optional[str] = Form(None),
    photo: Optional[UploadFile] = File(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> DeliveryConfirmResponse:
    """Confirm delivery completion with signature / photo"""
    verify_user_role(current_user, ["driver"])

    # Get delivery and verify ownership
    stmt = (
        select(RouteDelivery)
        .join(Route)
        .where(
            and_(RouteDelivery.id == delivery_id, Route.driver_id == current_user.id)
        )
        .options(selectinload(RouteDelivery.order).selectinload(Order.customer))
    )

    result = await db.execute(stmt)
    delivery = result.scalar_one_or_none()

    if not delivery:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="配送不存在或無權限確認"
        )

    # Update delivery record
    delivery.status = DeliveryStatus.DELIVERED
    delivery.delivered_at = datetime.utcnow()
    delivery.recipient_name = recipient_name or delivery.order.customer.name
    if notes:
        delivery.notes = notes

    # Save signature if provided
    if signature:
        # Decode base64 signature and save
        signature_data = base64.b64decode(
            signature.split(", ")[1] if ", " in signature else signature
        )
        signature_path = Path(
            f"uploads / signatures/{delivery_id}_{datetime.utcnow().timestamp()}.png"
        )
        signature_path.parent.mkdir(parents=True, exist_ok=True)

        async with aiofiles.open(signature_path, "wb") as f:
            await f.write(signature_data)

        delivery.signature_path = str(signature_path)

    # Save photo if provided
    if photo:
        photo_path = Path(
            f"uploads / delivery_photos/{delivery_id}_{datetime.utcnow().timestamp()}_{photo.filename}"
        )
        photo_path.parent.mkdir(parents=True, exist_ok=True)

        content = await photo.read()
        async with aiofiles.open(photo_path, "wb") as f:
            await f.write(content)

        delivery.photo_path = str(photo_path)

    # Update order status
    delivery.order.status = OrderStatus.DELIVERED

    # Create history record
    history = DeliveryStatusHistory(
        delivery_id=delivery.id,
        status=DeliveryStatus.DELIVERED,
        notes=f"已交付給: {delivery.recipient_name}. {notes or ''}",
        created_by=current_user.id,
        created_at=datetime.utcnow(),
    )
    db.add(history)

    await db.commit()

    # Send notifications
    await ws_manager.broadcast(
        {
            "type": "delivery.completed",
            "delivery_id": str(delivery_id),
            "order_id": str(delivery.order_id),
            "customer": delivery.order.customer.name,
            "driver": current_user.full_name,
            "timestamp": datetime.utcnow().isoformat(),
        }
    )

    await notification_service.send_notification(
        recipient={
            "user_id": str(delivery.order.customer_id),
            "phone": delivery.order.customer.phone,
            "name": delivery.order.customer.name,
        },
        event_type=NotificationType.DELIVERY_COMPLETED,
        context={
            "order_number": delivery.order.order_number,
            "customer_name": delivery.order.customer.name,
            "driver_name": current_user.full_name,
            "delivered_to": delivery.recipient_name,
        },
    )

    return DeliveryConfirmResponse(
        success=True,
        message="配送確認成功",
        delivery_id=str(delivery_id),
        order_id=str(delivery.order_id),
    )


@router.post("/sync", response_model=DriverSyncResponse)
async def sync_offline_data(
    sync_data: DriverSyncRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> DriverSyncResponse:
    """Sync offline data from driver app"""
    verify_user_role(current_user, ["driver"])

    synced_items = []
    failed_items = []

    # Process location updates
    for location in sync_data.locations:
        try:
            await gps_service.update_driver_location(
                driver_id=current_user.id,
                latitude=location["latitude"],
                longitude=location["longitude"],
                accuracy=location.get("accuracy"),
                speed=location.get("speed"),
                heading=location.get("heading"),
                timestamp=datetime.fromisoformat(location["timestamp"]),
            )
            synced_items.append(
                {"type": "location", "id": location.get("id"), "status": "synced"}
            )
        except Exception as e:
            failed_items.append(
                {"type": "location", "id": location.get("id"), "error": str(e)}
            )

    # Process delivery updates
    for delivery_update in sync_data.deliveries:
        try:
            delivery_id = delivery_update["delivery_id"]

            # Update delivery status
            stmt = (
                select(RouteDelivery)
                .join(Route)
                .where(
                    and_(
                        RouteDelivery.id == delivery_id,
                        Route.driver_id == current_user.id,
                    )
                )
            )
            result = await db.execute(stmt)
            delivery = result.scalar_one_or_none()

            if delivery:
                delivery.status = DeliveryStatus(delivery_update["status"])
                if "notes" in delivery_update:
                    delivery.notes = delivery_update["notes"]
                if "delivered_at" in delivery_update:
                    delivery.delivered_at = datetime.fromisoformat(
                        delivery_update["delivered_at"]
                    )

                # Create history record
                history = DeliveryStatusHistory(
                    delivery_id=delivery.id,
                    status=delivery.status,
                    notes=delivery_update.get("notes", ""),
                    created_by=current_user.id,
                    created_at=datetime.fromisoformat(delivery_update["timestamp"]),
                )
                db.add(history)

                synced_items.append(
                    {"type": "delivery", "id": str(delivery_id), "status": "synced"}
                )
            else:
                failed_items.append(
                    {
                        "type": "delivery",
                        "id": str(delivery_id),
                        "error": "Delivery not found",
                    }
                )

        except Exception as e:
            failed_items.append(
                {
                    "type": "delivery",
                    "id": str(delivery_update.get("delivery_id")),
                    "error": str(e),
                }
            )

    await db.commit()

    # Get updated data to return
    today_routes = await get_today_routes(db, current_user)
    today_stats = await get_today_stats(db, current_user)

    return DriverSyncResponse(
        success=len(failed_items) == 0,
        synced_count=len(synced_items),
        failed_count=len(failed_items),
        synced_items=synced_items,
        failed_items=failed_items,
        updated_routes=today_routes,
        updated_stats=today_stats,
    )


@router.post("/clock - out")
async def clock_out(
    db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """Clock out for the day"""
    verify_user_role(current_user, ["driver"])

    # Calculate working hours and summary
    # This would integrate with a time tracking system

    return {
        "success": True,
        "message": "打卡下班成功",
        "summary": {
            "working_hours": "8小時30分",
            "deliveries_completed": 25,
            "distance_traveled": 86.5,
            "overtime": "30分",
        },
    }
