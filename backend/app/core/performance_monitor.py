"""
Performance Monitoring Utilities
Tracks API response times, bundle sizes, and system metrics
"""

import time
import psutil
import asyncio
import logging
from typing import Dict, List, Optional, Any, Callable
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from functools import wraps
from collections import deque
import json

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

logger = logging.getLogger(__name__)


@dataclass
class PerformanceMetric:
    """Performance metric data structure."""
    endpoint: str
    method: str
    response_time: float
    status_code: int
    timestamp: datetime
    cpu_usage: float
    memory_usage: float
    request_size: int
    response_size: int
    user_id: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        data = asdict(self)
        data['timestamp'] = self.timestamp.isoformat()
        return data


class PerformanceMonitor:
    """
    Central performance monitoring system.
    Tracks metrics and alerts on regressions.
    """
    
    def __init__(
        self,
        window_size: int = 1000,
        alert_threshold: float = 0.1,  # 10% regression threshold
        baseline_file: str = "performance_baseline.json"
    ):
        self.metrics: deque = deque(maxlen=window_size)
        self.alert_threshold = alert_threshold
        self.baseline_file = baseline_file
        self.baselines: Dict[str, float] = self._load_baselines()
        self.alerts: List[Dict[str, Any]] = []
        self._aggregated_stats: Dict[str, Dict[str, Any]] = {}
        
    def _load_baselines(self) -> Dict[str, float]:
        """Load performance baselines from file."""
        try:
            with open(self.baseline_file, 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            logger.info("No baseline file found, starting fresh")
            return {}
        except Exception as e:
            logger.error(f"Error loading baselines: {e}")
            return {}
    
    def save_baselines(self):
        """Save current baselines to file."""
        try:
            with open(self.baseline_file, 'w') as f:
                json.dump(self.baselines, f, indent=2)
            logger.info(f"Saved {len(self.baselines)} baselines")
        except Exception as e:
            logger.error(f"Error saving baselines: {e}")
    
    def record_metric(self, metric: PerformanceMetric):
        """
        Record a performance metric and check for regressions.
        
        Args:
            metric: Performance metric to record
        """
        self.metrics.append(metric)
        
        # Check for regression
        endpoint_key = f"{metric.method}:{metric.endpoint}"
        
        if endpoint_key in self.baselines:
            baseline = self.baselines[endpoint_key]
            if metric.response_time > baseline * (1 + self.alert_threshold):
                self._create_alert(
                    endpoint_key,
                    baseline,
                    metric.response_time,
                    "response_time"
                )
        
        # Update aggregated stats
        self._update_stats(endpoint_key, metric)
    
    def _update_stats(self, endpoint_key: str, metric: PerformanceMetric):
        """Update aggregated statistics for an endpoint."""
        if endpoint_key not in self._aggregated_stats:
            self._aggregated_stats[endpoint_key] = {
                'count': 0,
                'total_time': 0,
                'max_time': 0,
                'min_time': float('inf'),
                'errors': 0,
                'last_updated': datetime.utcnow()
            }
        
        stats = self._aggregated_stats[endpoint_key]
        stats['count'] += 1
        stats['total_time'] += metric.response_time
        stats['max_time'] = max(stats['max_time'], metric.response_time)
        stats['min_time'] = min(stats['min_time'], metric.response_time)
        stats['last_updated'] = datetime.utcnow()
        
        if metric.status_code >= 400:
            stats['errors'] += 1
    
    def _create_alert(
        self,
        endpoint: str,
        baseline: float,
        current: float,
        metric_type: str
    ):
        """Create a performance regression alert."""
        alert = {
            'timestamp': datetime.utcnow().isoformat(),
            'endpoint': endpoint,
            'metric_type': metric_type,
            'baseline': baseline,
            'current': current,
            'regression_percent': ((current - baseline) / baseline) * 100,
            'severity': 'high' if current > baseline * 1.5 else 'medium'
        }
        
        self.alerts.append(alert)
        logger.warning(
            f"Performance regression detected for {endpoint}: "
            f"{metric_type} increased by {alert['regression_percent']:.1f}% "
            f"(baseline: {baseline:.3f}s, current: {current:.3f}s)"
        )
    
    def set_baseline(self, endpoint: str, response_time: float):
        """Set performance baseline for an endpoint."""
        self.baselines[endpoint] = response_time
        logger.info(f"Set baseline for {endpoint}: {response_time:.3f}s")
    
    def update_baselines_from_metrics(self, percentile: int = 50):
        """Update baselines from recent metrics using percentile."""
        from collections import defaultdict
        import numpy as np
        
        endpoint_times = defaultdict(list)
        
        for metric in self.metrics:
            endpoint_key = f"{metric.method}:{metric.endpoint}"
            endpoint_times[endpoint_key].append(metric.response_time)
        
        for endpoint, times in endpoint_times.items():
            if len(times) >= 10:  # Need minimum samples
                baseline = np.percentile(times, percentile)
                self.baselines[endpoint] = baseline
                logger.info(f"Updated baseline for {endpoint}: {baseline:.3f}s")
        
        self.save_baselines()
    
    def get_statistics(self, endpoint: Optional[str] = None) -> Dict[str, Any]:
        """
        Get performance statistics.
        
        Args:
            endpoint: Optional specific endpoint to get stats for
        
        Returns:
            Dictionary of statistics
        """
        if endpoint:
            stats = self._aggregated_stats.get(endpoint, {})
            if stats and stats['count'] > 0:
                stats['avg_time'] = stats['total_time'] / stats['count']
                stats['error_rate'] = stats['errors'] / stats['count']
            return stats
        
        # Overall statistics
        total_requests = len(self.metrics)
        if total_requests == 0:
            return {}
        
        response_times = [m.response_time for m in self.metrics]
        errors = sum(1 for m in self.metrics if m.status_code >= 400)
        
        import numpy as np
        return {
            'total_requests': total_requests,
            'avg_response_time': np.mean(response_times),
            'median_response_time': np.median(response_times),
            'p95_response_time': np.percentile(response_times, 95),
            'p99_response_time': np.percentile(response_times, 99),
            'max_response_time': max(response_times),
            'min_response_time': min(response_times),
            'error_rate': errors / total_requests,
            'endpoints_tracked': len(self._aggregated_stats),
            'active_alerts': len(self.alerts)
        }
    
    def get_recent_alerts(self, hours: int = 24) -> List[Dict[str, Any]]:
        """Get recent performance alerts."""
        cutoff = datetime.utcnow() - timedelta(hours=hours)
        return [
            alert for alert in self.alerts
            if datetime.fromisoformat(alert['timestamp']) > cutoff
        ]
    
    def clear_alerts(self):
        """Clear all alerts."""
        self.alerts.clear()
        logger.info("Cleared all performance alerts")


class PerformanceMiddleware(BaseHTTPMiddleware):
    """
    FastAPI middleware for automatic performance monitoring.
    """
    
    def __init__(
        self,
        app: ASGIApp,
        monitor: PerformanceMonitor,
        exclude_paths: List[str] = None
    ):
        super().__init__(app)
        self.monitor = monitor
        self.exclude_paths = exclude_paths or ['/health', '/metrics', '/docs']
    
    async def dispatch(self, request: Request, call_next):
        # Skip excluded paths
        if any(request.url.path.startswith(path) for path in self.exclude_paths):
            return await call_next(request)
        
        # Start timing
        start_time = time.time()
        
        # Get system metrics
        cpu_usage = psutil.cpu_percent(interval=0)
        memory_usage = psutil.virtual_memory().percent
        
        # Get request size
        request_size = int(request.headers.get('content-length', 0))
        
        # Process request
        response = await call_next(request)
        
        # Calculate response time
        response_time = time.time() - start_time
        
        # Get response size
        response_body = b""
        async for chunk in response.body_iterator:
            response_body += chunk
        response_size = len(response_body)
        
        # Create new response with body
        response = Response(
            content=response_body,
            status_code=response.status_code,
            headers=dict(response.headers),
            media_type=response.media_type
        )
        
        # Extract user ID if available
        user_id = None
        if hasattr(request.state, 'user'):
            user_id = getattr(request.state.user, 'id', None)
        
        # Record metric
        metric = PerformanceMetric(
            endpoint=str(request.url.path),
            method=request.method,
            response_time=response_time,
            status_code=response.status_code,
            timestamp=datetime.utcnow(),
            cpu_usage=cpu_usage,
            memory_usage=memory_usage,
            request_size=request_size,
            response_size=response_size,
            user_id=user_id
        )
        
        self.monitor.record_metric(metric)
        
        # Add performance headers
        response.headers['X-Response-Time'] = f"{response_time:.3f}"
        response.headers['X-Server-Load'] = f"CPU:{cpu_usage:.1f}%,Memory:{memory_usage:.1f}%"
        
        return response


def timing_decorator(
    name: Optional[str] = None,
    threshold: float = 1.0
) -> Callable:
    """
    Decorator to measure function execution time.
    
    Args:
        name: Custom name for the metric
        threshold: Alert threshold in seconds
    
    Example:
        @timing_decorator(name="complex_calculation", threshold=2.0)
        async def calculate_something():
            pass
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            start_time = time.time()
            try:
                result = await func(*args, **kwargs)
                return result
            finally:
                execution_time = time.time() - start_time
                metric_name = name or func.__name__
                
                if execution_time > threshold:
                    logger.warning(
                        f"Performance threshold exceeded for {metric_name}: "
                        f"{execution_time:.3f}s (threshold: {threshold}s)"
                    )
                else:
                    logger.debug(f"{metric_name} executed in {execution_time:.3f}s")
        
        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            start_time = time.time()
            try:
                result = func(*args, **kwargs)
                return result
            finally:
                execution_time = time.time() - start_time
                metric_name = name or func.__name__
                
                if execution_time > threshold:
                    logger.warning(
                        f"Performance threshold exceeded for {metric_name}: "
                        f"{execution_time:.3f}s (threshold: {threshold}s)"
                    )
                else:
                    logger.debug(f"{metric_name} executed in {execution_time:.3f}s")
        
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper
    
    return decorator


class BundleSizeMonitor:
    """
    Monitor frontend bundle sizes for regressions.
    """
    
    def __init__(
        self,
        baseline_file: str = "bundle_baseline.json",
        alert_threshold: float = 0.1  # 10% increase threshold
    ):
        self.baseline_file = baseline_file
        self.alert_threshold = alert_threshold
        self.baselines = self._load_baselines()
        self.measurements: List[Dict[str, Any]] = []
    
    def _load_baselines(self) -> Dict[str, int]:
        """Load bundle size baselines."""
        try:
            with open(self.baseline_file, 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            return {}
        except Exception as e:
            logger.error(f"Error loading bundle baselines: {e}")
            return {}
    
    def record_bundle_size(
        self,
        bundle_name: str,
        size_bytes: int,
        gzipped_size: Optional[int] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Record bundle size and check for regression.
        
        Args:
            bundle_name: Name of the bundle
            size_bytes: Size in bytes
            gzipped_size: Optional gzipped size
        
        Returns:
            Alert dict if regression detected, None otherwise
        """
        measurement = {
            'bundle_name': bundle_name,
            'size_bytes': size_bytes,
            'gzipped_size': gzipped_size,
            'timestamp': datetime.utcnow().isoformat()
        }
        
        self.measurements.append(measurement)
        
        # Check for regression
        if bundle_name in self.baselines:
            baseline = self.baselines[bundle_name]
            if size_bytes > baseline * (1 + self.alert_threshold):
                increase_percent = ((size_bytes - baseline) / baseline) * 100
                alert = {
                    'bundle_name': bundle_name,
                    'baseline_size': baseline,
                    'current_size': size_bytes,
                    'increase_percent': increase_percent,
                    'increase_kb': (size_bytes - baseline) / 1024
                }
                
                logger.warning(
                    f"Bundle size regression for {bundle_name}: "
                    f"increased by {increase_percent:.1f}% "
                    f"({alert['increase_kb']:.1f} KB)"
                )
                
                return alert
        
        return None
    
    def set_baseline(self, bundle_name: str, size_bytes: int):
        """Set bundle size baseline."""
        self.baselines[bundle_name] = size_bytes
        self._save_baselines()
    
    def _save_baselines(self):
        """Save baselines to file."""
        try:
            with open(self.baseline_file, 'w') as f:
                json.dump(self.baselines, f, indent=2)
        except Exception as e:
            logger.error(f"Error saving bundle baselines: {e}")
    
    def get_report(self) -> Dict[str, Any]:
        """Get bundle size report."""
        return {
            'baselines': self.baselines,
            'recent_measurements': self.measurements[-10:],
            'total_baseline_size': sum(self.baselines.values()),
            'bundle_count': len(self.baselines)
        }


# Global instances
_performance_monitor: Optional[PerformanceMonitor] = None
_bundle_monitor: Optional[BundleSizeMonitor] = None


def get_performance_monitor() -> PerformanceMonitor:
    """Get global performance monitor instance."""
    global _performance_monitor
    if _performance_monitor is None:
        _performance_monitor = PerformanceMonitor()
    return _performance_monitor


def get_bundle_monitor() -> BundleSizeMonitor:
    """Get global bundle size monitor instance."""
    global _bundle_monitor
    if _bundle_monitor is None:
        _bundle_monitor = BundleSizeMonitor()
    return _bundle_monitor