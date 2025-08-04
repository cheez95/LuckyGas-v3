from typing import Optional, List
from datetime import date
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_
from sqlalchemy.orm import joinedload

from app.api.deps import get_db, get_current_user
from app.models import User, DeliveryHistory as DeliveryHistoryModel, Customer
from app.schemas.delivery_history import (
    DeliveryHistory,
    DeliveryHistoryCreate,
    DeliveryHistoryUpdate,
    DeliveryHistoryList,
    DeliveryHistoryStats,
)

router = APIRouter()


@router.get("", response_model=DeliveryHistoryList)
async def get_delivery_history(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    customer_code: Optional[str] = None,
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get delivery history with optional filters"""
    # Build query
    query = select(DeliveryHistoryModel).options(
        joinedload(DeliveryHistoryModel.customer)
    )

    # Apply filters
    filters = []
    if customer_code:
        filters.append(DeliveryHistoryModel.customer_code == customer_code)
    if date_from:
        filters.append(DeliveryHistoryModel.transaction_date >= date_from)
    if date_to:
        filters.append(DeliveryHistoryModel.transaction_date <= date_to)

    if filters:
        query = query.where(and_(*filters))

    # Order by date descending
    query = query.order_by(DeliveryHistoryModel.transaction_date.desc())

    # Get total count
    count_query = select(func.count()).select_from(DeliveryHistoryModel)
    if filters:
        count_query = count_query.where(and_(*filters))

    result = await db.execute(count_query)
    total = result.scalar()

    # Get paginated results
    query = query.offset(skip).limit(limit)
    result = await db.execute(query)
    records = result.scalars().all()

    # Format response
    items = []
    for record in records:
        item = DeliveryHistory.model_validate(record)
        if record.customer:
            item.customer_name = record.customer.short_name
            item.customer_address = record.customer.address
        items.append(item)

    return DeliveryHistoryList(items=items, total=total, skip=skip, limit=limit)


@router.get("/stats", response_model=DeliveryHistoryStats)
async def get_delivery_stats(
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get delivery history statistics"""
    # Build base query
    query = select(DeliveryHistoryModel)

    # Apply date filters
    filters = []
    if date_from:
        filters.append(DeliveryHistoryModel.transaction_date >= date_from)
    if date_to:
        filters.append(DeliveryHistoryModel.transaction_date <= date_to)

    if filters:
        query = query.where(and_(*filters))

    # Get all records for statistics
    result = await db.execute(query)
    records = result.scalars().all()

    # Calculate statistics
    total_deliveries = len(records)
    total_weight_kg = sum(r.total_weight_kg or 0 for r in records)
    total_cylinders = sum(r.total_cylinders or 0 for r in records)
    unique_customers = len(set(r.customer_code for r in records))

    # Cylinders by type
    cylinders_by_type = {
        "50kg": sum(r.qty_50kg for r in records),
        "20kg": sum(r.qty_20kg + r.qty_ying20 for r in records),
        "16kg": sum(r.qty_16kg + r.qty_ying16 + r.qty_haoyun16 for r in records),
        "10kg": sum(r.qty_10kg + r.qty_pingantong10 for r in records),
        "4kg": sum(r.qty_4kg + r.qty_xingfuwan4 for r in records),
        "haoyun20": sum(r.qty_haoyun20 for r in records),
    }

    # Top customers by delivery count
    customer_counts = {}
    for record in records:
        if record.customer_code not in customer_counts:
            customer_counts[record.customer_code] = {
                "customer_code": record.customer_code,
                "deliveries": 0,
                "total_weight": 0,
                "total_cylinders": 0,
            }
        customer_counts[record.customer_code]["deliveries"] += 1
        customer_counts[record.customer_code]["total_weight"] += (
            record.total_weight_kg or 0
        )
        customer_counts[record.customer_code]["total_cylinders"] += (
            record.total_cylinders or 0
        )

    # Get customer names
    if customer_counts:
        customer_codes = list(customer_counts.keys())
        stmt = select(Customer).where(Customer.customer_code.in_(customer_codes))
        result = await db.execute(stmt)
        customers = {c.customer_code: c.short_name for c in result.scalars().all()}

        for code, data in customer_counts.items():
            data["customer_name"] = customers.get(code, code)

    top_customers = sorted(
        customer_counts.values(), key=lambda x: x["deliveries"], reverse=True
    )[:10]

    # Deliveries by date
    deliveries_by_date = {}
    for record in records:
        date_key = record.transaction_date.isoformat()
        if date_key not in deliveries_by_date:
            deliveries_by_date[date_key] = {
                "date": date_key,
                "count": 0,
                "weight": 0,
                "cylinders": 0,
            }
        deliveries_by_date[date_key]["count"] += 1
        deliveries_by_date[date_key]["weight"] += record.total_weight_kg or 0
        deliveries_by_date[date_key]["cylinders"] += record.total_cylinders or 0

    deliveries_by_date_list = sorted(
        deliveries_by_date.values(), key=lambda x: x["date"]
    )

    return DeliveryHistoryStats(
        total_deliveries=total_deliveries,
        total_weight_kg=total_weight_kg,
        total_cylinders=total_cylinders,
        unique_customers=unique_customers,
        date_from=date_from,
        date_to=date_to,
        cylinders_by_type=cylinders_by_type,
        top_customers=top_customers,
        deliveries_by_date=deliveries_by_date_list,
    )


@router.get("/{delivery_id}", response_model=DeliveryHistory)
async def get_delivery(
    delivery_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get a specific delivery history record"""
    stmt = (
        select(DeliveryHistoryModel)
        .options(joinedload(DeliveryHistoryModel.customer))
        .where(DeliveryHistoryModel.id == delivery_id)
    )

    result = await db.execute(stmt)
    delivery = result.scalar_one_or_none()

    if not delivery:
        raise HTTPException(status_code=404, detail="Delivery record not found")

    response = DeliveryHistory.model_validate(delivery)
    if delivery.customer:
        response.customer_name = delivery.customer.short_name
        response.customer_address = delivery.customer.address

    return response


@router.post("", response_model=DeliveryHistory)
async def create_delivery(
    delivery_data: DeliveryHistoryCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Create a new delivery history record"""
    # Find customer
    stmt = select(Customer).where(Customer.customer_code == delivery_data.customer_code)
    result = await db.execute(stmt)
    customer = result.scalar_one_or_none()

    if not customer:
        raise HTTPException(status_code=400, detail="Customer not found")

    # Calculate totals
    total_weight = (
        (delivery_data.qty_50kg * 50)
        + (delivery_data.qty_ying20 * 20)
        + (delivery_data.qty_ying16 * 16)
        + (delivery_data.qty_20kg * 20)
        + (delivery_data.qty_16kg * 16)
        + (delivery_data.qty_10kg * 10)
        + (delivery_data.qty_4kg * 4)
        + (delivery_data.qty_haoyun20 * 20)
        + (delivery_data.qty_haoyun16 * 16)
        + (delivery_data.qty_pingantong10 * 10)
        + (delivery_data.qty_xingfuwan4 * 4)
        + delivery_data.flow_50kg
        + delivery_data.flow_20kg
        + delivery_data.flow_16kg
        + delivery_data.flow_haoyun20kg
        + delivery_data.flow_haoyun16kg
    )

    total_cylinders = sum(
        [
            delivery_data.qty_50kg,
            delivery_data.qty_ying20,
            delivery_data.qty_ying16,
            delivery_data.qty_20kg,
            delivery_data.qty_16kg,
            delivery_data.qty_10kg,
            delivery_data.qty_4kg,
            delivery_data.qty_haoyun20,
            delivery_data.qty_haoyun16,
            delivery_data.qty_pingantong10,
            delivery_data.qty_xingfuwan4,
        ]
    )

    # Create record
    delivery = DeliveryHistoryModel(
        **delivery_data.model_dump(),
        customer_id=customer.id,
        total_weight_kg=total_weight,
        total_cylinders=total_cylinders,
        source_file="Manual Entry",
        source_sheet="API",
    )

    db.add(delivery)
    await db.commit()
    await db.refresh(delivery)

    response = DeliveryHistory.model_validate(delivery)
    response.customer_name = customer.short_name
    response.customer_address = customer.address

    return response


@router.put("/{delivery_id}", response_model=DeliveryHistory)
async def update_delivery(
    delivery_id: int,
    delivery_update: DeliveryHistoryUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Update a delivery history record"""
    # Get existing record
    stmt = select(DeliveryHistoryModel).where(DeliveryHistoryModel.id == delivery_id)
    result = await db.execute(stmt)
    delivery = result.scalar_one_or_none()

    if not delivery:
        raise HTTPException(status_code=404, detail="Delivery record not found")

    # Update fields
    update_data = delivery_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(delivery, field, value)

    # Recalculate totals
    total_weight = (
        (delivery.qty_50kg * 50)
        + (delivery.qty_ying20 * 20)
        + (delivery.qty_ying16 * 16)
        + (delivery.qty_20kg * 20)
        + (delivery.qty_16kg * 16)
        + (delivery.qty_10kg * 10)
        + (delivery.qty_4kg * 4)
        + (delivery.qty_haoyun20 * 20)
        + (delivery.qty_haoyun16 * 16)
        + (delivery.qty_pingantong10 * 10)
        + (delivery.qty_xingfuwan4 * 4)
        + delivery.flow_50kg
        + delivery.flow_20kg
        + delivery.flow_16kg
        + delivery.flow_haoyun20kg
        + delivery.flow_haoyun16kg
    )

    total_cylinders = sum(
        [
            delivery.qty_50kg,
            delivery.qty_ying20,
            delivery.qty_ying16,
            delivery.qty_20kg,
            delivery.qty_16kg,
            delivery.qty_10kg,
            delivery.qty_4kg,
            delivery.qty_haoyun20,
            delivery.qty_haoyun16,
            delivery.qty_pingantong10,
            delivery.qty_xingfuwan4,
        ]
    )

    delivery.total_weight_kg = total_weight
    delivery.total_cylinders = total_cylinders

    await db.commit()
    await db.refresh(delivery)

    # Load customer data
    await db.refresh(delivery, ["customer"])

    response = DeliveryHistory.model_validate(delivery)
    if delivery.customer:
        response.customer_name = delivery.customer.short_name
        response.customer_address = delivery.customer.address

    return response


@router.delete("/{delivery_id}")
async def delete_delivery(
    delivery_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Delete a delivery history record"""
    stmt = select(DeliveryHistoryModel).where(DeliveryHistoryModel.id == delivery_id)
    result = await db.execute(stmt)
    delivery = result.scalar_one_or_none()

    if not delivery:
        raise HTTPException(status_code=404, detail="Delivery record not found")

    await db.delete(delivery)
    await db.commit()

    return {"message": "Delivery record deleted successfully"}
