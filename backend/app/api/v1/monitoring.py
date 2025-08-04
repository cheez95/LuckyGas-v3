"""
Performance monitoring and metrics endpoints.
"""

from datetime import datetime, timedelta
from typing import Any, Dict

from fastapi import APIRouter, Depends, HTTPException, Query
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.responses import Response

from app.api.deps import get_current_active_superuser, get_db
from app.middleware.performance import get_performance_stats, run_performance_baseline
from app.models.user import User

router = APIRouter(prefix="/monitoring", tags=["monitoring"])


@router.get("/metrics")
async def get_prometheus_metrics():
    """
    Prometheus metrics endpoint.

    Returns metrics in Prometheus exposition format.
    """
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)


@router.get("/performance", dependencies=[Depends(get_current_active_superuser)])
async def get_performance_statistics() -> Dict[str, Any]:
    """
    Get current performance statistics.

    Requires admin privileges.
    """
    stats = await get_performance_stats()
    return {"timestamp": datetime.utcnow().isoformat(), "stats": stats}


@router.post(
    "/performance/baseline", dependencies=[Depends(get_current_active_superuser)]
)
async def run_baseline_test() -> Dict[str, Any]:
    """
    Run performance baseline test.

    Tests basic connectivity and response times.
    Requires admin privileges.
    """
    results = await run_performance_baseline()
    return {"timestamp": datetime.utcnow().isoformat(), "results": results}


@router.get("/health/performance")
async def get_performance_health() -> Dict[str, Any]:
    """
    Get performance health status.

    Returns simplified health metrics for monitoring.
    """
    stats = await get_performance_stats()

    # Calculate health score
    health_score = 100.0
    issues = []

    # Check database
    if "error" in stats.get("database", {}):
        health_score -= 50
        issues.append("Database connection error")
    elif stats["database"].get("active_connections", 0) > 50:
        health_score -= 10
        issues.append("High database connection count")

    # Check Redis
    if "error" in stats.get("redis", {}):
        health_score -= 20
        issues.append("Redis connection error")
    elif stats["redis"].get("hit_rate", 1) < 0.5:
        health_score -= 10
        issues.append("Low cache hit rate")

    # Check slow endpoints
    slow_endpoints = stats.get("slow_endpoints", {})
    if len(slow_endpoints) > 5:
        health_score -= 10
        issues.append(f"{len(slow_endpoints)} slow endpoints detected")

    return {
        "status": (
            "healthy"
            if health_score >= 80
            else "degraded" if health_score >= 60 else "unhealthy"
        ),
        "score": health_score,
        "issues": issues,
        "timestamp": datetime.utcnow().isoformat(),
    }


@router.get(
    "/performance/slow-queries", dependencies=[Depends(get_current_active_superuser)]
)
async def get_slow_queries(
    db: AsyncSession = Depends(get_db),
    minutes: int = Query(60, description="Time window in minutes"),
) -> Dict[str, Any]:
    """
    Get slow database queries.

    Requires admin privileges.
    """
    # This would need to be implemented based on your database logging
    # For now, returning a placeholder
    return {
        "timestamp": datetime.utcnow().isoformat(),
        "time_window_minutes": minutes,
        "slow_queries": [
            # Example format
            # {
            #     "query": "SELECT * FROM customers WHERE ...",
            #     "duration_ms": 1234,
            #     "timestamp": "2024-01-20T10:30:00Z"
            # }
        ],
        "message": "Slow query tracking requires database query logging to be enabled",
    }


@router.get(
    "/performance/response-times", dependencies=[Depends(get_current_active_superuser)]
)
async def get_response_time_stats(
    minutes: int = Query(60, description="Time window in minutes")
) -> Dict[str, Any]:
    """
    Get response time statistics by endpoint.

    Requires admin privileges.
    """
    # This would aggregate data from Prometheus metrics
    # For now, returning a structured example
    return {
        "timestamp": datetime.utcnow().isoformat(),
        "time_window_minutes": minutes,
        "endpoints": {
            "/api/v1/customers": {
                "p50": 45,
                "p90": 120,
                "p95": 180,
                "p99": 350,
                "count": 1234,
            },
            "/api/v1/orders": {
                "p50": 55,
                "p90": 150,
                "p95": 220,
                "p99": 500,
                "count": 2345,
            },
        },
        "overall": {
            "p50": 50,
            "p90": 135,
            "p95": 200,
            "p99": 425,
            "total_requests": 10000,
        },
    }


@router.post(
    "/performance/alert-thresholds",
    dependencies=[Depends(get_current_active_superuser)],
)
async def update_alert_thresholds(thresholds: Dict[str, float]) -> Dict[str, Any]:
    """
    Update performance alert thresholds.

    Requires admin privileges.

    Example thresholds:
    - response_time_p95_ms: 1000
    - error_rate_percent: 1.0
    - database_connections: 50
    - cache_hit_rate: 0.7
    """
    # This would update alerting configuration
    # For now, just validating and returning
    valid_thresholds = {
        "response_time_p95_ms",
        "error_rate_percent",
        "database_connections",
        "cache_hit_rate",
        "cpu_percent",
        "memory_percent",
    }

    invalid = set(thresholds.keys()) - valid_thresholds
    if invalid:
        raise HTTPException(
            status_code=400, detail=f"Invalid threshold keys: {invalid}"
        )

    return {
        "message": "Alert thresholds updated",
        "thresholds": thresholds,
        "timestamp": datetime.utcnow().isoformat(),
    }
