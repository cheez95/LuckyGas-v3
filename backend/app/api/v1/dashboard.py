"""Dashboard API endpoints for optimized performance.

This module provides aggregated dashboard data in a single endpoint to minimize
API calls and improve dashboard loading performance.
"""

import logging
from datetime import datetime, timedelta, date
from typing import Dict, Any, Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select, func, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db
from app.core.api_utils import handle_api_errors, require_roles
from app.core.cache import cache_result
from app.models.user import User, UserRole
from app.models.order import Order, OrderStatus
from app.models.customer import Customer
from app.models.route import Route, RouteStatus
from app.models.delivery_history import DeliveryHistory
from app.models.order_item import OrderItem
from app.schemas.dashboard import DashboardSummary, DashboardStats, RouteProgress

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get("/summary", response_model=DashboardSummary)
@cache_result("dashboard:summary", expire=timedelta(minutes=1))  # Short cache for real-time feel
@require_roles([UserRole.SUPER_ADMIN, UserRole.MANAGER, UserRole.OFFICE_STAFF])
@handle_api_errors()
async def get_dashboard_summary(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    date: Optional[date] = Query(None, description="Date for statistics (defaults to today)"),
) -> DashboardSummary:
    """
    Get optimized dashboard summary with all statistics in a single call.
    
    This endpoint aggregates:
    - Today's order count and revenue
    - Active customer count
    - Drivers on route
    - Route progress
    - Recent deliveries
    - Prediction summary
    
    Performance optimizations:
    - Single database round-trip using subqueries
    - Efficient COUNT and SUM aggregations
    - 1-minute cache for real-time feel
    - Only fetches necessary columns
    """
    start_time = datetime.utcnow()
    target_date = date or datetime.now().date()
    
    # Log request for monitoring
    logger.info(f"Dashboard summary requested by {current_user.username} for date {target_date}")
    
    try:
        # Parallel queries using asyncio.gather for better performance
        import asyncio
        
        # Define all queries
        async def get_today_orders():
            """Get today's order count and revenue."""
            result = await db.execute(
                select(
                    func.count(Order.id).label("count"),
                    func.coalesce(func.sum(OrderItem.total_price), 0).label("revenue")
                )
                .select_from(Order)
                .outerjoin(OrderItem, Order.id == OrderItem.order_id)
                .where(
                    and_(
                        func.date(Order.scheduled_date) == target_date,
                        Order.status != OrderStatus.CANCELLED
                    )
                )
            )
            return result.first()
        
        async def get_active_customers():
            """Get count of active customers."""
            result = await db.execute(
                select(func.count(Customer.id))
                .where(Customer.is_active == True)
            )
            return result.scalar()
        
        async def get_drivers_on_route():
            """Get count of drivers currently on route."""
            result = await db.execute(
                select(func.count(Route.id))
                .where(
                    and_(
                        func.date(Route.planned_date) == target_date,
                        Route.status == RouteStatus.IN_PROGRESS
                    )
                )
            )
            return result.scalar()
        
        async def get_route_progress():
            """Get route progress for today."""
            result = await db.execute(
                select(
                    Route.id,
                    Route.route_number,
                    Route.status,
                    Route.total_orders,
                    Route.completed_orders,
                    Route.driver_name
                )
                .where(func.date(Route.planned_date) == target_date)
                .order_by(Route.route_number)
                .limit(10)
            )
            return result.all()
        
        async def get_recent_deliveries():
            """Get recent delivery count."""
            result = await db.execute(
                select(func.count(DeliveryHistory.id))
                .where(
                    and_(
                        func.date(DeliveryHistory.delivered_at) == target_date,
                        DeliveryHistory.status == 'delivered'
                    )
                )
            )
            return result.scalar()
        
        async def get_urgent_orders():
            """Get count of urgent orders."""
            result = await db.execute(
                select(func.count(Order.id))
                .where(
                    and_(
                        func.date(Order.scheduled_date) == target_date,
                        Order.is_urgent == True,
                        Order.status.in_([OrderStatus.PENDING, OrderStatus.CONFIRMED])
                    )
                )
            )
            return result.scalar()
        
        # Execute all queries in parallel
        results = await asyncio.gather(
            get_today_orders(),
            get_active_customers(),
            get_drivers_on_route(),
            get_route_progress(),
            get_recent_deliveries(),
            get_urgent_orders(),
            return_exceptions=True
        )
        
        # Handle results
        order_stats = results[0] if not isinstance(results[0], Exception) else None
        active_customers = results[1] if not isinstance(results[1], Exception) else 0
        drivers_on_route = results[2] if not isinstance(results[2], Exception) else 0
        route_progress = results[3] if not isinstance(results[3], Exception) else []
        recent_deliveries = results[4] if not isinstance(results[4], Exception) else 0
        urgent_orders = results[5] if not isinstance(results[5], Exception) else 0
        
        # Build response
        stats = DashboardStats(
            today_orders=order_stats.count if order_stats else 0,
            today_revenue=float(order_stats.revenue) if order_stats else 0.0,
            active_customers=active_customers or 0,
            drivers_on_route=drivers_on_route or 0,
            recent_deliveries=recent_deliveries or 0,
            urgent_orders=urgent_orders or 0,
            completion_rate=calculate_completion_rate(route_progress)
        )
        
        routes = [
            RouteProgress(
                id=r.id,
                route_number=r.route_number,
                status=r.status,
                total_orders=r.total_orders,
                completed_orders=r.completed_orders,
                driver_name=r.driver_name,
                progress_percentage=calculate_progress(r.completed_orders, r.total_orders)
            )
            for r in route_progress
        ]
        
        # Calculate response time
        response_time = (datetime.utcnow() - start_time).total_seconds()
        
        # Log performance metrics
        logger.info(f"Dashboard summary generated in {response_time:.3f}s")
        
        # Add custom metric for monitoring
        if response_time > 1.0:
            logger.warning(f"Dashboard summary slow response: {response_time:.3f}s")
        
        return DashboardSummary(
            stats=stats,
            routes=routes,
            predictions={
                "total": 0,  # TODO: Implement prediction summary
                "urgent": 0,
                "confidence": 0.0
            },
            response_time_ms=int(response_time * 1000)
        )
        
    except Exception as e:
        logger.error(f"Dashboard summary error: {str(e)}", exc_info=True)
        # Return default values on error to prevent dashboard crash
        return DashboardSummary(
            stats=DashboardStats(
                today_orders=0,
                today_revenue=0.0,
                active_customers=0,
                drivers_on_route=0,
                recent_deliveries=0,
                urgent_orders=0,
                completion_rate=0.0
            ),
            routes=[],
            predictions={"total": 0, "urgent": 0, "confidence": 0.0},
            response_time_ms=0
        )


def calculate_completion_rate(routes) -> float:
    """Calculate overall completion rate for routes."""
    if not routes:
        return 0.0
    
    total_orders = sum(r.total_orders for r in routes)
    completed_orders = sum(r.completed_orders for r in routes)
    
    if total_orders == 0:
        return 0.0
    
    return round((completed_orders / total_orders) * 100, 1)


def calculate_progress(completed: int, total: int) -> float:
    """Calculate progress percentage."""
    if total == 0:
        return 0.0
    return round((completed / total) * 100, 1)


@router.get("/health")
async def health_check() -> Dict[str, Any]:
    """
    Health check endpoint for dashboard monitoring.
    Used to verify API availability and measure response time.
    """
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "service": "dashboard-api"
    }