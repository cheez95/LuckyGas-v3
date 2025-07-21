"""
Google API Dashboard Endpoints

Provides monitoring and management endpoints for Google API usage.
"""
from typing import Dict, Any, Optional
from datetime import datetime, timedelta
from fastapi import APIRouter, HTTPException, Depends, Query
from pydantic import BaseModel

from app.api.deps import get_current_user, require_admin
from app.models.user import User
from app.services.google_cloud.monitoring.rate_limiter import get_rate_limiter
from app.services.google_cloud.monitoring.cost_monitor import get_cost_monitor
from app.services.google_cloud.monitoring.api_cache import get_api_cache
from app.services.google_cloud.monitoring.circuit_breaker import circuit_manager
from app.services.google_cloud.development_mode import get_development_mode_manager
from app.services.google_cloud.routes_service_enhanced import get_enhanced_routes_service
from app.core.security.api_key_manager import get_api_key_manager

router = APIRouter()


class APIKeyUpdate(BaseModel):
    """Request model for updating API keys"""
    api_type: str
    api_key: str


class RateLimitUpdate(BaseModel):
    """Request model for updating rate limits"""
    api_type: str
    per_second: Optional[int] = None
    per_minute: Optional[int] = None
    per_day: Optional[int] = None


@router.get("/dashboard/overview")
async def get_dashboard_overview(
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Get comprehensive overview of Google API usage and health
    
    Returns:
        Dashboard overview including:
        - Development mode status
        - API health for each service
        - Current usage and costs
        - Rate limit status
        - Circuit breaker states
    """
    # Get development mode info
    dev_manager = get_development_mode_manager()
    dev_info = dev_manager.get_service_info()
    
    # Get rate limiter status
    rate_limiter = await get_rate_limiter()
    rate_status = {}
    for api_type in ["routes", "geocoding", "vertex_ai"]:
        rate_status[api_type] = await rate_limiter.get_current_usage(api_type)
    
    # Get cost monitor status
    cost_monitor = await get_cost_monitor()
    cost_report = await cost_monitor.get_cost_report("daily")
    
    # Get circuit breaker states
    circuit_states = await circuit_manager.get_all_states()
    
    # Get cache statistics
    cache = await get_api_cache()
    cache_stats = await cache.get_stats()
    
    # Get service health
    routes_service = get_enhanced_routes_service()
    routes_health = await routes_service.get_service_health()
    
    return {
        "timestamp": datetime.now().isoformat(),
        "development_mode": dev_info,
        "services": {
            "routes": routes_health
        },
        "rate_limits": rate_status,
        "costs": {
            "daily": cost_report,
            "warnings": cost_report.get("warnings", [])
        },
        "circuit_breakers": circuit_states,
        "cache": cache_stats
    }


@router.get("/dashboard/costs/{period}")
async def get_cost_report(
    period: str = "daily",
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Get detailed cost report for specified period
    
    Args:
        period: Time period (hourly, daily, monthly)
        
    Returns:
        Detailed cost breakdown by API type
    """
    if period not in ["hourly", "daily", "monthly"]:
        raise HTTPException(400, "Invalid period. Use hourly, daily, or monthly")
    
    cost_monitor = await get_cost_monitor()
    return await cost_monitor.get_cost_report(period)


@router.get("/dashboard/costs/detailed/{api_type}")
async def get_detailed_usage(
    api_type: str,
    start_date: datetime = Query(..., description="Start date for usage report"),
    end_date: datetime = Query(..., description="End date for usage report"),
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Get detailed usage report for specific API type and date range
    
    Args:
        api_type: Type of API (routes, geocoding, vertex_ai)
        start_date: Start of date range
        end_date: End of date range
        
    Returns:
        Hourly breakdown of usage and costs
    """
    cost_monitor = await get_cost_monitor()
    return await cost_monitor.get_detailed_usage(api_type, start_date, end_date)


@router.get("/dashboard/rate-limits")
async def get_rate_limit_status(
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Get current rate limit status for all APIs
    
    Returns:
        Current usage and limits for each API type
    """
    rate_limiter = await get_rate_limiter()
    
    status = {}
    for api_type in ["routes", "geocoding", "places", "vertex_ai"]:
        usage = await rate_limiter.get_current_usage(api_type)
        status[api_type] = usage
    
    return {
        "timestamp": datetime.now().isoformat(),
        "rate_limits": status
    }


@router.post("/dashboard/rate-limits", dependencies=[Depends(require_admin)])
async def update_rate_limits(
    update: RateLimitUpdate,
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Update rate limits for an API (admin only)
    
    Args:
        update: New rate limit configuration
        
    Returns:
        Updated rate limit status
    """
    rate_limiter = await get_rate_limiter()
    
    # Update limits
    new_limits = {}
    if update.per_second is not None:
        new_limits["per_second"] = update.per_second
    if update.per_minute is not None:
        new_limits["per_minute"] = update.per_minute
    if update.per_day is not None:
        new_limits["per_day"] = update.per_day
    
    # This would need to be implemented in the rate limiter
    # For now, return the request
    return {
        "message": "Rate limit update requested",
        "api_type": update.api_type,
        "new_limits": new_limits
    }


@router.get("/dashboard/circuit-breakers")
async def get_circuit_breaker_status(
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Get circuit breaker status for all APIs
    
    Returns:
        Current state of all circuit breakers
    """
    states = await circuit_manager.get_all_states()
    
    return {
        "timestamp": datetime.now().isoformat(),
        "circuit_breakers": states
    }


@router.post("/dashboard/circuit-breakers/reset/{api_type}", dependencies=[Depends(require_admin)])
async def reset_circuit_breaker(
    api_type: str,
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Manually reset a circuit breaker (admin only)
    
    Args:
        api_type: API type to reset
        
    Returns:
        Success message
    """
    success = await circuit_manager.reset_breaker(api_type)
    
    if not success:
        raise HTTPException(404, f"Circuit breaker not found for {api_type}")
    
    return {
        "message": f"Circuit breaker for {api_type} has been reset",
        "timestamp": datetime.now().isoformat()
    }


@router.post("/dashboard/circuit-breakers/reset-all", dependencies=[Depends(require_admin)])
async def reset_all_circuit_breakers(
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Reset all circuit breakers (admin only)
    
    Returns:
        Success message
    """
    await circuit_manager.reset_all()
    
    return {
        "message": "All circuit breakers have been reset",
        "timestamp": datetime.now().isoformat()
    }


@router.get("/dashboard/cache/stats")
async def get_cache_statistics(
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Get cache statistics
    
    Returns:
        Cache hit rates and memory usage
    """
    cache = await get_api_cache()
    stats = await cache.get_stats()
    
    return {
        "timestamp": datetime.now().isoformat(),
        "cache": stats
    }


@router.post("/dashboard/cache/clear/{api_type}", dependencies=[Depends(require_admin)])
async def clear_cache_by_type(
    api_type: str,
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Clear cache for specific API type (admin only)
    
    Args:
        api_type: API type to clear cache for
        
    Returns:
        Number of entries cleared
    """
    cache = await get_api_cache()
    cleared = await cache.invalidate_pattern(f"{api_type}*")
    
    return {
        "message": f"Cleared {cleared} cache entries for {api_type}",
        "timestamp": datetime.now().isoformat()
    }


@router.post("/dashboard/cache/clear-all", dependencies=[Depends(require_admin)])
async def clear_all_cache(
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Clear all API cache entries (admin only)
    
    Returns:
        Number of entries cleared
    """
    cache = await get_api_cache()
    cleared = await cache.clear_all()
    
    return {
        "message": f"Cleared {cleared} total cache entries",
        "timestamp": datetime.now().isoformat()
    }


@router.post("/dashboard/api-keys/{api_name}", dependencies=[Depends(require_admin)])
async def update_api_key(
    api_name: str,
    api_key: str,
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Update API key in secure storage (admin only)
    
    Args:
        api_name: Name of the API key (e.g., google_maps_api_key)
        api_key: The new API key value
        
    Returns:
        Success message
    """
    key_manager = await get_api_key_manager()
    success = await key_manager.set_key(api_name, api_key)
    
    if not success:
        raise HTTPException(500, "Failed to update API key")
    
    return {
        "message": f"API key {api_name} updated successfully",
        "timestamp": datetime.now().isoformat()
    }


@router.get("/dashboard/development-mode")
async def get_development_mode_status(
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Get current development mode status
    
    Returns:
        Current mode and service configuration
    """
    dev_manager = get_development_mode_manager()
    info = dev_manager.get_service_info()
    health = await dev_manager.health_check()
    
    return {
        "timestamp": datetime.now().isoformat(),
        "mode_info": info,
        "health_check": health
    }


@router.post("/dashboard/budgets/reset/{period}", dependencies=[Depends(require_admin)])
async def reset_budget_tracking(
    period: Optional[str] = None,
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Reset budget tracking (admin only)
    
    Args:
        period: Specific period to reset (hour, day, month) or None for all
        
    Returns:
        Success message
    """
    cost_monitor = await get_cost_monitor()
    success = await cost_monitor.reset_budgets(period)
    
    if not success:
        raise HTTPException(500, "Failed to reset budget tracking")
    
    return {
        "message": f"Budget tracking reset for period: {period or 'all'}",
        "timestamp": datetime.now().isoformat()
    }


@router.get("/dashboard/alerts")
async def get_recent_alerts(
    hours: int = Query(24, description="Number of hours to look back"),
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Get recent cost and rate limit alerts
    
    Args:
        hours: Number of hours to look back for alerts
        
    Returns:
        List of recent alerts
    """
    # This would need to be implemented with a proper alert storage system
    # For now, return current warning status
    cost_monitor = await get_cost_monitor()
    daily_report = await cost_monitor.get_cost_report("daily")
    
    alerts = []
    
    # Check for cost warnings
    if daily_report["budget_percentage"] > 80:
        alerts.append({
            "type": "cost_warning",
            "level": "warning",
            "message": f"Daily budget at {daily_report['budget_percentage']}%",
            "timestamp": datetime.now().isoformat()
        })
    
    if daily_report["budget_percentage"] > 100:
        alerts.append({
            "type": "cost_critical",
            "level": "critical",
            "message": "Daily budget exceeded!",
            "timestamp": datetime.now().isoformat()
        })
    
    # Check circuit breakers
    circuit_states = await circuit_manager.get_all_states()
    for api_type, state in circuit_states.items():
        if state["state"] == "open":
            alerts.append({
                "type": "circuit_breaker_open",
                "level": "critical",
                "message": f"Circuit breaker OPEN for {api_type}",
                "timestamp": state.get("last_failure", datetime.now().isoformat())
            })
    
    return {
        "timestamp": datetime.now().isoformat(),
        "period_hours": hours,
        "alerts": alerts
    }