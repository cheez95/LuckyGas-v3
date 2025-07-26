from typing import List, Optional
from datetime import datetime, timedelta
import time
from fastapi import APIRouter, Depends, HTTPException, Query, Body
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_, func, text
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
from app.schemas.credit import CreditSummary, CreditCheckResult
from app.schemas.order_search import OrderSearchCriteria, OrderSearchResult
from app.core.database import get_async_session
from app.api.v1.socketio_handler import notify_order_update
from app.core.cache import cache_result, invalidate_cache, CacheKeys, cache
from app.services.order_service import OrderService
from app.services.credit_service import CreditService

router = APIRouter()




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
    
    # Initialize service
    order_service = OrderService(db)
    
    # For date range filtering, we'll need to handle this differently
    # Currently the service only filters by single scheduled_date
    # So we'll use direct database access for now
    
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
    
    # Initialize service
    order_service = OrderService(db)
    
    # Get order using repository method with details
    order = await order_service.order_repo.get_with_details(order_id)
    
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
    
    # Initialize service
    order_service = OrderService(db)
    
    try:
        # Create order using service with credit checking
        order = await order_service.create_order(
            order_data=order_create,
            created_by=current_user.id,
            skip_credit_check=False,
            created_by_role=current_user.role
        )
        
        return order
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


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
    
    # Initialize service
    order_service = OrderService(db)
    
    try:
        # Update order using service
        order = await order_service.update_order(
            order_id=order_id,
            order_update=order_update,
            updated_by=current_user.id
        )
        
        if not order:
            raise HTTPException(status_code=404, detail="訂單不存在")
        
        # Invalidate specific order cache and order list cache
        await cache.invalidate(f"order:update_order:{order_id}:*")
        await cache.invalidate("orders:list:*")
        
        return order
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


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
    
    # Initialize service
    order_service = OrderService(db)
    
    try:
        # Update order status to cancelled using service
        order = await order_service.update_delivery_status(
            order_id=order_id,
            status=OrderStatus.CANCELLED.value,
            notes=f"取消原因：{reason}" if reason else None,
            updated_by=current_user.id
        )
        
        if not order:
            raise HTTPException(status_code=404, detail="訂單不存在")
        
        # Invalidate specific order cache and order list cache
        await cache.invalidate(f"order:cancel_order:{order_id}:*")
        await cache.invalidate("orders:list:*")
        
        # Send real-time notification
        await notify_order_update(
            order_id=order_id,
            status="cancelled",
            details={
                "order_number": order.order_number,
                "customer_id": order.customer_id,
                "cancelled_by": current_user.username,
                "reason": reason or "未提供原因",
                "cancelled_at": datetime.utcnow().isoformat()
            }
        )
        
        return {"message": "訂單已成功取消", "order_id": order_id}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


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
    from datetime import datetime
    timestamp = datetime.now()
    order_data["order_number"] = f"ORD-{timestamp.strftime('%Y%m%d')}-{timestamp.microsecond:06d}"
    
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
    
    # Send real-time notification
    await notify_order_update(
        order_id=order.id,
        status="created",
        details={
            "order_number": order.order_number,
            "customer_id": order.customer_id,
            "customer_name": customer.name,
            "total_amount": float(order.final_amount),
            "scheduled_date": order.scheduled_date.isoformat() if order.scheduled_date else None,
            "created_by": current_user.username
        }
    )
    
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
    
    # Store original status for notification
    original_status = order.status.value
    
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
    
    # Send real-time notification
    await notify_order_update(
        order_id=order.id,
        status=order.status.value,
        details={
            "order_number": order.order_number,
            "customer_id": order.customer_id,
            "customer_name": order.customer.name,
            "previous_status": original_status,
            "new_status": order.status.value,
            "updated_by": current_user.username,
            "delivered_at": order.delivered_at.isoformat() if order.delivered_at else None
        }
    )
    
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
    
    # Initialize service
    order_service = OrderService(db)
    
    # Get statistics using service
    stats = await order_service.get_order_statistics(
        start_date=date_from.date(),
        end_date=date_to.date(),
        area=None
    )
    
    # Convert status breakdown to expected format
    status_counts = stats.get("status_breakdown", {})
    
    # Count urgent orders (not available in service, need direct query)
    urgent_query = select(func.count(Order.id)).where(
        and_(
            Order.scheduled_date >= date_from.date(),
            Order.scheduled_date <= date_to.date(),
            Order.is_urgent == True
        )
    )
    urgent_result = await db.execute(urgent_query)
    urgent_count = urgent_result.scalar() or 0
    
    # Count unique customers (not available in service, need direct query)
    customers_query = select(func.count(func.distinct(Order.customer_id))).where(
        and_(
            Order.scheduled_date >= date_from.date(),
            Order.scheduled_date <= date_to.date()
        )
    )
    customers_result = await db.execute(customers_query)
    unique_customers = customers_result.scalar() or 0
    
    return {
        "date_range": {
            "from": date_from.isoformat(),
            "to": date_to.isoformat()
        },
        "status_summary": status_counts,
        "total_revenue": stats.get("total_revenue", 0),
        "urgent_orders": urgent_count,
        "unique_customers": unique_customers,
        "total_orders": stats.get("total_orders", 0)
    }


