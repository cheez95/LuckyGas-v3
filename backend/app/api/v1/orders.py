from typing import List, Optional
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_, func
from sqlalchemy.orm import selectinload

from app.api import deps
from app.models.order import Order, OrderStatus, PaymentStatus
from app.models.order_item import OrderItem
from app.models.customer import Customer
from app.models.user import User
from app.models.gas_product import GasProduct
from app.schemas.order import Order as OrderSchema, OrderCreate, OrderUpdate
from app.schemas.order import OrderCreateV2, OrderUpdateV2, OrderV2
from app.schemas.order_item import OrderItemCreate
from app.core.database import get_async_session
from app.api.v1.socketio_handler import notify_order_update
from app.core.cache import cache_result, invalidate_cache, CacheKeys, cache

router = APIRouter()


def generate_order_number() -> str:
    """Generate unique order number with format: ORD-YYYYMMDD-XXXX"""
    today = datetime.now().strftime("%Y%m%d")
    random_suffix = str(datetime.now().microsecond)[:4].zfill(4)
    return f"ORD-{today}-{random_suffix}"


def calculate_order_amount(order_data: dict) -> dict:
    """Calculate order amounts based on cylinder quantities and prices"""
    # Pricing per cylinder type (TWD)
    prices = {
        "50kg": 2500,
        "20kg": 1200,
        "16kg": 1000,
        "10kg": 700,
        "4kg": 350
    }
    
    total = 0
    total += order_data.get("qty_50kg", 0) * prices["50kg"]
    total += order_data.get("qty_20kg", 0) * prices["20kg"]
    total += order_data.get("qty_16kg", 0) * prices["16kg"]
    total += order_data.get("qty_10kg", 0) * prices["10kg"]
    total += order_data.get("qty_4kg", 0) * prices["4kg"]
    
    # Apply discount if any (future feature)
    discount = 0
    
    return {
        "total_amount": total,
        "discount_amount": discount,
        "final_amount": total - discount
    }


@router.get("/", response_model=List[OrderSchema])
@cache_result("orders:list", expire=timedelta(minutes=10))
async def get_orders(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    status: Optional[str] = None,
    customer_id: Optional[int] = None,
    date_from: Optional[datetime] = None,
    date_to: Optional[datetime] = None,
    is_urgent: Optional[bool] = None,
    db: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(deps.get_current_user)
):
    """
    獲取訂單列表
    
    - **skip**: 跳過的記錄數
    - **limit**: 返回的最大記錄數
    - **status**: 訂單狀態篩選
    - **customer_id**: 客戶ID篩選
    - **date_from**: 開始日期
    - **date_to**: 結束日期
    - **is_urgent**: 是否緊急訂單
    """
    # Check permissions
    if current_user.role not in ["super_admin", "manager", "office_staff"]:
        raise HTTPException(status_code=403, detail="權限不足")
    
    # Build query
    query = select(Order).options(selectinload(Order.customer))
    
    # Apply filters
    conditions = []
    if status and status != "all":
        try:
            order_status = OrderStatus(status)
            conditions.append(Order.status == order_status)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"無效的訂單狀態: {status}")
    if customer_id:
        conditions.append(Order.customer_id == customer_id)
    if date_from:
        conditions.append(Order.scheduled_date >= date_from)
    if date_to:
        conditions.append(Order.scheduled_date <= date_to)
    if is_urgent is not None:
        conditions.append(Order.is_urgent == is_urgent)
    
    if conditions:
        query = query.where(and_(*conditions))
    
    # Order by scheduled date descending
    query = query.order_by(Order.scheduled_date.desc())
    
    # Apply pagination
    query = query.offset(skip).limit(limit)
    
    # Execute query
    result = await db.execute(query)
    orders = result.scalars().all()
    
    return orders


@router.get("/{order_id}", response_model=OrderSchema)
@cache_result("order", expire=timedelta(hours=1))
async def get_order(
    order_id: int,
    db: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(deps.get_current_user)
):
    """獲取特定訂單詳情"""
    # Check permissions
    if current_user.role not in ["super_admin", "manager", "office_staff", "driver"]:
        raise HTTPException(status_code=403, detail="權限不足")
    
    # Get order with customer info
    query = select(Order).options(selectinload(Order.customer)).where(Order.id == order_id)
    result = await db.execute(query)
    order = result.scalar_one_or_none()
    
    if not order:
        raise HTTPException(status_code=404, detail="訂單不存在")
    
    # Drivers can only see orders assigned to them
    if current_user.role == "driver" and order.driver_id != current_user.id:
        raise HTTPException(status_code=403, detail="無權查看此訂單")
    
    return order


