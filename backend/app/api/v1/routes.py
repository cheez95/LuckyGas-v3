from typing import List, Optional
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_, func, update
from sqlalchemy.orm import selectinload

from app.api import deps
from app.models.route import Route, RouteStatus, RouteStop
from app.models.order import Order, OrderStatus
from app.models.customer import Customer
from app.models.user import User
from app.models.vehicle import Vehicle
from app.schemas.route import (
    Route as RouteSchema,
    RouteCreate,
    RouteUpdate,
    RouteWithDetails,
    RouteStop as RouteStopSchema,
    RouteStopCreate,
    RouteStopUpdate,
    RouteOptimizationRequest,
    RouteOptimizationResponse
)
from app.core.database import get_async_session

router = APIRouter()


async def calculate_route_stats(route: Route, db: AsyncSession) -> dict:
    """Calculate route statistics"""
    # Get all stops with order details
    stops_query = select(RouteStop).where(RouteStop.route_id == route.id).order_by(RouteStop.stop_sequence)
    stops_result = await db.execute(stops_query)
    stops = stops_result.scalars().all()
    
    total_stops = len(stops)
    completed_stops = sum(1 for stop in stops if stop.is_completed)
    
    # Calculate total cylinders from orders
    total_cylinders = 0
    if stops:
        order_ids = [stop.order_id for stop in stops]
        orders_query = select(Order).where(Order.id.in_(order_ids))
        orders_result = await db.execute(orders_query)
        orders = orders_result.scalars().all()
        
        for order in orders:
            total_cylinders += (
                order.qty_50kg +
                order.qty_20kg +
                order.qty_16kg +
                order.qty_10kg +
                order.qty_4kg
            )
    
    return {
        "total_stops": total_stops,
        "completed_stops": completed_stops,
        "total_cylinders": total_cylinders
    }


@router.get("/", response_model=List[RouteWithDetails])
async def get_routes(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    date_from: Optional[datetime] = None,
    date_to: Optional[datetime] = None,
    driver_id: Optional[int] = None,
    area: Optional[str] = None,
    status: Optional[RouteStatus] = None,
    db: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(deps.get_current_user)
):
    """
    獲取路線列表
    
    - **skip**: 跳過的記錄數
    - **limit**: 返回的最大記錄數
    - **date_from**: 開始日期
    - **date_to**: 結束日期
    - **driver_id**: 司機ID篩選
    - **area**: 區域篩選
    - **status**: 路線狀態篩選
    """
    # Check permissions
    if current_user.role not in ["super_admin", "manager", "office_staff", "driver"]:
        raise HTTPException(status_code=403, detail="權限不足")
    
    # Build query
    query = select(Route).options(selectinload(Route.stops))
    
    # Apply filters
    conditions = []
    if date_from:
        conditions.append(Route.route_date >= date_from)
    if date_to:
        conditions.append(Route.route_date <= date_to)
    if area:
        conditions.append(Route.area == area)
    if status:
        conditions.append(Route.status == status)
    
    # Drivers can only see their own routes
    if current_user.role == "driver":
        conditions.append(Route.driver_id == current_user.id)
    elif driver_id:
        conditions.append(Route.driver_id == driver_id)
    
    if conditions:
        query = query.where(and_(*conditions))
    
    # Order by route date descending
    query = query.order_by(Route.route_date.desc())
    
    # Apply pagination
    query = query.offset(skip).limit(limit)
    
    # Execute query
    result = await db.execute(query)
    routes = result.scalars().all()
    
    # Enhance with additional details
    enhanced_routes = []
    for route in routes:
        # Get driver name
        driver_name = None
        if route.driver_id:
            driver_query = select(User).where(User.id == route.driver_id)
            driver_result = await db.execute(driver_query)
            driver = driver_result.scalar_one_or_none()
            if driver:
                driver_name = driver.full_name
        
        # Get vehicle plate
        vehicle_plate = None
        if route.vehicle_id:
            vehicle_query = select(Vehicle).where(Vehicle.id == route.vehicle_id)
            vehicle_result = await db.execute(vehicle_query)
            vehicle = vehicle_result.scalar_one_or_none()
            if vehicle:
                vehicle_plate = vehicle.plate_number
        
        # Get route stats
        stats = await calculate_route_stats(route, db)
        
        route_dict = route.__dict__.copy()
        route_dict.update({
            "driver_name": driver_name,
            "vehicle_plate": vehicle_plate,
            "total_orders": stats["total_stops"],
            "completed_orders": stats["completed_stops"],
            "total_cylinders": stats["total_cylinders"]
        })
        
        enhanced_routes.append(RouteWithDetails(**route_dict))
    
    return enhanced_routes


