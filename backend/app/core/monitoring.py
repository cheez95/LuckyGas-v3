"""
Monitoring and observability setup for Lucky Gas backend.
Includes Sentry, OpenTelemetry, and custom metrics.
"""

import logging
import os
from typing import Any, Dict, Optional

import sentry_sdk
from sentry_sdk.integrations.asgi import SentryAsgiMiddleware
from sentry_sdk.integrations.fastapi import FastApiIntegration
from sentry_sdk.integrations.sqlalchemy import SqlalchemyIntegration
from sentry_sdk.integrations.redis import RedisIntegration
from sentry_sdk.integrations.logging import LoggingIntegration

from opentelemetry import trace
from opentelemetry.exporter.cloud_trace import CloudTraceSpanExporter
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.redis import RedisInstrumentor
from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor
from opentelemetry.instrumentation.requests import RequestsInstrumentor
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.sdk.resources import Resource

from prometheus_client import Counter, Histogram, Gauge, generate_latest
from prometheus_client.core import CollectorRegistry

from .config import settings

# Logger setup
logger = logging.getLogger(__name__)

# Prometheus metrics
REGISTRY = CollectorRegistry()

request_count = Counter(
    'luckygas_http_requests_total',
    'Total HTTP requests',
    ['method', 'endpoint', 'status_code'],
    registry=REGISTRY
)

request_duration = Histogram(
    'luckygas_http_request_duration_seconds',
    'HTTP request duration',
    ['method', 'endpoint'],
    registry=REGISTRY
)

active_orders = Gauge(
    'luckygas_active_orders',
    'Number of active orders',
    registry=REGISTRY
)

delivery_duration = Histogram(
    'luckygas_delivery_duration_minutes',
    'Delivery completion time in minutes',
    ['driver_id', 'route_type'],
    registry=REGISTRY
)

prediction_accuracy = Gauge(
    'luckygas_prediction_accuracy',
    'AI prediction accuracy percentage',
    ['model_type'],
    registry=REGISTRY
)

websocket_connections = Gauge(
    'luckygas_websocket_connections',
    'Active WebSocket connections',
    ['connection_type'],
    registry=REGISTRY
)


def init_sentry(
    dsn: Optional[str] = None,
    environment: Optional[str] = None,
    release: Optional[str] = None
) -> None:
    """Initialize Sentry error tracking."""
    
    if not dsn:
        dsn = settings.SENTRY_DSN
    
    if not dsn:
        logger.warning("Sentry DSN not configured, skipping initialization")
        return
    
    sentry_sdk.init(
        dsn=dsn,
        environment=environment or settings.ENVIRONMENT,
        release=release or settings.VERSION,
        traces_sample_rate=0.1 if settings.ENVIRONMENT == "production" else 1.0,
        profiles_sample_rate=0.1 if settings.ENVIRONMENT == "production" else 1.0,
        integrations=[
            FastApiIntegration(
                transaction_style="endpoint",
                failed_request_status_codes={400, 401, 403, 404, 405, 500, 502, 503, 504}
            ),
            SqlalchemyIntegration(),
            RedisIntegration(),
            LoggingIntegration(
                level=logging.INFO,
                event_level=logging.ERROR
            ),
        ],
        before_send=before_send_filter,
        attach_stacktrace=True,
        send_default_pii=False,  # Respect user privacy
    )
    
    logger.info(f"Sentry initialized for environment: {settings.ENVIRONMENT}")