@router.post("/", response_model=OrderSchema)
@invalidate_cache("orders:list:*")
async def create_order(
    order_create: OrderCreate,
    db: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(deps.get_current_user)
):
    """
    創建新訂單
    """
    # Check permissions
    if current_user.role not in ["super_admin", "manager", "office_staff"]:
        raise HTTPException(status_code=403, detail="權限不足")
    
    # Verify customer exists
    customer_query = select(Customer).where(Customer.id == order_create.customer_id)
    customer_result = await db.execute(customer_query)
    customer = customer_result.scalar_one_or_none()
    
    if not customer:
        raise HTTPException(status_code=404, detail="客戶不存在")
    
    # Create order data
    order_data = order_create.model_dump()
    
    # Generate order number
    order_data["order_number"] = generate_order_number()
    
    # Calculate amounts
    amounts = calculate_order_amount(order_data)
    order_data.update(amounts)
    
    # Use customer's address if not specified
    if not order_data.get("delivery_address"):
        order_data["delivery_address"] = customer.address
    
    # Use customer's delivery time preferences if not specified
    if not order_data.get("delivery_time_start"):
        order_data["delivery_time_start"] = customer.delivery_time_start
    if not order_data.get("delivery_time_end"):
        order_data["delivery_time_end"] = customer.delivery_time_end
    
    # Create order
    order = Order(**order_data)
    db.add(order)
    await db.commit()
    await db.refresh(order)
    
    # Send WebSocket notification
    await notify_order_update(
        order_id=order.id,
        status=order.status.value,
        details={"action": "created", "order_number": order.order_number}
    )
    
    return order


@router.put("/{order_id}", response_model=OrderSchema)
async def update_order(
    order_id: int,
    order_update: OrderUpdate,
    db: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(deps.get_current_user)
):
    """更新訂單"""
    # Check permissions
    if current_user.role not in ["super_admin", "manager", "office_staff"]:
        raise HTTPException(status_code=403, detail="權限不足")
    
    # Get order
    query = select(Order).where(Order.id == order_id)
    result = await db.execute(query)
    order = result.scalar_one_or_none()
    
    if not order:
        raise HTTPException(status_code=404, detail="訂單不存在")
    
    # Check if order can be modified
    if order.status in [OrderStatus.DELIVERED, OrderStatus.CANCELLED]:
        raise HTTPException(status_code=400, detail="已完成或已取消的訂單無法修改")
    
    # Update order fields
    update_data = order_update.model_dump(exclude_unset=True)
    
    # Recalculate amounts if quantities changed
    quantity_fields = ["qty_50kg", "qty_20kg", "qty_16kg", "qty_10kg", "qty_4kg"]
    if any(field in update_data for field in quantity_fields):
        # Merge current quantities with updates
        current_quantities = {
            "qty_50kg": order.qty_50kg,
            "qty_20kg": order.qty_20kg,
            "qty_16kg": order.qty_16kg,
            "qty_10kg": order.qty_10kg,
            "qty_4kg": order.qty_4kg
        }
        current_quantities.update(update_data)
        amounts = calculate_order_amount(current_quantities)
        update_data.update(amounts)
    
    # Update status timestamps
    if "status" in update_data:
        if update_data["status"] == OrderStatus.DELIVERED:
            update_data["delivered_at"] = datetime.utcnow()
    
    # Apply updates
    for field, value in update_data.items():
        setattr(order, field, value)
    
    await db.commit()
    await db.refresh(order)
    
    # Invalidate specific order cache and order list cache
    await cache.invalidate(f"order:update_order:{order_id}:*")
    await cache.invalidate("orders:list:*")
    
    # Send WebSocket notification
    await notify_order_update(
        order_id=order.id,
        status=order.status.value,
        details={"action": "updated", "order_number": order.order_number}
    )
    
    return order


