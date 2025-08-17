"""
Simplified Customer API endpoints - Direct ORM, no service layers
"""
from typing import List, Optional
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, and_

from app.core.database import get_db
from app.models import Customer, Order, Delivery, CustomerType
from app.schemas.customer import (
    CustomerCreate, CustomerUpdate, CustomerResponse,
    CustomerDeliveryHistory
)
from app.api.deps import get_current_user, require_role
from app.core.cache import cache_result

router = APIRouter()


@router.get("/", response_model=List[CustomerResponse])
def get_customers(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    customer_type: Optional[CustomerType] = None,
    area: Optional[str] = None,
    is_active: bool = True,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """
    Get all customers with optional filtering
    Simple, direct query - no unnecessary abstractions
    """
    query = db.query(Customer)
    
    # Apply filters
    if customer_type:
        query = query.filter(Customer.customer_type == customer_type)
    if area:
        query = query.filter(Customer.area == area)
    query = query.filter(Customer.is_active == is_active)
    
    # Pagination
    customers = query.offset(skip).limit(limit).all()
    return customers


@router.get("/search/")
def search_customers(
    q: str = Query(..., min_length=1),
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Search customers by name, phone, or address"""
    # Mock search results for now
    customers = []
    for i in range(3):
        customers.append({
            "id": i + 1,
            "customer_code": f"C{1000 + i}",
            "name": f"Customer matching '{q}'",
            "phone": f"091{i}-345-678",
            "address": f"台北市中正區路{i+1}號",
            "customer_type": "commercial",
            "is_active": True,
            "created_at": datetime.now().isoformat()
        })
    
    return {
        "customers": customers,
        "total": 3,
        "query": q
    }


@router.get("/{customer_id}", response_model=CustomerResponse)
@cache_result(ttl_seconds=300)  # Cache for 5 minutes
def get_customer(
    customer_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """
    Get single customer by ID
    Cached because customer info doesn't change often
    """
    customer = db.query(Customer).filter(Customer.id == customer_id).first()
    if not customer:
        raise HTTPException(status_code=404, detail="客戶不存在")
    return customer


@router.get("/{customer_id}/deliveries", response_model=CustomerDeliveryHistory)
def get_customer_deliveries(
    customer_id: int,
    days: int = Query(30, ge=1, le=365),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """
    Get customer delivery history
    This is the CRITICAL query - must be fast!
    Uses index: idx_delivery_customer_date
    """
    # Check customer exists
    customer = db.query(Customer).filter(Customer.id == customer_id).first()
    if not customer:
        raise HTTPException(status_code=404, detail="客戶不存在")
    
    # Calculate date range
    end_date = datetime.now().date()
    start_date = end_date - timedelta(days=days)
    
    # Query deliveries - USES INDEX!
    deliveries_query = db.query(Delivery).filter(
        and_(
            Delivery.customer_id == customer_id,
            Delivery.delivery_date >= start_date,
            Delivery.delivery_date <= end_date
        )
    ).order_by(Delivery.delivery_date.desc())
    
    # Get total count for pagination
    total_count = deliveries_query.count()
    
    # Apply pagination
    deliveries = deliveries_query.offset(skip).limit(limit).all()
    
    # Calculate summary stats
    summary_stats = db.query(
        func.count(Delivery.id).label('total_deliveries'),
        func.sum(Order.total_amount).label('total_amount')
    ).select_from(Delivery).join(
        Order, Delivery.order_id == Order.id
    ).filter(
        and_(
            Delivery.customer_id == customer_id,
            Delivery.delivery_date >= start_date,
            Delivery.status == 'delivered'
        )
    ).first()
    
    return {
        "customer": customer,
        "deliveries": deliveries,
        "total_count": total_count,
        "summary": {
            "total_deliveries": summary_stats.total_deliveries or 0,
            "total_amount": summary_stats.total_amount or 0.0,
            "date_range": {
                "start": start_date,
                "end": end_date
            }
        }
    }


@router.post("/", response_model=CustomerResponse)
def create_customer(
    customer: CustomerCreate,
    db: Session = Depends(get_db),
    current_user = Depends(require_role(["admin", "manager", "staff"]))
):
    """
    Create new customer
    Simple direct creation - no service layer needed
    """
    # Check if customer code already exists
    existing = db.query(Customer).filter(Customer.code == customer.code).first()
    if existing:
        raise HTTPException(status_code=400, detail="客戶代碼已存在")
    
    # Create customer
    db_customer = Customer(**customer.dict())
    db.add(db_customer)
    db.commit()
    db.refresh(db_customer)
    
    return db_customer


@router.put("/{customer_id}", response_model=CustomerResponse)
def update_customer(
    customer_id: int,
    customer: CustomerUpdate,
    db: Session = Depends(get_db),
    current_user = Depends(require_role(["admin", "manager", "staff"]))
):
    """
    Update customer information
    Direct update - no unnecessary complexity
    """
    db_customer = db.query(Customer).filter(Customer.id == customer_id).first()
    if not db_customer:
        raise HTTPException(status_code=404, detail="客戶不存在")
    
    # Update fields
    update_data = customer.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_customer, field, value)
    
    db_customer.updated_at = datetime.now()
    db.commit()
    db.refresh(db_customer)
    
    return db_customer


@router.delete("/{customer_id}")
def delete_customer(
    customer_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(require_role(["admin"]))
):
    """
    Soft delete customer (set is_active = False)
    We never actually delete data
    """
    db_customer = db.query(Customer).filter(Customer.id == customer_id).first()
    if not db_customer:
        raise HTTPException(status_code=404, detail="客戶不存在")
    
    # Soft delete
    db_customer.is_active = False
    db_customer.updated_at = datetime.now()
    db.commit()
    
    return {"message": "客戶已停用"}


@router.get("/stats/summary")
@cache_result(ttl_seconds=600)  # Cache for 10 minutes
def get_customer_stats(
    db: Session = Depends(get_db),
    current_user = Depends(require_role(["admin", "manager"]))
):
    """
    Get customer statistics summary
    Cached because stats don't change frequently
    """
    stats = db.query(
        func.count(Customer.id).label('total_customers'),
        func.count(Customer.id).filter(Customer.is_active == True).label('active_customers'),
        func.count(Customer.id).filter(Customer.customer_type == CustomerType.RESTAURANT).label('restaurants'),
        func.count(Customer.id).filter(Customer.customer_type == CustomerType.RESIDENTIAL).label('residential'),
        func.count(Customer.id).filter(Customer.customer_type == CustomerType.COMMERCIAL).label('commercial'),
        func.count(Customer.id).filter(Customer.customer_type == CustomerType.INDUSTRIAL).label('industrial')
    ).first()
    
    return {
        "total_customers": stats.total_customers,
        "active_customers": stats.active_customers,
        "by_type": {
            "restaurant": stats.restaurants,
            "residential": stats.residential,
            "commercial": stats.commercial,
            "industrial": stats.industrial
        }
    }