"""
Route analytics API endpoints - MVP version.
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional, Dict
from datetime import date, timedelta
import logging

from app.api.deps import get_db, get_current_user
from app.models.user import User
from app.services.route_analytics_service import route_analytics_service
from app.core.decorators import rate_limit

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get("/dashboard/summary")
@rate_limit(requests_per_minute=30)
async def get_dashboard_summary(
    db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)
) -> Dict:
    """
    Get summary metrics for analytics dashboard - MVP version.

    Returns key metrics for today and comparisons with yesterday.
    """
    try:
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

        return {
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

    except Exception as e:
        logger.error(f"Error getting dashboard summary: {str(e)}")
        raise HTTPException(status_code=500, detail="獲取儀表板摘要時發生錯誤")


@router.get("/fuel-savings/weekly")
@rate_limit(requests_per_minute=20)
async def get_weekly_fuel_savings(
    db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)
) -> Dict:
    """
    Get weekly fuel savings data for chart display - MVP version.
    """
    try:
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

        return {
            "period": {"start": start_date.isoformat(), "end": end_date.isoformat()},
            "daily_breakdown": daily_data,
            "total_fuel_saved": sum(d["fuel_saved"] for d in daily_data),
            "total_cost_saved": sum(d["cost_saved"] for d in daily_data),
        }

    except Exception as e:
        logger.error(f"Error getting weekly fuel savings: {str(e)}")
        raise HTTPException(status_code=500, detail="獲取週燃料節省資料時發生錯誤")


@router.get("/drivers/top-performers")
@rate_limit(requests_per_minute=20)
async def get_top_drivers(
    limit: int = Query(5, ge=1, le=20),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Dict:
    """
    Get top performing drivers - MVP version.
    """
    try:
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

        return {"date": today.isoformat(), "top_drivers": enhanced_drivers}

    except Exception as e:
        logger.error(f"Error getting top drivers: {str(e)}")
        raise HTTPException(status_code=500, detail="獲取最佳司機資料時發生錯誤")