@router.delete("/{order_id}")
async def cancel_order(
    order_id: int,
    reason: Optional[str] = Query(None, description="取消原因"),
    db: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(deps.get_current_user)
):
    """取消訂單"""
    # Check permissions
    if current_user.role not in ["super_admin", "manager", "office_staff"]:
        raise HTTPException(status_code=403, detail="權限不足")
    
    # Get order
    query = select(Order).where(Order.id == order_id)
    result = await db.execute(query)
    order = result.scalar_one_or_none()
    
    if not order:
        raise HTTPException(status_code=404, detail="訂單不存在")
    
    # Check if order can be cancelled
    if order.status == OrderStatus.DELIVERED:
        raise HTTPException(status_code=400, detail="已完成的訂單無法取消")
    
    if order.status == OrderStatus.CANCELLED:
        raise HTTPException(status_code=400, detail="訂單已經取消")
    
    # Cancel order
    order.status = OrderStatus.CANCELLED
    if reason:
        order.delivery_notes = f"取消原因：{reason}"
    
    await db.commit()
    
    # Invalidate specific order cache and order list cache
    await cache.invalidate(f"order:cancel_order:{order_id}:*")
    await cache.invalidate("orders:list:*")
    
    # Send WebSocket notification
    await notify_order_update(
        order_id=order.id,
        status=OrderStatus.CANCELLED.value,
        details={"action": "cancelled", "order_number": order.order_number, "reason": reason or ""}
    )
    
    return {"message": "訂單已成功取消", "order_id": order_id}


# V2 endpoints for flexible product system
@router.post("/v2/", response_model=OrderV2)
async def create_order_v2(
    order_create: OrderCreateV2,
    db: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(deps.get_current_user)
):
    """
    創建新訂單（支援彈性產品系統）
    
    使用新的產品系統，通過 order_items 指定產品和數量
    """
    # Check permissions
    if current_user.role not in ["super_admin", "manager", "office_staff"]:
        raise HTTPException(status_code=403, detail="權限不足")
    
    # Verify customer exists
    customer_query = select(Customer).where(Customer.id == order_create.customer_id)
    customer_result = await db.execute(customer_query)
    customer = customer_result.scalar_one_or_none()
    
    if not customer:
        raise HTTPException(status_code=404, detail="客戶不存在")
    
    # Create order data
    order_data = order_create.model_dump(exclude={'order_items'})
    
    # Generate order number
    order_data["order_number"] = generate_order_number()
    
    # Use customer's address if not specified
    if not order_data.get("delivery_address"):
        order_data["delivery_address"] = customer.address
    
    # Use customer's delivery time preferences if not specified
    if not order_data.get("delivery_time_start"):
        order_data["delivery_time_start"] = customer.delivery_time_start
    if not order_data.get("delivery_time_end"):
        order_data["delivery_time_end"] = customer.delivery_time_end
    
    # Initialize amounts
    order_data["total_amount"] = 0
    order_data["discount_amount"] = 0
    order_data["final_amount"] = 0
    
    # Create order
    order = Order(**order_data)
    db.add(order)
    await db.flush()  # Get order ID without committing
    
    # Create order items and calculate total
    total_amount = 0
    discount_amount = 0
    
    for item_data in order_create.order_items:
        # Verify product exists
        product_query = select(GasProduct).where(GasProduct.id == item_data.gas_product_id)
        product_result = await db.execute(product_query)
        product = product_result.scalar_one_or_none()
        
        if not product:
            raise HTTPException(status_code=404, detail=f"產品ID {item_data.gas_product_id} 不存在")
        
        if not product.is_available:
            raise HTTPException(status_code=400, detail=f"產品 {product.display_name} 目前無法訂購")
        
        # Create order item
        item = OrderItem(
            order_id=order.id,
            gas_product_id=item_data.gas_product_id,
            quantity=item_data.quantity,
            unit_price=item_data.unit_price or product.unit_price,
            discount_percentage=item_data.discount_percentage,
            discount_amount=item_data.discount_amount,
            is_exchange=item_data.is_exchange,
            empty_received=item_data.empty_received,
            is_flow_delivery=item_data.is_flow_delivery,
            meter_reading_start=item_data.meter_reading_start,
            meter_reading_end=item_data.meter_reading_end,
            actual_quantity=item_data.actual_quantity,
            notes=item_data.notes
        )
        
        # Calculate subtotal and final amount
        item.calculate_subtotal()
        item.calculate_final_amount()
        total_amount += item.subtotal
        discount_amount += item.discount_amount
        
        db.add(item)
    
    # Update order amounts
    order.total_amount = total_amount
    order.discount_amount = discount_amount
    order.final_amount = total_amount - discount_amount
    
    await db.commit()
    
    # Load order with items
    query = select(Order).options(
        selectinload(Order.order_items).selectinload(OrderItem.gas_product)
    ).where(Order.id == order.id)
    result = await db.execute(query)
    order = result.scalar_one()
    
    return order