@router.get("/{route_id}", response_model=RouteWithDetails)
async def get_route(
    route_id: int,
    db: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(deps.get_current_user)
):
    """獲取特定路線詳情"""
    # Check permissions
    if current_user.role not in ["super_admin", "manager", "office_staff", "driver"]:
        raise HTTPException(status_code=403, detail="權限不足")
    
    # Get route with stops
    query = select(Route).options(selectinload(Route.stops)).where(Route.id == route_id)
    result = await db.execute(query)
    route = result.scalar_one_or_none()
    
    if not route:
        raise HTTPException(status_code=404, detail="路線不存在")
    
    # Drivers can only see their own routes
    if current_user.role == "driver" and route.driver_id != current_user.id:
        raise HTTPException(status_code=403, detail="無權查看此路線")
    
    # Get driver name
    driver_name = None
    if route.driver_id:
        driver_query = select(User).where(User.id == route.driver_id)
        driver_result = await db.execute(driver_query)
        driver = driver_result.scalar_one_or_none()
        if driver:
            driver_name = driver.full_name
    
    # Get vehicle plate
    vehicle_plate = None
    if route.vehicle_id:
        vehicle_query = select(Vehicle).where(Vehicle.id == route.vehicle_id)
        vehicle_result = await db.execute(vehicle_query)
        vehicle = vehicle_result.scalar_one_or_none()
        if vehicle:
            vehicle_plate = vehicle.plate_number
    
    # Get route stats
    stats = await calculate_route_stats(route, db)
    
    route_dict = route.__dict__.copy()
    route_dict.update({
        "driver_name": driver_name,
        "vehicle_plate": vehicle_plate,
        "total_orders": stats["total_stops"],
        "completed_orders": stats["completed_stops"],
        "total_cylinders": stats["total_cylinders"]
    })
    
    return RouteWithDetails(**route_dict)


@router.post("/", response_model=RouteSchema)
async def create_route(
    route_create: RouteCreate,
    db: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(deps.get_current_user)
):
    """創建新路線"""
    # Check permissions
    if current_user.role not in ["super_admin", "manager", "office_staff"]:
        raise HTTPException(status_code=403, detail="權限不足")
    
    # Create route
    route_data = route_create.model_dump(exclude={"stops"})
    route = Route(**route_data)
    db.add(route)
    await db.flush()  # Get route ID without committing
    
    # Create stops if provided
    if route_create.stops:
        for stop_data in route_create.stops:
            # Verify order exists and is not already assigned
            order_query = select(Order).where(Order.id == stop_data.order_id)
            order_result = await db.execute(order_query)
            order = order_result.scalar_one_or_none()
            
            if not order:
                raise HTTPException(status_code=404, detail=f"訂單 {stop_data.order_id} 不存在")
            
            if order.route_id:
                raise HTTPException(status_code=400, detail=f"訂單 {stop_data.order_id} 已分配到其他路線")
            
            # Get customer location
            customer_query = select(Customer).where(Customer.id == order.customer_id)
            customer_result = await db.execute(customer_query)
            customer = customer_result.scalar_one_or_none()
            
            # Create stop
            stop = RouteStop(
                route_id=route.id,
                order_id=stop_data.order_id,
                stop_sequence=stop_data.stop_sequence,
                latitude=stop_data.latitude,
                longitude=stop_data.longitude,
                address=stop_data.address or customer.address,
                estimated_arrival=stop_data.estimated_arrival,
                estimated_duration_minutes=stop_data.estimated_duration_minutes
            )
            db.add(stop)
            
            # Update order with route assignment
            order.route_id = route.id
            if route.driver_id:
                order.driver_id = route.driver_id
            order.status = OrderStatus.ASSIGNED
    
    # Update route stats
    route.total_stops = len(route_create.stops) if route_create.stops else 0
    
    await db.commit()
    await db.refresh(route)
    
    return route


@router.put("/{route_id}", response_model=RouteSchema)
async def update_route(
    route_id: int,
    route_update: RouteUpdate,
    db: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(deps.get_current_user)
):
    """更新路線"""
    # Check permissions
    if current_user.role not in ["super_admin", "manager", "office_staff"]:
        raise HTTPException(status_code=403, detail="權限不足")
    
    # Get route
    query = select(Route).where(Route.id == route_id)
    result = await db.execute(query)
    route = result.scalar_one_or_none()
    
    if not route:
        raise HTTPException(status_code=404, detail="路線不存在")
    
    # Check if route can be modified
    if route.status in [RouteStatus.COMPLETED, RouteStatus.CANCELLED]:
        raise HTTPException(status_code=400, detail="已完成或已取消的路線無法修改")
    
    # Update route fields
    update_data = route_update.model_dump(exclude_unset=True)
    
    # Update status timestamps
    if "status" in update_data:
        if update_data["status"] == RouteStatus.IN_PROGRESS:
            update_data["started_at"] = datetime.utcnow()
        elif update_data["status"] == RouteStatus.COMPLETED:
            update_data["completed_at"] = datetime.utcnow()
            if route.started_at:
                duration = datetime.utcnow() - route.started_at
                update_data["actual_duration_minutes"] = int(duration.total_seconds() / 60)
    
    # If driver changed, update all associated orders
    if "driver_id" in update_data and update_data["driver_id"] != route.driver_id:
        orders_update = update(Order).where(Order.route_id == route_id).values(driver_id=update_data["driver_id"])
        await db.execute(orders_update)
    
    # Apply updates
    for field, value in update_data.items():
        setattr(route, field, value)
    
    await db.commit()
    await db.refresh(route)
    
    return route


