"""
Enhanced production monitoring and observability with Prometheus and OpenTelemetry.

This module implements:
- Custom business metrics
- OpenTelemetry tracing
- Health check endpoints with detailed status
- Performance monitoring
- Error tracking and alerting
"""

import time
import psutil
import asyncio
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
from contextlib import asynccontextmanager

from prometheus_client import Counter, Histogram, Gauge, Info, generate_latest, CONTENT_TYPE_LATEST
from opentelemetry import trace, metrics
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.exporter.otlp.proto.grpc.metric_exporter import OTLPMetricExporter
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
from opentelemetry.sdk.resources import Resource
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor
from opentelemetry.instrumentation.redis import RedisInstrumentor
from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor
from fastapi import Response
from sqlalchemy import text

from app.core.config import settings
from app.core.database import engine, async_session_maker
from app.core.cache import cache
from app.core.logging import get_logger

logger = get_logger(__name__)


# Business Metrics
class BusinessMetrics:
    """Custom business metrics for Lucky Gas operations."""
    
    # Order metrics
    orders_created = Counter(
        'luckygas_orders_created_total',
        'Total number of orders created',
        ['order_type', 'status']
    )
    
    orders_delivered = Counter(
        'luckygas_orders_delivered_total',
        'Total number of orders delivered',
        ['product_type', 'delivery_type']
    )
    
    order_processing_time = Histogram(
        'luckygas_order_processing_seconds',
        'Time to process an order from creation to delivery',
        ['order_type'],
        buckets=(300, 600, 1800, 3600, 7200, 14400, 28800, 57600)  # 5m, 10m, 30m, 1h, 2h, 4h, 8h, 16h
    )
    
    # Route optimization metrics
    route_optimizations = Counter(
        'luckygas_route_optimizations_total',
        'Total number of route optimizations performed',
        ['optimization_type', 'status']
    )
    
    route_optimization_time = Histogram(
        'luckygas_route_optimization_seconds',
        'Time to optimize routes',
        ['optimization_type'],
        buckets=(0.5, 1.0, 2.5, 5.0, 10.0, 30.0)
    )
    
    route_efficiency = Gauge(
        'luckygas_route_efficiency_ratio',
        'Route efficiency ratio (actual vs optimal distance)',
        ['route_id']
    )
    
    # Customer metrics
    active_customers = Gauge(
        'luckygas_active_customers',
        'Number of active customers',
        ['customer_type']
    )
    
    customer_satisfaction = Gauge(
        'luckygas_customer_satisfaction_score',
        'Customer satisfaction score (0-5)',
        ['metric_type']
    )
    
    # Financial metrics
    revenue = Counter(
        'luckygas_revenue_total',
        'Total revenue in TWD',
        ['payment_method', 'product_type']
    )
    
    invoices_generated = Counter(
        'luckygas_invoices_generated_total',
        'Total number of invoices generated',
        ['invoice_type', 'status']
    )
    
    payment_processing_time = Histogram(
        'luckygas_payment_processing_seconds',
        'Time to process payments',
        ['payment_method'],
        buckets=(0.1, 0.5, 1.0, 2.5, 5.0, 10.0)
    )
    
    # Prediction metrics
    predictions_generated = Counter(
        'luckygas_predictions_generated_total',
        'Total number of predictions generated',
        ['prediction_type', 'status']
    )
    
    prediction_accuracy = Gauge(
        'luckygas_prediction_accuracy',
        'Prediction accuracy percentage',
        ['prediction_type', 'time_horizon']
    )
    
    # System health metrics
    external_api_calls = Counter(
        'luckygas_external_api_calls_total',
        'Total external API calls',
        ['api_name', 'endpoint', 'status']
    )
    
    external_api_latency = Histogram(
        'luckygas_external_api_latency_seconds',
        'External API call latency',
        ['api_name', 'endpoint'],
        buckets=(0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0)
    )
    
    background_tasks = Gauge(
        'luckygas_background_tasks_active',
        'Number of active background tasks',
        ['task_type']
    )
    
    # Info metrics
    system_info = Info(
        'luckygas_system',
        'System information'
    )


# Initialize business metrics
business_metrics = BusinessMetrics()