@router.get("/v2/{order_id}", response_model=OrderV2)
async def get_order_v2(
    order_id: int,
    db: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(deps.get_current_user)
):
    """獲取特定訂單詳情（包含彈性產品）"""
    # Check permissions
    if current_user.role not in ["super_admin", "manager", "office_staff", "driver"]:
        raise HTTPException(status_code=403, detail="權限不足")
    
    # Get order with items and products
    query = select(Order).options(
        selectinload(Order.customer),
        selectinload(Order.order_items).selectinload(OrderItem.gas_product)
    ).where(Order.id == order_id)
    result = await db.execute(query)
    order = result.scalar_one_or_none()
    
    if not order:
        raise HTTPException(status_code=404, detail="訂單不存在")
    
    # Drivers can only see orders assigned to them
    if current_user.role == "driver" and order.driver_id != current_user.id:
        raise HTTPException(status_code=403, detail="無權查看此訂單")
    
    # Add customer info to response
    if order.customer:
        order.customer_name = order.customer.name
        order.customer_phone = order.customer.phone
    
    return order


@router.put("/v2/{order_id}", response_model=OrderV2)
async def update_order_v2(
    order_id: int,
    order_update: OrderUpdateV2,
    db: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(deps.get_current_user)
):
    """更新訂單（彈性產品系統）"""
    # Check permissions
    if current_user.role not in ["super_admin", "manager", "office_staff"]:
        raise HTTPException(status_code=403, detail="權限不足")
    
    # Get order
    query = select(Order).options(
        selectinload(Order.order_items).selectinload(OrderItem.gas_product)
    ).where(Order.id == order_id)
    result = await db.execute(query)
    order = result.scalar_one_or_none()
    
    if not order:
        raise HTTPException(status_code=404, detail="訂單不存在")
    
    # Check if order can be modified
    if order.status in [OrderStatus.DELIVERED, OrderStatus.CANCELLED]:
        raise HTTPException(status_code=400, detail="已完成或已取消的訂單無法修改")
    
    # Update order fields
    update_data = order_update.model_dump(exclude_unset=True)
    
    # Update status timestamps
    if "status" in update_data:
        if update_data["status"] == OrderStatus.DELIVERED:
            update_data["delivered_at"] = datetime.utcnow()
    
    # Apply updates
    for field, value in update_data.items():
        setattr(order, field, value)
    
    await db.commit()
    await db.refresh(order)
    
    # Reload with relationships
    query = select(Order).options(
        selectinload(Order.customer),
        selectinload(Order.order_items).selectinload(OrderItem.gas_product)
    ).where(Order.id == order_id)
    result = await db.execute(query)
    order = result.scalar_one()
    
    # Add customer info
    if order.customer:
        order.customer_name = order.customer.name
        order.customer_phone = order.customer.phone
    
    return order


@router.get("/stats/summary")
@cache_result("orders:stats", expire=timedelta(minutes=30))
async def get_order_stats(
    date_from: Optional[datetime] = Query(None, description="開始日期"),
    date_to: Optional[datetime] = Query(None, description="結束日期"),
    db: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(deps.get_current_user)
):
    """獲取訂單統計摘要"""
    # Check permissions
    if current_user.role not in ["super_admin", "manager", "office_staff"]:
        raise HTTPException(status_code=403, detail="權限不足")
    
    # Default date range: last 30 days
    if not date_to:
        date_to = datetime.now()
    if not date_from:
        date_from = date_to - timedelta(days=30)
    
    # Build base query with date filter
    base_conditions = [
        Order.created_at >= date_from,
        Order.created_at <= date_to
    ]
    
    # Count orders by status
    status_counts = {}
    for status in OrderStatus:
        count_query = select(func.count(Order.id)).where(
            and_(*base_conditions, Order.status == status)
        )
        result = await db.execute(count_query)
        status_counts[status.value] = result.scalar()
    
    # Calculate total revenue
    revenue_query = select(
        func.sum(Order.final_amount)
    ).where(
        and_(*base_conditions, Order.status == OrderStatus.DELIVERED)
    )
    revenue_result = await db.execute(revenue_query)
    total_revenue = revenue_result.scalar() or 0
    
    # Count urgent orders
    urgent_query = select(func.count(Order.id)).where(
        and_(*base_conditions, Order.is_urgent == True)
    )
    urgent_result = await db.execute(urgent_query)
    urgent_count = urgent_result.scalar()
    
    # Count unique customers
    customers_query = select(func.count(func.distinct(Order.customer_id))).where(
        and_(*base_conditions)
    )
    customers_result = await db.execute(customers_query)
    unique_customers = customers_result.scalar()
    
    return {
        "date_range": {
            "from": date_from.isoformat(),
            "to": date_to.isoformat()
        },
        "status_summary": status_counts,
        "total_revenue": total_revenue,
        "urgent_orders": urgent_count,
        "unique_customers": unique_customers,
        "total_orders": sum(status_counts.values())
    }