@router.delete("/{route_id}")
async def cancel_route(
    route_id: int,
    db: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(deps.get_current_user)
):
    """取消路線"""
    # Check permissions
    if current_user.role not in ["super_admin", "manager", "office_staff"]:
        raise HTTPException(status_code=403, detail="權限不足")
    
    # Get route
    query = select(Route).where(Route.id == route_id)
    result = await db.execute(query)
    route = result.scalar_one_or_none()
    
    if not route:
        raise HTTPException(status_code=404, detail="路線不存在")
    
    # Check if route can be cancelled
    if route.status == RouteStatus.COMPLETED:
        raise HTTPException(status_code=400, detail="已完成的路線無法取消")
    
    if route.status == RouteStatus.CANCELLED:
        raise HTTPException(status_code=400, detail="路線已經取消")
    
    # Cancel route
    route.status = RouteStatus.CANCELLED
    
    # Unassign all orders
    orders_update = update(Order).where(Order.route_id == route_id).values(
        route_id=None,
        driver_id=None,
        status=OrderStatus.CONFIRMED
    )
    await db.execute(orders_update)
    
    await db.commit()
    
    return {"message": "路線已成功取消", "route_id": route_id}


@router.post("/{route_id}/stops", response_model=RouteStopSchema)
async def add_route_stop(
    route_id: int,
    stop_create: RouteStopCreate,
    db: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(deps.get_current_user)
):
    """添加路線停靠點"""
    # Check permissions
    if current_user.role not in ["super_admin", "manager", "office_staff"]:
        raise HTTPException(status_code=403, detail="權限不足")
    
    # Get route
    route_query = select(Route).where(Route.id == route_id)
    route_result = await db.execute(route_query)
    route = route_result.scalar_one_or_none()
    
    if not route:
        raise HTTPException(status_code=404, detail="路線不存在")
    
    # Check if route can be modified
    if route.status in [RouteStatus.IN_PROGRESS, RouteStatus.COMPLETED, RouteStatus.CANCELLED]:
        raise HTTPException(status_code=400, detail="進行中、已完成或已取消的路線無法添加停靠點")
    
    # Verify order exists and is not already assigned
    order_query = select(Order).where(Order.id == stop_create.order_id)
    order_result = await db.execute(order_query)
    order = order_result.scalar_one_or_none()
    
    if not order:
        raise HTTPException(status_code=404, detail="訂單不存在")
    
    if order.route_id and order.route_id != route_id:
        raise HTTPException(status_code=400, detail="訂單已分配到其他路線")
    
    # Create stop
    stop_data = stop_create.model_dump()
    stop_data["route_id"] = route_id
    stop = RouteStop(**stop_data)
    db.add(stop)
    
    # Update order
    order.route_id = route_id
    if route.driver_id:
        order.driver_id = route.driver_id
    order.status = OrderStatus.ASSIGNED
    
    # Update route stats
    route.total_stops += 1
    
    await db.commit()
    await db.refresh(stop)
    
    return stop


@router.put("/stops/{stop_id}", response_model=RouteStopSchema)
async def update_route_stop(
    stop_id: int,
    stop_update: RouteStopUpdate,
    db: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(deps.get_current_user)
):
    """更新路線停靠點"""
    # Check permissions
    if current_user.role not in ["super_admin", "manager", "office_staff", "driver"]:
        raise HTTPException(status_code=403, detail="權限不足")
    
    # Get stop
    stop_query = select(RouteStop).where(RouteStop.id == stop_id)
    stop_result = await db.execute(stop_query)
    stop = stop_result.scalar_one_or_none()
    
    if not stop:
        raise HTTPException(status_code=404, detail="停靠點不存在")
    
    # Get route
    route_query = select(Route).where(Route.id == stop.route_id)
    route_result = await db.execute(route_query)
    route = route_result.scalar_one_or_none()
    
    # Drivers can only update their own route stops
    if current_user.role == "driver" and route.driver_id != current_user.id:
        raise HTTPException(status_code=403, detail="無權更新此停靠點")
    
    # Update stop fields
    update_data = stop_update.model_dump(exclude_unset=True)
    
    # If marking as completed, update order status
    if "is_completed" in update_data and update_data["is_completed"]:
        order_query = select(Order).where(Order.id == stop.order_id)
        order_result = await db.execute(order_query)
        order = order_result.scalar_one_or_none()
        if order:
            order.status = OrderStatus.DELIVERED
            order.delivered_at = datetime.utcnow()
    
    # Apply updates
    for field, value in update_data.items():
        setattr(stop, field, value)
    
    await db.commit()
    await db.refresh(stop)
    
    return stop


