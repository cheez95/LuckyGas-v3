"""
Route analytics API endpoints - MVP version.
"""

import logging
from datetime import date, timedelta
from typing import Dict

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db
from app.core.api_utils import handle_api_errors, require_roles, success_response
from app.core.decorators import rate_limit
from app.models.user import User
from app.schemas.user import UserRole
from app.services.route_analytics_service import route_analytics_service

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get("/dashboard / summary")
@rate_limit(requests_per_minute=30)
@handle_api_errors({
    ValueError: "無效的日期參數",
    KeyError: "缺少必要的分析資料"
})
@require_roles([UserRole.MANAGER, UserRole.SUPER_ADMIN, UserRole.OFFICE_STAFF])
async def get_dashboard_summary(
    db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)
) -> Dict:
    """
    Get summary metrics for analytics dashboard - MVP version.

    Returns key metrics for today and comparisons with yesterday.
    """
    today = date.today()
    yesterday = today - timedelta(days=1)

    # Get today's analytics
    today_analytics = await route_analytics_service.get_daily_analytics(
        target_date=today, session=db
    )

    # Get yesterday's analytics for comparison
    yesterday_analytics = await route_analytics_service.get_daily_analytics(
        target_date=yesterday, session=db
    )

    # Calculate changes
    def calculate_change(today_val, yesterday_val):
        if yesterday_val == 0:
            return 0
        return ((today_val - yesterday_val) / yesterday_val) * 100

    dashboard_data = {
        "today": {
            "date": today.isoformat(),
            "total_routes": today_analytics.total_routes,
            "total_deliveries": today_analytics.total_deliveries,
            "total_distance_km": today_analytics.total_distance_km,
            "fuel_saved_liters": today_analytics.total_fuel_saved_liters,
            "cost_saved_twd": today_analytics.total_cost_saved,
            "on_time_percentage": today_analytics.on_time_percentage,
        },
        "changes": {
            "routes_change": calculate_change(
                today_analytics.total_routes, yesterday_analytics.total_routes
            ),
            "deliveries_change": calculate_change(
                today_analytics.total_deliveries,
                yesterday_analytics.total_deliveries,
            ),
            "distance_change": calculate_change(
                today_analytics.total_distance_km,
                yesterday_analytics.total_distance_km,
            ),
            "fuel_savings_change": calculate_change(
                today_analytics.total_fuel_saved_liters,
                yesterday_analytics.total_fuel_saved_liters,
            ),
        },
        "highlights": {
            "best_driver": (
                today_analytics.top_performing_drivers[0]
                if today_analytics.top_performing_drivers
                else None
            ),
            "peak_hour": (
                max(
                    today_analytics.deliveries_by_hour.items(),
                    key=lambda x: x[1],
                    default=(None, 0),
                )[0]
                if today_analytics.deliveries_by_hour
                else None
            ),
            "optimization_effectiveness": today_analytics.optimization_savings_percentage,
        },
    }
    
    return success_response(data=dashboard_data, message="儀表板摘要獲取成功")


@router.get("/fuel - savings / weekly")
@rate_limit(requests_per_minute=20)
@handle_api_errors({
    ValueError: "無效的日期參數",
    KeyError: "缺少必要的燃料節省資料"
})
@require_roles([UserRole.MANAGER, UserRole.SUPER_ADMIN, UserRole.OFFICE_STAFF])
async def get_weekly_fuel_savings(
    db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)
) -> Dict:
    """
    Get weekly fuel savings data for chart display - MVP version.
    """
    end_date = date.today()
    start_date = end_date - timedelta(days=6)

    # Collect daily fuel savings
    daily_data = []
    current = start_date

    while current <= end_date:
        daily_analytics = await route_analytics_service.get_daily_analytics(
            target_date=current, session=db
        )

        daily_data.append(
            {
                "date": current.isoformat(),
                "fuel_saved": daily_analytics.total_fuel_saved_liters,
                "cost_saved": daily_analytics.total_cost_saved,
                "distance_saved": daily_analytics.total_distance_km
                * 0.2,  # Estimate 20% savings
            }
        )

        current += timedelta(days=1)

    fuel_savings_data = {
        "period": {"start": start_date.isoformat(), "end": end_date.isoformat()},
        "daily_breakdown": daily_data,
        "total_fuel_saved": sum(d["fuel_saved"] for d in daily_data),
        "total_cost_saved": sum(d["cost_saved"] for d in daily_data),
    }
    
    return success_response(data=fuel_savings_data, message="週燃料節省資料獲取成功")


@router.get("/drivers / top - performers")
@rate_limit(requests_per_minute=20)
@handle_api_errors({
    ValueError: "無效的驅駛員參數",
    KeyError: "缺少必要的驅駛員資料"
})
@require_roles([UserRole.MANAGER, UserRole.SUPER_ADMIN, UserRole.OFFICE_STAFF])
async def get_top_drivers(
    limit: int = Query(5, ge=1, le=20),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Dict:
    """
    Get top performing drivers - MVP version.
    """
    today = date.today()

    # Get today's analytics
    today_analytics = await route_analytics_service.get_daily_analytics(
        target_date=today, session=db
    )

    # Get top drivers
    top_drivers = today_analytics.top_performing_drivers[:limit]

    # Enhance driver data
    enhanced_drivers = []
    for driver in top_drivers:
        # Get weekly performance
        weekly_metrics = await route_analytics_service.get_driver_performance(
            driver_id=driver["driver_id"],
            period="weekly",
            end_date=today,
            session=db,
        )

        enhanced_drivers.append(
            {
                "driver_id": driver["driver_id"],
                "driver_name": driver["driver_name"],
                "today_on_time_pct": driver["on_time_pct"],
                "weekly_metrics": {
                    "total_routes": weekly_metrics.total_routes,
                    "total_deliveries": weekly_metrics.total_deliveries,
                    "average_on_time_pct": weekly_metrics.on_time_percentage,
                    "fuel_efficiency_score": weekly_metrics.fuel_efficiency_score,
                    "overall_score": weekly_metrics.overall_score,
                },
            }
        )

    drivers_data = {"date": today.isoformat(), "top_drivers": enhanced_drivers}
    
    return success_response(data=drivers_data, message="最佳司機資料獲取成功")