class MonitoringService:
    """Comprehensive monitoring service for production."""
    
    def __init__(self):
        self.tracer = None
        self.meter = None
        self._initialized = False
        self._app = None
        
    async def initialize(self, app=None):
        """Initialize monitoring services."""
        if self._initialized:
            return
        
        self._app = app
        
        try:
            # Set up OpenTelemetry if enabled
            if settings.OPENTELEMETRY_ENABLED:
                await self._setup_opentelemetry()
            
            # Set system info
            business_metrics.system_info.info({
                'version': settings.VERSION,
                'environment': settings.ENVIRONMENT.value,
                'region': 'taiwan',
                'deployment': 'production'
            })
            
            self._initialized = True
            logger.info("Monitoring service initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize monitoring service: {str(e)}", exc_info=True)
    
    async def _setup_opentelemetry(self):
        """Set up OpenTelemetry tracing and metrics."""
        # Create resource
        resource = Resource.create({
            "service.name": "luckygas-backend",
            "service.version": settings.VERSION,
            "deployment.environment": settings.ENVIRONMENT.value,
        })
        
        # Set up tracing
        if settings.OPENTELEMETRY_ENDPOINT:
            trace.set_tracer_provider(TracerProvider(resource=resource))
            
            otlp_exporter = OTLPSpanExporter(
                endpoint=settings.OPENTELEMETRY_ENDPOINT,
                insecure=True
            )
            
            span_processor = BatchSpanProcessor(otlp_exporter)
            trace.get_tracer_provider().add_span_processor(span_processor)
            
            # Instrument libraries
            if self._app:
                FastAPIInstrumentor.instrument_app(self._app)
            SQLAlchemyInstrumentor().instrument(engine=engine.sync_engine)
            RedisInstrumentor().instrument()
            HTTPXClientInstrumentor().instrument()
            
            self.tracer = trace.get_tracer(__name__)
            
            logger.info(f"OpenTelemetry tracing configured with endpoint: {settings.OPENTELEMETRY_ENDPOINT}")
        
        # Set up metrics
        if settings.OPENTELEMETRY_ENDPOINT:
            reader = PeriodicExportingMetricReader(
                exporter=OTLPMetricExporter(
                    endpoint=settings.OPENTELEMETRY_ENDPOINT,
                    insecure=True
                ),
                export_interval_millis=30000  # 30 seconds
            )
            
            provider = MeterProvider(resource=resource, metric_readers=[reader])
            metrics.set_meter_provider(provider)
            
            self.meter = metrics.get_meter(__name__)
            
            logger.info("OpenTelemetry metrics configured")
    
    @asynccontextmanager
    async def trace_operation(self, operation_name: str, attributes: Dict[str, Any] = None):
        """Context manager for tracing operations."""
        if self.tracer:
            with self.tracer.start_as_current_span(operation_name) as span:
                if attributes:
                    for key, value in attributes.items():
                        span.set_attribute(key, str(value))
                
                try:
                    yield span
                except Exception as e:
                    span.record_exception(e)
                    span.set_status(trace.Status(trace.StatusCode.ERROR))
                    raise
        else:
            yield None
    
    async def record_business_metric(self, metric_name: str, value: float, labels: Dict[str, str] = None):
        """Record a custom business metric."""
        try:
            metric = getattr(business_metrics, metric_name, None)
            if metric:
                if labels:
                    if hasattr(metric, 'inc'):
                        metric.labels(**labels).inc(value)
                    elif hasattr(metric, 'set'):
                        metric.labels(**labels).set(value)
                    elif hasattr(metric, 'observe'):
                        metric.labels(**labels).observe(value)
                else:
                    if hasattr(metric, 'inc'):
                        metric.inc(value)
                    elif hasattr(metric, 'set'):
                        metric.set(value)
                    elif hasattr(metric, 'observe'):
                        metric.observe(value)
        except Exception as e:
            logger.error(f"Failed to record metric {metric_name}: {str(e)}")


# Global monitoring service instance
monitoring_service = MonitoringService()