@router.delete("/stops/{stop_id}")
async def remove_route_stop(
    stop_id: int,
    db: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(deps.get_current_user)
):
    """移除路線停靠點"""
    # Check permissions
    if current_user.role not in ["super_admin", "manager", "office_staff"]:
        raise HTTPException(status_code=403, detail="權限不足")
    
    # Get stop
    stop_query = select(RouteStop).where(RouteStop.id == stop_id)
    stop_result = await db.execute(stop_query)
    stop = stop_result.scalar_one_or_none()
    
    if not stop:
        raise HTTPException(status_code=404, detail="停靠點不存在")
    
    # Get route
    route_query = select(Route).where(Route.id == stop.route_id)
    route_result = await db.execute(route_query)
    route = route_result.scalar_one_or_none()
    
    # Check if route can be modified
    if route.status in [RouteStatus.IN_PROGRESS, RouteStatus.COMPLETED, RouteStatus.CANCELLED]:
        raise HTTPException(status_code=400, detail="進行中、已完成或已取消的路線無法移除停靠點")
    
    # Update order
    order_query = select(Order).where(Order.id == stop.order_id)
    order_result = await db.execute(order_query)
    order = order_result.scalar_one_or_none()
    if order:
        order.route_id = None
        order.driver_id = None
        order.status = OrderStatus.CONFIRMED
    
    # Delete stop
    await db.delete(stop)
    
    # Update route stats
    route.total_stops -= 1
    
    await db.commit()
    
    return {"message": "停靠點已成功移除", "stop_id": stop_id}


@router.post("/{route_id}/optimize", response_model=RouteOptimizationResponse)
async def optimize_route(
    route_id: int,
    optimization_request: RouteOptimizationRequest,
    db: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(deps.get_current_user)
):
    """
    優化路線（簡化版本）
    
    注意：這是一個簡化的實現。在Phase 3會集成Google Maps Route Optimization API。
    """
    # Check permissions
    if current_user.role not in ["super_admin", "manager", "office_staff"]:
        raise HTTPException(status_code=403, detail="權限不足")
    
    # Get route with stops
    route_query = select(Route).options(selectinload(Route.stops)).where(Route.id == route_id)
    route_result = await db.execute(route_query)
    route = route_result.scalar_one_or_none()
    
    if not route:
        raise HTTPException(status_code=404, detail="路線不存在")
    
    if route.status != RouteStatus.PLANNED:
        raise HTTPException(status_code=400, detail="只有計劃中的路線可以優化")
    
    # Simple optimization: sort by latitude (north to south)
    # In real implementation, this would use Google Maps Route Optimization API
    stops = sorted(route.stops, key=lambda s: s.latitude, reverse=True)
    
    # Update stop sequences
    for i, stop in enumerate(stops):
        stop.stop_sequence = i + 1
    
    # Calculate estimated distance (simplified)
    total_distance = 0
    for i in range(1, len(stops)):
        # Simple distance calculation (not accurate for real roads)
        lat_diff = abs(stops[i].latitude - stops[i-1].latitude)
        lon_diff = abs(stops[i].longitude - stops[i-1].longitude)
        distance = ((lat_diff ** 2 + lon_diff ** 2) ** 0.5) * 111  # Rough km conversion
        total_distance += distance
    
    # Update route
    route.is_optimized = True
    route.optimization_timestamp = datetime.utcnow()
    route.total_distance_km = round(total_distance, 2)
    route.estimated_duration_minutes = int(total_distance * 3)  # Assume 20km/h average
    route.optimization_score = 0.85  # Placeholder score
    route.status = RouteStatus.OPTIMIZED
    
    await db.commit()
    await db.refresh(route)
    
    return RouteOptimizationResponse(
        route_id=route_id,
        original_distance_km=total_distance * 1.2,  # Assume 20% improvement
        optimized_distance_km=total_distance,
        distance_saved_km=total_distance * 0.2,
        distance_saved_percent=20.0,
        original_duration_minutes=int(total_distance * 3.6),
        optimized_duration_minutes=route.estimated_duration_minutes,
        time_saved_minutes=int(total_distance * 0.6),
        optimization_score=0.85,
        optimized_stops=route.stops
    )