@router.post("/search", response_model=OrderSearchResult)
async def search_orders(
    criteria: OrderSearchCriteria = Body(...),
    db: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(deps.get_current_user)
):
    """
    訂單進階搜尋
    
    支援:
    - 全文搜尋 (訂單號、客戶名稱、地址、備註)
    - 日期範圍篩選
    - 多選篩選器 (狀態、優先級、付款狀態等)
    - 金額範圍篩選
    - 地區與客戶類型篩選
    """
    start_time = time.time()
    
    # Base query with joins
    query = select(Order).options(
        selectinload(Order.customer),
        selectinload(Order.order_items).selectinload(OrderItem.gas_product)
    )
    
    conditions = []
    
    # Full-text search
    if criteria.keyword:
        keyword_conditions = or_(
            Order.order_number.ilike(f"%{criteria.keyword}%"),
            Order.delivery_notes.ilike(f"%{criteria.keyword}%"),
            Customer.name.ilike(f"%{criteria.keyword}%"),
            Customer.phone.ilike(f"%{criteria.keyword}%"),
            Customer.address.ilike(f"%{criteria.keyword}%")
        )
        conditions.append(keyword_conditions)
    
    # Date range filter
    if criteria.date_from:
        conditions.append(Order.order_date >= criteria.date_from)
    if criteria.date_to:
        conditions.append(Order.order_date <= criteria.date_to)
    
    # Status filters
    if criteria.status:
        conditions.append(Order.status.in_(criteria.status))
    
    # Priority filters
    if criteria.priority:
        priority_conditions = []
        for priority in criteria.priority:
            if priority == "urgent":
                priority_conditions.append(Order.is_urgent == True)
            elif priority == "scheduled":
                priority_conditions.append(Order.scheduled_date.isnot(None))
            elif priority == "normal":
                priority_conditions.append(
                    and_(Order.is_urgent == False, Order.scheduled_date.is_(None))
                )
        if priority_conditions:
            conditions.append(or_(*priority_conditions))
    
    # Payment filters
    if criteria.payment_status:
        conditions.append(Order.payment_status.in_(criteria.payment_status))
    if criteria.payment_method:
        conditions.append(Order.payment_method.in_(criteria.payment_method))
    
    # Customer and driver filters
    if criteria.customer_id:
        conditions.append(Order.customer_id == criteria.customer_id)
    if criteria.driver_id:
        conditions.append(Order.driver_id == criteria.driver_id)
    
    # Amount range filters
    if criteria.min_amount is not None:
        conditions.append(Order.final_amount >= criteria.min_amount)
    if criteria.max_amount is not None:
        conditions.append(Order.final_amount <= criteria.max_amount)
    
    # Join with customer table if needed
    if criteria.keyword or criteria.region or criteria.customer_type:
        query = query.join(Customer, Order.customer_id == Customer.id)
    
    # Region filter
    if criteria.region:
        # Assuming region is stored in customer address or a separate field
        region_map = {
            "north": ["北區", "北部"],
            "south": ["南區", "南部"],
            "east": ["東區", "東部"],
            "west": ["西區", "西部"],
            "central": ["中區", "中部"]
        }
        region_keywords = region_map.get(criteria.region, [])
        if region_keywords:
            region_conditions = [Customer.address.ilike(f"%{kw}%") for kw in region_keywords]
            conditions.append(or_(*region_conditions))
    
    # Customer type filter
    if criteria.customer_type:
        # Assuming customer_type is a field in Customer model
        # If not, we can use tags or other classification
        conditions.append(Customer.customer_type == criteria.customer_type)
    
    # Cylinder type filter
    if criteria.cylinder_type:
        # Need to join with order items and gas products
        query = query.join(OrderItem, Order.id == OrderItem.order_id)
        query = query.join(GasProduct, OrderItem.gas_product_id == GasProduct.id)
        
        cylinder_conditions = []
        for cylinder in criteria.cylinder_type:
            cylinder_conditions.append(GasProduct.display_name.ilike(f"%{cylinder}%"))
        if cylinder_conditions:
            conditions.append(or_(*cylinder_conditions))
    
    # Apply all conditions
    if conditions:
        query = query.where(and_(*conditions))
    
    # Get total count
    count_query = select(func.count()).select_from(Order)
    if conditions:
        # Need to re-apply joins for count query
        if criteria.keyword or criteria.region or criteria.customer_type:
            count_query = count_query.join(Customer, Order.customer_id == Customer.id)
        if criteria.cylinder_type:
            count_query = count_query.join(OrderItem, Order.id == OrderItem.order_id)
            count_query = count_query.join(GasProduct, OrderItem.gas_product_id == GasProduct.id)
        count_query = count_query.where(and_(*conditions))
    
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0
    
    # Apply pagination and ordering
    query = query.order_by(Order.created_at.desc())
    query = query.offset(criteria.skip).limit(criteria.limit)
    
    # Execute query
    result = await db.execute(query)
    orders = result.scalars().unique().all()
    
    # Convert to dict format
    order_dicts = []
    for order in orders:
        order_dict = {
            "id": order.id,
            "order_number": order.order_number,
            "customer_id": order.customer_id,
            "customer_name": order.customer.name if order.customer else None,
            "customer_phone": order.customer.phone if order.customer else None,
            "customer_address": order.customer.address if order.customer else None,
            "order_date": order.order_date.isoformat() if order.order_date else None,
            "scheduled_date": order.scheduled_date.isoformat() if order.scheduled_date else None,
            "status": order.status,
            "payment_status": order.payment_status,
            "payment_method": order.payment_method,
            "total_amount": float(order.total_amount) if order.total_amount else 0,
            "final_amount": float(order.final_amount) if order.final_amount else 0,
            "is_urgent": order.is_urgent,
            "delivery_notes": order.delivery_notes,
            "driver_id": order.driver_id,
            "created_at": order.created_at.isoformat() if order.created_at else None,
            "items": [
                {
                    "product_name": item.gas_product.display_name if item.gas_product else None,
                    "quantity": item.quantity,
                    "unit_price": float(item.unit_price) if item.unit_price else 0,
                    "subtotal": float(item.subtotal) if item.subtotal else 0
                }
                for item in order.order_items
            ] if hasattr(order, 'order_items') else []
        }
        order_dicts.append(order_dict)
    
    # Calculate search time
    search_time = (time.time() - start_time) * 1000  # Convert to milliseconds
    
    return OrderSearchResult(
        orders=order_dicts,
        total=total,
        skip=criteria.skip,
        limit=criteria.limit,
        search_time=search_time
    )