def before_send_filter(event: Dict[str, Any], hint: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Filter sensitive data before sending to Sentry."""
    
    # Filter out sensitive headers
    if 'request' in event and 'headers' in event['request']:
        headers = event['request']['headers']
        sensitive_headers = ['authorization', 'cookie', 'x-api-key']
        for header in sensitive_headers:
            if header in headers:
                headers[header] = '[FILTERED]'
    
    # Filter out sensitive query params
    if 'request' in event and 'query_string' in event['request']:
        # Implement query string filtering if needed
        pass
    
    # Filter out PII from exception values
    if 'exception' in event and 'values' in event['exception']:
        for exception in event['exception']['values']:
            if 'stacktrace' in exception and 'frames' in exception['stacktrace']:
                for frame in exception['stacktrace']['frames']:
                    if 'vars' in frame:
                        # Filter sensitive variables
                        sensitive_vars = ['password', 'token', 'secret', 'api_key']
                        for var in sensitive_vars:
                            if var in frame['vars']:
                                frame['vars'][var] = '[FILTERED]'
    
    return event


def init_opentelemetry() -> None:
    """Initialize OpenTelemetry for distributed tracing."""
    
    if not settings.ENABLE_TRACING:
        logger.info("OpenTelemetry tracing disabled")
        return
    
    # Create resource
    resource = Resource.create({
        "service.name": "luckygas-backend",
        "service.version": settings.VERSION,
        "deployment.environment": settings.ENVIRONMENT,
    })
    
    # Set up tracer provider
    tracer_provider = TracerProvider(resource=resource)
    trace.set_tracer_provider(tracer_provider)
    
    # Add Cloud Trace exporter for GCP
    if settings.GCP_PROJECT_ID:
        cloud_trace_exporter = CloudTraceSpanExporter(
            project_id=settings.GCP_PROJECT_ID
        )
        tracer_provider.add_span_processor(
            BatchSpanProcessor(cloud_trace_exporter)
        )
    
    # Instrument libraries
    FastAPIInstrumentor.instrument_app(None)  # Will be set in main.py
    RedisInstrumentor().instrument()
    SQLAlchemyInstrumentor().instrument()
    RequestsInstrumentor().instrument()
    
    logger.info("OpenTelemetry tracing initialized")


def track_request(method: str, endpoint: str, status_code: int, duration: float) -> None:
    """Track HTTP request metrics."""
    request_count.labels(
        method=method,
        endpoint=endpoint,
        status_code=str(status_code)
    ).inc()
    
    request_duration.labels(
        method=method,
        endpoint=endpoint
    ).observe(duration)


def track_order_metrics(active: int) -> None:
    """Track order-related metrics."""
    active_orders.set(active)


def track_delivery_metrics(driver_id: str, route_type: str, duration_minutes: float) -> None:
    """Track delivery performance metrics."""
    delivery_duration.labels(
        driver_id=driver_id,
        route_type=route_type
    ).observe(duration_minutes)


def track_prediction_metrics(model_type: str, accuracy: float) -> None:
    """Track AI prediction metrics."""
    prediction_accuracy.labels(
        model_type=model_type
    ).set(accuracy)


def track_websocket_metrics(connection_type: str, count: int) -> None:
    """Track WebSocket connection metrics."""
    websocket_connections.labels(
        connection_type=connection_type
    ).set(count)


def get_metrics() -> bytes:
    """Generate Prometheus metrics."""
    return generate_latest(REGISTRY)


# Custom exception tracking
def track_exception(
    exception: Exception,
    context: Optional[Dict[str, Any]] = None,
    user_id: Optional[int] = None
) -> None:
    """Track custom exceptions with additional context."""
    
    with sentry_sdk.push_scope() as scope:
        if context:
            for key, value in context.items():
                scope.set_context(key, value)
        
        if user_id:
            scope.set_user({"id": user_id})
        
        sentry_sdk.capture_exception(exception)


# Performance monitoring
def track_performance(
    operation: str,
    duration: float,
    tags: Optional[Dict[str, str]] = None
) -> None:
    """Track custom performance metrics."""
    
    with sentry_sdk.start_transaction(
        op=f"custom.{operation}",
        name=operation
    ) as transaction:
        if tags:
            for key, value in tags.items():
                transaction.set_tag(key, value)
        
        transaction.set_measurement("duration", duration, "millisecond")


# Initialize monitoring on module import
def init_monitoring():
    """Initialize all monitoring systems."""
    init_sentry()
    init_opentelemetry()
    logger.info("Monitoring systems initialized")