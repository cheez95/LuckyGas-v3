"""
Custom Prometheus metrics for Lucky Gas monitoring with Google Cloud Monitoring integration
"""

import logging
import os
from typing import Optional

from prometheus_client import Counter, Gauge, Histogram, Info, Summary

from app.core.config import settings

logger = logging.getLogger(__name__)

# Business metrics
prediction_counter = Counter(
    "lucky_gas_predictions_total",
    "Total number of predictions generated",
    ["customer_type", "status"],
)

route_optimization_histogram = Histogram(
    "lucky_gas_route_optimization_duration_seconds",
    "Time spent optimizing routes",
    ["method", "num_stops"],
    buckets=(0.5, 1, 2, 5, 10, 30, 60, 120),
)

vrp_optimization_summary = Summary(
    "lucky_gas_vrp_optimization_summary",
    "VRP optimization performance summary",
    ["optimization_mode", "clustered"],
)

vrp_solution_quality_gauge = Gauge(
    "lucky_gas_vrp_solution_quality",
    "Quality metrics for VRP solutions",
    ["metric_type"],  # savings_percentage, efficiency_score, unassigned_ratio
)

vrp_constraint_violations_counter = Counter(
    "lucky_gas_vrp_constraint_violations_total",
    "Number of constraint violations in VRP solutions",
    ["constraint_type"],  # time_window, capacity, shift_time
)

route_adjustment_counter = Counter(
    "lucky_gas_route_adjustments_total",
    "Total number of route adjustments made",
    ["adjustment_type", "trigger"],
)

route_adjustment_summary = Summary(
    "lucky_gas_route_adjustment_duration_seconds",
    "Time spent on route adjustments",
    ["adjustment_type"],
)

active_deliveries_gauge = Gauge(
    "lucky_gas_active_deliveries", "Number of active deliveries", ["area", "driver"]
)

orders_created_counter = Counter(
    "lucky_gas_orders_created_total",
    "Total number of orders created",
    ["order_type", "customer_type"],
)

cache_operations_counter = Counter(
    "lucky_gas_cache_operations_total",
    "Total number of cache operations",
    ["operation", "status", "api_type"],
)

background_tasks_counter = Counter(
    "lucky_gas_background_tasks_total",
    "Total number of background tasks",
    ["task_type", "status"],
)

# Business KPIs
revenue_counter = Counter(
    "lucky_gas_revenue_total",
    "Total revenue in TWD",
    ["payment_method", "customer_type"],
)

cylinders_delivered_counter = Counter(
    "lucky_gas_cylinders_delivered_total",
    "Total number of cylinders delivered",
    ["size", "area"],
)

customer_satisfaction_gauge = Gauge(
    "lucky_gas_customer_satisfaction_score",
    "Customer satisfaction score (1-5)",
    ["area", "customer_type"],
)

delivery_time_histogram = Histogram(
    "lucky_gas_delivery_time_seconds",
    "Time from order to delivery",
    ["area", "is_urgent"],
    buckets=(3600, 7200, 14400, 28800, 43200, 86400),  # 1h, 2h, 4h, 8h, 12h, 24h
)

# API Performance metrics
api_request_counter = Counter(
    "lucky_gas_api_requests_total",
    "Total API requests",
    ["method", "endpoint", "status_code"],
)

api_request_duration_histogram = Histogram(
    "lucky_gas_api_request_duration_seconds",
    "API request duration",
    ["method", "endpoint"],
    buckets=(0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1, 2.5, 5),
)

# Database performance
db_query_counter = Counter(
    "lucky_gas_db_queries_total", "Total database queries", ["operation", "table"]
)

db_query_duration_histogram = Histogram(
    "lucky_gas_db_query_duration_seconds",
    "Database query duration",
    ["operation", "table"],
    buckets=(0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1),
)

db_connection_pool_gauge = Gauge(
    "lucky_gas_db_connection_pool_size",
    "Database connection pool status",
    ["status"],  # active, idle, overflow
)

# Authentication & Security
auth_attempts_counter = Counter(
    "lucky_gas_auth_attempts_total",
    "Total authentication attempts",
    ["result", "method"],
)

active_sessions_gauge = Gauge(
    "lucky_gas_active_sessions", "Number of active user sessions", ["role"]
)

# Inventory metrics
inventory_gauge = Gauge(
    "lucky_gas_inventory_cylinders",
    "Current cylinder inventory",
    ["size", "location", "status"],
)

low_inventory_alerts_counter = Counter(
    "lucky_gas_low_inventory_alerts_total",
    "Low inventory alerts triggered",
    ["size", "location"],
)

# Driver performance
driver_deliveries_counter = Counter(
    "lucky_gas_driver_deliveries_total",
    "Total deliveries by driver",
    ["driver_id", "status"],
)

driver_efficiency_gauge = Gauge(
    "lucky_gas_driver_efficiency_score",
    "Driver efficiency score (deliveries per hour)",
    ["driver_id"],
)

# Error tracking
error_counter = Counter(
    "lucky_gas_errors_total", "Total errors", ["error_type", "severity", "component"]
)

