"""
Performance monitoring middleware for tracking API response times and metrics.
"""

import logging
import time
from contextlib import asynccontextmanager

import redis.asyncio as redis
from fastapi import Request, Response
from fastapi.routing import APIRoute
from prometheus_client import Counter, Gauge, Histogram
from sqlalchemy import text

from app.core.config import settings
from app.core.database import async_session_maker

logger = logging.getLogger(__name__)

# Prometheus metrics
request_count = Counter(
    "http_requests_total", "Total HTTP requests", ["method", "endpoint", "status"]
)

request_duration = Histogram(
    "http_request_duration_seconds",
    "HTTP request duration in seconds",
    ["method", "endpoint", "status"],
    buckets=(
        0.005,
        0.01,
        0.025,
        0.05,
        0.075,
        0.1,
        0.25,
        0.5,
        0.75,
        1.0,
        2.5,
        5.0,
        7.5,
        10.0,
    ),
)

active_requests = Gauge(
    "http_active_requests", "Number of active HTTP requests", ["method", "endpoint"]
)

db_query_duration = Histogram(
    "db_query_duration_seconds",
    "Database query duration in seconds",
    ["query_type"],
    buckets=(0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5),
)

cache_operations = Counter(
    "cache_operations_total", "Total cache operations", ["operation", "result"]
)

response_size = Histogram(
    "http_response_size_bytes",
    "HTTP response size in bytes",
    ["method", "endpoint", "status"],
    buckets=(100, 1000, 10000, 100000, 1000000, 10000000),
)

# Performance thresholds
SLOW_REQUEST_THRESHOLD = 1.0  # seconds
VERY_SLOW_REQUEST_THRESHOLD = 5.0  # seconds
LARGE_RESPONSE_THRESHOLD = 1_000_000  # 1MB


class PerformanceMiddleware:
    """Middleware for monitoring request performance."""

    def __init__(self, redis_client: Optional[redis.Redis] = None):
        self.redis_client = redis_client
        self._slow_endpoints: Dict[str, Dict[str, Any]] = {}

    async def __call__(self, request: Request, call_next: Callable) -> Response:
        """Process request and track performance metrics."""
        # Skip health check endpoints
        if request.url.path in ["/health", "/health / ready", "/metrics"]:
            return await call_next(request)

        # Extract endpoint info
        method = request.method
        endpoint = self._get_endpoint_pattern(request)

        # Track active requests
        active_requests.labels(method=method, endpoint=endpoint).inc()

        # Start timing
        start_time = time.time()

        try:
            # Process request
            response = await call_next(request)

            # Calculate duration
            duration = time.time() - start_time

            # Get response size (estimate if not available)
            response_size_value = int(response.headers.get("content - length", 0))

            # Update metrics
            request_count.labels(
                method=method, endpoint=endpoint, status=response.status_code
            ).inc()

            request_duration.labels(
                method=method, endpoint=endpoint, status=response.status_code
            ).observe(duration)

            response_size.labels(
                method=method, endpoint=endpoint, status=response.status_code
            ).observe(response_size_value)

            # Log slow requests
            if duration > SLOW_REQUEST_THRESHOLD:
                await self._handle_slow_request(request, response, duration)

            # Add performance headers
            response.headers["X-Response-Time"] = f"{duration:.3f}"
            response.headers["X-Request-ID"] = (
                request.state.request_id
                if hasattr(request.state, "request_id")
                else "unknown"
            )

            return response

        except Exception as e:
            # Track failed requests
            duration = time.time() - start_time
            request_count.labels(method=method, endpoint=endpoint, status=500).inc()
            request_duration.labels(
                method=method, endpoint=endpoint, status=500
            ).observe(duration)

            logger.error(f"Request failed: {method} {endpoint}", exc_info=e)
            raise

        finally:
            # Decrement active requests
            active_requests.labels(method=method, endpoint=endpoint).dec()

    def _get_endpoint_pattern(self, request: Request) -> str:
        """Extract endpoint pattern from request."""
        # Try to get the matched route
        for route in request.app.routes:
            if isinstance(route, APIRoute):
                match, _ = route.path_regex.match(request.url.path)
                if match:
                    return route.path

        # Fallback to raw path
        return request.url.path

    async def _handle_slow_request(
        self, request: Request, response: Response, duration: float
    ):
        """Handle slow request logging and tracking."""
        endpoint = self._get_endpoint_pattern(request)

        # Log slow request
        log_level = (
            logging.ERROR if duration > VERY_SLOW_REQUEST_THRESHOLD else logging.WARNING
        )
        logger.log(
            log_level,
            f"Slow request detected: {request.method} {endpoint} took {duration:.3f}s",
        )

        # Track slow endpoint statistics
        if endpoint not in self._slow_endpoints:
            self._slow_endpoints[endpoint] = {
                "count": 0,
                "total_duration": 0,
                "max_duration": 0,
                "last_slow_request": None,
            }

        stats = self._slow_endpoints[endpoint]
        stats["count"] += 1
        stats["total_duration"] += duration
        stats["max_duration"] = max(stats["max_duration"], duration)
        stats["last_slow_request"] = time.time()

        # Store in Redis if available
        if self.redis_client:
            try:
                await self.redis_client.hincrby(
                    f"slow_endpoints:{endpoint}", "count", 1
                )
                await self.redis_client.hincrbyfloat(
                    f"slow_endpoints:{endpoint}", "total_duration", duration
                )
                await self.redis_client.hset(
                    f"slow_endpoints:{endpoint}", "last_slow_request", time.time()
                )
                await self.redis_client.expire(
                    f"slow_endpoints:{endpoint}", 86400
                )  # 24 hours
            except Exception as e:
                logger.error(f"Failed to update slow endpoint stats in Redis: {e}")


