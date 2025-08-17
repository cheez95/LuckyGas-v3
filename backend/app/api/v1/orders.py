"""
Order management endpoints - Simple implementation
"""
from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session
from typing import Optional, List
from datetime import datetime

from app.core.database import get_db
from app.api.deps import get_current_user

router = APIRouter()

@router.get("")
def get_orders(
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=100),
    status: Optional[str] = None,
    customer_id: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Get all orders with pagination"""
    # Mock data for now
    orders = []
    for i in range(5):
        orders.append({
            "id": i + 1,
            "order_number": f"ORD-2025-{1000 + i}",
            "customer_id": 1,
            "customer_name": "Test Customer",
            "status": "pending",
            "total_amount": 1500.00,
            "created_at": datetime.now().isoformat()
        })
    
    return {
        "orders": orders,
        "total": 5,
        "skip": skip,
        "limit": limit
    }

@router.get("/stats/summary/")
def get_order_statistics(
    date_from: Optional[str] = Query(None),
    date_to: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Get order statistics"""
    return {
        "total_orders": 150,
        "pending": 25,
        "in_progress": 10,
        "completed": 100,
        "cancelled": 15,
        "today": 8,
        "this_week": 45,
        "this_month": 150,
        "revenue_today": 12500.00,
        "revenue_week": 87500.00,
        "revenue_month": 375000.00
    }

@router.get("/search/")
def search_orders(
    q: str = Query(..., min_length=1),
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Search orders by customer name or order number"""
    # Mock search results
    orders = []
    for i in range(3):
        orders.append({
            "id": i + 1,
            "order_number": f"ORD-2025-{1000 + i}",
            "customer_id": 1,
            "customer_name": f"Customer matching '{q}'",
            "status": "pending",
            "total_amount": 1500.00,
            "created_at": datetime.now().isoformat()
        })
    
    return {
        "orders": orders,
        "total": 3,
        "query": q
    }

@router.get("/{order_id}")
def get_order(
    order_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Get specific order by ID"""
    return {
        "id": order_id,
        "order_number": f"ORD-2025-{1000 + order_id}",
        "customer_id": 1,
        "customer_name": "Test Customer",
        "customer_phone": "0912-345-678",
        "delivery_address": "台北市中正區重慶南路一段122號",
        "status": "pending",
        "items": [
            {
                "product": "20kg 瓦斯桶",
                "quantity": 2,
                "unit_price": 750.00,
                "subtotal": 1500.00
            }
        ],
        "total_amount": 1500.00,
        "created_at": datetime.now().isoformat(),
        "scheduled_date": datetime.now().isoformat()
    }

@router.post("")
def create_order(
    order_data: dict,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Create new order"""
    return {
        "id": 999,
        "order_number": "ORD-2025-1999",
        "status": "pending",
        "message": "訂單已建立"
    }

@router.put("/{order_id}")
def update_order(
    order_id: int,
    order_data: dict,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Update order"""
    return {
        "id": order_id,
        "status": "updated",
        "message": "訂單已更新"
    }

@router.delete("/{order_id}")
def cancel_order(
    order_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Cancel order"""
    return {
        "id": order_id,
        "status": "cancelled",
        "message": "訂單已取消"
    }