# External service metrics
google_api_calls_counter = Counter(
    "lucky_gas_google_api_calls_total", "Google API calls", ["api_type", "status"]
)

google_api_latency_histogram = Histogram(
    "lucky_gas_google_api_latency_seconds",
    "Google API call latency",
    ["api_type"],
    buckets=(0.1, 0.25, 0.5, 1, 2, 5, 10),
)

# WebSocket metrics
websocket_connections_gauge = Gauge(
    "lucky_gas_websocket_connections", "Active WebSocket connections", ["client_type"]
)

websocket_messages_counter = Counter(
    "lucky_gas_websocket_messages_total",
    "WebSocket messages sent/received",
    ["direction", "message_type"],
)

# System info
system_info = Info("lucky_gas_system", "Lucky Gas system information")
system_info.info(
    {
        "version": "1.0.0",
        "environment": settings.ENVIRONMENT.value,
        "framework": "FastAPI",
        "project": settings.PROJECT_NAME,
    }
)


# Initialize Google Cloud Monitoring if available
_cloud_metrics = None


def get_cloud_metrics():
    """Get or initialize Cloud Monitoring metrics collector"""
    global _cloud_metrics
    if _cloud_metrics is None and os.getenv("GCP_PROJECT_ID"):
        try:
            # Import at runtime to avoid dependency issues
            import sys
            from pathlib import Path

            sys.path.insert(0, str(Path(__file__).parent.parent.parent))
            from infrastructure.monitoring.metrics_config import get_metrics_collector

            _cloud_metrics = get_metrics_collector()
            logger.info("Initialized Google Cloud Monitoring")
        except Exception as e:
            logger.warning(f"Could not initialize Cloud Monitoring: {e}")
    return _cloud_metrics


# Enhanced metric recording functions with Cloud Monitoring integration
def record_prediction(customer_type: str, status: str):
    """Record prediction generation in both Prometheus and Cloud Monitoring"""
    prediction_counter.labels(customer_type=customer_type, status=status).inc()

    cloud_metrics = get_cloud_metrics()
    if cloud_metrics and status == "success":
        cloud_metrics.record_order_created("predicted", customer_type)


def record_route_optimization(
    method: str, num_stops: int, duration: float, efficiency: float = 0.0
):
    """Record route optimization metrics"""
    route_optimization_histogram.labels(
        method=method, num_stops=str(num_stops)
    ).observe(duration)

    cloud_metrics = get_cloud_metrics()
    if cloud_metrics:
        cloud_metrics.record_route_optimization(duration, efficiency)


def record_delivery_completed(driver_id: str, area: str, status: str = "completed"):
    """Record delivery completion"""
    driver_deliveries_counter.labels(driver_id=driver_id, status=status).inc()

    cloud_metrics = get_cloud_metrics()
    if cloud_metrics:
        cloud_metrics.record_delivery_completed(driver_id, area)


def record_order_created(order_type: str, customer_type: str):
    """Record order creation"""
    orders_created_counter.labels(
        order_type=order_type, customer_type=customer_type
    ).inc()

    cloud_metrics = get_cloud_metrics()
    if cloud_metrics:
        cloud_metrics.record_order_created(order_type, customer_type)


def record_revenue(amount: float, payment_method: str, customer_type: str):
    """Record revenue"""
    revenue_counter.labels(
        payment_method=payment_method, customer_type=customer_type
    ).inc(amount)

    cloud_metrics = get_cloud_metrics()
    if cloud_metrics:
        cloud_metrics.record_revenue(amount, customer_type, payment_method)


def record_google_api_call(
    api_type: str, status: str, latency: float, cost: Optional[float] = None
):
    """Record Google API usage"""
    google_api_calls_counter.labels(api_type=api_type, status=status).inc()
    google_api_latency_histogram.labels(api_type=api_type).observe(latency)

    cloud_metrics = get_cloud_metrics()
    if cloud_metrics:
        cloud_metrics.record_google_api_call(api_type, status, cost)


def record_api_request(method: str, endpoint: str, status_code: int, duration: float):
    """Record API request metrics"""
    api_request_counter.labels(
        method=method, endpoint=endpoint, status_code=str(status_code)
    ).inc()
    api_request_duration_histogram.labels(method=method, endpoint=endpoint).observe(
        duration
    )

    cloud_metrics = get_cloud_metrics()
    if cloud_metrics:
        cloud_metrics.record_request(method, endpoint, status_code, duration)


def set_cache_metrics(hits: int, misses: int):
    """Set cache performance metrics"""
    total = hits + misses
    if total > 0:
        hit_rate = (hits / total) * 100
        cloud_metrics = get_cloud_metrics()
        if cloud_metrics:
            cloud_metrics.set_cache_hit_rate(hit_rate)


def set_prediction_accuracy(accuracy: float):
    """Set ML prediction accuracy"""
    cloud_metrics = get_cloud_metrics()
    if cloud_metrics:
        cloud_metrics.set_prediction_accuracy(accuracy)
