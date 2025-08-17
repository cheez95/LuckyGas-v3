"""
Simplified Routes API endpoints for Lucky Gas system
Sync version - no async complications
"""
from typing import List, Optional
from datetime import datetime, date
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.api.deps import get_current_user

router = APIRouter()


@router.get("/")
def get_routes(
    date: Optional[date] = Query(None, description="Filter by date"),
    status: Optional[str] = Query(None, description="Filter by status"),
    driver_id: Optional[int] = Query(None, description="Filter by driver"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """
    Get all routes with optional filtering
    Returns mock data for now
    """
    # Return mock data for now
    return {
        "routes": [
            {
                "id": 1,
                "route_number": "R001",
                "status": "進行中",
                "totalOrders": 15,
                "completedOrders": 8,
                "driverName": "陳大明",
                "driver_id": 1,
                "progressPercentage": 53,
                "date": str(date or datetime.now().date()),
                "area": "信義區"
            },
            {
                "id": 2,
                "route_number": "R002",
                "status": "進行中",
                "totalOrders": 12,
                "completedOrders": 10,
                "driverName": "李小華",
                "driver_id": 2,
                "progressPercentage": 83,
                "date": str(date or datetime.now().date()),
                "area": "大安區"
            },
            {
                "id": 3,
                "route_number": "R003",
                "status": "準備中",
                "totalOrders": 8,
                "completedOrders": 0,
                "driverName": "王小明",
                "driver_id": 3,
                "progressPercentage": 0,
                "date": str(date or datetime.now().date()),
                "area": "松山區"
            }
        ],
        "total": 3
    }


@router.get("/optimize")
def optimize_routes(
    date: date = Query(..., description="Date to optimize routes for"),
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """
    Optimize routes for a specific date
    """
    return {
        "success": True,
        "message": "路線優化成功",
        "optimized_routes": [
            {
                "id": 1,
                "route_number": "R001-OPT",
                "orders": 15,
                "estimatedTime": 240,
                "estimatedDistance": 45.5,
                "driverName": "陳大明"
            },
            {
                "id": 2,
                "route_number": "R002-OPT",
                "orders": 12,
                "estimatedTime": 180,
                "estimatedDistance": 32.3,
                "driverName": "李小華"
            }
        ]
    }


@router.get("/{route_id}")
def get_route_detail(
    route_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """
    Get detailed information about a specific route
    """
    return {
        "id": route_id,
        "route_number": f"R{route_id:03d}",
        "status": "進行中",
        "driverName": "陳大明",
        "driver_id": 1,
        "vehicleNumber": "ABC-123",
        "startTime": "09:00",
        "area": "信義區",
        "orders": [
            {
                "id": 1,
                "orderNumber": "ORD-20250116-001",
                "customerName": "幸福餐廳",
                "address": "台北市信義區信義路五段7號",
                "status": "已完成",
                "deliveryTime": "09:30",
                "cylinders": {"50kg": 2, "20kg": 1}
            },
            {
                "id": 2,
                "orderNumber": "ORD-20250116-002",
                "customerName": "大同工廠",
                "address": "台北市大同區重慶北路三段",
                "status": "配送中",
                "deliveryTime": None,
                "cylinders": {"50kg": 3}
            }
        ],
        "totalOrders": 15,
        "completedOrders": 8,
        "estimatedCompletionTime": "14:30",
        "actualDistance": 25.3,
        "estimatedDistance": 45.5
    }


@router.post("/{route_id}/complete")
def complete_route(
    route_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """
    Mark a route as completed
    """
    return {
        "success": True,
        "message": f"路線 R{route_id:03d} 已標記為完成",
        "route": {
            "id": route_id,
            "status": "已完成",
            "completedAt": datetime.now().isoformat()
        }
    }


@router.put("/{route_id}/status")
def update_route_status(
    route_id: int,
    status: str,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """
    Update the status of a route
    Valid statuses: draft, assigned, in_progress, completed, cancelled
    """
    valid_statuses = ["draft", "assigned", "in_progress", "completed", "cancelled"]
    
    if status not in valid_statuses:
        raise HTTPException(
            status_code=400,
            detail=f"無效的狀態。有效狀態為: {', '.join(valid_statuses)}"
        )
    
    return {
        "success": True,
        "message": "路線狀態已更新",
        "route_id": route_id,
        "status": status,
        "updated_at": datetime.now().isoformat()
    }


@router.post("/publish")
def publish_routes(
    route_ids: List[int],
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """
    Publish routes to drivers (send notifications)
    """
    published_count = len(route_ids)
    
    return {
        "success": True,
        "message": f"已成功發布 {published_count} 條路線",
        "published_routes": route_ids,
        "published_at": datetime.now().isoformat()
    }


@router.get("/analytics/performance")
def get_route_performance_analytics(
    start_date: Optional[date] = Query(None, description="Start date"),
    end_date: Optional[date] = Query(None, description="End date"),
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """
    Get route performance analytics
    """
    return {
        "period": {
            "start": str(start_date or datetime.now().date()),
            "end": str(end_date or datetime.now().date())
        },
        "metrics": {
            "total_routes": 150,
            "avg_optimization_score": 82.5,
            "avg_distance_per_route": 65.3,
            "avg_time_per_route": 240,
            "on_time_delivery_rate": 0.92,
            "fuel_efficiency": 8.5
        },
        "trends": {
            "optimization_improvement": 5.2,
            "distance_reduction": -8.3,
            "time_reduction": -12.5
        },
        "driver_performance": [
            {
                "driver_id": 1,
                "driver_name": "陳大明",
                "routes_completed": 28,
                "avg_optimization_score": 85.0,
                "on_time_rate": 0.96
            },
            {
                "driver_id": 2,
                "driver_name": "李小華",
                "routes_completed": 25,
                "avg_optimization_score": 82.0,
                "on_time_rate": 0.92
            }
        ]
    }