"""
Monitoring and tracking utilities for security events, API usage, and webhooks.
"""

import asyncio
import logging
import time
from collections import defaultdict
from datetime import datetime, timedelta
from typing import Any, Dict, Optional

from sqlalchemy import func, select

from app.core.config import settings
from app.models.audit import AuditAction, AuditLog
from app.models.webhook import WebhookLog
from app.api.deps import get_db

logger = logging.getLogger(__name__)


class SecurityMonitor:
    """Monitor security events and detect anomalies."""

    def __init__(self):
        self._failed_auth_attempts = defaultdict(list)  # IP -> timestamps
        self._webhook_failures = defaultdict(int)  # provider -> count
        self._api_usage = defaultdict(
            lambda: defaultdict(int)
        )  # user_id -> endpoint -> count
        self._alert_queue = asyncio.Queue()
        self._monitoring_task = None

    async def start(self):
        """Start monitoring tasks."""
        self._monitoring_task = asyncio.create_task(self._monitor_loop())

    async def stop(self):
        """Stop monitoring tasks."""
        if self._monitoring_task:
            self._monitoring_task.cancel()

    async def _monitor_loop(self):
        """Main monitoring loop."""
        while True:
            try:
                # Check for anomalies every minute
                await asyncio.sleep(60)
                await self._check_failed_auth_anomalies()
                await self._check_webhook_anomalies()
                await self._check_api_usage_anomalies()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in monitoring loop: {e}")

    async def _check_failed_auth_anomalies(self):
        """Check for brute force attempts."""
        current_time = time.time()

        for ip, attempts in list(self._failed_auth_attempts.items()):
            # Remove old attempts (older than 1 hour)
            recent_attempts = [t for t in attempts if current_time - t < 3600]

            if len(recent_attempts) > 10:  # More than 10 failures in an hour
                await self._send_alert(
                    {
                        "type": "brute_force_attempt",
                        "ip": ip,
                        "attempts": len(recent_attempts),
                        "severity": "high",
                    }
                )
                # Clear after alerting to avoid duplicate alerts
                del self._failed_auth_attempts[ip]
            else:
                self._failed_auth_attempts[ip] = recent_attempts

    async def _check_webhook_anomalies(self):
        """Check for webhook processing issues."""
        for provider, failure_count in self._webhook_failures.items():
            if failure_count > 5:  # More than 5 failures
                await self._send_alert(
                    {
                        "type": "webhook_failures",
                        "provider": provider,
                        "failure_count": failure_count,
                        "severity": "medium",
                    }
                )
                self._webhook_failures[provider] = 0  # Reset counter

    async def _check_api_usage_anomalies(self):
        """Check for unusual API usage patterns."""
        for user_id, endpoints in self._api_usage.items():
            total_requests = sum(endpoints.values())

            if total_requests > 1000:  # More than 1000 requests per minute
                await self._send_alert(
                    {
                        "type": "excessive_api_usage",
                        "user_id": user_id,
                        "request_count": total_requests,
                        "endpoints": dict(endpoints),
                        "severity": "medium",
                    }
                )
                self._api_usage[user_id].clear()

    async def _send_alert(self, alert: dict):
        """Send security alert."""
        alert["timestamp"] = datetime.utcnow().isoformat()
        await self._alert_queue.put(alert)

        # Log alert
        logger.warning(f"Security alert: {alert}")

        # TODO: Send to monitoring service (e.g., Cloud Monitoring, PagerDuty)
        if settings.ENVIRONMENT == "production":
            # Send to external monitoring
            pass

    def track_failed_auth(self, ip: str):
        """Track failed authentication attempt."""
        self._failed_auth_attempts[ip].append(time.time())

    def track_webhook_failure(self, provider: str):
        """Track webhook processing failure."""
        self._webhook_failures[provider] += 1

    def track_api_usage(self, user_id: int, endpoint: str):
        """Track API usage."""
        self._api_usage[user_id][endpoint] += 1

    async def get_alerts(self, limit: int = 10) -> list:
        """Get recent alerts."""
        alerts = []
        try:
            while len(alerts) < limit and not self._alert_queue.empty():
                alert = await asyncio.wait_for(self._alert_queue.get(), timeout=0.1)
                alerts.append(alert)
        except asyncio.TimeoutError:
            pass
        return alerts