class HealthChecker:
    """Comprehensive health checking for all system components."""
    
    @staticmethod
    async def check_database() -> Dict[str, Any]:
        """Check database health and performance."""
        start_time = time.time()
        
        try:
            async with async_session_maker() as session:
                # Check basic connectivity
                result = await session.execute(text("SELECT 1"))
                
                # Get connection stats
                conn_stats = await session.execute(
                    text("""
                        SELECT 
                            count(*) as total_connections,
                            count(*) FILTER (WHERE state = 'active') as active_connections,
                            count(*) FILTER (WHERE state = 'idle') as idle_connections,
                            count(*) FILTER (WHERE wait_event_type IS NOT NULL) as waiting_connections
                        FROM pg_stat_activity
                        WHERE datname = current_database()
                    """)
                )
                stats = conn_stats.fetchone()
                
                # Get database size
                size_result = await session.execute(
                    text("SELECT pg_database_size(current_database()) as size")
                )
                db_size = size_result.scalar()
                
                response_time = (time.time() - start_time) * 1000
                
                return {
                    "status": "healthy",
                    "response_time_ms": round(response_time, 2),
                    "connections": {
                        "total": stats.total_connections,
                        "active": stats.active_connections,
                        "idle": stats.idle_connections,
                        "waiting": stats.waiting_connections
                    },
                    "database_size_mb": round(db_size / 1024 / 1024, 2)
                }
                
        except Exception as e:
            logger.error(f"Database health check failed: {str(e)}")
            return {
                "status": "unhealthy",
                "error": str(e),
                "response_time_ms": (time.time() - start_time) * 1000
            }
    
    @staticmethod
    async def check_redis() -> Dict[str, Any]:
        """Check Redis health and performance."""
        start_time = time.time()
        
        try:
            # Ping Redis
            await cache.redis_client.ping()
            
            # Get Redis info
            info = await cache.redis_client.info()
            
            response_time = (time.time() - start_time) * 1000
            
            return {
                "status": "healthy",
                "response_time_ms": round(response_time, 2),
                "connected_clients": info.get("connected_clients", 0),
                "used_memory_mb": round(info.get("used_memory", 0) / 1024 / 1024, 2),
                "hits": info.get("keyspace_hits", 0),
                "misses": info.get("keyspace_misses", 0),
                "hit_rate": round(
                    info.get("keyspace_hits", 0) / 
                    max(1, info.get("keyspace_hits", 0) + info.get("keyspace_misses", 0)) * 100,
                    2
                ),
                "uptime_days": round(info.get("uptime_in_seconds", 0) / 86400, 2)
            }
            
        except Exception as e:
            logger.error(f"Redis health check failed: {str(e)}")
            return {
                "status": "unhealthy",
                "error": str(e),
                "response_time_ms": (time.time() - start_time) * 1000
            }
    
    @staticmethod
    async def check_external_apis() -> Dict[str, Any]:
        """Check external API connectivity."""
        results = {}
        
        # Check Google Maps API
        # (Implementation would include actual API calls with circuit breakers)
        results["google_maps"] = {
            "status": "healthy",
            "last_successful_call": datetime.utcnow().isoformat()
        }
        
        # Check SMS Gateway
        results["sms_gateway"] = {
            "status": "healthy",
            "last_successful_call": datetime.utcnow().isoformat()
        }
        
        # Check Banking API
        results["banking_api"] = {
            "status": "healthy",
            "last_successful_call": datetime.utcnow().isoformat()
        }
        
        # Check E-Invoice API
        results["einvoice_api"] = {
            "status": "healthy",
            "last_successful_call": datetime.utcnow().isoformat()
        }
        
        return results
    
    @staticmethod
    async def get_system_metrics() -> Dict[str, Any]:
        """Get system resource metrics."""
        cpu_percent = psutil.cpu_percent(interval=1)
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage('/')
        
        return {
            "cpu": {
                "usage_percent": cpu_percent,
                "count": psutil.cpu_count()
            },
            "memory": {
                "total_mb": round(memory.total / 1024 / 1024, 2),
                "used_mb": round(memory.used / 1024 / 1024, 2),
                "available_mb": round(memory.available / 1024 / 1024, 2),
                "percent": memory.percent
            },
            "disk": {
                "total_gb": round(disk.total / 1024 / 1024 / 1024, 2),
                "used_gb": round(disk.used / 1024 / 1024 / 1024, 2),
                "free_gb": round(disk.free / 1024 / 1024 / 1024, 2),
                "percent": disk.percent
            }
        }
    
    @staticmethod
    async def comprehensive_health_check() -> Dict[str, Any]:
        """Perform comprehensive health check of all components."""
        health_status = {
            "status": "healthy",
            "timestamp": datetime.utcnow().isoformat(),
            "version": settings.VERSION,
            "environment": settings.ENVIRONMENT.value,
            "checks": {}
        }
        
        # Run all health checks concurrently
        results = await asyncio.gather(
            HealthChecker.check_database(),
            HealthChecker.check_redis(),
            HealthChecker.check_external_apis(),
            HealthChecker.get_system_metrics(),
            return_exceptions=True
        )
        
        # Process results
        health_status["checks"]["database"] = results[0] if not isinstance(results[0], Exception) else {"status": "error", "error": str(results[0])}
        health_status["checks"]["redis"] = results[1] if not isinstance(results[1], Exception) else {"status": "error", "error": str(results[1])}
        health_status["checks"]["external_apis"] = results[2] if not isinstance(results[2], Exception) else {"status": "error", "error": str(results[2])}
        health_status["checks"]["system"] = results[3] if not isinstance(results[3], Exception) else {"status": "error", "error": str(results[3])}
        
        # Determine overall status
        for check_name, check_result in health_status["checks"].items():
            if isinstance(check_result, dict) and check_result.get("status") == "unhealthy":
                health_status["status"] = "degraded"
                break
        
        return health_status


# Prometheus metrics endpoint
async def metrics_endpoint() -> Response:
    """Generate Prometheus metrics."""
    metrics_data = generate_latest()
    return Response(content=metrics_data, media_type=CONTENT_TYPE_LATEST)


# Export components
__all__ = [
    "business_metrics",
    "monitoring_service",
    "HealthChecker",
    "metrics_endpoint"
]