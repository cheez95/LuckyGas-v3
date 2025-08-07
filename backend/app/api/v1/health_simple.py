"""
Simple health check endpoints for monitoring simplified services
"""

from datetime import datetime
from typing import Any, Dict

import redis.asyncio as redis
from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.api import deps
from app.core.config import settings
from app.services.simple_notifications import notification_service
from app.services.simple_websocket import websocket_manager

router = APIRouter()


@router.get("/")
async def health_check() -> Dict[str, Any]:
    """
    Basic health check endpoint.

    Returns system status and uptime.
    """
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "service": "LuckyGas API - Simplified",
        "version": "2.0.0",
    }


@router.get("/websocket")
async def health_websocket() -> Dict[str, Any]:
    """
    WebSocket service health check.

    Returns connection count and Redis status.
    """
    try:
        # Check Redis connection
        redis_healthy = False
        if websocket_manager.redis_client:
            try:
                await websocket_manager.redis_client.ping()
                redis_healthy = True
            except Exception:
                pass

        return {
            "status": "healthy" if redis_healthy else "degraded",
            "connections": len(websocket_manager.connections),
            "redis_connected": redis_healthy,
            "timestamp": datetime.now().isoformat(),
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e),
            "timestamp": datetime.now().isoformat(),
        }


@router.get("/notifications")
async def health_notifications(
    db: AsyncSession = Depends(deps.get_db),
) -> Dict[str, Any]:
    """
    Notification service health check.

    Returns notification statistics for the last 24 hours.
    """
    try:
        # Get notification stats
        stats = await notification_service.get_notification_stats(days=1)

        # Calculate success rate
        total_sms = stats.get("sms", {}).get("sent", 0) + stats.get("sms", {}).get(
            "failed", 0
        )
        sms_success_rate = (
            (stats.get("sms", {}).get("sent", 0) / total_sms * 100)
            if total_sms > 0
            else 100
        )

        return {
            "status": "healthy" if sms_success_rate > 90 else "degraded",
            "sms_sent_24h": stats.get("sms", {}).get("sent", 0),
            "sms_failed_24h": stats.get("sms", {}).get("failed", 0),
            "sms_success_rate": round(sms_success_rate, 2),
            "email_sent_24h": stats.get("email", {}).get("sent", 0),
            "timestamp": datetime.now().isoformat(),
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e),
            "timestamp": datetime.now().isoformat(),
        }


@router.get("/database")
async def health_database(db: AsyncSession = Depends(deps.get_db)) -> Dict[str, Any]:
    """
    Database health check.

    Tests database connectivity and response time.
    """
    try:
        # Simple query to test database
        start_time = datetime.now()
        result = await db.execute(text("SELECT 1"))
        await result.scalar()
        query_time = (datetime.now() - start_time).total_seconds() * 1000

        return {
            "status": "healthy" if query_time < 100 else "degraded",
            "query_time_ms": round(query_time, 2),
            "timestamp": datetime.now().isoformat(),
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e),
            "timestamp": datetime.now().isoformat(),
        }


@router.get("/redis")
async def health_redis() -> Dict[str, Any]:
    """
    Redis health check.

    Tests Redis connectivity and response time.
    """
    try:
        # Try to connect to Redis
        redis_url = getattr(settings, "REDIS_URL", "redis://localhost:6379 / 0")
        redis_client = redis.from_url(redis_url, decode_responses=True)

        start_time = datetime.now()
        await redis_client.ping()
        ping_time = (datetime.now() - start_time).total_seconds() * 1000

        # Get some Redis info
        info = await redis_client.info()

        await redis_client.close()

        return {
            "status": "healthy" if ping_time < 50 else "degraded",
            "ping_time_ms": round(ping_time, 2),
            "connected_clients": info.get("connected_clients", 0),
            "used_memory_human": info.get("used_memory_human", "unknown"),
            "timestamp": datetime.now().isoformat(),
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e),
            "timestamp": datetime.now().isoformat(),
        }


@router.get("/summary")
async def health_summary(db: AsyncSession = Depends(deps.get_db)) -> Dict[str, Any]:
    """
    Comprehensive health check summary.

    Aggregates all health checks into a single response.
    """
    # Gather all health statuses
    checks = {}

    # Basic health
    checks["api"] = await health_check()

    # Database health
    checks["database"] = await health_database(db)

    # Redis health
    checks["redis"] = await health_redis()

    # WebSocket health
    checks["websocket"] = await health_websocket()

    # Notification health
    checks["notifications"] = await health_notifications(db)

    # Determine overall status
    statuses = [check.get("status", "unknown") for check in checks.values()]
    if all(status == "healthy" for status in statuses):
        overall_status = "healthy"
    elif any(status == "unhealthy" for status in statuses):
        overall_status = "unhealthy"
    else:
        overall_status = "degraded"

    return {
        "status": overall_status,
        "checks": checks,
        "timestamp": datetime.now().isoformat(),
    }


@router.get("/metrics")
async def get_simple_metrics() -> Dict[str, Any]:
    """
    Get simplified metrics for monitoring.

    Returns basic operational metrics.
    """
    try:
        # Get WebSocket metrics
        ws_metrics = {
            "active_connections": len(websocket_manager.connections),
            "redis_connected": websocket_manager.redis_client is not None,
        }

        # Get notification metrics (last 7 days)
        notification_stats = await notification_service.get_notification_stats(days=7)

        notification_metrics = {
            "sms_sent_7d": notification_stats.get("sms", {}).get("sent", 0),
            "sms_failed_7d": notification_stats.get("sms", {}).get("failed", 0),
            "email_sent_7d": notification_stats.get("email", {}).get("sent", 0),
            "email_failed_7d": notification_stats.get("email", {}).get("failed", 0),
        }

        return {
            "websocket": ws_metrics,
            "notifications": notification_metrics,
            "timestamp": datetime.now().isoformat(),
        }
    except Exception as e:
        return {"error": str(e), "timestamp": datetime.now().isoformat()}