class DatabasePerformanceTracker:
    """Track database query performance."""

    @staticmethod
    @asynccontextmanager
    async def track_query(query_type: str):
        """Context manager for tracking database query performance."""
        start_time = time.time()
        try:
            yield
        finally:
            duration = time.time() - start_time
            db_query_duration.labels(query_type=query_type).observe(duration)

            if duration > 1.0:  # Log slow queries
                logger.warning(f"Slow database query ({query_type}): {duration:.3f}s")


class CachePerformanceTracker:
    """Track cache operation performance."""

    @staticmethod
    def track_cache_operation(operation: str, hit: bool):
        """Track cache operation metrics."""
        result = "hit" if hit else "miss"
        cache_operations.labels(operation=operation, result=result).inc()


async def get_performance_stats() -> Dict[str, Any]:
    """Get current performance statistics."""
    # Collect database stats
    db_stats = {}
    try:
        async with async_session_maker() as session:
            # Get connection count
            result = await session.execute(
                text("SELECT count(*) FROM pg_stat_activity WHERE state = 'active'")
            )
            db_stats["active_connections"] = result.scalar()

            # Get database size
            result = await session.execute(
                text("SELECT pg_database_size(current_database())")
            )
            db_stats["database_size_bytes"] = result.scalar()

    except Exception as e:
        logger.error(f"Failed to get database stats: {e}")
        db_stats = {"error": str(e)}

    # Collect Redis stats if available
    redis_stats = {}
    if settings.REDIS_URL:
        try:
            redis_client = redis.from_url(settings.REDIS_URL)
            info = await redis_client.info()
            redis_stats = {
                "connected_clients": info.get("connected_clients", 0),
                "used_memory": info.get("used_memory", 0),
                "hits": info.get("keyspace_hits", 0),
                "misses": info.get("keyspace_misses", 0),
                "hit_rate": (
                    info.get("keyspace_hits", 0)
                    / (info.get("keyspace_hits", 0) + info.get("keyspace_misses", 1))
                    if info.get("keyspace_hits", 0) + info.get("keyspace_misses", 0) > 0
                    else 0
                ),
            }
            await redis_client.close()
        except Exception as e:
            logger.error(f"Failed to get Redis stats: {e}")
            redis_stats = {"error": str(e)}

    return {
        "database": db_stats,
        "redis": redis_stats,
        "slow_endpoints": getattr(PerformanceMiddleware, "_slow_endpoints", {}),
        "thresholds": {
            "slow_request_seconds": SLOW_REQUEST_THRESHOLD,
            "very_slow_request_seconds": VERY_SLOW_REQUEST_THRESHOLD,
            "large_response_bytes": LARGE_RESPONSE_THRESHOLD,
        },
    }


async def run_performance_baseline():
    """Run performance baseline tests."""
    results = {}

    # Test database connection
    start = time.time()
    try:
        async with async_session_maker() as session:
            await session.execute(text("SELECT 1"))
        results["database_connection_ms"] = (time.time() - start) * 1000
    except Exception as e:
        results["database_connection_error"] = str(e)

    # Test Redis connection if available
    if settings.REDIS_URL:
        start = time.time()
        try:
            redis_client = redis.from_url(settings.REDIS_URL)
            await redis_client.ping()
            await redis_client.close()
            results["redis_connection_ms"] = (time.time() - start) * 1000
        except Exception as e:
            results["redis_connection_error"] = str(e)

    # Calculate baseline scores
    results["baseline_score"] = _calculate_baseline_score(results)
    results["timestamp"] = time.time()

    return results


def _calculate_baseline_score(results: Dict[str, Any]) -> float:
    """Calculate overall baseline performance score (0 - 100)."""
    score = 100.0

    # Database penalties
    if "database_connection_error" in results:
        score -= 50
    elif results.get("database_connection_ms", 0) > 100:
        score -= min(20, (results["database_connection_ms"] - 100) / 10)

    # Redis penalties
    if "redis_connection_error" in results:
        score -= 20
    elif results.get("redis_connection_ms", 0) > 50:
        score -= min(10, (results["redis_connection_ms"] - 50) / 10)

    return max(0, score)