@router.get("/credit/{customer_id}", response_model=CreditSummary)
async def get_customer_credit_summary(
    customer_id: int,
    db: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(deps.get_current_user)
):
    """
    獲取客戶信用額度摘要
    
    - **customer_id**: 客戶ID
    """
    # Check permissions
    if current_user.role not in ["super_admin", "manager", "office_staff"]:
        raise HTTPException(status_code=403, detail="權限不足")
    
    # Get credit summary
    summary = await CreditService.get_credit_summary(db, customer_id)
    
    if not summary:
        raise HTTPException(status_code=404, detail="客戶不存在")
    
    return summary


@router.post("/credit/check", response_model=CreditCheckResult)
async def check_credit_limit(
    customer_id: int = Query(..., description="客戶ID"),
    order_amount: float = Query(..., description="訂單金額"),
    db: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(deps.get_current_user)
):
    """
    檢查客戶信用額度是否足夠
    
    - **customer_id**: 客戶ID
    - **order_amount**: 訂單金額
    """
    # Check permissions
    if current_user.role not in ["super_admin", "manager", "office_staff"]:
        raise HTTPException(status_code=403, detail="權限不足")
    
    # Check credit limit
    result = await CreditService.check_credit_limit(
        db=db,
        customer_id=customer_id,
        order_amount=order_amount,
        skip_check=current_user.role == "super_admin"
    )
    
    # Convert to response model
    return CreditCheckResult(
        approved=result["approved"],
        reason=result["reason"],
        credit_limit=result["details"].get("credit_limit", 0),
        current_balance=result["details"].get("current_balance", 0),
        available_credit=result["details"].get("available_credit", 0),
        requested_amount=result["details"].get("requested_amount", order_amount),
        exceeds_by=result["details"].get("exceeds_by"),
        is_blocked=result["details"].get("is_blocked", False)
    )


@router.post("/credit/{customer_id}/block")
async def block_customer_credit(
    customer_id: int,
    reason: str = Query(..., description="封鎖原因"),
    db: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(deps.get_current_user)
):
    """
    封鎖客戶信用額度
    
    - **customer_id**: 客戶ID
    - **reason**: 封鎖原因
    """
    # Check permissions - only managers and super admin
    if current_user.role not in ["super_admin", "manager"]:
        raise HTTPException(status_code=403, detail="只有經理以上權限才能封鎖信用額度")
    
    # Block credit
    success = await CreditService.block_customer_credit(db, customer_id, reason)
    
    if not success:
        raise HTTPException(status_code=404, detail="客戶不存在")
    
    return {"message": "客戶信用額度已封鎖", "customer_id": customer_id}


@router.post("/credit/{customer_id}/unblock")
async def unblock_customer_credit(
    customer_id: int,
    reason: str = Query(..., description="解除封鎖原因"),
    db: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(deps.get_current_user)
):
    """
    解除封鎖客戶信用額度
    
    - **customer_id**: 客戶ID
    - **reason**: 解除封鎖原因
    """
    # Check permissions - only managers and super admin
    if current_user.role not in ["super_admin", "manager"]:
        raise HTTPException(status_code=403, detail="只有經理以上權限才能解除信用額度封鎖")
    
    # Unblock credit
    success = await CreditService.unblock_customer_credit(db, customer_id, reason)
    
    if not success:
        raise HTTPException(status_code=404, detail="客戶不存在")
    
    return {"message": "客戶信用額度封鎖已解除", "customer_id": customer_id}