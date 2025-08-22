"""
Synchronous Delivery History API endpoints
Compatible with the synchronous database setup
"""
from datetime import date
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import and_, func, text

from app.core.database import get_db
from app.models import Customer, User
from app.api.deps import get_current_user

router = APIRouter()


@router.get("")
def get_delivery_history(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    customer_code: Optional[str] = Query(None),
    date_from: Optional[date] = Query(None),
    date_to: Optional[date] = Query(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """Get delivery history with optional filters"""
    
    # For now, return empty data structure to fix 404
    # Will be populated when data is imported
    return {
        "items": [],
        "total": 0,
        "skip": skip,
        "limit": limit
    }


@router.get("/stats")
def get_delivery_stats(
    date_from: Optional[date] = Query(None),
    date_to: Optional[date] = Query(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """Get delivery history statistics"""
    
    # Return default stats structure
    return {
        "total_deliveries": 0,
        "total_weight_kg": 0,
        "total_cylinders": 0,
        "unique_customers": 0,
        "date_from": date_from,
        "date_to": date_to,
        "cylinders_by_type": {
            "50kg": 0,
            "20kg": 0,
            "16kg": 0,
            "10kg": 0,
            "4kg": 0,
        },
        "top_customers": [],
        "deliveries_by_date": []
    }