"""
Simplified Dashboard endpoints for the Lucky Gas system.
Provides summary statistics and real-time data for the dashboard.
"""

from datetime import datetime, timedelta, date
from typing import Dict, Any, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, or_, text

from app.core.database import get_db
from app.models import Order, Customer, Driver, OrderStatus, UserRole, User
from app.api.v1.auth import get_current_user

router = APIRouter()

@router.get("/health")
def dashboard_health():
    """Check dashboard service health"""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "service": "dashboard",
        "version": "2.0.0"
    }

@router.get("/summary")
def get_dashboard_summary(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Get comprehensive dashboard summary including:
    - Today's statistics
    - Routes in progress
    - AI predictions
    - Recent activities
    """
    
    # Get today's date
    today = date.today()
    today_start = datetime.combine(today, datetime.min.time())
    today_end = datetime.combine(today, datetime.max.time())
    
    # Calculate today's orders
    today_orders = db.query(func.count(Order.id)).filter(
        and_(
            Order.created_at >= today_start,
            Order.created_at <= today_end
        )
    ).scalar() or 0
    
    # Calculate today's revenue (simplified calculation)
    today_revenue = 0
    try:
        today_orders_list = db.query(Order).filter(
            and_(
                Order.created_at >= today_start,
                Order.created_at <= today_end,
                Order.status.in_([OrderStatus.DELIVERED, OrderStatus.COMPLETED])
            )
        ).all()
        
        for order in today_orders_list:
            if order.total_amount:
                today_revenue += float(order.total_amount)
    except:
        today_revenue = 0
    
    # Get active customers (all customers for now)
    active_customers = db.query(func.count(Customer.id)).scalar() or 0
    
    # Get drivers on route
    drivers_on_route = db.query(func.count(Driver.id)).filter(
        and_(
            Driver.is_active == True,
            Driver.is_available == False  # Drivers on route are not available
        )
    ).scalar() or 0
    
    # Get recent deliveries count
    seven_days_ago = datetime.utcnow() - timedelta(days=7)
    recent_deliveries = db.query(func.count(Order.id)).filter(
        and_(
            Order.updated_at >= seven_days_ago,
            Order.status == OrderStatus.DELIVERED
        )
    ).scalar() or 0
    
    # Get urgent orders (orders pending or confirmed)
    urgent_orders = db.query(func.count(Order.id)).filter(
        Order.status.in_([OrderStatus.PENDING, OrderStatus.CONFIRMED])
    ).scalar() or 0
    
    # Calculate completion rate
    if today_orders > 0:
        delivered_today = db.query(func.count(Order.id)).filter(
            and_(
                Order.created_at >= today_start,
                Order.created_at <= today_end,
                Order.status == OrderStatus.DELIVERED
            )
        ).scalar() or 0
        completion_rate = (delivered_today / today_orders) * 100
    else:
        completion_rate = 0
    
    # Get route progress (mock data for now)
    routes = [
        {
            "id": 1,
            "routeNumber": "R001",
            "status": "進行中",
            "totalOrders": 15,
            "completedOrders": 8,
            "driverName": "陳大明",
            "progressPercentage": 53
        },
        {
            "id": 2,
            "routeNumber": "R002",
            "status": "進行中",
            "totalOrders": 12,
            "completedOrders": 10,
            "driverName": "李小華",
            "progressPercentage": 83
        },
        {
            "id": 3,
            "routeNumber": "R003",
            "status": "準備中",
            "totalOrders": 8,
            "completedOrders": 0,
            "driverName": "王小明",
            "progressPercentage": 0
        }
    ]
    
    # Generate predictions (mock data)
    predictions = {
        "total": 125,
        "urgent": 15,
        "confidence": 85,
        "peakHours": ["09:00-11:00", "14:00-16:00"],
        "recommendedDrivers": 5
    }
    
    # Get recent activities (simplified)
    activities = []
    recent_orders = db.query(Order).order_by(Order.created_at.desc()).limit(5).all()
    for order in recent_orders:
        customer = db.query(Customer).filter(Customer.id == order.customer_id).first()
        activities.append({
            "id": f"order-{order.id}",
            "type": "order",
            "message": f"新訂單來自 {customer.name if customer else '未知客戶'}",
            "timestamp": order.created_at.isoformat() if order.created_at else datetime.utcnow().isoformat(),
            "status": "info"
        })
    
    # Add some mock activities if not enough orders
    if len(activities) < 5:
        mock_activities = [
            {
                "id": "route-1",
                "type": "route",
                "message": "路線 R001 開始配送",
                "timestamp": (datetime.utcnow() - timedelta(minutes=30)).isoformat(),
                "status": "success"
            },
            {
                "id": "delivery-1",
                "type": "delivery",
                "message": "訂單 #1234 已送達",
                "timestamp": (datetime.utcnow() - timedelta(minutes=45)).isoformat(),
                "status": "success"
            },
            {
                "id": "prediction-1",
                "type": "prediction",
                "message": "預測明日需求量增加 15%",
                "timestamp": (datetime.utcnow() - timedelta(hours=1)).isoformat(),
                "status": "warning"
            }
        ]
        activities.extend(mock_activities[:5-len(activities)])
    
    # Return comprehensive dashboard data
    return {
        "stats": {
            "todayOrders": today_orders,
            "todayRevenue": round(today_revenue, 2),
            "activeCustomers": active_customers,
            "driversOnRoute": drivers_on_route,
            "recentDeliveries": recent_deliveries,
            "urgentOrders": urgent_orders,
            "completionRate": round(completion_rate, 1)
        },
        "routes": routes,
        "predictions": predictions,
        "activities": activities,
        "lastUpdated": datetime.utcnow().isoformat()
    }

@router.get("/metrics")
def get_dashboard_metrics(
    period: str = Query("today", description="Period for metrics: today, week, month"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """Get detailed metrics for dashboard charts"""
    
    # Determine date range based on period
    if period == "today":
        start_date = datetime.combine(date.today(), datetime.min.time())
        end_date = datetime.utcnow()
    elif period == "week":
        start_date = datetime.utcnow() - timedelta(days=7)
        end_date = datetime.utcnow()
    elif period == "month":
        start_date = datetime.utcnow() - timedelta(days=30)
        end_date = datetime.utcnow()
    else:
        start_date = datetime.combine(date.today(), datetime.min.time())
        end_date = datetime.utcnow()
    
    # Get order trends (simplified)
    order_trends = {
        "pending": 10,
        "confirmed": 15,
        "delivered": 45,
        "cancelled": 5
    }
    
    # Get revenue trend (mock data for now)
    revenue_trend = []
    current = start_date
    while current <= end_date:
        revenue_trend.append({
            "date": current.date().isoformat(),
            "revenue": 5000 + (current.day * 100)  # Mock data
        })
        current += timedelta(days=1)
    
    return {
        "period": period,
        "orderTrends": order_trends,
        "revenueTrend": revenue_trend,
        "startDate": start_date.isoformat(),
        "endDate": end_date.isoformat()
    }