# Global monitor instance
security_monitor = SecurityMonitor()


async def track_webhook_event(
    provider: str,
    event_type: str,
    status: str,
    metadata: Optional[Dict[str, Any]] = None,
):
    """Track webhook event for monitoring."""
    try:
        if status in ["rejected", "failed"]:
            security_monitor.track_webhook_failure(provider)

        # Log to database for audit trail
        async for db in get_db():
            audit_log = AuditLog(
                action=AuditAction.WEBHOOK_RECEIVED,
                resource_type="webhook",
                resource_id=f"{provider}:{event_type}",
                details={
                    "provider": provider,
                    "event_type": event_type,
                    "status": status,
                    "metadata": metadata or {},
                },
                performed_at=datetime.utcnow(),
            )
            db.add(audit_log)
            await db.commit()
    except Exception as e:
        logger.error(f"Failed to track webhook event: {e}")


async def track_api_usage(
    user_id: int,
    api_name: str,
    endpoint: str,
    request_params: dict,
    response_time: float,
    cached: bool = False,
):
    """Track API usage for monitoring and billing."""
    try:
        security_monitor.track_api_usage(user_id, f"{api_name}:{endpoint}")

        # Log to database for usage tracking
        async for db in get_db():
            # TODO: Create APIUsageLog model
            audit_log = AuditLog(
                action=AuditAction.API_CALL,
                resource_type="api",
                resource_id=f"{api_name}:{endpoint}",
                user_id=user_id,
                details={
                    "api_name": api_name,
                    "endpoint": endpoint,
                    "response_time_ms": int(response_time * 1000),
                    "cached": cached,
                    "params_count": len(request_params),
                },
                performed_at=datetime.utcnow(),
            )
            db.add(audit_log)
            await db.commit()
    except Exception as e:
        logger.error(f"Failed to track API usage: {e}")


async def track_failed_authentication(
    username: Optional[str], ip_address: str, reason: str
):
    """Track failed authentication attempts."""
    try:
        security_monitor.track_failed_auth(ip_address)

        # Log to database
        async for db in get_db():
            audit_log = AuditLog(
                action=AuditAction.LOGIN_FAILED,
                resource_type="auth",
                resource_id=username or "unknown",
                details={"ip_address": ip_address, "reason": reason},
                performed_at=datetime.utcnow(),
            )
            db.add(audit_log)
            await db.commit()
    except Exception as e:
        logger.error(f"Failed to track authentication failure: {e}")


async def get_security_metrics(hours: int = 24) -> dict:
    """Get security metrics for the specified time period."""
    try:
        since = datetime.utcnow() - timedelta(hours=hours)

        async for db in get_db():
            # Count webhook events
            webhook_stats = await db.execute(
                select(
                    WebhookLog.provider,
                    WebhookLog.status,
                    func.count(WebhookLog.id).label("count"),
                )
                .where(WebhookLog.received_at >= since)
                .group_by(WebhookLog.provider, WebhookLog.status)
            )

            # Count authentication failures
            auth_failures = await db.execute(
                select(func.count(AuditLog.id)).where(
                    AuditLog.action == AuditAction.LOGIN_FAILED,
                    AuditLog.performed_at >= since,
                )
            )

            # Get recent alerts
            recent_alerts = await security_monitor.get_alerts(limit=20)

            return {
                "period_hours": hours,
                "webhook_stats": [
                    {"provider": row[0], "status": row[1], "count": row[2]}
                    for row in webhook_stats
                ],
                "auth_failures": auth_failures.scalar() or 0,
                "recent_alerts": recent_alerts,
            }
    except Exception as e:
        logger.error(f"Failed to get security metrics: {e}")
        return {"error": str(e), "period_hours": hours}


# Start monitoring on import - DISABLED for testing
# This should be started in the app startup event, not at import time
# asyncio.create_task(security_monitor.start())
