"""
Google API Cost Monitoring and Control
"""

import asyncio
import logging
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Dict, List, Optional

import redis.asyncio as redis

from app.core.cache import get_redis_client
from app.core.metrics import google_api_calls_counter

logger = logging.getLogger(__name__)


class GoogleAPICostMonitor:
    """Monitor and control Google API costs"""

    # Estimated costs per 1000 API calls (in USD)
    COST_PER_1000_CALLS = {
        "routes": Decimal("5.00"),  # $5 per 1000 requests
        "geocoding": Decimal("5.00"),  # $5 per 1000 requests
        "places": Decimal("17.00"),  # $17 per 1000 requests
        "vertex_ai": Decimal("1.00"),  # $1 per 1000 predictions
        "distance_matrix": Decimal("5.00"),  # $5 per 1000 elements
    }

    # Budget thresholds (in USD)
    THRESHOLDS = {
        "hourly_warning": Decimal("5.00"),  # $5/hour warning
        "hourly_critical": Decimal("10.00"),  # $10/hour critical
        "daily_warning": Decimal("50.00"),  # $50/day warning
        "daily_critical": Decimal("100.00"),  # $100/day critical
        "monthly_warning": Decimal("1000.00"),  # $1000/month warning
        "monthly_critical": Decimal("2000.00"),  # $2000/month critical
    }

    def __init__(self, redis_client: Optional[redis.Redis] = None):
        self.redis = redis_client
        self._initialized = False
        self.last_alert_time: Dict[str, datetime] = {}
        self._alert_callbacks = []

    async def _ensure_redis(self):
        """Ensure Redis client is initialized"""
        if not self._initialized:
            if not self.redis:
                self.redis = await get_redis_client()
            self._initialized = True

    def register_alert_callback(self, callback):
        """Register a callback for cost alerts"""
        self._alert_callbacks.append(callback)

    async def record_api_call(
        self,
        api_type: str,
        endpoint: str,
        response_size: Optional[int] = None,
        processing_time: Optional[float] = None,
    ) -> Dict[str, any]:
        """Record an API call and update costs"""
        await self._ensure_redis()

        # Update metrics (for now, just mark as 'allowed' - budget check happens later)
        google_api_calls_counter.labels(api_type=api_type, status="allowed").inc()

        # Calculate cost (per call, not per 1000)
        cost_per_call = self.COST_PER_1000_CALLS.get(api_type, Decimal("0")) / 1000

        # Get current timestamps
        now = datetime.now()
        hour_key = now.strftime("%Y-%m-%d-%H")
        day_key = now.strftime("%Y-%m-%d")
        month_key = now.strftime("%Y-%m")

        # Update costs for different time windows
        cost_updates = [
            (f"api_cost:hour:{hour_key}:{api_type}", 3600),  # 1 hour TTL
            (f"api_cost:day:{day_key}:{api_type}", 86400 * 7),  # 7 days TTL
            (f"api_cost:month:{month_key}:{api_type}", 86400 * 35),  # 35 days TTL
        ]

        for key, ttl in cost_updates:
            await self.redis.incrbyfloat(key, float(cost_per_call))
            await self.redis.expire(key, ttl)

        # Also track call counts
        count_updates = [
            (f"api_count:hour:{hour_key}:{api_type}", 3600),
            (f"api_count:day:{day_key}:{api_type}", 86400 * 7),
            (f"api_count:month:{month_key}:{api_type}", 86400 * 35),
        ]

        for key, ttl in count_updates:
            await self.redis.incr(key)
            await self.redis.expire(key, ttl)

        # Store additional metadata if provided
        if response_size or processing_time:
            metadata_key = f"api_metadata:{api_type}:{now.timestamp()}"
            metadata = {
                "endpoint": endpoint,
                "response_size": response_size,
                "processing_time": processing_time,
                "cost": float(cost_per_call),
            }
            await self.redis.hset(metadata_key, mapping=metadata)
            await self.redis.expire(metadata_key, 86400)  # 1 day TTL

        # Check thresholds
        alerts = await self._check_cost_thresholds(api_type)

        return {
            "api_type": api_type,
            "endpoint": endpoint,
            "cost": float(cost_per_call),
            "timestamp": now.isoformat(),
            "alerts": alerts,
        }

    async def _check_cost_thresholds(self, api_type: str) -> List[Dict]:
        """Check if costs exceed thresholds and return alerts"""
        alerts = []
        now = datetime.now()

        # Check hourly threshold
        hourly_total = await self._get_period_total("hour", now.strftime("%Y-%m-%d-%H"))
        if hourly_total > self.THRESHOLDS["hourly_critical"]:
            alert = await self._create_alert(
                "critical",
                f"Hourly API cost critical: ${hourly_total:.2f}",
                {"api_type": api_type, "total": str(hourly_total), "period": "hourly"},
            )
            if alert:
                alerts.append(alert)
        elif hourly_total > self.THRESHOLDS["hourly_warning"]:
            alert = await self._create_alert(
                "warning",
                f"Hourly API cost warning: ${hourly_total:.2f}",
                {"api_type": api_type, "total": str(hourly_total), "period": "hourly"},
            )
            if alert:
                alerts.append(alert)

        # Check daily threshold
        daily_total = await self._get_period_total("day", now.strftime("%Y-%m-%d"))
        if daily_total > self.THRESHOLDS["daily_critical"]:
            alert = await self._create_alert(
                "critical",
                f"Daily API cost critical: ${daily_total:.2f}",
                {"api_type": api_type, "total": str(daily_total), "period": "daily"},
            )
            if alert:
                alerts.append(alert)
        elif daily_total > self.THRESHOLDS["daily_warning"]:
            alert = await self._create_alert(
                "warning",
                f"Daily API cost warning: ${daily_total:.2f}",
                {"api_type": api_type, "total": str(daily_total), "period": "daily"},
            )
            if alert:
                alerts.append(alert)

        return alerts

    async def _get_period_total(self, period: str, period_key: str) -> Decimal:
        """Get total cost for a time period across all API types"""
        try:
            total = Decimal("0")

            for api_type in self.COST_PER_1000_CALLS.keys():
                key = f"api_cost:{period}:{period_key}:{api_type}"
                cost = await self.redis.get(key)
                if cost:
                    total += Decimal(cost.decode() if isinstance(cost, bytes) else cost)

            return total
        except (redis.ConnectionError, redis.RedisError) as e:
            # If Redis is unavailable, return 0 to avoid blocking calls
            logger.warning(f"Redis error in _get_period_total, returning 0: {e}")
            return Decimal("0")

    async def _create_alert(
        self, level: str, message: str, data: Dict
    ) -> Optional[Dict]:
        """Create an alert with rate limiting"""
        alert_key = f"{level}:{data.get('period', 'unknown')}"
        now = datetime.now()

        # Rate limit alerts to once per hour for same type
        if alert_key in self.last_alert_time:
            if now - self.last_alert_time[alert_key] < timedelta(hours=1):
                return None

        self.last_alert_time[alert_key] = now

        alert = {
            "level": level,
            "message": message,
            "data": data,
            "timestamp": now.isoformat(),
        }

        # Call registered callbacks
        for callback in self._alert_callbacks:
            try:
                await callback(alert)
            except Exception as e:
                logger.error(f"Alert callback failed: {e}")

        logger.warning(f"Cost alert: {level} - {message}")
        return alert

    async def enforce_budget_limit(self, api_type: str) -> bool:
        """
        Check if API call should be blocked due to budget limits
        Returns: True if allowed, False if blocked
        """
        try:
            await self._ensure_redis()

            now = datetime.now()

            # Check hourly limit first (more restrictive)
            hourly_total = await self._get_period_total(
                "hour", now.strftime("%Y-%m-%d-%H")
            )
            if hourly_total >= self.THRESHOLDS["hourly_critical"]:
                logger.error(
                    f"Blocking {api_type} API call - hourly budget exceeded: ${hourly_total:.2f}"
                )
                google_api_calls_counter.labels(
                    api_type=api_type, status="blocked_budget"
                ).inc()
                return False

            # Check daily limit
            daily_total = await self._get_period_total("day", now.strftime("%Y-%m-%d"))
            if daily_total >= self.THRESHOLDS["daily_critical"]:
                logger.error(
                    f"Blocking {api_type} API call - daily budget exceeded: ${daily_total:.2f}"
                )
                google_api_calls_counter.labels(
                    api_type=api_type, status="blocked_budget"
                ).inc()
                return False

            return True
        except (redis.ConnectionError, redis.RedisError) as e:
            # If Redis is unavailable, allow the call but log the error
            logger.warning(f"Redis error in enforce_budget_limit, allowing call: {e}")
            return True

    async def get_cost_report(self, period: str = "daily") -> Dict[str, any]:
        """Generate cost report for specified period"""
        await self._ensure_redis()

        now = datetime.now()
        report = {
            "period": period,
            "timestamp": now.isoformat(),
            "costs_by_api": {},
            "counts_by_api": {},
            "total_cost": 0.0,
            "total_calls": 0,
        }

        if period == "hourly":
            period_key = now.strftime("%Y-%m-%d-%H")
            budget_limit = float(self.THRESHOLDS["hourly_warning"])
        elif period == "daily":
            period_key = now.strftime("%Y-%m-%d")
            budget_limit = float(self.THRESHOLDS["daily_warning"])
        elif period == "monthly":
            period_key = now.strftime("%Y-%m")
            budget_limit = float(self.THRESHOLDS["monthly_warning"])
        else:
            return {"error": f"Invalid period: {period}"}

        total_cost = Decimal("0")
        total_calls = 0

        for api_type in self.COST_PER_1000_CALLS.keys():
            # Get cost
            cost_key = f"api_cost:{period}:{period_key}:{api_type}"
            cost = await self.redis.get(cost_key)
            if cost:
                # Handle bytes response from Redis
                if isinstance(cost, bytes):
                    cost = cost.decode("utf-8")
                cost_decimal = Decimal(cost)
                report["costs_by_api"][api_type] = float(cost_decimal)
                total_cost += cost_decimal

            # Get count
            count_key = f"api_count:{period}:{period_key}:{api_type}"
            count = await self.redis.get(count_key)
            if count:
                # Handle bytes response from Redis
                if isinstance(count, bytes):
                    count = count.decode("utf-8")
                count_int = int(count)
                report["counts_by_api"][api_type] = count_int
                total_calls += count_int

        report["total_cost"] = float(total_cost)
        report["total_calls"] = total_calls
        report["budget_limit"] = budget_limit
        report["budget_remaining"] = max(0, budget_limit - float(total_cost))
        report["budget_percentage"] = (
            round((float(total_cost) / budget_limit) * 100, 2)
            if budget_limit > 0
            else 0
        )

        # Add threshold warnings
        report["warnings"] = []
        if report["budget_percentage"] > 80:
            report["warnings"].append(f"Approaching {period} budget limit (>80% used)")
        if report["budget_percentage"] > 100:
            report["warnings"].append(f"Exceeded {period} budget limit!")

        return report

    async def get_detailed_usage(
        self, api_type: str, start_time: datetime, end_time: datetime
    ) -> Dict[str, any]:
        """Get detailed usage for a specific API type and time range"""
        try:
            await self._ensure_redis()

            usage = {
                "api_type": api_type,
                "start_time": start_time.isoformat(),
                "end_time": end_time.isoformat(),
                "hourly_breakdown": [],
                "total_cost": 0.0,
                "total_calls": 0,
            }

            # Iterate through hours in the range
            current = start_time.replace(minute=0, second=0, microsecond=0)
            while current <= end_time:
                hour_key = current.strftime("%Y-%m-%d-%H")

                # Get cost and count for this hour
                cost_key = f"api_cost:hour:{hour_key}:{api_type}"
                count_key = f"api_count:hour:{hour_key}:{api_type}"

                cost = await self.redis.get(cost_key)
                count = await self.redis.get(count_key)

                if cost or count:
                    hour_data = {
                        "hour": hour_key,
                        "cost": (
                            float(cost.decode() if isinstance(cost, bytes) else cost)
                            if cost
                            else 0.0
                        ),
                        "calls": (
                            int(
                                float(
                                    count.decode()
                                    if isinstance(count, bytes)
                                    else count
                                )
                            )
                            if count
                            else 0
                        ),
                    }
                    usage["hourly_breakdown"].append(hour_data)
                    usage["total_cost"] += hour_data["cost"]
                    usage["total_calls"] += hour_data["calls"]

                current += timedelta(hours=1)

            return usage
        except (redis.ConnectionError, redis.RedisError) as e:
            # If Redis is unavailable, return empty but valid structure
            logger.warning(
                f"Redis error in get_detailed_usage, returning empty data: {e}"
            )
            return {
                "api_type": api_type,
                "start_time": start_time.isoformat(),
                "end_time": end_time.isoformat(),
                "hourly_breakdown": [],
                "total_cost": 0.0,
                "total_calls": 0,
            }

    async def reset_budgets(self, period: Optional[str] = None) -> bool:
        """Reset budget tracking (admin function)"""
        await self._ensure_redis()

        try:
            patterns = []
            if period:
                patterns.append(f"api_cost:{period}:*")
                patterns.append(f"api_count:{period}:*")
            else:
                patterns.extend(
                    [
                        "api_cost:hour:*",
                        "api_cost:day:*",
                        "api_cost:month:*",
                        "api_count:hour:*",
                        "api_count:day:*",
                        "api_count:month:*",
                    ]
                )

            for pattern in patterns:
                async for key in self.redis.scan_iter(match=pattern):
                    await self.redis.delete(key)

            logger.info(f"Reset budget tracking for period: {period or 'all'}")
            return True
        except Exception as e:
            logger.error(f"Failed to reset budgets: {e}")
            return False


# Singleton instance
_cost_monitor_instance: Optional[GoogleAPICostMonitor] = None


async def get_cost_monitor() -> GoogleAPICostMonitor:
    """Get or create the singleton cost monitor instance"""
    global _cost_monitor_instance
    if _cost_monitor_instance is None:
        _cost_monitor_instance = GoogleAPICostMonitor()
    return _cost_monitor_instance
