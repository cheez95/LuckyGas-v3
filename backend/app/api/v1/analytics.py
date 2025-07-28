"""Analytics API endpoints for executive and operations dashboards."""
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
from fastapi import APIRouter, Depends, Query, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, or_, case
from sqlalchemy.ext.asyncio import AsyncSession
from redis import asyncio as aioredis
import json

from app.api.deps import get_current_user, get_db
from app.core.cache import get_redis_client
from app.models import Order, Customer, Route, DeliveryHistory, Payment, Invoice
from app.models.user import User
from app.models.order import OrderStatus
from app.models.route import RouteStatus
from app.services.analytics_service import AnalyticsService

router = APIRouter()

# Cache TTL in seconds
CACHE_TTL = 300  # 5 minutes for dashboard data
REALTIME_CACHE_TTL = 30  # 30 seconds for real-time metrics


@router.get("/executive")
async def get_executive_dashboard(
    start_date: Optional[datetime] = Query(None),
    end_date: Optional[datetime] = Query(None),
    db: AsyncSession = Depends(get_db),
    redis: aioredis.Redis = Depends(get_redis_client),
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """Get executive dashboard metrics."""
    # Check permissions
    if current_user.role not in ["super_admin", "manager"]:
        raise HTTPException(status_code=403, detail="沒有權限查看此數據")
    
    # Default date range (last 30 days)
    if not end_date:
        end_date = datetime.now()
    if not start_date:
        start_date = end_date - timedelta(days=30)
    
    # Check cache
    cache_key = f"executive_dashboard:{start_date.date()}:{end_date.date()}"
    cached_data = await redis.get(cache_key)
    if cached_data:
        return json.loads(cached_data)
    
    # Initialize analytics service
    analytics = AnalyticsService(db)
    
    # Fetch all metrics
    metrics = {
        "revenue": await analytics.get_revenue_metrics(start_date, end_date),
        "orders": await analytics.get_order_metrics(start_date, end_date),
        "customers": await analytics.get_customer_metrics(start_date, end_date),
        "cashFlow": await analytics.get_cash_flow_metrics(start_date, end_date),
        "performance": await analytics.get_performance_comparison(start_date, end_date),
        "topMetrics": await analytics.get_top_performing_metrics(start_date, end_date)
    }
    
    # Cache the results
    await redis.setex(cache_key, CACHE_TTL, json.dumps(metrics))
    
    return metrics


@router.get("/operations")
async def get_operations_dashboard(
    date: Optional[datetime] = Query(None),
    db: AsyncSession = Depends(get_db),
    redis: aioredis.Redis = Depends(get_redis_client),
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """Get operations dashboard metrics."""
    # Check permissions
    if current_user.role not in ["super_admin", "manager", "office_staff"]:
        raise HTTPException(status_code=403, detail="沒有權限查看此數據")
    
    # Default to today
    if not date:
        date = datetime.now()
    
    # Check cache for real-time data
    cache_key = f"operations_dashboard:{date.date()}"
    cached_data = await redis.get(cache_key)
    if cached_data:
        return json.loads(cached_data)
    
    # Initialize analytics service
    analytics = AnalyticsService(db)
    
    # Fetch operational metrics
    metrics = {
        "realTimeOrders": await analytics.get_realtime_order_status(date),
        "driverUtilization": await analytics.get_driver_utilization(date),
        "routeEfficiency": await analytics.get_route_efficiency_metrics(date),
        "deliveryMetrics": await analytics.get_delivery_success_metrics(date),
        "inventory": await analytics.get_equipment_inventory_status(),
        "alerts": await analytics.get_operational_alerts()
    }
    
    # Cache with shorter TTL for real-time data
    await redis.setex(cache_key, REALTIME_CACHE_TTL, json.dumps(metrics))
    
    return metrics


@router.get("/financial")
async def get_financial_dashboard(
    start_date: Optional[datetime] = Query(None),
    end_date: Optional[datetime] = Query(None),
    db: AsyncSession = Depends(get_db),
    redis: aioredis.Redis = Depends(get_redis_client),
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """Get financial dashboard metrics."""
    # Check permissions
    if current_user.role not in ["super_admin", "manager"]:
        raise HTTPException(status_code=403, detail="沒有權限查看此數據")
    
    # Default date range (current month)
    if not end_date:
        end_date = datetime.now()
    if not start_date:
        start_date = datetime(end_date.year, end_date.month, 1)
    
    # Check cache
    cache_key = f"financial_dashboard:{start_date.date()}:{end_date.date()}"
    cached_data = await redis.get(cache_key)
    if cached_data:
        return json.loads(cached_data)
    
    # Initialize analytics service
    analytics = AnalyticsService(db)
    
    # Fetch financial metrics
    metrics = {
        "receivables": await analytics.get_accounts_receivable_aging(),
        "collections": await analytics.get_payment_collection_metrics(start_date, end_date),
        "outstandingInvoices": await analytics.get_outstanding_invoices(),
        "revenueBySegment": await analytics.get_revenue_by_segment(start_date, end_date),
        "profitMargins": await analytics.get_profit_margin_analysis(start_date, end_date),
        "cashPosition": await analytics.get_cash_position_trend(start_date, end_date)
    }
    
    # Cache the results
    await redis.setex(cache_key, CACHE_TTL, json.dumps(metrics))
    
    return metrics


@router.get("/performance")
async def get_performance_analytics(
    time_range: str = Query("24h", regex="^(1h|6h|24h|7d|30d)$"),
    db: AsyncSession = Depends(get_db),
    redis: aioredis.Redis = Depends(get_redis_client),
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """Get system performance analytics."""
    # Check permissions
    if current_user.role != "super_admin":
        raise HTTPException(status_code=403, detail="沒有權限查看此數據")
    
    # Check cache
    cache_key = f"performance_analytics:{time_range}"
    cached_data = await redis.get(cache_key)
    if cached_data:
        return json.loads(cached_data)
    
    # Initialize analytics service
    analytics = AnalyticsService(db)
    
    # Parse time range
    time_delta = {
        "1h": timedelta(hours=1),
        "6h": timedelta(hours=6),
        "24h": timedelta(days=1),
        "7d": timedelta(days=7),
        "30d": timedelta(days=30)
    }[time_range]
    
    start_time = datetime.now() - time_delta
    
    # Fetch performance metrics
    metrics = {
        "systemMetrics": await analytics.get_system_performance_metrics(start_time),
        "apiUsage": await analytics.get_api_usage_statistics(start_time),
        "errorAnalysis": await analytics.get_error_rate_analysis(start_time),
        "userActivity": await analytics.get_user_activity_metrics(start_time),
        "resourceUtilization": await analytics.get_resource_utilization(start_time)
    }
    
    # Cache with appropriate TTL
    cache_ttl = REALTIME_CACHE_TTL if time_range in ["1h", "6h"] else CACHE_TTL
    await redis.setex(cache_key, cache_ttl, json.dumps(metrics))
    
    return metrics


@router.post("/export")
async def export_report(
    report_type: str = Query(..., regex="^(executive|operations|financial|performance)$"),
    format: str = Query(..., regex="^(pdf|excel|csv)$"),
    start_date: Optional[datetime] = Query(None),
    end_date: Optional[datetime] = Query(None),
    email: Optional[str] = Query(None),
    background_tasks: BackgroundTasks = BackgroundTasks(),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> Dict[str, str]:
    """Export analytics report in specified format."""
    # Check permissions
    if current_user.role not in ["super_admin", "manager"]:
        raise HTTPException(status_code=403, detail="沒有權限查看此數據")
    
    # Default date range
    if not end_date:
        end_date = datetime.now()
    if not start_date:
        start_date = end_date - timedelta(days=30)
    
    # Initialize analytics service
    analytics = AnalyticsService(db)
    
    # Generate report in background
    if email:
        background_tasks.add_task(
            analytics.generate_and_email_report,
            report_type=report_type,
            format=format,
            start_date=start_date,
            end_date=end_date,
            email=email,
            user_id=current_user.id
        )
        return {"message": f"報表將會寄送至 {email}"}
    else:
        # Generate report immediately
        report_url = await analytics.generate_report(
            report_type=report_type,
            format=format,
            start_date=start_date,
            end_date=end_date,
            user_id=current_user.id
        )
        return {"url": report_url}


@router.get("/realtime/orders")
async def get_realtime_orders(
    db: AsyncSession = Depends(get_db),
    redis: aioredis.Redis = Depends(get_redis_client),
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """Get real-time order updates for WebSocket fallback."""
    # Check permissions
    if current_user.role not in ["super_admin", "manager", "office_staff"]:
        raise HTTPException(status_code=403, detail="沒有權限查看此數據")
    
    # Get from Redis pub/sub or recent cache
    cache_key = "realtime:orders:latest"
    cached_data = await redis.get(cache_key)
    
    if cached_data:
        return json.loads(cached_data)
    
    # Fallback to database query
    analytics = AnalyticsService(db)
    data = await analytics.get_latest_order_updates()
    
    # Cache briefly
    await redis.setex(cache_key, 5, json.dumps(data))
    
    return data


@router.get("/custom")
async def get_custom_analytics(
    metrics: List[str] = Query(...),
    start_date: datetime = Query(...),
    end_date: datetime = Query(...),
    group_by: Optional[str] = Query(None),
    filters: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """Get custom analytics based on selected metrics."""
    # Check permissions
    if current_user.role not in ["super_admin", "manager"]:
        raise HTTPException(status_code=403, detail="沒有權限查看此數據")
    
    # Validate metrics
    allowed_metrics = [
        "revenue", "orders", "customers", "deliveries",
        "payments", "inventory", "routes", "drivers"
    ]
    
    invalid_metrics = [m for m in metrics if m not in allowed_metrics]
    if invalid_metrics:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid metrics: {', '.join(invalid_metrics)}"
        )
    
    # Parse filters
    filter_dict = {}
    if filters:
        try:
            filter_dict = json.loads(filters)
        except json.JSONDecodeError:
            raise HTTPException(status_code=400, detail="Invalid filter format")
    
    # Initialize analytics service
    analytics = AnalyticsService(db)
    
    # Fetch custom metrics
    result = await analytics.get_custom_metrics(
        metrics=metrics,
        start_date=start_date,
        end_date=end_date,
        group_by=group_by,
        filters=filter_dict
    )
    
    return result